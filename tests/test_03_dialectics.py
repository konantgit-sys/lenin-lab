"""
Tests for Engine #3: Диалектический парсер.
"""

import sys
import sqlite3
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_03_dialectics import (
    get_connection,
    get_dialectical_stats,
    count_pattern_matches,
    STRONG_OPPOSITION,
    SYNTHESIS_MARKERS,
    DIALECTICAL_PAIRS,
    NEGATION_AFFIRMATION,
)

DB_PATH = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")


def test_table_exists():
    """Таблица dialectical_triples создана."""
    conn = get_connection()
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dialectical_triples'"
    ).fetchone()
    conn.close()
    assert exists is not None, "Table dialectical_triples not found"
    print("✅ test_table_exists passed")


def test_triples_count():
    """Количество троек ≥ 15000."""
    stats = get_dialectical_stats()
    assert stats["total_triples"] >= 15000, (
        f"Expected ≥15000, got {stats['total_triples']}"
    )
    print(f"✅ test_triples_count passed ({stats['total_triples']} triples)")


def test_intra_and_inter():
    """Есть оба типа: внутри- и меж-параграфная диалектика."""
    stats = get_dialectical_stats()
    assert stats["intra_paragraph"] > 0, "No intra-paragraph triples"
    assert stats["inter_paragraph"] > 0, "No inter-paragraph triples"
    print(f"✅ test_intra_and_inter passed (intra={stats['intra_paragraph']}, inter={stats['inter_paragraph']})")


def test_synthesis_present():
    """Хотя бы 10% троек имеют синтез."""
    stats = get_dialectical_stats()
    pct = stats["with_synthesis"] / max(stats["total_triples"], 1) * 100
    assert pct >= 5, f"Only {pct:.1f}% have synthesis, expected ≥5%"
    print(f"✅ test_synthesis_present passed ({pct:.1f}%)")


def test_year_distribution():
    """Распределение по годам покрывает все периоды."""
    stats = get_dialectical_stats()
    years = stats["year_distribution"]
    assert len(years) >= 20, f"Only {len(years)} years covered"
    assert 1893 in years, "1893 missing"
    assert 1917 in years, "1917 missing"
    assert 1922 in years, "1922 missing"
    print(f"✅ test_year_distribution passed ({len(years)} years)")


def test_top_triples_score():
    """Топ-тройки имеют диалектический скор ≥ 18."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT dialectical_score FROM dialectical_triples ORDER BY dialectical_score DESC LIMIT 5"
    ).fetchall()
    conn.close()
    assert len(rows) >= 5, f"Only {len(rows)} top triples"
    scores = [r[0] for r in rows]
    assert max(scores) >= 18, f"Top score only {max(scores)}"
    print(f"✅ test_top_triples_score passed (top5: {scores})")


def test_pattern_markers_work():
    """Регулярные выражения ловят реальные тексты."""
    assert STRONG_OPPOSITION.search("Это верно, но есть нюанс")
    assert SYNTHESIS_MARKERS.search("Таким образом, мы приходим к выводу")
    assert DIALECTICAL_PAIRS.search("С одной стороны, это правда")
    assert NEGATION_AFFIRMATION.search("не теория, а практика")
    print("✅ test_pattern_markers_work passed")


def test_pattern_stats():
    """Статистика паттернов возвращает все 4 категории."""
    conn = get_connection()
    stats = count_pattern_matches(conn)
    conn.close()
    assert "strong_opposition" in stats
    assert "dialectical_pairs" in stats
    assert "negation_affirmation" in stats
    assert "synthesis_markers" in stats
    for key in stats:
        assert stats[key] > 0, f"{key} = 0"
    print("✅ test_pattern_stats passed")


if __name__ == "__main__":
    print("=" * 50)
    print("Engine #3: Dialectical Parser Tests")
    print("=" * 50)

    test_table_exists()
    test_triples_count()
    test_intra_and_inter()
    test_synthesis_present()
    test_year_distribution()
    test_top_triples_score()
    test_pattern_markers_work()
    test_pattern_stats()

    print("\n" + "=" * 50)
    print("✅ ALL 8 TESTS PASSED")
    print("=" * 50)
