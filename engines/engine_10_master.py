"""
Engine #10: Master API — единый поисковый интерфейс.

Объединяет все 9 механик:
1. Хроно-разметка (engine_01_api)
2. Концептуальный граф (paragraphs-based)
3. Диалектический парсер (dialectical_triples)
4. Карта оппонентов (engine_04_api)
5. Машина времени (engine_05_api)
6. Риторический отпечаток (paragraphs-based)
7. 500 позиций Ленина (lenin_positions)
8. Цитатомёт (lenin_quotes)
9. Сравнительный анализатор (lenin_comparative)

master_search(query) -> результаты по всем механикам
master_stats() -> сводная статистика
master_timeline(year) -> полный портрет года
"""

import json
import sqlite3
import sys
import subprocess
from pathlib import Path

DB_PATH = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")
ENGINES_DIR = Path("/home/agent/data/sites/lenin-book/engines")


def get_connection():
    return sqlite3.connect(str(DB_PATH))


def run_api(api_file, *args):
    """Запускает API-скрипт и возвращает JSON."""
    try:
        result = subprocess.run(
            ["python3", str(ENGINES_DIR / api_file)] + list(args),
            capture_output=True, text=True, timeout=10, cwd=str(ENGINES_DIR.parent),
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def master_stats():
    """Сводная статистика по всем 9 механикам."""
    conn = get_connection()

    # E1: Chronology
    row = conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT year), MIN(year), MAX(year), COUNT(DISTINCT volume_id) FROM paragraphs WHERE year IS NOT NULL"
    ).fetchone()

    # E2: Concepts from paragraphs (top keywords mentioned)
    concepts = conn.execute(
        "SELECT COUNT(*) FROM paragraphs WHERE text LIKE '%капитал%' OR text LIKE '%пролетариат%' OR text LIKE '%буржуазия%' OR text LIKE '%революция%' OR text LIKE '%социализм%'"
    ).fetchone()[0]

    # E3: Dialectics
    triads = conn.execute("SELECT COUNT(*) FROM dialectical_triples").fetchone()[0]
    with_syn = conn.execute(
        "SELECT COUNT(*) FROM dialectical_triples WHERE synthesis IS NOT NULL AND synthesis != ''"
    ).fetchone()[0]

    # E4: Opponents
    opps = run_api("engine_04_api.py") or {}
    ops_total = conn.execute("SELECT COUNT(*) FROM opponents").fetchone()[0]
    mentions = conn.execute("SELECT SUM(total_mentions) FROM opponents").fetchone()[0]

    # E5: Time Machine
    tm = run_api("engine_05_api.py", "1917") or {}

    # E6: Rhetoric — paragraphs count
    paras_with_data = conn.execute(
        "SELECT COUNT(DISTINCT year) FROM paragraphs WHERE year IS NOT NULL"
    ).fetchone()[0]

    # E7: Positions
    pos_topics = conn.execute("SELECT COUNT(DISTINCT topic) FROM lenin_positions").fetchone()[0]
    pos_count = conn.execute("SELECT COUNT(*) FROM lenin_positions").fetchone()[0]

    # E8: Quotes
    q = conn.execute(
        "SELECT COUNT(*), ROUND(AVG(aphorism_score),1), MAX(aphorism_score) FROM lenin_quotes"
    ).fetchone()

    # E9: Comparative
    comp = conn.execute("SELECT COUNT(*) FROM lenin_comparative").fetchone()[0]

    conn.close()

    return {
        "total_engines": 9,
        "corpus_paragraphs": 169067,
        "corpus_chars": "48.5M",
        "db_size_mb": round(Path(DB_PATH).stat().st_size / 1024 / 1024, 1),
        "engines": {
            "1_chronology": {"paragraphs": row[0], "years": row[1], "range": f"{row[2]}-{row[3]}", "volumes": row[4]},
            "2_concepts": {"concept_paragraphs": concepts, "clusters": 8},
            "3_dialectics": {"triads": triads, "with_synthesis": with_syn, "synthesis_pct": round(100 * with_syn / max(triads, 1), 1)},
            "4_opponents": {"active": ops_total, "mentions": mentions or 0, "disputes": opps.get("active_disputes", 0)},
            "5_timemachine": {"contexts": 31, "formats": 4},
            "6_rhetoric": {"years_analyzed": paras_with_data, "categories": 5},
            "7_positions": {"topics": pos_topics, "quotes": pos_count, "categories": 14},
            "8_quotes": {"extracted": q[0], "avg_score": q[1], "max_score": q[2]},
            "9_comparative": {"topics": comp, "marxist_basis": 89},
        },
    }


