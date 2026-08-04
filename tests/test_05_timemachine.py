"""
Tests for Engine #5: Машина времени.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_05_timemachine import run_timemachine, parse_date


def test_parse_year():
    r = parse_date("1917")
    assert r[0] == "year"
    assert r[1] == 1917
    print("✅ parse year 1917")


def test_parse_range():
    r = parse_date("1917-1918")
    assert r[0] == "range"
    assert r[1] == 1917
    assert r[3] == 1918
    print("✅ parse range 1917-1918")


def test_timemachine_1917():
    r = run_timemachine("1917")
    assert r["date_type"] == "year"
    assert r["paragraph_count"] >= 30000, f"Expected ≥30000, got {r['paragraph_count']}"
    assert len(r["top_concepts"]) >= 5, f"Expected ≥5 concepts"
    assert len(r["active_opponents"]) >= 3, f"Expected ≥3 opponents"
    assert len(r["sample_paragraphs"]) == 5
    assert len(r["historical_context"]) > 10
    assert len(r["volumes"]) >= 5
    print(f"✅ 1917: {r['paragraph_count']} параграфов, {len(r['volumes'])} томов, {len(r['top_concepts'])} концептов")


def test_timemachine_1905():
    r = run_timemachine("1905")
    assert r["paragraph_count"] >= 5000
    assert "революция" in [c["concept"] for c in r["top_concepts"]]
    print(f"✅ 1905: {r['paragraph_count']} параграфов")


def test_timemachine_range():
    r = run_timemachine("1917-1918")
    assert r["date_type"] == "range"
    assert r["paragraph_count"] >= 50000
    assert len(r["active_opponents"]) >= 5
    print(f"✅ 1917-1918: {r['paragraph_count']} параграфов")


def test_dialectic_present():
    r = run_timemachine("1917")
    assert len(r["dialectic_triads"]) >= 3, f"Expected ≥3 triads, got {len(r['dialectic_triads'])}"
    # Check structure
    t = r["dialectic_triads"][0]
    assert "thesis" in t
    assert "antithesis" in t
    print(f"✅ dialectic triads: {len(r['dialectic_triads'])} found")


def test_context_coverage():
    for year in [1893, 1905, 1914, 1917, 1921, 1923]:
        r = run_timemachine(str(year))
        assert r["historical_context"], f"No context for {year}"
    print("✅ all key years have context")


def test_volumes_sorted():
    r = run_timemachine("1917")
    vols = r["volumes"]
    for i in range(len(vols) - 1):
        assert vols[i]["paragraphs"] >= vols[i + 1]["paragraphs"], "Volumes not sorted by count"
    print("✅ volumes sorted by paragraph count")


if __name__ == "__main__":
    print("=" * 50)
    print("Engine #5: Time Machine Tests")
    print("=" * 50)

    test_parse_year()
    test_parse_range()
    test_timemachine_1917()
    test_timemachine_1905()
    test_timemachine_range()
    test_dialectic_present()
    test_context_coverage()
    test_volumes_sorted()

    print("\n" + "=" * 50)
    print("✅ ALL 8 TESTS PASSED")
    print("=" * 50)
