"""API для Engine #7: 500 позиций Ленина."""
import json
import sys
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("LENIN_DB", "/home/agent/data/projects/lenin-knowledge/lenin.db"))
sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_07_positions import search_position
import os


def list_topics():
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute("SELECT DISTINCT topic, COUNT(*) as cnt FROM lenin_positions GROUP BY topic ORDER BY topic").fetchall()
    conn.close()
    return [{"topic": r[0], "quotes": r[1]} for r in rows]


def topic_stats():
    conn = sqlite3.connect(str(DB_PATH))
    total_topics = conn.execute("SELECT COUNT(DISTINCT topic) FROM lenin_positions").fetchone()[0]
    total_positions = conn.execute("SELECT COUNT(*) FROM lenin_positions").fetchone()[0]
    year_range = conn.execute("SELECT MIN(year), MAX(year) FROM lenin_positions WHERE year IS NOT NULL").fetchone()
    conn.close()

    return {
        "topics": total_topics,
        "positions": total_positions,
        "year_range": f"{year_range[0]}–{year_range[1]}",
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--topics":
            print(json.dumps(list_topics(), indent=2, ensure_ascii=False))
        elif cmd == "--stats":
            print(json.dumps(topic_stats(), indent=2, ensure_ascii=False))
        else:
            # поиск по теме
            results = search_position(cmd)
            print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(topic_stats(), indent=2, ensure_ascii=False))