def master_search(query: str):
    """Поиск по всем механикам."""
    results = {}
    conn = get_connection()
    q = f"%{query}%"

    # E1: Raw paragraphs
    results["paragraphs"] = [
        {"volume": r[0], "year": r[1], "text": r[2][:300]}
        for r in conn.execute(
            "SELECT volume_id, year, text FROM paragraphs WHERE text LIKE ? ORDER BY year LIMIT 5",
            (q,),
        ).fetchall()
    ]

    # E7: Positions
    results["positions"] = [
        {"topic": r[0], "year": r[1], "text": r[2][:250]}
        for r in conn.execute(
            "SELECT topic, year, text FROM lenin_positions WHERE topic LIKE ? OR text LIKE ? LIMIT 5",
            (q, q),
        ).fetchall()
    ]

    # E8: Quotes
    results["quotes"] = [
        {"year": r[0], "score": r[1], "text": r[2][:250]}
        for r in conn.execute(
            "SELECT year, aphorism_score, text FROM lenin_quotes WHERE text LIKE ? ORDER BY aphorism_score DESC LIMIT 5",
            (q,),
        ).fetchall()
    ]

    # E4: Opponents
    results["opponents"] = [
        {"name": r[0], "mentions": r[1]}
        for r in conn.execute(
            "SELECT full_name, total_mentions FROM opponents WHERE full_name LIKE ? OR camp LIKE ? ORDER BY total_mentions DESC LIMIT 5",
            (q, q),
        ).fetchall()
    ]

    # E9: Comparative
    results["comparative"] = [
        {"topic": r[0], "evolution": r[1][:200] if r[1] else ""}
        for r in conn.execute(
            "SELECT topic, evolution FROM lenin_comparative WHERE topic LIKE ? LIMIT 3",
            (q,),
        ).fetchall()
    ]

    # E3: Dialectical triples
    results["triads"] = [
        {"year": r[0], "pattern": r[1][:200] if r[1] else ""}
        for r in conn.execute(
            "SELECT year, thesis FROM dialectical_triples WHERE thesis LIKE ? OR antithesis LIKE ? LIMIT 3",
            (q, q),
        ).fetchall()
    ]

    conn.close()
    engines_hit = sum(1 for v in results.values() if v)
    return {"query": query, "engines_hit": engines_hit, "results": results}


def master_timeline(year: int):
    """Полный портрет года."""
    conn = get_connection()

    paras = conn.execute("SELECT COUNT(*) FROM paragraphs WHERE year = ?", (year,)).fetchone()[0]
    volumes = conn.execute(
        "SELECT DISTINCT volume_id FROM paragraphs WHERE year = ? ORDER BY volume_id", (year,)
    ).fetchall()
    pos_count = conn.execute("SELECT COUNT(*) FROM lenin_positions WHERE year = ?", (year,)).fetchone()[0]
    quote_count = conn.execute("SELECT COUNT(*) FROM lenin_quotes WHERE year = ?", (year,)).fetchone()[0]
    triads = conn.execute("SELECT COUNT(*) FROM dialectical_triples WHERE year = ?", (year,)).fetchone()[0]

    # Top quotes
    top_quotes = [
        {"score": r[1], "text": r[0][:200]}
        for r in conn.execute(
            "SELECT text, aphorism_score FROM lenin_quotes WHERE year = ? ORDER BY aphorism_score DESC LIMIT 3",
            (year,),
        ).fetchall()
    ]

    # Top positions
    top_positions = [
        {"topic": r[0], "text": r[1][:200]}
        for r in conn.execute(
            "SELECT topic, text FROM lenin_positions WHERE year = ? AND rank = 1 LIMIT 5",
            (year,),
        ).fetchall()
    ]

    conn.close()

    return {
        "year": year,
        "paragraphs": paras,
        "volumes": [v[0] for v in volumes],
        "positions": pos_count,
        "quotes": quote_count,
        "triads": triads,
        "top_quotes": top_quotes,
        "top_positions": top_positions,
    }


def master_engines_summary():
    """Краткая сводка для лендинга."""
    return {
        "engines": [
            {"id": 1, "name": "Хроно-разметка", "key": "169K параграфов, 55 томов, 3 периода"},
            {"id": 2, "name": "Концептуальный граф", "key": "206 концептов, 8 кластеров"},
            {"id": 3, "name": "Диалектический парсер", "key": "24 781 триада тезис→антитезис→синтез"},
            {"id": 4, "name": "Карта оппонентов", "key": "29 оппонентов, 9 262 упоминания"},
            {"id": 5, "name": "Машина времени", "key": "4 формата дат, 31 событие"},
            {"id": 6, "name": "Риторический отпечаток", "key": "5 осей, сарказм→агрессия"},
            {"id": 7, "name": "500 позиций Ленина", "key": "518 тем, 14 категорий"},
            {"id": 8, "name": "Цитатомёт", "key": "5 000 цитат, скор до 18"},
            {"id": 9, "name": "Сравнительный анализатор", "key": "62 темы: Маркс/Энгельс vs Ленин"},
        ]
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--stats":
            print(json.dumps(master_stats(), indent=2, ensure_ascii=False))
        elif cmd == "--summary":
            print(json.dumps(master_engines_summary(), indent=2, ensure_ascii=False))
        elif cmd == "--search" and len(sys.argv) > 2:
            print(json.dumps(master_search(sys.argv[2]), indent=2, ensure_ascii=False))
        elif cmd == "--timeline" and len(sys.argv) > 2:
            print(json.dumps(master_timeline(int(sys.argv[2])), indent=2, ensure_ascii=False))
        else:
            print(json.dumps(master_stats(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(master_engines_summary(), indent=2, ensure_ascii=False))
