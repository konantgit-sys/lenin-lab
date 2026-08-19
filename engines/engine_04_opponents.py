"""
Engine #4: Карта оппонентов
Извлекает всех ключевых оппонентов Ленина, строит карту:
- Кто, когда, о чём спор, аргументы
- Граф со-упоминаний оппонентов
- Хронология полемики

Охватывает ~40 оппонентов, ~7K+ параграфов с упоминаниями.
"""

import re
import sqlite3
import json
from pathlib import Path
from collections import defaultdict
import networkx as nx
import os

DB_PATH = Path(os.environ.get("LENIN_DB", "/home/agent/data/projects/lenin-knowledge/lenin.db"))

# 42 ОППОНЕНТА с вариациями имён
OPPONENTS = {
    # === МАРКСИСТЫ-РЕВИЗИОНИСТЫ ===
    "каутский": {
        "full_name": "Карл Каутский",
        "variants": ["каутский", "каутского", "каутскому", "каутским", "каутском",
                     "каутскианство", "каутскианского", "каутскианцы"],
        "camp": "центристы",
        "key_issues": ["диктатура пролетариата", "демократия", "империализм", "государство"],
    },
    "бернштейн": {
        "full_name": "Эдуард Бернштейн",
        "variants": ["бернштейн", "бернштейна", "бернштейну", "бернштейном",
                     "бернштейнианство", "бернштейнианцы", "бернштейнианского",
                     "ревизионизм", "ревизионисты"],
        "camp": "ревизионисты",
        "key_issues": ["ревизионизм", "реформы", "движение всё цель ничто", "кооперация"],
    },

    # === МЕНЬШЕВИКИ ===
    "мартов": {
        "full_name": "Юлий Мартов",
        "variants": ["мартов", "мартова", "мартову", "мартовым", "мартове"],
        "camp": "меньшевики",
        "key_issues": ["партийное строительство", "демократический централизм", "коалиция"],
    },
    "плеханов": {
        "full_name": "Георгий Плеханов",
        "variants": ["плеханов", "плеханова", "плеханову", "плехановым", "плеханове",
                     "плехановский", "плехановской", "плехановцы"],
        "camp": "меньшевики",
        "key_issues": ["диалектика", "материализм", "террор", "революция 1905"],
    },
    "аксельрод": {
        "full_name": "Павел Аксельрод",
        "variants": ["аксельрод", "аксельрода", "аксельроду", "аксельродом"],
        "camp": "меньшевики",
        "key_issues": ["партийное строительство", "рабочее движение", "съезд"],
    },
    "дан": {
        "full_name": "Фёдор Дан",
        "variants": ["ф. дан", " ф дан ", "фёдор дан", "федора дана",
                     "товарищ дан", "т. дан", "т.дана"],
        "camp": "меньшевики",
        "key_issues": ["коалиционное правительство", "советы", "война"],
    },
    "потресов": {
        "full_name": "Александр Потресов",
        "variants": ["потресов", "потресова", "потресову"],
        "camp": "меньшевики",
        "key_issues": ["ликвидаторство", "легальный марксизм"],
    },
    "череванин": {
        "full_name": "Фёдор Череванин",
        "variants": ["череванин", "череванина"],
        "camp": "меньшевики-ликвидаторы",
        "key_issues": ["ликвидаторство", "открытая партия"],
    },

    # === ЛЕГАЛЬНЫЕ МАРКСИСТЫ / ЛИБЕРАЛЫ ===
    "струве": {
        "full_name": "Пётр Струве",
        "variants": ["струве", "струвеизм", "струвизм", "струвистский"],
        "camp": "легальные марксисты",
        "key_issues": ["легальный марксизм", "капитализм в России", "нация"],
    },
    "туган-барановский": {
        "full_name": "Михаил Туган-Барановский",
        "variants": ["туган-барановский", "туган-барановского", "туган"],
        "camp": "легальные марксисты",
        "key_issues": ["кризисы", "рынки", "кооперация"],
    },
    "булгаков": {
        "full_name": "Сергей Булгаков",
        "variants": ["булгаков", "булгакова", "булгакову", "булгаковым",
                     "с. булгаков", "с. н. булгаков"],
        "camp": "легальные марксисты",
        "key_issues": ["аграрный вопрос", "капитализм", "философия"],
    },

    # === НАРОДНИКИ / ЭСЕРЫ ===
    "чернов": {
        "full_name": "Виктор Чернов",
        "variants": ["чернов", "чернова", "чернову"],
        "camp": "эсеры",
        "key_issues": ["аграрный вопрос", "социализация земли", "учредительное собрание"],
    },
    "михайловский": {
        "full_name": "Николай Михайловский",
        "variants": ["михайловский", "михайловского", "михайловскому",
                     "н. михайловский", "н. к. михайловский"],
        "camp": "народники",
        "key_issues": ["субъективная социология", "герои и толпа", "марксизм"],
    },
    "южаков": {
        "full_name": "Сергей Южаков",
        "variants": ["южаков", "южакова"],
        "camp": "народники",
        "key_issues": ["народничество", "община"],
    },
    "кривенко": {
        "full_name": "Сергей Кривенко",
        "variants": ["кривенко", "кривенко"],
        "camp": "народники",
        "key_issues": ["кустарная промышленность", "народничество"],
    },

    # === БОЛЬШЕВИКИ-ОППОЗИЦИОНЕРЫ ===
    "троцкий": {
        "full_name": "Лев Троцкий",
        "variants": ["троцкий", "троцкого", "троцкому", "троцким", "троцком",
                     "троцкизм", "троцкистский", "троцкисты"],
        "camp": "большевики-оппозиция",
        "key_issues": ["перманентная революция", "бюрократизм", "профсоюзы", "брестский мир"],
    },
    "бухарин": {
        "full_name": "Николай Бухарин",
        "variants": ["бухарин", "бухарина", "бухарину", "бухариным",
                     "бухаринский", "бухаринцы"],
        "camp": "большевики-оппозиция",
        "key_issues": ["империализм", "государственный капитализм", "нэп"],
    },
    "зиновьев": {
        "full_name": "Григорий Зиновьев",
        "variants": ["зиновьев", "зиновьева", "зиновьеву"],
        "camp": "большевики-оппозиция",
        "key_issues": ["коминтерн", "партийная дисциплина", "восстание"],
    },
    "каменев": {
        "full_name": "Лев Каменев",
        "variants": ["каменев", "каменева", "каменеву"],
        "camp": "большевики-оппозиция",
        "key_issues": ["октябрьское восстание", "коалиция", "советы"],
    },
    "шляпников": {
        "full_name": "Александр Шляпников",
        "variants": ["шляпников", "шляпникова"],
        "camp": "рабочая оппозиция",
        "key_issues": ["профсоюзы", "рабочий контроль", "партия"],
    },

    # === МЕЖДУНАРОДНЫЕ СОЦИАЛИСТЫ ===
    "люксембург": {
        "full_name": "Роза Люксембург",
        "variants": ["люксембург", "роза люксембург", "розы люксембург"],
        "camp": "левые социал-демократы",
        "key_issues": ["национальный вопрос", "накопление капитала", "партия"],
    },
    "паннекук": {
        "full_name": "Антон Паннекук",
        "variants": ["паннекук", "паннекука"],
        "camp": "левые коммунисты",
        "key_issues": ["массовая стачка", "парламентаризм", "советы"],
    },
    "гед": {
        "full_name": "Жюль Гед",
        "variants": ["гед", "геда", "гедовский"],
        "camp": "французские социалисты",
        "key_issues": ["парламентаризм", "война", "колониализм"],
    },

    # === АНАРХИСТЫ ===
    "бакунин": {
        "full_name": "Михаил Бакунин",
        "variants": ["бакунин", "бакунина", "бакунизм", "бакунистский"],
        "camp": "анархисты",
        "key_issues": ["государство", "диктатура пролетариата", "авторитет"],
    },
    "кропоткин": {
        "full_name": "Пётр Кропоткин",
        "variants": ["кропоткин", "кропоткина"],
        "camp": "анархисты",
        "key_issues": ["государство", "коммунизм", "взаимопомощь"],
    },

    # === БУРЖУАЗНЫЕ ДЕМОКРАТЫ ===
    "милюков": {
        "full_name": "Павел Милюков",
        "variants": ["милюков", "милюкова", "милюкову", "милюковым",
                     "кадет", "кадеты", "кадетов", "кадетский", "кадетской",
                     "к.-д.", "конституционные демократы"],
        "camp": "кадеты",
        "key_issues": ["конституционная монархия", "война до победного конца", "учредительное собрание"],
    },
    "керенский": {
        "full_name": "Александр Керенский",
        "variants": ["керенский", "керенского", "керенскому", "керенским"],
        "camp": "эсеры/временное правительство",
        "key_issues": ["временное правительство", "наступление", "корниловщина"],
    },

    # === ЭКОНОМИСТЫ / ОТЗОВИСТЫ / БОГОСТРОИТЕЛИ ===
    "богданов": {
        "full_name": "Александр Богданов",
        "variants": ["богданов", "богданова", "богданову", "богдановым",
                     "богдановский", "богдановщина", "эмпириомонизм"],
        "camp": "отзовисты",
        "key_issues": ["эмпириомонизм", "богостроительство", "отзовизм"],
    },
    "луначарский": {
        "full_name": "Анатолий Луначарский",
        "variants": ["луначарский", "луначарского", "луначарскому"],
        "camp": "богостроители",
        "key_issues": ["богостроительство", "культура", "пролеткульт"],
    },

    # === ПРОЧИЕ ===
    "маслоу": {
        "full_name": "Пётр Маслов",
        "variants": ["маслов", "маслова", "маслову"],
        "camp": "меньшевики",
        "key_issues": ["аграрный вопрос", "муниципализация земли"],
    },
    "мартынов": {
        "full_name": "Александр Мартынов",
        "variants": ["мартынов", "мартынова", "мартынову"],
        "camp": "экономисты",
        "key_issues": ["экономизм", "политическая борьба", "стихийность"],
    },
    "ларин": {
        "full_name": "Юрий Ларин",
        "variants": ["ларин", "ларина"],
        "camp": "меньшевики-ликвидаторы",
        "key_issues": ["ликвидаторство", "рабочий съезд"],
    },
    "суханов": {
        "full_name": "Николай Суханов",
        "variants": ["суханов", "суханова"],
        "camp": "меньшевики-интернационалисты",
        "key_issues": ["октябрь", "советы", "коалиция"],
    },

    # === МЕЖДУНАРОДНЫЕ ===
    "гильфердинг": {
        "full_name": "Рудольф Гильфердинг",
        "variants": ["гильфердинг", "гильфердинга"],
        "camp": "австромарксисты",
        "key_issues": ["финансовый капитал", "империализм", "организованный капитализм"],
    },
    "реннер": {
        "full_name": "Карл Реннер",
        "variants": ["реннер", "реннера", "шпрингер"],
        "camp": "австромарксисты",
        "key_issues": ["национальный вопрос", "культурная автономия"],
    },
    "бауэр": {
        "full_name": "Отто Бауэр",
        "variants": ["отто бауэр", "бауэр", "бауэра", "бауэру"],
        "camp": "австромарксисты",
        "key_issues": ["национальный вопрос", "культурно-национальная автономия"],
    },
    "шейдеман": {
        "full_name": "Филипп Шейдеман",
        "variants": ["шейдеман", "шейдемана", "шейдемановский"],
        "camp": "немецкие социал-демократы",
        "key_issues": ["социал-шовинизм", "война", "веймарская республика"],
    },
    "носке": {
        "full_name": "Густав Носке",
        "variants": ["носке"],
        "camp": "немецкие социал-демократы",
        "key_issues": ["контрреволюция", "советы", "рейхсвер"],
    },

    # === ИДЕОЛОГИЧЕСКИЕ ТЕЧЕНИЯ (не персоны, но оппоненты) ===
    "махизм": {
        "full_name": "Махизм (Эрнст Мах)",
        "variants": ["махизм", "махистский", "махисты", "эмпириокритицизм", "эмпириокритики",
                     "мах и", "мах.", "э. мах", "эрнст мах"],
        "camp": "философские ревизионисты",
        "key_issues": ["материализм", "эмпириокритицизм", "теория познания"],
    },
    "эсеры": {
        "full_name": "Партия социалистов-революционеров",
        "variants": ["эсеры", "эсеров", "эсерам", "эсеровский", "эсеровской",
                     "социалисты-революционеры", "с.-р.", "с.-ров"],
        "camp": "эсеры",
        "key_issues": ["террор", "аграрный вопрос", "учредительное собрание"],
    },
}


