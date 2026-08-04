#!/usr/bin/env python3
"""
Фаза 2.1 — Выборка и разметка для ручной валидации
Стратифицированная выборка 50 концептов из 8 кластеров.
Выводит таблицу для ручной проверки: концепт → кластер → топ-контексты → вердикт.
"""
import json, sqlite3, random, sys
from pathlib import Path
from collections import defaultdict

PROJECT = Path(__file__).parent.parent
random.seed(42)

# Загрузка кеша графа
with open(PROJECT / "concept_cache.json") as f:
    graph = json.load(f)["graph"]

nodes = graph["nodes_data"]
cn_list = graph["cluster_names"]  # list of 8 names

# Группируем по кластерам
by_cluster = defaultdict(list)
for n in nodes:
    by_cluster[n["cluster_name"]].append(n)

print("=" * 70)
print("ФАЗА 2.1: ВЫБОРКА 50 КОНЦЕПТОВ ДЛЯ РУЧНОЙ ВАЛИДАЦИИ")
print("=" * 70)

# Стратифицированная выборка: пропорционально размеру кластера
total_nodes = len(nodes)
sample_size = 50
samples = {}
for cname, cnodes in sorted(by_cluster.items()):
    n_take = max(1, round(len(cnodes) / total_nodes * sample_size))
    chosen = random.sample(cnodes, min(n_take, len(cnodes)))
    samples[cname] = chosen
    print(f"\nКластер [{cname}]: {len(cnodes)} → взято {len(chosen)}")

# Поправка: если меньше 50, докидываем из самых больших кластеров
actual = sum(len(v) for v in samples.values())
if actual < sample_size:
    deficit = sample_size - actual
    biggest = sorted(by_cluster.items(), key=lambda x: -len(x[1]))
    for cname, cnodes in biggest:
        if deficit <= 0:
            break
        already = {s["id"] for s in samples[cname]}
        pool = [n for n in cnodes if n["id"] not in already]
        extra = random.sample(pool, min(deficit, len(pool)))
        samples[cname].extend(extra)
        deficit -= len(extra)

print(f"\nВсего в выборке: {sum(len(v) for v in samples.values())}")

# Подключаем БД для топ-контекстов
db_paths = [
    Path("/home/agent/data/projects/lenin-knowledge/lenin.db"),
    Path("/home/agent/data/projects/lenin-knowledge/lenin.db"),
]
db = None
for p in db_paths:
    if p.exists():
        db = sqlite3.connect(str(p))
        break

# Функция: получить топ-5 параграфов для концепта
def get_top_contexts(concept_id, n=5):
    if db is None:
        return ["(БД недоступна)"]
    try:
        cur = db.cursor()
        # Ищем параграфы где часто встречается концепт
        forms = []
        for n_ in nodes:
            if n_["id"] == concept_id:
                forms = [concept_id]  # fallback
                break
        query = " OR ".join([f'text LIKE "%{w}%"' for w in forms])
        cur.execute(f"""
            SELECT paragraph_id, text, volume_id, year
            FROM paragraphs
            WHERE {query}
            ORDER BY length(content) DESC
            LIMIT {n}
        """)
        rows = cur.fetchall()
        return [f"[v{r[2]} {r[3]}] {r[1][:180]}..." for r in rows]
    except Exception as e:
        return [f"(ошибка: {e})"]

# Генерируем формуляр
output = []
output.append("# Аудиторский формуляр: Ручная валидация 50 концептов\n")
output.append(f"Дата: 2026-08-04")
output.append(f"Проверяющий: Антон / эксперт")
output.append(f"Метод: стратифицированная выборка, seed=42\n")
output.append("## Инструкция")
output.append("Для каждого концепта: прочитайте название, кластер и 5 контекстов.")
output.append("Поставьте ✓ если кластер верный, ✗ если нет, ? если сомневаетесь.")
output.append("В колонке «Замечание» можно указать правильный кластер.\n")
output.append("| # | Концепт | Кластер | Упоминаний | ✓/✗/? | Замечание |")
output.append("|---|---|---|---|---|---|")

i = 1
validation_data = []
for cname in sorted(samples.keys()):
    output.append(f"| | **{cname}** | | | | |")
    for n in sorted(samples[cname], key=lambda x: -x["count"]):
        contexts = get_top_contexts(n["id"])
        output.append(f"| {i} | **{n['id']}** | {cname} | {n['count']} | | |")
        for ctx in contexts[:2]:  # показываем 2 топа
            output.append(f"| | _{ctx}_ | | | | |")
        validation_data.append({
            "num": i,
            "concept": n["id"],
            "cluster": cname,
            "count": n["count"],
            "contexts": contexts
        })
        i += 1

form = "\n".join(output)

# Сохраняем
out_path = PROJECT / "validation_form_50_concepts.txt"
out_path.write_text(form, encoding="utf-8")
print(f"\n✅ Формуляр сохранён: {out_path}")

# Также JSON для машинной обработки
json_path = PROJECT / "validation_data_50.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(validation_data, f, ensure_ascii=False, indent=2)
print(f"✅ JSON: {json_path}")

# Статистика по кластерам
print("\n--- СТАТИСТИКА ВЫБОРКИ ---")
for cname in sorted(samples.keys()):
    ns = samples[cname]
    total_mentions = sum(n["count"] for n in ns)
    print(f"  {cname}: {len(ns)} концептов, {total_mentions} упоминаний, "
          f"топ: {ns[0]['id']} ({ns[0]['count']})")

print(f"\nИТОГО: {sum(len(v) for v in samples.values())} концептов")
print(f"Формуляр готов к ручной разметке.")
