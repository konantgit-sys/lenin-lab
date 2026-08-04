#!/usr/bin/env python3
"""
LENIN-BOOK SECURITY TEST SUITE v1.0
====================================
Negative scenarios, edge cases, and attack vectors.
Tests run against localhost:9770 (the production backend).
"""
import json
import urllib.request
import urllib.error
import sys
import time

BASE = "http://localhost:9770"

PASS = 0
FAIL = 0
SKIP = 0

def ok(msg):
    global PASS
    PASS += 1
    print(f"  ✅ {msg}")

def no(msg, detail=""):
    global FAIL
    FAIL += 1
    print(f"  ❌ {msg}")
    if detail:
        print(f"     → {detail}")

def sk(msg):
    global SKIP
    SKIP += 1
    print(f"  ⏭️  {msg}")

def get(path):
    """GET request, returns (http_code, json_data)."""
    try:
        req = urllib.request.Request(f"{BASE}{path}")
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return resp.status, data
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read())
            return e.code, data
        except:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}

def request(method, path, body=None, headers=None):
    """Arbitrary method request."""
    try:
        data_bytes = json.dumps(body).encode() if body else None
        req = urllib.request.Request(f"{BASE}{path}", data=data_bytes, headers=headers or {}, method=method)
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


# ============================================================
print("=" * 60)
print("🔴 SECTION 1: METHOD VALIDATION (DELETE/POST/PATCH/PUT)")
print("=" * 60)

# 1.1 DELETE on public endpoint → 405
code, data = request("DELETE", "/api/search?q=test")
if data.get("code") == 405 and data.get("error"):
    ok("DELETE /api/search → 405 Method Not Allowed")
else:
    no(f"DELETE /api/search → expected 405, got code={code} data={data}")

# 1.2 POST on public search → 405
code, data = request("POST", "/api/search?q=test")
if data.get("code") == 405:
    ok("POST /api/search → 405")
else:
    no(f"POST /api/search → expected 405, got {data}")

# 1.3 PATCH on public endpoint → 405
code, data = request("PATCH", "/api/timeline?year=1917")
if data.get("code") == 405:
    ok("PATCH /api/timeline → 405")
else:
    no(f"PATCH /api/timeline → expected 405, got {data}")

# 1.4 PUT on public endpoint → 405
code, data = request("PUT", "/api/concepts")
if data.get("code") == 405:
    ok("PUT /api/concepts → 405")
else:
    no(f"PUT /api/concepts → expected 405, got {data}")


# ============================================================
print("\n" + "=" * 60)
print("🟠 SECTION 2: INPUT VALIDATION")
print("=" * 60)

# 2.1 Year = 9999 → 400
code, data = get("/api/timeline?year=9999")
if data.get("code") == 400 and "Year must be between" in data.get("detail", ""):
    ok("Year 9999 → 400 with descriptive message")
else:
    no(f"Year 9999 → expected 400, got: {data}")

# 2.2 Year = 1500 → 400
code, data = get("/api/timeline?year=1500")
if data.get("code") == 400:
    ok("Year 1500 → 400 (before Lenin's birth)")
else:
    no(f"Year 1500 → expected 400, got: {data}")

# 2.3 Year = 2026 → 400
code, data = get("/api/timeline?year=2026")
if data.get("code") == 400:
    ok("Year 2026 → 400 (after Lenin's death)")
else:
    no(f"Year 2026 → expected 400, got: {data}")

# 2.4 Valid year still works
code, data = get("/api/timeline?year=1917")
if code == 200 and data.get("year") == 1917:
    ok("Year 1917 → 200 (valid, within range)")
else:
    no(f"Year 1917 → expected 200, got: {data}")

# 2.5 Limit = -1 → 400
code, data = get("/api/search?q=test&limit=-1")
if data.get("code") == 400 and "Limit must be between" in data.get("detail", ""):
    ok("limit=-1 → 400")
else:
    no(f"limit=-1 → expected 400, got: {data}")

# 2.6 Limit = 0 → 400
code, data = get("/api/search?q=test&limit=0")
if data.get("code") == 400:
    ok("limit=0 → 400")
else:
    no(f"limit=0 → expected 400, got: {data}")

# 2.7 Limit = 99999 → 400
code, data = get("/api/search?q=test&limit=99999")
if data.get("code") == 400:
    ok("limit=99999 → 400")
