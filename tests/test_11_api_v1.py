"""
API Contract Tests: v1 endpoints via HTTP.
Tests all 15 API v1 endpoints through the running server.
Handles proxy-friendly 200+error responses.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helper import load_concept_cache, load_rhetoric_cache

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

def _get(path: str, expect_error: bool = False) -> dict:
    """GET with API key. Returns parsed JSON."""
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, headers={"X-API-Key": API_KEY})
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def _get_no_key(path: str) -> dict:
    """GET without API key — should return 200+error."""
    url = f"{BASE}{path}"
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def _has_error(data: dict, expected_code: int = None) -> bool:
    """Check if response has error:true."""
    is_err = data.get("error") is True
    if expected_code is not None:
        is_err = is_err and data.get("code") == expected_code
    return is_err


# ===== CORE API TESTS =====

def test_health_v2():
    """Health check returns DB stats."""
    data = _get("/api/v1/health")
    assert data["status"] == "ok", f"Status: {data['status']}"
    assert data["database"]["status"] == "ok"
    assert data["database"]["total_paragraphs"] == 169067
    assert data["database"]["year_range"]["from"] == 1893
    assert data["cache"]["concepts"] is True
    print(f"✅ health: {data['database']['total_paragraphs']} paragraphs, v={data['version']}")


def test_stats():
    """Stats endpoint."""
    data = _get("/api/v1/stats")
    assert data["total_paragraphs"] == 169067
    assert data["concepts"] >= 190
    assert "date_range" in data
    print(f"✅ stats: {data['total_paragraphs']} paragraphs, {data['concepts']} concepts")


def test_search_basic():
    """Basic search works."""
    q = urllib.parse.quote("революция")
    data = _get(f"/api/v1/search?q={q}&limit=5")
    assert data["total"] > 0, f"Zero results for 'революция'"
    assert len(data["results"]) <= 5
    for r in data["results"]:
        assert "snippet" in r
        assert "year" in r
    print(f"✅ search: {data['total']} results for 'революция'")


def test_search_with_year():
    """Search with year filter."""
    q = urllib.parse.quote("война")
    data = _get(f"/api/v1/search?q={q}&year=1917&limit=10")
    assert data["total"] > 0
    for r in data["results"]:
        assert r["year"] == 1917, f"Year mismatch: {r['year']}"
    print(f"✅ search+year: {data['total']} results for 'война' in 1917")


def test_timeline():
    """Timeline for a specific year."""
    data = _get("/api/v1/timeline/1917")
    assert data["year"] == 1917
    assert data["total_paragraphs"] > 30000
    assert len(data["top_volumes"]) > 0
    assert len(data["samples"]) == 3
    print(f"✅ timeline: {data['total_paragraphs']} paragraphs in 1917")


def test_quotes():
    """Quotes endpoint."""
    data = _get("/api/v1/quotes?n=5")
    assert data["count"] == 5
    assert len(data["quotes"]) == 5
    for q in data["quotes"]:
        assert len(q["text"]) >= 80
    print(f"✅ quotes: {data['count']} quotes")


def test_quotes_by_topic():
    """Quotes filtered by topic."""
    q = urllib.parse.quote("революция")
    data = _get(f"/api/v1/quotes?n=3&topic={q}")
    assert data["count"] > 0
    for qd in data["quotes"]:
        assert "революц" in qd["text"].lower(), f"No 'революц' in: {qd['text'][:50]}"
    print(f"✅ quotes+topic: {data['count']} revolution quotes")


def test_concepts():
    """Concepts endpoint returns nodes+links+clusters."""
    data = _get("/api/v1/concepts")
    assert "nodes" in data, f"Missing 'nodes': {list(data.keys())}"
    assert "links" in data
    assert "clusters" in data
    cache = load_concept_cache()
    # nodes is a list, stats.nodes is the count
    assert len(data["nodes"]) == cache["graph"]["nodes"], \
        f"Expected {cache['graph']['nodes']} nodes, got {len(data['nodes'])}"
    assert data["stats"]["clusters"] == cache["graph"]["clusters"]
    print(f"✅ concepts: {len(data['nodes'])} nodes, {data['stats']['clusters']} clusters")


def test_concept_detail():
    """Single concept detail."""
    # Need URL-encoded Cyrillic in path param for urllib
    q = urllib.parse.quote("революция")
    data = _get(f"/api/v1/concept/{q}?q={q}")
    assert data["concept"] == "революция"
    assert data["frequency"] > 1000
    assert len(data["top_connections"]) > 0
    print(f"✅ concept: {data['concept']} freq={data['frequency']}, connections={len(data['top_connections'])}")


def test_compare():
    """Year comparison."""
    data = _get("/api/v1/compare?y1=1917&y2=1905")
    assert data["year1"]["year"] == 1917
    assert data["year2"]["year"] == 1905
    # 1917=39727p, 1905=9429p, ratio=9429/39727=0.24
    assert data["ratio"] < 1.0, f"Expected ratio < 1, got {data['ratio']}"
    print(f"✅ compare: 1917({data['year1']['paragraphs']}) vs 1905({data['year2']['paragraphs']}), ratio={data['ratio']}")


def test_entropy():
    """Entropy endpoint returns data."""
    data = _get("/api/v1/entropy")
    assert len(data) > 0, "Empty entropy response"
    print(f"✅ entropy: {len(data)} keys")


def test_rhetoric():
    """Rhetoric matches cache."""
    data = _get("/api/v1/rhetoric")
    cache = load_rhetoric_cache()
    assert data["total_paragraphs"] == cache["total_paragraphs"]
    assert data["years_analyzed"] == cache["years_analyzed"]
    print(f"✅ rhetoric: {data['years_analyzed']} years analyzed")


def test_tomography():
    """Tomography endpoint."""
    data = _get("/api/v1/tomography?n=100")
    assert data["total_points"] == 100
    assert len(data["points"]) > 0
    print(f"✅ tomography: {len(data['points'])} points")


# ===== VALIDATION TESTS (proxy-friendly: 200 + error:true) =====

def test_search_empty_query():
    """Empty query returns 200 + error:true (proxy-friendly)."""
    data = _get("/api/v1/search?q=")
    assert _has_error(data, 400), f"Expected error:true code:400, got: {data}"
    print(f"✅ empty query → code={data['code']}: {data['detail'][:50]}")


def test_year_out_of_range():
    """Year 2000 returns 200 + error (proxy-friendly)."""
    data = _get("/api/v1/timeline/2000")
    assert _has_error(data, 400), f"Expected error, got: {data}"
    print(f"✅ year 2000 → code={data['code']}: {data['detail'][:50]}")


def test_same_years_compare():
    """Comparing same years returns error."""
    data = _get("/api/v1/compare?y1=1917&y2=1917")
    assert _has_error(data, 400), f"Expected error, got: {data}"
    print(f"✅ same years → code={data['code']}: {data['detail']}")


def test_fts5_special_chars_sanitized():
    """FTS5 operators are stripped."""
    data = _get("/api/v1/search?q=OR+AND+NOT+test")
    assert data["query"] == "test"
    print(f"✅ FTS5 sanitized: '{data['query']}' → {data['total']} results")


def test_fts5_injection_blocked():
    """FTS5 special chars sanitized."""
    encoded = urllib.parse.quote("test*^\"()")
    data = _get(f"/api/v1/search?q={encoded}")
    assert data["query"] == "test"
    print(f"✅ FTS5 injection: '{data['query']}' → {data['total']} results")


def test_empty_query_validation():
    """Empty query (just spaces) returns error."""
    data = _get("/api/v1/search?q=%20")
    assert _has_error(data), f"Expected error, got: {data}"
    print(f"✅ empty query (spaces) → blocked")


# ===== SECURITY TESTS =====

def test_no_key_blocked():
    """Request without API key returns 200 + error (proxy-friendly)."""
    data = _get_no_key("/api/v1/search?q=test")
    assert _has_error(data, 401), f"Expected 401 error, got: {data}"
    print(f"✅ no key → code={data['code']}")


def test_bad_key_blocked():
    """Bad API key returns 200 + error."""
    url = "http://localhost:9770/api/v1/search?q=test"
    req = urllib.request.Request(url, headers={"X-API-Key": "this-is-not-valid"})
    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        data = json.loads(e.read())
    assert _has_error(data, 403), f"Expected 403, got: {data}"
    print(f"✅ bad key → code={data['code']}")


if __name__ == "__main__":
    print("=" * 60)
    print("API v1 Contract Tests")
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
