"""
Tests for Engine #9: Сравнительный анализатор.
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_09_comparative import search_comparison, list_comparisons, MARXIST_BASIS

DB_PATH = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")


def test_table_exists():
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='lenin_comparative'"
    ).fetchone()
    conn.close()
    assert row is not None, "Table lenin_comparative not found"
    print("✅ table lenin_comparative exists")


def test_comparison_count():
    conn = sqlite3.connect(str(DB_PATH))
    cnt = conn.execute("SELECT COUNT(*) FROM lenin_comparative").fetchone()[0]
    conn.close()
    assert cnt >= 50, f"Expected ≥50 comparisons, got {cnt}"
    print(f"✅ {cnt} comparisons")


def test_marxist_basis_loaded():
    assert len(MARXIST_BASIS) >= 60, f"Expected ≥60 basis topics, got {len(MARXIST_BASIS)}"
    for topic in ["капитал", "революция", "государство", "диктатура пролетариата", "социализм"]:
        assert topic in MARXIST_BASIS, f"Missing basis: {topic}"
        assert "marx" in MARXIST_BASIS[topic]
        assert "engels" in MARXIST_BASIS[topic]
        assert "source" in MARXIST_BASIS[topic]
    print(f"✅ {len(MARXIST_BASIS)} basis topics, key topics present")


def test_search_known_topic():
    for topic in ["диктатура пролетариата", "государство", "революция", "капитал"]:
        comp = search_comparison(topic)
        assert comp is not None, f"No comparison for '{topic}'"
        assert comp["marx"], f"Empty marx for '{topic}'"
        assert comp["engels"], f"Empty engels for '{topic}'"
        assert comp["lenin"], f"Empty lenin for '{topic}'"
        assert comp["evolution"], f"Empty evolution for '{topic}'"
        assert comp["source"], f"Empty source for '{topic}'"
    print("✅ 4 key comparisons all complete")


def test_comparison_structure():
    comp = search_comparison("революция")
    for field in ["topic", "marx", "engels", "lenin", "lenin_year", "lenin_volume", "evolution", "source"]:
        assert field in comp, f"Missing field: {field}"
    print(f"✅ comparison structure valid: {list(comp.keys())}")


def test_list_comparisons():
    comps = list_comparisons()
    assert len(comps) >= 50
    assert all("topic" in c for c in comps)
    topics = [c["topic"] for c in comps]
    assert "диктатура пролетариата" in topics
    assert "государство" in topics
    print(f"✅ list: {len(comps)} topics, key topics present")


def test_lenin_context_present():
    comp = search_comparison("диктатура пролетариата")
    assert comp["lenin_year"] is not None, "No Lenin year"
    assert comp["lenin_volume"] is not None, "No Lenin volume"
    assert len(comp["lenin"]) > 100, f"Lenin text too short: {len(comp['lenin'])}"
    print(f"✅ Lenin context: {comp['lenin_year']}, т.{comp['lenin_volume']}, {len(comp['lenin'])} chars")


def test_evolution_analysis():
    comp = search_comparison("диктатура пролетариата")
    assert "Развитие" in comp["evolution"] or "Ленин" in comp["evolution"]
    print(f"✅ evolution: {comp['evolution'][:80]}...")


if __name__ == "__main__":
    print("=" * 50)
    print("Engine #9: Comparative Analyzer Tests")
    print("=" * 50)

    test_table_exists()
    test_comparison_count()
    test_marxist_basis_loaded()
    test_search_known_topic()
    test_comparison_structure()
    test_list_comparisons()
    test_lenin_context_present()
    test_evolution_analysis()

    print("\n" + "=" * 50)
    print("✅ ALL 8 TESTS PASSED")
    print("=" * 50)
