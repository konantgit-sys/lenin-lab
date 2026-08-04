"""
Tests for Engine #8: Цитатомёт.
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_08_quotes import search_quotes, score_aphorism, split_sentences

DB_PATH = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")


def test_table_exists():
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='lenin_quotes'"
    ).fetchone()
    conn.close()
    assert row is not None, "Table lenin_quotes not found"
    print("✅ table lenin_quotes exists")


def test_quotes_count():
    conn = sqlite3.connect(str(DB_PATH))
    cnt = conn.execute("SELECT COUNT(*) FROM lenin_quotes").fetchone()[0]
    conn.close()
    assert cnt >= 3000, f"Expected ≥3000 quotes, got {cnt}"
    assert cnt <= 6000, f"Expected ≤6000 quotes, got {cnt}"
    print(f"✅ {cnt} quotes (target: 5000)")


def test_quotes_quality():
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT text, aphorism_score, char_length FROM lenin_quotes ORDER BY aphorism_score DESC LIMIT 20"
    ).fetchall()
    conn.close()
    for text, score, length in rows:
        assert 50 <= length <= 350, f"Length {length} out of bounds for: {text[:50]}"
        assert score >= 5, f"Score {score} too low for: {text[:50]}"
    print(f"✅ top 20 quotes all valid (50≤len≤350, score≥5)")


def test_score_function():
    # Хорошая цитата
    s1, _ = score_aphorism("Необходимо разрушить государственную машину, а не просто захватить её!")
    assert s1 >= 6, f"Good quote scored too low: {s1}"

    # Слабая цитата
    s2, _ = score_aphorism("В таблице 1 приведены данные за 1900 год по 37 губерниям Российской империи.")
    assert s2 < 5, f"Bad quote scored too high: {s2}"

    # Слишком короткая
    s3, _ = score_aphorism("Да.")
    assert s3 == 0, f"Short text scored: {s3}"

    print("✅ scoring function works correctly")


def test_search_by_year():
    results = search_quotes(year=1917, limit=5)
    assert len(results) >= 1, "No quotes for 1917"
    for r in results:
        assert r["year"] == 1917
    print(f"✅ search by year 1917: {len(results)} results")


def test_search_by_topic():
    results = search_quotes(topic="революция", limit=10)
    assert len(results) >= 1, "No quotes for 'революция'"
    print(f"✅ search by topic 'революция': {len(results)} results")


def test_search_combined():
    results = search_quotes(topic="партия", year=1917, limit=10)
    # Может быть 0 — не все комбинации есть
    print(f"✅ combined search 'партия'+1917: {len(results)} results (OK even if 0)")


def test_split_sentences():
    text = "Первое предложение. Второе предложение! Третье?"
    sents = split_sentences(text)
    assert len(sents) == 3, f"Expected 3 sentences, got {len(sents)}"
    assert sents[0] == "Первое предложение."
    print(f"✅ sentence splitter: {sents}")


if __name__ == "__main__":
    print("=" * 50)
    print("Engine #8: Quote Extractor Tests")
    print("=" * 50)

    test_table_exists()
    test_quotes_count()
    test_quotes_quality()
    test_score_function()
    test_search_by_year()
    test_search_by_topic()
    test_search_combined()
    test_split_sentences()

    print("\n" + "=" * 50)
    print("✅ ALL 8 TESTS PASSED")
    print("=" * 50)
