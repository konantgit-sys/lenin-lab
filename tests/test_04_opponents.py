"""
Tests for Engine #4: Карта оппонентов.
"""

import sys
import sqlite3
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_04_opponents import (
    get_connection,
    get_opponent_stats,
    OPPONENTS,
    find_opponent_mentions,
    compute_opponent_stats,
    compute_co_mention_graph,
    find_disputes,
)


def test_table_exists():
    """Таблицы opponents, opponent_links, opponent_disputes созданы."""
    conn = get_connection()
    for table in ["opponents", "opponent_links", "opponent_disputes"]:
        exists = conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
        ).fetchone()
        assert exists is not None, f"Table {table} not found"
    conn.close()
    print("✅ test_table_exists passed")


def test_opponent_count():
    """Минимум 25 оппонентов."""
    stats = get_opponent_stats()
    assert stats["total_opponents"] >= 25, (
        f"Expected ≥25 opponents, got {stats['total_opponents']}"
    )
    print(f"✅ test_opponent_count passed ({stats['total_opponents']} opponents)")


def test_mention_count():
    """Минимум 5000 упоминаний."""
    stats = get_opponent_stats()
    assert stats["total_mentions"] >= 5000, (
        f"Expected ≥5000 mentions, got {stats['total_mentions']}"
    )
    print(f"✅ test_mention_count passed ({stats['total_mentions']} mentions)")


def test_disputes_present():
    """Минимум 500 активных споров."""
    stats = get_opponent_stats()
    assert stats["active_disputes"] >= 500, (
        f"Expected ≥500 disputes, got {stats['active_disputes']}"
    )
    print(f"✅ test_disputes_present passed ({stats['active_disputes']} disputes)")


def test_graph_edges():
    """Граф со-упоминаний имеет рёбра."""
    stats = get_opponent_stats()
    assert stats["graph_edges"] >= 30, (
        f"Expected ≥30 co-mention edges, got {stats['graph_edges']}"
    )
    print(f"✅ test_graph_edges passed ({stats['graph_edges']} edges)")


def test_key_opponents_found():
    """Ключевые оппоненты найдены."""
    conn = get_connection()
    keys = [row[0] for row in conn.execute("SELECT key FROM opponents").fetchall()]
    conn.close()
    required = ["каутский", "плеханов", "мартов", "троцкий", "струве", "бернштейн"]
    for r in required:
        assert r in keys, f"{r} not found in opponents"
    print("✅ test_key_opponents_found passed")


def test_camps_distribution():
    """Минимум 8 лагерей."""
    stats = get_opponent_stats()
    conn = get_connection()
    camps = set(row[0] for row in conn.execute("SELECT camp FROM opponents").fetchall())
    conn.close()
    assert len(camps) >= 8, f"Only {len(camps)} camps"
    print(f"✅ test_camps_distribution passed ({len(camps)} camps)")


def test_no_false_dan():
    """Дан не включает ложные срабатывания от 'данный'."""
    conn = get_connection()
    row = conn.execute(
        "SELECT total_mentions FROM opponents WHERE key='дан'"
    ).fetchone()
    conn.close()
    assert row is None or row[0] < 100, f"Дан has {row[0]} mentions — suspicious"
    print("✅ test_no_false_dan passed")


if __name__ == "__main__":
    print("=" * 50)
    print("Engine #4: Opponent Map Tests")
    print("=" * 50)

    test_table_exists()
    test_opponent_count()
    test_mention_count()
    test_disputes_present()
    test_graph_edges()
    test_key_opponents_found()
    test_camps_distribution()
    test_no_false_dan()

    print("\n" + "=" * 50)
    print("✅ ALL 8 TESTS PASSED")
    print("=" * 50)