def get_connection():
    return sqlite3.connect(str(DB_PATH))


def find_opponent_mentions(conn):
    """Находит все параграфы с упоминаниями оппонентов."""
    opponent_mentions = defaultdict(list)

    for key, data in OPPONENTS.items():
        variants = data["variants"]
        # Build query with LIKE for each variant
        conditions = []
        params = []
        for v in variants:
            conditions.append("LOWER(text) LIKE ?")
            params.append(f"%{v.lower()}%")

        query = f"""
            SELECT id, volume_id, paragraph_index, text, year
            FROM paragraphs
            WHERE {' OR '.join(conditions)}
            LIMIT 5000
        """

        rows = conn.execute(query, params).fetchall()

        for row in rows:
            pid, vol, pidx, text, year = row
            opponent_mentions[key].append({
                "paragraph_id": pid,
                "volume_id": vol,
                "paragraph_index": pidx,
                "year": year,
                "text_preview": text[:400],
            })

    return opponent_mentions


def compute_opponent_stats(opponent_mentions):
    """Агрегирует статистику по каждому оппоненту."""
    stats = []

    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from engines.engine_02_concepts import CONCEPTS

    concept_patterns = {}
    for name, keywords in CONCEPTS.items():
        for kw in keywords[:2]:
            concept_patterns[kw.lower()] = name

    for key, mentions in opponent_mentions.items():
        data = OPPONENTS[key]

        years = [m["year"] for m in mentions if m["year"]]
        years_active = f"{min(years)}–{max(years)}" if years else "неизвестно"

        # Пик полемики
        year_counts = defaultdict(int)
        for y in years:
            year_counts[y] += 1
        peak_year = max(year_counts, key=year_counts.get) if year_counts else None

        # Темы (через концепты)
        topic_counts = defaultdict(int)
        for m in mentions:
            text_lower = m["text_preview"].lower()
            for pattern, concept_name in concept_patterns.items():
                if pattern in text_lower:
                    topic_counts[concept_name] += 1

        top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        top_topics = [{"topic": t, "mentions": c} for t, c in top_topics]

        stats.append({
            "key": key,
            "full_name": data["full_name"],
            "camp": data["camp"],
            "total_mentions": len(mentions),
            "years_active": years_active,
            "peak_year": peak_year,
            "year_distribution": dict(sorted(year_counts.items())),
            "top_topics": top_topics,
            "key_issues": data["key_issues"],
        })

    stats.sort(key=lambda x: x["total_mentions"], reverse=True)
    return stats