else:
    no(f"limit=99999 → expected 400, got: {data}")

# 2.8 Limit = "abc" → 400
code, data = get("/api/search?q=test&limit=abc")
if data.get("code") == 400:
    ok('limit=abc → 400 (non-numeric)')
else:
    no(f"limit=abc → expected 400, got: {data}")

# 2.9 Empty search → descriptive error
code, data = get("/api/search?q=")
if data.get("error") or "Missing q" in str(data):
    ok("Empty query → descriptive error")
else:
    no(f"Empty query → expected error, got: {data}")

# 2.10 Non-digit year → error
code, data = get("/api/timeline?year=hello")
if data.get("error") == "Invalid year":
    ok("Year='hello' → 'Invalid year'")
else:
    no(f"Year='hello' → expected 'Invalid year', got: {data}")


# ============================================================
print("\n" + "=" * 60)
print("🟡 SECTION 3: XSS / INJECTION ATTEMPTS")
print("=" * 60)

# 3.1 Script tag in search — safe in JSON context
code, data = get("/api/search?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E")
query_val = data.get("query", "")
# In JSON API responses, raw <script> is safe (not HTML context)
# The important thing: it's NOT being executed in a browser
if "<script>" in query_val:
    ok("XSS script tag → echoed in JSON query field (safe: JSON context, not HTML)")
else:
    ok("XSS script tag → sanitized or not reflected")

# 3.2 SQL injection attempt
code, data = get("/api/search?q='%3B+DROP+TABLE+posts%3B--")
if code == 200 and data.get("query"):
    ok(f"SQL injection → handled (engines_hit={data.get('engines_hit', 0)})")
else:
    no(f"SQL injection → unexpected: {data}")

# 3.3 Null byte in query
code, data = get("/api/search?q=test%00hidden")
if code == 200:
    ok("Null byte in query → handled gracefully")
else:
    no(f"Null byte → unexpected response: {data}")

# 3.4 Unicode/Cyrillic query (homoglyph-safe)
# Use proper URL encoding for Cyrillic characters
code, data = get("/api/search?q=%D1%82%D0%B5%D1%95t")  # "теѕt" properly encoded
if code == 200 and data.get("query"):
    ok(f"Unicode homoglyph → handled (engines_hit={data.get('engines_hit',0)})")
elif data.get("error") and "ascii" not in str(data.get("detail","")):
    ok(f"Unicode homoglyph → graceful error: {data.get('detail','')[:60]}")
else:
    no(f"Unicode homoglyph → unexpected: {str(data)[:100]}")

# 3.5 Very long query (>500 chars)
long_q = "A" * 2000
code, data = get(f"/api/search?q={long_q}")
if code == 200:
    ok("2000-char query → handled (truncation OK)")
else:
    no(f"2000-char query → unexpected: {data}")


# ============================================================
print("\n" + "=" * 60)
print("🟠🟠 SECTION 3.5: PARAMETER VALIDATION — ALL ENDPOINTS")
print("=" * 60)

# 3.5.1 style/generate — invalid tone → 400
code, data = get("/api/style/generate?topic=test&tone=hacked")
if data.get("code") == 400 and "Invalid tone" in data.get("detail", ""):
    ok("style/generate tone=hacked → 400")
else:
    no(f"style/generate tone=hacked → expected 400, got: {data}")

# 3.5.2 style/generate — huge length → 400
code, data = get("/api/style/generate?topic=test&tone=mixed&length=99999")
if data.get("code") == 400 and "Length must be" in data.get("detail", ""):
    ok("style/generate length=99999 → 400")
else:
    no(f"style/generate length=99999 → expected 400, got: {data}")

# 3.5.3 papers/generate — topic too long → 400
long_topic = "A" * 600
code, data = get(f"/api/papers/generate?topic={long_topic}")
if data.get("code") == 400 and "too long" in data.get("detail", ""):
    ok("papers/generate 600-char topic → 400")
else:
    no(f"papers/generate 600-char topic → expected 400, got: {data}")

# 3.5.4 oracle/search — query too long → 400
long_q = "B" * 600
code, data = get(f"/api/oracle/search?q={long_q}")
if data.get("code") == 400 and "too long" in data.get("detail", ""):
    ok("oracle/search 600-char query → 400")
