#!/usr/bin/env python3
"""
Фаза 2.2 — A/B тест: Граф концептов vs FTS-поиск
10 исследовательских задач. Замеряем время, релевантность, полноту.
"""
import json, sqlite3, time, sys
from pathlib import Path

PROJECT = Path(__file__).parent.parent

# Загрузка кеша
with open(PROJECT / "concept_cache.json") as f:
    graph = json.load(f)["graph"]

nodes_data = graph["nodes_data"]
edges = graph["top_edges"]

# Индексы для быстрого поиска
node_by_id = {n["id"]: n for n in nodes_data}
adjacency = {}
for e in edges:
    s, t, w = e["source"], e["target"], e["weight"]
    adjacency.setdefault(s, []).append((t, w))
    adjacency.setdefault(t, []).append((s, w))

# Подключаем БД
db_paths = [Path("/home/agent/data/projects/lenin-knowledge/lenin.db"), Path("/home/agent/data/projects/lenin-knowledge/lenin.db")]
db = None
for p in db_paths:
    if p.exists():
        db = sqlite3.connect(str(p))
        break

# ====== МЕТОД A: ГРАФ КОНЦЕПТОВ ======
def graph_search(task_concepts, top_n=10):
    """Найти связанные концепты через граф"""
    t0 = time.time()
    found = set()
    for c in task_concepts:
        if c in adjacency:
            neighbors = sorted(adjacency[c], key=lambda x: -x[1])[:top_n]
            for nb, w in neighbors:
                found.add((nb, w))
    # Сортируем по весу
    result = sorted(found, key=lambda x: -x[1])[:top_n]
    elapsed = time.time() - t0

    # Получаем контексты для топ-3
    contexts = []
    for nb, w in result[:3]:
        ctx = get_paragraphs_for_concept(nb, limit=2)
        contexts.append({"concept": nb, "weight": w, "contexts": ctx})

    return {
        "method": "GRAPH",
        "time_ms": round(elapsed * 1000),
        "related_concepts": [{"concept": r[0], "weight": r[1]} for r in result],
        "top_contexts": contexts
    }

