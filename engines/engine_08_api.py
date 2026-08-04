"""API для Engine #8: Цитатомёт."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_08_quotes import search_quotes
import sqlite3

DB_PATH = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")


def quotes_stats():
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute("""
        SELECT COUNT(*), ROUND(AVG(aphorism_score),1), MAX(aphorism_score),
               ROUND(AVG(char_length),1), COUNT(DISTINCT year)
        FROM lenin_quotes
    """).fetchone()
    conn.close()
    return {
        "total": row[0],
        "avg_score": row[1],
        "max_score": row[2],
        "avg_length": row[3],
        "years": row[4],
    }


def quotes_by_year(year: int):
    return search_quotes(year=year, limit=20)


def quotes_by_topic(topic: str):
    return search_quotes(topic=topic, limit=10)


def daily_quote():
    """Случайная топ-цитата."""
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT text, year, volume_id, aphorism_score FROM lenin_quotes ORDER BY RANDOM() LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return {"text": row[0], "year": row[1], "volume": row[2], "score": row[3]}
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--stats":
            print(json.dumps(quotes_stats(), indent=2, ensure_ascii=False))
        elif cmd == "--daily":
            print(json.dumps(daily_quote(), indent=2, ensure_ascii=False))
        elif cmd == "--year" and len(sys.argv) > 2:
            results = quotes_by_year(int(sys.argv[2]))
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            results = quotes_by_topic(cmd)
            print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(quotes_stats(), indent=2, ensure_ascii=False))
