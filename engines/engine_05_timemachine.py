"""
Engine #5: Машина времени
На вход: дата (год, месяц.год, или диапазон)
На выход: что писал Ленин в этот момент, контекст эпохи,
           активные темы, оппоненты, диалектика.
"""

import json
import sqlite3
from pathlib import Path
from collections import defaultdict

DB_PATH = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")

# Ключевые исторические события
HISTORICAL_CONTEXT = {
    1893: "Начало марксистского движения в России. Голод в Поволжье.",
    1894: "Полемика с народниками. «Что такое „друзья народа“».",
    1895: "Создание «Союза борьбы». Арест Ленина.",
    1896: "Стачка текстильщиков. Ленин в тюрьме.",
    1897: "Ссылка в Шушенское.",
    1898: "I съезд РСДРП. Ленин в ссылке.",
    1899: "Экономизм. «Развитие капитализма в России».",
    1900: "Запуск «Искры».",
    1901: "«Что делать?».",
    1902: "Организационные принципы партии.",
    1903: "II съезд РСДРП. Раскол.",
    1904: "Русско-японская война. «Шаг вперёд, два шага назад».",
    1905: "Первая русская революция. «Две тактики». III съезд.",
    1906: "Спад революции. I Дума. Стокгольмский съезд.",
    1907: "II Дума. Третьеиюньский переворот. V съезд.",
    1908: "Реакция. «Материализм и эмпириокритицизм».",
    1909: "«Вехи». Фракционная борьба.",
    1910: "Пленум ЦК. Попытка примирения.",
    1911: "Пражская конференция.",
    1912: "Ленский расстрел. «Правда». IV Дума.",
    1913: "Рост движения. Национальный вопрос.",
    1914: "Первая мировая. Краха II Интернационала.",
    1915: "Циммервальд. «Империализм...».",
    1916: "Кинталь. Циммервальдская левая.",
    1917: "Февраль → Апрельские тезисы → Октябрь. «Государство и революция».",
    1918: "Брестский мир. Гражданская война. Конституция РСФСР.",
    1919: "Коминтерн. VIII съезд. Пик гражданской войны.",
    1920: "Советско-польская война. II Конгресс Коминтерна. ГОЭЛРО.",
    1921: "Кронштадт. НЭП. X съезд — запрет фракций.",
    1922: "Образование СССР. Генуя. Болезнь Ленина.",
    1923: "Последние статьи: «О кооперации», «Лучше меньше, да лучше».",
}


def get_connection():
    return sqlite3.connect(str(DB_PATH))


def parse_date(date_str: str) -> tuple:
    date_str = date_str.strip()
    if "-" in date_str:
        parts = date_str.split("-")
        s = parse_date(parts[0])
        e = parse_date(parts[1])
        return ("range", s[1], s[2], e[1], e[2])

    if "." in date_str:
        parts = date_str.split(".")
        if len(parts) == 2:
            return ("month", int(parts[1]), int(parts[0]))
        elif len(parts) == 3:
            return ("day", int(parts[2]), int(parts[1]), int(parts[0]))
    return ("year", int(date_str), None)


def _year_clause(date_parsed):
    dt = date_parsed[0]
    if dt == "year":
        return f"year = {date_parsed[1]}", []
    elif dt == "month":
        return f"year = ?", [date_parsed[1]]
    elif dt == "range":
        return f"year BETWEEN ? AND ?", [date_parsed[1], date_parsed[3]]
    return "1=0", []


def get_paragraph_count(conn, dp) -> int:
    clause, params = _year_clause(dp)
    return conn.execute(
        f"SELECT COUNT(*) FROM paragraphs WHERE {clause}", params
    ).fetchone()[0]


def get_volume_list(conn, dp) -> list:
    clause, params = _year_clause(dp)
    rows = conn.execute(
        f"SELECT DISTINCT volume_id, COUNT(*) as cnt FROM paragraphs WHERE {clause} GROUP BY volume_id ORDER BY cnt DESC",
        params,
    ).fetchall()
    return [{"volume": r[0], "paragraphs": r[1]} for r in rows]


