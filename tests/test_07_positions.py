"""
Tests for Engine #7: 500 позиций Ленина.
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_07_positions import search_position, TOPICS, auto_keywords

DB_PATH = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")


def test_table_exists():
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='lenin_positions'"
    ).fetchone()
    conn.close()
    assert row is not None, "Table lenin_positions not found"
    print("✅ table lenin_positions exists")


def test_positions_count():
    conn = sqlite3.connect(str(DB_PATH))
    cnt = conn.execute("SELECT COUNT(*) FROM lenin_positions").fetchone()[0]
    topics = conn.execute("SELECT COUNT(DISTINCT topic) FROM lenin_positions").fetchone()[0]
    conn.close()
    assert cnt >= 1000, f"Expected ≥1000 positions, got {cnt}"
    assert topics >= 400, f"Expected ≥400 topics, got {topics}"
    print(f"✅ {topics} topics, {cnt} positions")


def test_search_known_topic():
    results = search_position("диктатура пролетариата")
    assert len(results) >= 1, f"No results for 'диктатура пролетариата': {results}"
    assert results[0]["rank"] == 1
    assert results[0]["topic"] == "диктатура пролетариата"
    assert len(results[0]["text"]) > 50
    print(f"✅ 'диктатура пролетариата': {len(results)} quotes, top={results[0]['year']}")


def test_search_multiple_topics():
    for topic in ["капитал", "революция", "партия", "социализм", "империализм", "демократия", "крестьянство", "нация"]:
        results = search_position(topic)
        assert len(results) >= 1, f"No results for '{topic}'"
        assert results[0]["text"], f"Empty text for '{topic}'"
    print("✅ all 8 core topics have results")


def test_position_structure():
    results = search_position("государство")
    r = results[0]
    for field in ["topic", "rank", "volume", "year", "text", "length", "score"]:
        assert field in r, f"Missing field '{field}'"
    assert isinstance(r["year"], int) or r["year"] is None
    assert r["rank"] in (1, 2, 3)
    print(f"✅ position structure valid: {list(r.keys())}")


def test_year_distribution():
    conn = sqlite3.connect(str(DB_PATH))
    year_1917 = conn.execute(
        "SELECT COUNT(*) FROM lenin_positions WHERE year=1917"
    ).fetchone()[0]
    conn.close()
    assert year_1917 > 100, f"Expected >100 for 1917, got {year_1917}"
    print(f"✅ 1917 has {year_1917} positions (top year)")


def test_topic_deduplication():
    results = search_position("революция")
    texts = [r["text"] for r in results]
    # Все тексты должны быть разными
    assert len(set(texts)) == len(texts), "Duplicate texts found"
    print(f"✅ no duplicate texts for 'революция': {len(results)} unique")


def test_auto_keywords():
    kws = auto_keywords("троцкизм")
    assert "троцкизм" in kws
    assert "троцкист" in kws
    print(f"✅ auto_keywords for 'троцкизм': {kws}")


if __name__ == "__main__":
    print("=" * 50)
    print("Engine #7: 500 Lenin Positions Tests")
    print("=" * 50)

    test_table_exists()
    test_positions_count()
    test_search_known_topic()
    test_search_multiple_topics()
    test_position_structure()
    test_year_distribution()
    test_topic_deduplication()
    test_auto_keywords()

    print("\n" + "=" * 50)
    print("✅ ALL 8 TESTS PASSED")
    print("=" * 50)