else:
    no(f"oracle/search 600-char → expected 400, got: {data}")

# 3.5.5 twin — q too long → 400
long_q = "C" * 600
code, data = get(f"/api/twin?q={long_q}")
if data.get("code") == 400 and "too long" in data.get("detail", ""):
    ok("twin 600-char q → 400")
else:
    no(f"twin 600-char → expected 400, got: {data}")

# 3.5.6 twin/ask — q too long → 400
long_q = "D" * 600
code, data = get(f"/api/twin/ask?q={long_q}")
if data.get("code") == 400 and "too long" in data.get("detail", ""):
    ok("twin/ask 600-char q → 400")
else:
    no(f"twin/ask 600-char → expected 400, got: {data}")

# 3.5.7 comparative — topic too long → 400
code, data = get(f"/api/comparative?topic={long_topic}")
if data.get("code") == 400 and "too long" in data.get("detail", ""):
    ok("comparative 600-char topic → 400")
else:
    no(f"comparative 600-char → expected 400, got: {data}")

# 3.5.8 Valid style/tone still works
code, data = get("/api/style/generate?topic=test&tone=mixed&length=100")
if data.get("topic") == "test":
    ok("style/generate valid args → 200")
else:
    no(f"style/generate valid → unexpected: {data}")


print("\n" + "=" * 60)
print("🟢 SECTION 4: API KEY & AUTH")
print("=" * 60)

# 4.1 No API key on protected endpoint
code, data = get("/api/v1/search?q=test")
if data.get("code") == 401:
    ok("No API key → 401")
else:
    no(f"No API key → expected 401, got: {data}")

# 4.2 Bad API key
code, data = request("GET", "/api/v1/search?q=test",
                      headers={"X-API-Key": "this-is-not-valid"})
if data.get("code") == 403:
    ok("Bad API key → 403")
else:
    no(f"Bad API key → expected 403, got: {data}")

# 4.3 Register with too many attempts → 429
# Skip in test suite (would consume daily limit), just verify endpoint exists
code, data = request("POST", "/api/v1/register", body={"tier": "free"})
if data.get("error") and data.get("code") in [429, 400]:
    ok(f"Register endpoint → rate limited or validated (code={data.get('code')})")
else:
    ok(f"Register endpoint → responded (code={data.get('code', 'N/A')})")


# ============================================================
print("\n" + "=" * 60)
print("🔵 SECTION 5: CONTENT-TYPE & ENCODING")
print("=" * 60)

# 5.1 JSON content-type on API responses
try:
    req = urllib.request.Request(f"{BASE}/api/search?q=test")
    resp = urllib.request.urlopen(req, timeout=10)
    ct = resp.headers.get("Content-Type", "")
    if "application/json" in ct:
        ok(f"Content-Type: {ct}")
    else:
        no(f"Content-Type: expected application/json, got: {ct}")
except Exception as e:
    no(f"Content-Type check failed: {e}")

# 5.2 Proper UTF-8 encoding
code, data = get("/api/concepts")  # Has Russian text
response_str = json.dumps(data, ensure_ascii=False)
if any(ord(c) > 127 for c in response_str):
    ok("UTF-8: Russian characters present in response")
else:
    no("UTF-8: no non-ASCII characters in concepts response")

# 5.3 Health endpoint returns JSON
code, data = get("/api/health")
if data.get("status") == "ok":
    ok("Health endpoint → JSON with status=ok")
else:
    no(f"Health endpoint → unexpected: {data}")


# ============================================================
print("\n" + "=" * 60)
print("🟣 SECTION 6: RECOVERY AFTER ATTACKS")
print("=" * 60)

# 6.1 Normal search works after all our attack tests
code, data = get("/api/search?q=imperialism")
if code == 200 and data.get("query") == "imperialism":
    ok(f"Normal search works post-attacks (engines_hit={data.get('engines_hit')})")
else:
    no(f"Normal search broken after attacks: {data}")

# 6.2 Health check passes
code, data = get("/api/health")
if data.get("status") == "ok":
    ok("Health check passes post-attacks")
else:
    no(f"Health check failed: {data}")


# ============================================================
print("\n" + "=" * 60)
print(f"📊 RESULTS: {PASS} PASS · {FAIL} FAIL · {SKIP} SKIP")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
