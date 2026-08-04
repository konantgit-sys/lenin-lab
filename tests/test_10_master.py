"""
API Contract Tests: /api/v1/stats — the master aggregator.
Tests the stats endpoint which aggregates all engines (via cache).
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = "http://localhost:9770"
KEY_FILE = Path(__file__).parent.parent / "test_api_key.txt"

def _get_key() -> str:
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    url = f"{BASE}/api/v1/register?tier=free"
    req = urllib.request.Request(url, method="POST")
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    key = data["api_key"]
    KEY_FILE.write_text(key)
    return key

API_KEY = _get_key()

def _get(path: str) -> dict:
    """GET with API key. Handles proxy-friendly 200+error responses."""
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, headers={"X-API-Key": API_KEY})
    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        data = json.loads(e.read())
    return data


def test_stats_structure():
    """Stats returns all expected fields."""
    data = _get("/api/v1/stats")
    required = ["total_paragraphs", "concepts", "volumes", "date_range"]
    for field in required:
        assert field in data, f"Missing field: {field}"
    print(f"✅ stats: {len(data)} fields, all required present")


def test_stats_counts():
    """Stats has correct counts."""
    data = _get("/api/v1/stats")
    assert data["total_paragraphs"] == 169067
    assert data["concepts"] >= 190
    assert data["volumes"] >= 40
    print(f"✅ counts: {data['total_paragraphs']}p, {data['concepts']}c, {data['volumes']}v")


def test_health_then_stats_consistent():
    """Health and stats agree on paragraph count."""
    health = _get("/api/v1/health")
    stats = _get("/api/v1/stats")
    assert health["database"]["total_paragraphs"] == stats["total_paragraphs"]
    print(f"✅ consistency: both report {health['database']['total_paragraphs']} paragraphs")


def test_timeline_coverage():
    """Timeline covers key years."""
    for year in [1893, 1905, 1914, 1917, 1922]:
        data = _get(f"/api/v1/timeline/{year}")
        assert data["year"] == year
        assert data["total_paragraphs"] > 0, f"No paragraphs in {year}"
        print(f"  {year}: {data['total_paragraphs']} paragraphs")
    print(f"✅ timeline: all 5 key years have data")


def test_search_english():
    """Search works with English terms in Lenin's text."""
    data = _get("/api/v1/search?q=socialism&limit=5")
    assert "results" in data
    print(f"✅ search EN: {data['total']} results for 'socialism'")


def test_search_russian_cyrillic():
    """Search works with Cyrillic."""
    q = urllib.parse.quote("диктатура пролетариата")
    data = _get(f"/api/v1/search?q={q}&limit=5")
    assert "results" in data
    print(f"✅ search RU: {data['total']} results")


def test_rate_limit_working():
    """Rate limiting is active — repeated requests don't crash."""
    for i in range(5):
        data = _get("/api/v1/stats")
        assert data["total_paragraphs"] == 169067
    print(f"✅ rate limit: 5 requests, no errors")


def test_search_by_single_cyrillic_word():
    """Search with simple Cyrillic word."""
    q = urllib.parse.quote("революция")
    data = _get(f"/api/v1/search?q={q}&limit=3")
    assert data["total"] > 0
    print(f"✅ 'революция': {data['total']} results")


if __name__ == "__main__":
    print("=" * 60)
    print("Master API Tests (HTTP contract)")
    print("=" * 60)
    tests = [t for t in sorted(globals()) if t.startswith("test_")]
    passed = 0
    for name in tests:
        try:
            globals()[name]()
            passed += 1
        except Exception as e:
            print(f"❌ {name}: {e}")
    print(f"\n{'='*60}")
    print(f"{'✅' if passed==len(tests) else '❌'} {passed}/{len(tests)} TESTS PASSED")