def compute_co_mention_graph(opponent_mentions):
    """Строит граф совместных упоминаний оппонентов."""
    G = nx.Graph()

    # Создаём обратный индекс: paragraph_id → [opponents]
    paragraph_opponents = defaultdict(set)
    for key, mentions in opponent_mentions.items():
        for m in mentions:
            paragraph_opponents[m["paragraph_id"]].add(key)

    # Рёбра: два оппонента в одном параграфе
    edge_weights = defaultdict(int)
    for opp_set in paragraph_opponents.values():
        opp_list = sorted(opp_set)
        for i in range(len(opp_list)):
            for j in range(i + 1, len(opp_list)):
                edge_weights[(opp_list[i], opp_list[j])] += 1

    for (a, b), weight in edge_weights.items():
        G.add_edge(a, b, weight=weight)

    for key in OPPONENTS:
        if key not in G:
            G.add_node(key)

    return G


def find_disputes(conn, opponent_mentions):
    """
    Находит активные споры: параграфы, где Ленин явно полемизирует
    с оппонентом (используя маркеры спора).
    """
    dispute_markers = [
        "возражает", "возражая", "возражение",
        "неверно", "неверно утверждает", "ошибается",
        "противоречит", "неправ", "не прав",
        "клевещет", "извращает", "фальсифицирует",
        "смешно", "нелепо", "вздор",
        "оппортунизм", "оппортунистический",
        "предательство", "предатель", "предал",
        "ренегат", "ренегатство",
        "ревизионист", "ревизионизм",
        "напрасно", "тщетно",
        "утверждает будто", "говорит будто",
        "уверяет", "уверяет что",
    ]

    disputes = []

    for key, mentions in opponent_mentions.items():
        disputable = []
        for m in mentions:
            text_lower = m["text_preview"].lower()
            markers_found = [dm for dm in dispute_markers if dm in text_lower]
            if markers_found:
                disputable.append({
                    "paragraph_id": m["paragraph_id"],
                    "volume_id": m["volume_id"],
                    "year": m["year"],
                    "markers": markers_found,
                    "text_preview": m["text_preview"][:300],
                })

        if disputable:
            # Сортируем по количеству маркеров (интенсивность спора)
            disputable.sort(key=lambda x: len(x["markers"]), reverse=True)
            disputes.append({
                "opponent_key": key,
                "opponent_name": OPPONENTS[key]["full_name"],
                "active_disputes": len(disputable),
                "top_disputes": disputable[:5],
            })

    disputes.sort(key=lambda x: x["active_disputes"], reverse=True)
    return disputes