def get_top_concepts(conn, dp, limit=8) -> list:
    """Топ концептов через keyword-сопоставление с текстом."""
    # Ключевые концепты с поисковыми словами
    concept_keywords = {
        "капитал": ["капитал", "капитализм", "капиталистический", "капиталиста"],
        "пролетариат": ["пролетариат", "пролетарии", "пролетарский"],
        "революция": ["революци", "восстание", "переворот"],
        "диктатура пролетариата": ["диктатура пролетариата", "диктатуры пролетариата"],
        "социализм": ["социализм", "социалистический"],
        "крестьянство": ["крестьян", "крестьянин", "крестьянство"],
        "государство": ["государств", "государственн"],
        "демократия": ["демократ", "демократический", "демократическ"],
        "война": ["война", "войны", "войне"],
        "империализм": ["империализм", "империалистический", "империалист"],
        "партия": ["парти", "рсдрп", "ркп", "большевик"],
        "нация": ["национальн", "нация", "нации"],
        "буржуазия": ["буржуаз", "буржуа"],
        "советы": ["совет", "советы", "советов"],
        "диктатура": ["диктатур"],
        "класс": ["классов", "классовая", "класс"],
        "реформа": ["реформ", "реформист", "ревизионизм"],
        "террор": ["террор", "террорист"],
        "империалистская война": ["империалистская война", "империалистическая война"],
        "учредительное собрание": ["учредительное собрание", "учредиловк"],
    }

    clause, params = _year_clause(dp)
    # Выборочно: 5000 параграфов
    rows = conn.execute(
        f"SELECT text FROM paragraphs WHERE {clause} ORDER BY paragraph_index LIMIT 5000",
        params,
    ).fetchall()

    scores = defaultdict(int)
    for (text,) in rows:
        text_lower = text.lower()
        for concept, keywords in concept_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    scores[concept] += 1
                    break

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"concept": c, "mentions": n} for c, n in ranked[:limit]]


def get_active_opponents(conn, dp) -> list:
    """Активные оппоненты в период."""
    dt = dp[0]
    rows = conn.execute(
        "SELECT key, full_name, camp, total_mentions, years_active FROM opponents ORDER BY total_mentions DESC"
    ).fetchall()

    result = []
    for row in rows:
        key, name, camp, mentions, years_str = row
        try:
            ya_start, ya_end = years_str.split("–")
            ya_start, ya_end = int(ya_start), int(ya_end)
        except Exception:
            continue

        if dt == "year":
            if ya_start <= dp[1] <= ya_end:
                result.append({"key": key, "name": name, "camp": camp, "mentions": mentions})
        elif dt == "month":
            if ya_start <= dp[1] <= ya_end:
                result.append({"key": key, "name": name, "camp": camp, "mentions": mentions})
        elif dt == "range":
            if ya_start <= dp[3] and ya_end >= dp[1]:
                result.append({"key": key, "name": name, "camp": camp, "mentions": mentions})

    return result[:10]


def get_top_dialectic(conn, dp, limit=5) -> list:
    """Диалектические тройки за период."""
    clause, params = _year_clause(dp)
    try:
        rows = conn.execute(
            f"""SELECT thesis, antithesis, synthesis, dialectical_score
                FROM dialectical_triples
                WHERE {clause} AND thesis != '' AND antithesis != ''
                ORDER BY dialectical_score DESC LIMIT ?""",
            params + [limit],
        ).fetchall()

        return [
            {
                "thesis": r[0][:200] if r[0] else "",
                "antithesis": r[1][:200] if r[1] else "",
                "synthesis": r[2][:200] if r[2] else "",
                "score": r[3],
            }
            for r in rows
        ]
    except Exception:
        return []


def get_sample_paragraphs(conn, dp, count=5) -> list:
    """Репрезентативные параграфы."""
    clause, params = _year_clause(dp)
    rows = conn.execute(
        f"""SELECT id, volume_id, paragraph_index, text, year
            FROM paragraphs
            WHERE {clause} AND LENGTH(text) > 300
            ORDER BY LENGTH(text) DESC LIMIT ?""",
        params + [count],
    ).fetchall()

    return [
        {"id": r[0], "volume": r[1], "index": r[2], "year": r[4], "text": r[3][:400]}
        for r in rows
    ]


def run_timemachine(date_str: str) -> dict:
    dp = parse_date(date_str)
    conn = get_connection()

    try:
        dt = dp[0]

        if dt == "year":
            year_range = str(dp[1])
            context = HISTORICAL_CONTEXT.get(dp[1], "")
        elif dt == "range":
            year_range = f"{dp[1]}–{dp[3]}"
            context = " / ".join(
                HISTORICAL_CONTEXT.get(y, "")
                for y in range(dp[1], dp[3] + 1)
            )[:500]
        else:
            year_range = date_str
            context = HISTORICAL_CONTEXT.get(dp[1], "")

        return {
            "date": date_str,
            "date_type": dt,
            "year_range": year_range,
            "historical_context": context,
            "paragraph_count": get_paragraph_count(conn, dp),
            "volumes": get_volume_list(conn, dp),
            "top_concepts": get_top_concepts(conn, dp),
            "active_opponents": get_active_opponents(conn, dp),
            "dialectic_triads": get_top_dialectic(conn, dp),
            "sample_paragraphs": get_sample_paragraphs(conn, dp),
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    test_date = sys.argv[1] if len(sys.argv) > 1 else "1917"
    result = run_timemachine(test_date)
    print(json.dumps(result, indent=2, ensure_ascii=False))