# ====== МЕТОД B: FTS5 ПОЛНОТЕКСТОВЫЙ ПОИСК ======
def fts_search(query_terms, top_n=10):
    """Полнотекстовый поиск по корпусу"""
    t0 = time.time()
    if db is None:
        return {"method": "FTS", "time_ms": 0, "error": "БД недоступна"}

    cur = db.cursor()
    fts_query = " OR ".join(query_terms)
    try:
        cur.execute("""
            SELECT id, text, volume_id, year,
                   snippet(paragraphs_fts, 2, '<b>', '</b>', '...', 32) as snip
            FROM paragraphs_fts
            WHERE paragraphs_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, top_n))
        rows = cur.fetchall()
    except Exception as e:
        # Fallback: LIKE поиск
        like_clause = " OR ".join([f'text LIKE "%{t}%"' for t in query_terms[:5]])
        cur.execute(f"""
            SELECT id, text, volume_id, year
            FROM paragraphs
            WHERE {like_clause}
            ORDER BY length(text) DESC
            LIMIT {top_n}
        """)
        rows = cur.fetchall()

    elapsed = time.time() - t0
    results = []
    for r in rows:
        if len(r) >= 3:
            results.append({
                "para_id": r[0],
                "text": (r[1][:200] + "...") if len(r[1]) > 200 else r[1],
                "volume_id": r[2] if len(r) > 2 else "?",
                "year": r[3] if len(r) > 3 else "?"
            })

    return {
        "method": "FTS",
        "time_ms": round(elapsed * 1000),
        "total_hits": len(results),
        "results": results
    }

def get_paragraphs_for_concept(concept_id, limit=3):
    """Получить параграфы содержащие концепт"""
    if db is None:
        return []
    cur = db.cursor()
    cur.execute("""
        SELECT id, text, volume_id, year
        FROM paragraphs
        WHERE text LIKE ?
        ORDER BY length(text) DESC
        LIMIT ?
    """, (f"%{concept_id}%", limit))
    rows = cur.fetchall()
    return [f"[v{r[2]} {r[3]}] {r[1][:150]}..." for r in rows]

# ====== 10 ИССЛЕДОВАТЕЛЬСКИХ ЗАДАЧ ======
TASKS = [
    {
        "id": 1,
        "question": "Найди связь между концепцией империализма и аграрным вопросом",
        "graph_concepts": ["империализм", "капитализм", "рента", "крестьянство"],
        "fts_terms": ["империализм", "аграрный", "земельный", "крестьянство"],
        "expected_connection": "Ленин связывал империализм с концентрацией земли и аграрным капитализмом"
    },
    {
        "id": 2,
        "question": "Какие экономические термины Ленин использовал чаще в 1917 vs 1905?",
        "graph_concepts": ["капитализм", "монополия", "кризис", "банк"],
        "fts_terms": ["капитализм", "монополия", "кризис", "банк", "1917"],
        "expected_connection": "В 1917 чаще экономические термины связаны с войной и разрухой"
    },
    {
        "id": 3,
        "question": "С какими оппонентами Ленин спорил о диктатуре пролетариата?",
        "graph_concepts": ["диктатура пролетариата", "демократия", "государство"],
        "fts_terms": ["диктатура пролетариата", "Каутский", "Бернштейн", "меньшевики"],
        "expected_connection": "Каутский, Бернштейн, меньшевики — главные оппоненты"
    },
    {
        "id": 4,
        "question": "Покажи эволюцию термина 'госкапитализм' от 1918 к 1923",
        "graph_concepts": ["капитализм", "государство", "монополия"],
        "fts_terms": ["госкапитализм", "государственный капитализм", "1918", "1921", "1923"],
        "expected_connection": "От военного коммунизма к НЭПу — эволюция отношения к госкапитализму"
    },
    {
        "id": 5,
        "question": "Как связаны понятия 'революция' и 'государство' в работах Ленина?",
        "graph_concepts": ["революция", "государство", "диктатура пролетариата"],
        "fts_terms": ["революция", "государство", "слом государственной машины"],
        "expected_connection": "Революция = слом буржуазного государства + диктатура пролетариата"
    },
    {
        "id": 6,
        "question": "Какие философские концепты чаще всего пересекаются с политическими?",
        "graph_concepts": ["диалектика", "материализм", "практика", "революция"],
        "fts_terms": ["диалектика", "материализм", "практика", "революция"],
        "expected_connection": "Диалектический материализм → практика революционной борьбы"
    },
    {
        "id": 7,
        "question": "Найди все упоминания 'демократического централизма' в контексте партийной организации",
        "graph_concepts": ["централизм", "партия", "фракция"],
        "fts_terms": ["демократический централизм", "партия", "фракция", "дисциплина"],
        "expected_connection": "Демократический централизм — стержень партийной организации"
    },
    {
        "id": 8,
        "question": "Какие концепты образуют мост между 'империализмом' и 'социалистической революцией'?",
        "graph_concepts": ["империализм", "социалистическая революция", "мировая война", "кризис"],
        "fts_terms": ["империализм", "социалистическая революция", "слабое звено"],
        "expected_connection": "Империализм → война → кризис → слабое звено → социалистическая революция"
    },
    {
        "id": 9,
        "question": "Как меняется употребление термина 'демократия' в контексте классов?",
        "graph_concepts": ["демократия", "диктатура пролетариата", "буржуазия"],
        "fts_terms": ["демократия", "буржуазная демократия", "пролетарская демократия"],
        "expected_connection": "Ленин различал буржуазную (формальную) и пролетарскую (реальную) демократию"
    },
    {
        "id": 10,
        "question": "Существует ли 'теневая связь' между 'террором' и 'бюрократизмом'?",
        "graph_concepts": ["террор", "бюрократизм", "государство", "аппарат"],
        "fts_terms": ["террор", "бюрократизм", "аппарат", "государство"],
        "expected_connection": "Террор и бюрократизм — две стороны отчуждения государства от масс"
    },
]

# ====== ЗАПУСК ТЕСТОВ ======
print("=" * 70)
print("ФАЗА 2.2: A/B ТЕСТ — ГРАФ КОНЦЕПТОВ vs FTS-ПОИСК")
print("=" * 70)

results = []
for task in TASKS:
    print(f"\n{'─'*60}")
    print(f"Задача #{task['id']}: {task['question']}")
    print(f"Ожидаемая связь: {task['expected_connection']}")

    graph_result = graph_search(task["graph_concepts"])
    fts_result = fts_search(task["fts_terms"])

    print(f"  GRAPH: {graph_result['time_ms']}ms, {len(graph_result['related_concepts'])} связанных концептов")
    for rc in graph_result['related_concepts'][:5]:
        print(f"    → {rc['concept']} (weight: {rc['weight']})")

    print(f"  FTS:   {fts_result['time_ms']}ms, {fts_result.get('total_hits', '?')} результатов")
    if fts_result.get("results"):
        for r in fts_result["results"][:3]:
            print(f"    → [v{r['volume_id']} {r['year']}] {r['text'][:100]}...")

    results.append({
        "task_id": task["id"],
        "question": task["question"],
        "expected": task["expected_connection"],
        "graph": graph_result,
        "fts": fts_result,
        "graph_winner": None  # заполняется экспертом
    })

# Сохраняем
out_path = PROJECT / "ab_test_results.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# Сводка
print(f"\n{'='*70}")
print("СВОДКА A/B ТЕСТА")
print(f"{'='*70}")
print(f"{'#':>3} {'Задача':<45} {'GRAPH':>8} {'FTS':>8} {'Победитель'}")
print(f"{'─'*3} {'─'*45} {'─'*8} {'─'*8} {'─'*15}")
for r in results:
    g_time = r["graph"]["time_ms"]
    f_time = r["fts"]["time_ms"]
    g_hits = len(r["graph"]["related_concepts"])
    f_hits = r["fts"].get("total_hits", 0)
    winner = "GRAPH" if g_time < f_time else "FTS"
    print(f"{r['task_id']:>3} {r['question'][:43]:<45} {g_time:>4}ms{g_hits:>3}c {f_time:>4}ms{f_hits:>3}h {winner:>15}")

print(f"\n✅ Результаты сохранены: {out_path}")
print(f"⚠️  Финальный вердикт (graph_winner) заполняется экспертом.")

# Считаем предварительное преимущество
g_faster = sum(1 for r in results if r["graph"]["time_ms"] < r["fts"]["time_ms"])
f_faster = sum(1 for r in results if r["fts"]["time_ms"] < r["graph"]["time_ms"])
print(f"\nПредварительно (по скорости): GRAPH быстрее в {g_faster}/10, FTS быстрее в {f_faster}/10")