def store_opponent_data(conn, stats, G, disputes):
    """Сохраняет все данные в БД."""
    # Таблица оппонентов
    conn.execute("""
        CREATE TABLE IF NOT EXISTS opponents (
            key TEXT PRIMARY KEY,
            full_name TEXT,
            camp TEXT,
            total_mentions INTEGER,
            years_active TEXT,
            peak_year INTEGER,
            year_distribution TEXT,
            top_topics TEXT,
            key_issues TEXT
        )
    """)
    conn.execute("DELETE FROM opponents")
    for s in stats:
        conn.execute("""
            INSERT INTO opponents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s["key"], s["full_name"], s["camp"], s["total_mentions"],
            s["years_active"], s["peak_year"],
            json.dumps(s["year_distribution"]),
            json.dumps(s["top_topics"]),
            json.dumps(s["key_issues"]),
        ))

    # Таблица со-упоминаний
    conn.execute("""
        CREATE TABLE IF NOT EXISTS opponent_links (
            opponent_a TEXT,
            opponent_b TEXT,
            weight INTEGER,
            PRIMARY KEY (opponent_a, opponent_b)
        )
    """)
    conn.execute("DELETE FROM opponent_links")
    for a, b, data in G.edges(data=True):
        conn.execute(
            "INSERT INTO opponent_links VALUES (?, ?, ?)",
            (a, b, data["weight"])
        )

    # Таблица споров
    conn.execute("""
        CREATE TABLE IF NOT EXISTS opponent_disputes (
            opponent_key TEXT,
            opponent_name TEXT,
            active_disputes INTEGER,
            top_disputes TEXT
        )
    """)
    conn.execute("DELETE FROM opponent_disputes")
    for d in disputes:
        conn.execute(
            "INSERT INTO opponent_disputes VALUES (?, ?, ?, ?)",
            (d["opponent_key"], d["opponent_name"], d["active_disputes"],
             json.dumps(d["top_disputes"], ensure_ascii=False))
        )

    conn.commit()


def run_opponent_map() -> dict:
    """Запускает полное построение карты оппонентов."""
    conn = get_connection()

    try:
        # Шаг 1: найти все упоминания
        opponent_mentions = find_opponent_mentions(conn)

        # Шаг 2: агрегировать статистику
        stats = compute_opponent_stats(opponent_mentions)

        # Шаг 3: граф со-упоминаний
        G = compute_co_mention_graph(opponent_mentions)

        # Шаг 4: найти активные споры
        disputes = find_disputes(conn, opponent_mentions)

        # Шаг 5: сохранить
        store_opponent_data(conn, stats, G, disputes)

        total_mentions = sum(s["total_mentions"] for s in stats)
        camps = defaultdict(list)
        for s in stats:
            camps[s["camp"]].append(s["full_name"])

        # Топ со-упоминаний
        top_edges = sorted(G.edges(data=True), key=lambda e: e[2]["weight"], reverse=True)[:10]

        return {
            "total_opponents": len(stats),
            "total_mentions": total_mentions,
            "total_co_mentions": sum(d["weight"] for _, _, d in G.edges(data=True)),
            "graph_nodes": G.number_of_nodes(),
            "graph_edges": G.number_of_edges(),
            "camps": {camp: len(names) for camp, names in camps.items()},
            "top_opponents": [
                {"name": s["full_name"], "camp": s["camp"], "mentions": s["total_mentions"],
                 "peak_year": s["peak_year"], "years": s["years_active"]}
                for s in stats[:10]
            ],
            "top_co_mentions": [
                {"pair": f"{OPPONENTS[a]['full_name']} ←→ {OPPONENTS[b]['full_name']}",
                 "weight": d["weight"]}
                for a, b, d in top_edges
            ],
            "top_disputes": [
                {"opponent": d["opponent_name"], "count": d["active_disputes"]}
                for d in disputes[:10]
            ],
        }
    finally:
        conn.close()


def get_opponent_stats() -> dict:
    """Возвращает статистику без перегенерации."""
    conn = get_connection()
    try:
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='opponents'"
        ).fetchone()

        if not exists:
            return {"status": "not_built", "total_opponents": 0}

        total = conn.execute("SELECT COUNT(*) FROM opponents").fetchone()[0]
        mentions = conn.execute("SELECT SUM(total_mentions) FROM opponents").fetchone()[0]
        edges = conn.execute("SELECT COUNT(*) FROM opponent_links").fetchone()[0]
        disputes_total = conn.execute("SELECT SUM(active_disputes) FROM opponent_disputes").fetchone()[0]

        top = conn.execute(
            "SELECT full_name, camp, total_mentions, peak_year FROM opponents ORDER BY total_mentions DESC LIMIT 5"
        ).fetchall()

        return {
            "status": "built",
            "total_opponents": total,
            "total_mentions": mentions,
            "graph_edges": edges,
            "active_disputes": disputes_total,
            "top_5": [{"name": r[0], "camp": r[1], "mentions": r[2], "peak": r[3]} for r in top],
        }
    finally:
        conn.close()


if __name__ == "__main__":
    result = run_opponent_map()
    print(json.dumps(result, indent=2, ensure_ascii=False))
