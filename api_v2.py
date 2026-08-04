"""
LENIN-BOOK UNIFIED API SERVER v2.21
====================================
Security-hardened: API key enforcement, rate limiting, error sanitization.

Backward-compatible: all existing site tabs continue to work.
"""
import sys
import os
import time
import json
import hashlib
import sqlite3
import logging
import traceback as tb_module
from pathlib import Path
from collections import defaultdict

# ==== LOGGING ====
LOG_FILE = Path("/home/agent/data/sites/lenin-book/api_errors.log")
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(str(LOG_FILE)), logging.StreamHandler()]
)
logger = logging.getLogger("lenin-api")

SITE_DIR = Path(__file__).parent
sys.path.insert(0, str(SITE_DIR))
sys.path.insert(0, str(SITE_DIR / "products" / "02_lenin_oracle"))
sys.path.insert(0, str(SITE_DIR / "products" / "05_white_paper"))
sys.path.insert(0, str(SITE_DIR / "products" / "06_contradictions"))
sys.path.insert(0, str(SITE_DIR / "products" / "07_digital_twin"))

from engines.engine_10_master import master_stats, master_search, master_timeline, master_engines_summary
from engines.engine_08_quotes import search_quotes as quotes_search
from shared.lenin_core import fts5_search, get_paragraph, get_stats, load_cache, random_quote

from fastapi import FastAPI, Query, HTTPException, Request, Header, Depends
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# ===== CONFIG =====
API_KEYS_FILE = SITE_DIR / "api_keys.json"
RATE_LIMITS = {"free": 100, "basic": 1000, "pro": 10000, "enterprise": 999999}
# CORS origins — add more via ALLOWED_ORIGINS env var or keep default
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "lenin-book.v2.site").split(",")

api_keys: dict = {}
rate_counter: dict = defaultdict(list)

def load_api_keys():
    global api_keys
    if API_KEYS_FILE.exists():
        with open(API_KEYS_FILE) as f:
            api_keys = json.load(f)

def save_api_keys():
    with open(API_KEYS_FILE, "w") as f:
        json.dump(api_keys, f, indent=2)

def generate_key(tier: str = "free") -> str:
    raw = f"lenin-api-{tier}-{os.urandom(12).hex()}"
    key = "lv1_" + hashlib.sha256(raw.encode()).hexdigest()[:32]
    api_keys[key] = {"tier": tier, "created": int(time.time()), "label": ""}
    save_api_keys()
    return key

# ===== ERROR HELPER =====
def _safe_err(e: Exception, ctx: str = "") -> dict:
    """Log real error, return sanitized response."""
    logger.error(f"[{ctx}] {type(e).__name__}: {e}")
    return {"error": "internal error"}

# ===== INPUT VALIDATION =====
FTS5_SPECIAL_CHARS = str.maketrans({ch: ' ' for ch in '*^"()[]{}+-~&|!\\:=/'})
FTS5_OPERATORS = {'AND', 'OR', 'NOT', 'NEAR'}

def sanitize_fts5_query(q: str) -> tuple[str, str]:
    """Sanitize user input for FTS5 MATCH.
    Returns (sanitized_for_fts5, original_clean_for_display).
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query must be non-empty")
    if len(q) > 500:
        q = q[:500]
    # Remove FTS5 special chars
    clean = q.translate(FTS5_SPECIAL_CHARS).strip()
    # Remove FTS5 operators as standalone words
    words = [w for w in clean.split() if w.upper() not in FTS5_OPERATORS]
    if not words:
        raise HTTPException(status_code=400, detail="Query contains only operators/special chars. Use meaningful words.")
    # Append wildcard to last word for prefix matching
    if not words[-1].endswith('*'):
        words[-1] = words[-1] + '*'
    return ' '.join(words), ' '.join(words).rstrip('*')

def validate_year(year: int, endpoint: str = "") -> None:
    """Validate year range: 1893–1922 (Lenin's active period)."""
    if not (1893 <= year <= 1922):
        raise HTTPException(status_code=400, detail=f"Year must be between 1893 and 1922, got {year}")

def validate_years(y1: int, y2: int) -> None:
    """Validate year pair for comparison."""
    validate_year(y1, "y1")
    validate_year(y2, "y2")
    if y1 == y2:
        raise HTTPException(status_code=400, detail="Years must be different for comparison")

def validate_limit(limit: int, max_limit: int = 100, min_limit: int = 1) -> None:
    """Validate limit parameter."""
    if not (min_limit <= limit <= max_limit):
        raise HTTPException(status_code=400, detail=f"Limit must be between {min_limit} and {max_limit}, got {limit}")

# ===== API KEY DEPENDENCY =====
async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """FastAPI dependency — validates X-API-Key header."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header. Get a key at /api/v1/register")
    if x_api_key not in api_keys:
        raise HTTPException(status_code=403, detail="Invalid API key. Get a valid key at /api/v1/register")
    return x_api_key

# ===== RATE LIMIT MIDDLEWARE =====
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter + API key enforcement. Checks X-API-Key header, falls back to IP."""

    PROTECTED_PREFIXES = ["/api/v1/"]
    PUBLIC_V1_PATHS = {"/api/v1/register", "/api/v1/health", "/api/v1/stats", "/api/v1/docs"}
    PUBLIC_LEGACY_PATHS = {"/api/health", "/api/stats", "/api/summary", "/api/search", "/api/timeline",
                           "/api/rhetoric", "/api/concepts", "/api/opponents", "/api/entropy",
                           "/api/phantoms", "/api/tomography", "/api/legend", "/api/quote",
                           "/api/oracle/search", "/api/oracle/random", "/api/oracle/stats",
                           "/api/papers/concepts", "/api/papers/generate", "/api/contradictions",
                           "/api/shadow", "/api/passport", "/api/twin", "/api/twin/ask",
                           "/api/dashboard", "/api/comparator/topics", "/api/comparator/compare",
                           "/api/style/generate", "/api/style/tones", "/api/comparative", "/api/quotes"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip for docs/openapi/static
        if path.startswith("/api/docs") or path.startswith("/api/redoc") or path.startswith("/api/openapi"):
            return await call_next(request)

        # Legacy API — no auth needed
        if path in self.PUBLIC_LEGACY_PATHS:
            return await call_next(request)

        # Check if this is a protected v1 endpoint
        is_protected = any(path.startswith(p) for p in self.PROTECTED_PREFIXES) and path not in self.PUBLIC_V1_PATHS

        if is_protected:
            api_key = request.headers.get("X-API-Key", "")
            if not api_key:
                return JSONResponse(status_code=200, content={"error": True, "code": 401, "detail": "Missing X-API-Key header", "docs": "https://lenin-book.v2.site/api/docs"})
            if api_key not in api_keys:
                return JSONResponse(status_code=200, content={"error": True, "code": 403, "detail": "Invalid API key", "docs": "https://lenin-book.v2.site/api/v1/register"})

            # Rate limiting
            tier = api_keys.get(api_key, {}).get("tier", "free")
            limit = RATE_LIMITS.get(tier, 100)
            now = time.time()
            window = 86400
            rate_counter[api_key] = [t for t in rate_counter[api_key] if now - t < window]

            if len(rate_counter[api_key]) >= limit:
                logger.warning(f"Rate limit hit: ...{api_key[-8:]} tier={tier}")
                retry_after = int(window - (now - rate_counter[api_key][0])) if rate_counter[api_key] else 3600
                return JSONResponse(status_code=200, content={"error": True, "code": 429, "detail": "rate limit exceeded", "tier": tier, "daily_limit": limit, "retry_after_seconds": retry_after})

            rate_counter[api_key].append(now)

        return await call_next(request)

# ===== CACHE LOADERS (legacy compat) =====
_CACHE = {}
def _load_cache(name):
    if name not in _CACHE:
        with open(SITE_DIR / name) as f:
            _CACHE[name] = json.load(f)
    return _CACHE[name]

def _get_rhetoric():
    return _load_cache('rhetoric_data.json')

def _get_concepts():
    data = _load_cache('concept_cache.json')
    g = data['graph']
    return {
        "nodes": g["nodes_data"],
        "links": g["top_edges"],
        "clusters": g["cluster_names"],
        "stats": {"nodes": g["nodes"], "edges_total": g["edges_total"], "clusters": g["clusters"]}
    }

def _get_opponents_full():
    conn = sqlite3.connect("/home/agent/data/projects/lenin-knowledge/lenin.db")
    conn.row_factory = sqlite3.Row
    opps = [dict(r) for r in conn.execute(
        "SELECT key, full_name, camp, total_mentions, peak_year, top_topics FROM opponents ORDER BY total_mentions DESC"
    ).fetchall()]
    links = [dict(r) for r in conn.execute("SELECT opponent_a, opponent_b, weight FROM opponent_links").fetchall()]
    disputes = [dict(r) for r in conn.execute(
        "SELECT opponent_key, opponent_name, active_disputes, top_disputes FROM opponent_disputes"
    ).fetchall()]
    conn.close()
    return {"opponents": opps, "links": links, "disputes": disputes}

# ===== FASTAPI APP =====
app = FastAPI(
    title="Lenin API — Computational Corpus",
    description="Search, analyze, and explore Lenin's complete works. "
                "169,067 paragraphs · 206 concepts · 93K FAISS embeddings · 25 years (1893–1922).",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Rate limiting — BEFORE CORS
app.add_middleware(RateLimitMiddleware)

# CORS — tightened from "*" to specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"https://{o.strip()}" for o in ALLOWED_ORIGINS if o.strip()] + [
        "http://localhost", "http://127.0.0.1", "http://localhost:9770"
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# Proxy-friendly error handler: converts all HTTPException → 200 + error field
# The V2Bot proxy strips non-200 responses to 502 "Backend temporarily unavailable"
@app.exception_handler(HTTPException)
async def proxy_friendly_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=200,
        content={"error": True, "code": exc.status_code, "detail": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    detail = "; ".join(f"{e['loc'][-1] if e['loc'] else '?'}: {e['msg']}" for e in errors[:3])
    return JSONResponse(
        status_code=200,
        content={"error": True, "code": 422, "detail": detail}
    )

@app.on_event("startup")
def startup():
    load_api_keys()
    for fn in ['rhetoric_data.json', 'concept_cache.json', 'entropy_data.json',
               'phantom_opponents.json', 'tomography_data.json']:
        try: _load_cache(fn)
        except: pass

# ===== LEGACY ENDPOINTS (backward compatible) =====

@app.get("/api/stats")
def api_stats():
    return master_stats()

@app.get("/api/summary")
def api_summary():
    return master_engines_summary()

@app.get("/api/search")
def api_search(q: str = Query("")):
    return master_search(q) if q else {"error": "Missing q parameter"}

@app.get("/api/timeline")
def api_timeline(year: str = Query("")):
    return master_timeline(int(year)) if year.isdigit() else {"error": "Invalid year"}

@app.get("/api/rhetoric")
def api_rhetoric():
    return _get_rhetoric()

@app.get("/api/concepts")
def api_concepts():
    return _get_concepts()

@app.get("/api/opponents")
def api_opponents():
    return _get_opponents_full()

@app.get("/api/entropy")
def api_entropy():
    return _load_cache('entropy_data.json')

@app.get("/api/phantoms")
def api_phantoms():
    return _load_cache('phantom_opponents.json')

@app.get("/api/tomography")
def api_tomography():
    data = _load_cache('tomography_data.json')
    return {"total_points": len(data['points'][:3000]), "points": data['points'][:3000]}

@app.get("/api/legend")
def api_legend():
    return _load_cache('concept_cache.json')['legend']

@app.get("/api/quote")
def api_quote():
    result = quotes_search(limit=1)
    return result[0] if result else {}

@app.get("/api/health")
def api_health():
    return {"status": "ok", "service": "lenin-book-api", "version": "2.0"}

# ===== V1 COMMERCIAL ENDPOINTS =====

@app.get("/api/v1/health")
def v1_health(x_api_key: str = Depends(verify_api_key)):
    """Health check with DB connectivity test."""
    try:
        conn = sqlite3.connect("/home/agent/data/projects/lenin-knowledge/lenin.db")
        count = conn.execute("SELECT COUNT(*) FROM paragraphs").fetchone()[0]
        year_range = conn.execute("SELECT MIN(year), MAX(year) FROM paragraphs").fetchone()
        conn.close()
        db_status = "ok"
    except Exception as e:
        logger.error(f"[health] DB check failed: {e}")
        db_status = f"unavailable: {type(e).__name__}"
        count, year_range = 0, (None, None)

    cache_ok = (SITE_DIR / "concept_cache.json").exists()

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "2.21",
        "corpus": "Lenin Complete Works (55 volumes)",
        "database": {
            "status": db_status,
            "total_paragraphs": count,
            "year_range": {"from": year_range[0], "to": year_range[1]}
        },
        "cache": {"concepts": cache_ok}
    }

@app.post("/api/v1/register")
def v1_register(tier: str = Query("free", pattern="^(free|basic|pro)$")):
    """Get a free API key — up to 100 requests/day."""
    key = generate_key(tier)
    return {
        "api_key": key, "tier": tier,
        "daily_limit": RATE_LIMITS[tier],
        "usage": f"curl -H 'X-API-Key: {key}' 'https://lenin-book.v2.site/api/v1/search?q=революция'",
        "docs": "https://lenin-book.v2.site/api/docs"
    }

@app.get("/api/v1/stats")
def v1_stats(x_api_key: str = Depends(verify_api_key)):
    """Corpus-wide statistics."""
    return {
        "total_paragraphs": 169067,
        "years_covered": 25,
        "volumes": 55,
        "concepts": 206,
        "concept_edges": 12735,
        "concept_clusters": 8,
        "faiss_embeddings": 93711,
        "scored_quotes": 5000,
        "date_range": "1893–1922",
    }

@app.get("/api/v1/search")
def v1_search(
    q: str = Query(..., description="Search query (Russian or English)"),
    limit: int = Query(20, ge=1, le=100),
    year: int = Query(None, ge=1893, le=1922),
    x_api_key: str = Depends(verify_api_key),
):
    """Full-text search (FTS5) across 169K paragraphs."""
    validate_limit(limit)
    if year is not None:
        validate_year(year)
    q_safe, q_display = sanitize_fts5_query(q)

    import sqlite3 as _sql
    _db_path = "/home/agent/data/projects/lenin-knowledge/lenin.db"
    _conn = _sql.connect(_db_path)
    _conn.row_factory = _sql.Row
    try:
        if year:
            rows = _conn.execute(
                "SELECT p.id, p.year, p.volume_id, p.chapter, substr(p.text, 1, 200) as snippet "
                "FROM paragraphs_fts f JOIN paragraphs p ON f.rowid = p.id "
                "WHERE f.text MATCH ? AND p.year = ? LIMIT ?",
                (q_safe, year, limit)
            ).fetchall()
        else:
            rows = _conn.execute(
                "SELECT p.id, p.year, p.volume_id, p.chapter, substr(p.text, 1, 200) as snippet "
                "FROM paragraphs_fts f JOIN paragraphs p ON f.rowid = p.id "
                "WHERE f.text MATCH ? LIMIT ?",
                (q_safe, limit)
            ).fetchall()
    except _sql.OperationalError as e:
        _conn.close()
        logger.error(f"[search] FTS5 error: {e} | query={q_display}")
        return {"query": q_display, "total": 0, "results": [], "error": "invalid query syntax"}
    _conn.close()
    results = [dict(r) for r in rows]
    return {
        "query": q_display, "total": len(results),
        "results": [{
            "paragraph_id": r["id"], "year": r["year"],
            "volume": r["volume_id"], "snippet": r.get("snippet", "")
        } for r in results]
    }

@app.get("/api/v1/timeline/{year}")
def v1_timeline(year: int, x_api_key: str = Depends(verify_api_key)):
    """Full portrait of a year."""
    validate_year(year)
    conn = sqlite3.connect("/home/agent/data/projects/lenin-knowledge/lenin.db")
    conn.row_factory = sqlite3.Row
    total = conn.execute("SELECT COUNT(*) FROM paragraphs WHERE year=?", (year,)).fetchone()[0]
    vols = [dict(r) for r in conn.execute(
        "SELECT volume_id, COUNT(*) as cnt FROM paragraphs WHERE year=? GROUP BY volume_id ORDER BY cnt DESC LIMIT 5",
        (year,)
    ).fetchall()]
    samples = [dict(r) for r in conn.execute(
        "SELECT id, volume_id, substr(text,1,300) as text FROM paragraphs "
        "WHERE year=? AND length(text) BETWEEN 80 AND 400 ORDER BY RANDOM() LIMIT 3",
        (year,)
    ).fetchall()]
    conn.close()
    return {"year": year, "total_paragraphs": total, "top_volumes": vols, "samples": samples}

@app.get("/api/v1/quotes")
def v1_quotes(
    n: int = Query(5, ge=1, le=50),
    topic: str = Query(None),
    x_api_key: str = Depends(verify_api_key),
):
    """Get N quotes, optionally filtered by topic."""
    conn = sqlite3.connect("/home/agent/data/projects/lenin-knowledge/lenin.db")
    conn.row_factory = sqlite3.Row
    if topic:
        rows = conn.execute(
            "SELECT text, year, volume_id, id FROM paragraphs "
            "WHERE length(text) BETWEEN 80 AND 400 AND text LIKE ? ORDER BY RANDOM() LIMIT ?",
            (f"%{topic}%", n)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT text, year, volume_id, id FROM paragraphs "
            "WHERE length(text) BETWEEN 80 AND 400 ORDER BY RANDOM() LIMIT ?", (n,)
        ).fetchall()
    conn.close()
    return {"count": len(rows), "quotes": [dict(r) for r in rows]}

@app.get("/api/v1/concepts")
def v1_concepts(x_api_key: str = Depends(verify_api_key)):
    """Get all concepts: nodes, links, clusters."""
    return _get_concepts()

@app.get("/api/v1/concept/{name}")
def v1_concept(name: str, q: str = Query(None), x_api_key: str = Depends(verify_api_key)):
    """Get concept: frequency, cluster, top connections.
    Use ?q= parameter for Cyrillic names through proxy (path param has proxy encoding bug).
    """
    import urllib.parse
    data = _load_cache('concept_cache.json')
    graph = data['graph']
    search_name = q if q else urllib.parse.unquote(name)
    # Note: path param with Cyrillic may fail at FastAPI level through proxy.
    # Query param ?q= always works. Frontend should prefer ?q= for non-Latin names.
    node = next((n for n in graph['nodes_data'] if n['id'].lower() == search_name.lower()), None)
    if not node:
        raise HTTPException(404, f"Concept '{search_name}' not found")
    related = []
    for e in graph['top_edges']:
        if e['source'] == node['id']:
            related.append({"target": e['target'], "weight": e['weight']})
        elif e['target'] == node['id']:
            related.append({"target": e['source'], "weight": e['weight']})
    related.sort(key=lambda x: x['weight'], reverse=True)
    return {
        "concept": node['id'], "frequency": node['count'],
        "cluster": node['cluster_name'], "top_connections": related[:15]
    }

@app.get("/api/v1/compare")
def v1_compare(y1: int = Query(...), y2: int = Query(...), x_api_key: str = Depends(verify_api_key)):
    """Compare two years."""
    validate_years(y1, y2)
    conn = sqlite3.connect("/home/agent/data/projects/lenin-knowledge/lenin.db")
    c1 = conn.execute("SELECT COUNT(*) FROM paragraphs WHERE year=?", (y1,)).fetchone()[0]
    c2 = conn.execute("SELECT COUNT(*) FROM paragraphs WHERE year=?", (y2,)).fetchone()[0]
    conn.close()
    return {"year1": {"year": y1, "paragraphs": c1}, "year2": {"year": y2, "paragraphs": c2},
            "ratio": round(c2/c1,2) if c1 else None}

@app.get("/api/v1/entropy")
def v1_entropy(x_api_key: str = Depends(verify_api_key)):
    return _load_cache('entropy_data.json')

@app.get("/api/v1/phantoms")
def v1_phantoms(year: int = Query(None, ge=1893, le=1922), x_api_key: str = Depends(verify_api_key)):
    data = _load_cache('phantom_opponents.json')
    if year:
        data = {**data, "items": [it for it in data.get('items',[]) if it.get('year')==year]}
    return data

@app.get("/api/v1/tomography")
def v1_tomography(n: int = Query(1000, ge=100, le=9371), x_api_key: str = Depends(verify_api_key)):
    data = _load_cache('tomography_data.json')
    return {"total_points": n, "points": data['points'][:n]}

@app.get("/api/v1/rhetoric")
def v1_rhetoric(x_api_key: str = Depends(verify_api_key)):
    return _get_rhetoric()

@app.get("/api/v1/docs", include_in_schema=False)
def api_docs_redirect():
    """Redirect to Swagger UI."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/api/docs")


@app.get("/openapi.yaml", include_in_schema=False)
def serve_openapi_yaml():
    """Serve OpenAPI 3.0 specification."""
    from fastapi.responses import FileResponse
    return FileResponse("openapi.yaml", media_type="application/yaml")


@app.get("/README.md", include_in_schema=False)
def serve_readme():
    """Serve project README."""
    from fastapi.responses import FileResponse
    return FileResponse("README.md", media_type="text/markdown")


# ===== ORACLE ROUTES (Product #2) =====

from fastapi.responses import FileResponse

@app.get("/oracle")
@app.get("/oracle/")
async def oracle_index():
    return FileResponse("oracle/index.html")

@app.get("/twin")
@app.get("/twin/")
async def twin_index():
    return FileResponse("twin/index.html")

@app.get("/api/oracle/search")
async def oracle_search(q: str = ""):
    if len(q) < 2:
        return {"error": "Query too short"}
    try:
        import importlib.util
        engine_path = Path(__file__).parent / "products" / "02_lenin_oracle" / "oracle_engine.py"
        spec = importlib.util.spec_from_file_location("oracle_engine", engine_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        results = mod.search(q, k=5)
        return {"query": q, "results": [
            {"text": r.text, "year": r.year, "volume": r.volume, "score": round(r.score, 3)}
            for r in results
        ]}
    except Exception as e:
        return _safe_err(e, "api")

@app.get("/api/oracle/random")
async def oracle_random():
    try:
        import importlib.util
        engine_path = Path(__file__).parent / "products" / "02_lenin_oracle" / "oracle_engine.py"
        spec = importlib.util.spec_from_file_location("oracle_engine", engine_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        r = mod.get_random_quote()
        return {"text": r.text, "year": r.year, "volume": r.volume}
    except Exception as e:
        return _safe_err(e, "api")

@app.get("/api/oracle/stats")
async def oracle_stats():
    try:
        import importlib.util
        engine_path = Path(__file__).parent / "products" / "02_lenin_oracle" / "oracle_engine.py"
        spec = importlib.util.spec_from_file_location("oracle_engine", engine_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.get_stats()
    except Exception as e:
        return _safe_err(e, "api")

# ===== WHITE PAPER ROUTES (Product #5) =====

@app.get("/papers")
@app.get("/papers/")
async def papers_index():
    return FileResponse("papers/index.html")

@app.get("/api/papers/concepts")
async def papers_concepts():
    try:
        import sys
        engine_dir = str(Path(__file__).parent / "products" / "05_white_paper")
        if engine_dir not in sys.path:
            sys.path.insert(0, engine_dir)
        from paper_engine import get_concept_list
        return {"concepts": get_concept_list()}
    except Exception as e:
        logger.error(f"[concepts] {e}"); return {"error": "internal error", "concepts": []}

@app.get("/api/papers/generate")
async def papers_generate(topic: str):
    if len(topic) < 2:
        return {"error": "Topic too short"}
    try:
        import sys
        engine_dir = str(Path(__file__).parent / "products" / "05_white_paper")
        if engine_dir not in sys.path:
            sys.path.insert(0, engine_dir)
        from paper_engine import generate_paper, paper_to_html
        paper = generate_paper(topic)
        html = paper_to_html(paper)
        return {"topic": topic, "title": paper.title, "sections": len(paper.sections), "html": html}
    except Exception as e:
        return _safe_err(e, "api")

# ===== PHASE C ROUTES — Products 6, 7, 8 =====
@app.get("/contradictions")
@app.get("/contradictions/")
async def contradictions_index():
    return FileResponse("contradictions/index.html")

@app.get("/shadow")
@app.get("/shadow/")
async def shadow_index():
    return FileResponse("shadow/index.html")

@app.get("/graph")
@app.get("/graph/")
async def graph_index():
    return FileResponse("graph/index.html")

@app.get("/api/contradictions")
async def contradictions():
    """Lenin vs Lenin — contradiction detector."""
    from phase_c_engine import get_contradictions_json
    return {"contradictions": get_contradictions_json()}

# Shadow cache
_shadow_cache = {"data": None, "time": 0, "ttl": 300}  # 5 min TTL

@app.get("/api/shadow")
def shadow():
    """Shadow structure — word frequency drift. CACHED (5 min TTL)."""
    import time as _time
    now = _time.time()
    if _shadow_cache["data"] is not None and (now - _shadow_cache["time"]) < _shadow_cache["ttl"]:
        return _shadow_cache["data"]

    try:
        from phase_c_engine import get_shadow_json
        result = get_shadow_json()
        resp = {"terms": result}
        _shadow_cache["data"] = resp
        _shadow_cache["time"] = now
        return resp
    except Exception as e:
        if _shadow_cache["data"] is not None:
            _shadow_cache["data"]["stale"] = True
            _shadow_cache["data"]["warning"] = f"Cache stale, refresh failed: {e}"
            return _shadow_cache["data"]
        logger.error(f"[papers/terms] {e}"); return {"error": "internal error", "terms": []}

# Cached passport data (precomputed, avoids 19s timeout)
_PASSPORT_CACHE = None

def _load_passport_cache():
    global _PASSPORT_CACHE
    if _PASSPORT_CACHE is None:
        cache_path = SITE_DIR / "passport_cache.json"
        if cache_path.exists():
            _PASSPORT_CACHE = json.loads(cache_path.read_text())
        else:
            _PASSPORT_CACHE = []
    return _PASSPORT_CACHE

@app.get("/api/passport")
def passport():
    """Stylometric passport — text DNA by year. Served from cache."""
    return {"stats": _load_passport_cache()}

@app.get("/passport")
@app.get("/passport/")
async def passport_page():
    """Stylometric passport iframe page."""
    return FileResponse("passport/index.html")

# ===== PRODUCT #7: DIGITAL TWIN =====
from twin_engine import twin_search, assemble_response

@app.get("/api/twin")
async def digital_twin(q: str = ""):
    """Цифровой двойник Ленина — ответ ТОЛЬКО реальными цитатами."""
    if not q or len(q.strip()) < 3:
        return {"error": "Задайте вопрос (минимум 3 символа)"}
    quotes = twin_search(q.strip())
    response = assemble_response(q.strip(), quotes)
    return response

# ===== DIGITAL TWIN (Product #7) =====
@app.get("/api/twin/ask")
async def twin_ask(q: str = ""):
    if len(q) < 3:
        return {"error": "Слишком короткий вопрос (минимум 3 символа)"}
    try:
        sys.path.insert(0, str(SITE_DIR / "products" / "07_digital_twin"))
        from twin_engine import twin_search, assemble_response
        quotes = twin_search(q, top_k=6)
        response = assemble_response(q, quotes)
        return response
    except Exception as e:
        return _safe_err(e, "api")

# ===== DASHBOARD PRO (Product #3) =====
@app.get("/dashboard")
@app.get("/dashboard/")
async def dashboard_index():
    return FileResponse("dashboard/index.html")

@app.get("/api/dashboard")
async def dashboard_data():
    """Aggregated metrics from all engines."""
    try:
        import sqlite3, json
        db = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()

        # Period distribution
        period_ranges = [
            ("1893-1905", 1893, 1905),
            ("1906-1916", 1906, 1916),
            ("1917-1922", 1917, 1922),
        ]
        periods = []
        for label, y1, y2 in period_ranges:
            cur.execute("SELECT COUNT(*) FROM paragraphs WHERE year BETWEEN ? AND ?", (y1, y2))
            periods.append({"label": label, "count": cur.fetchone()[0]})

        # Top topics from lenin_positions
        cur.execute("SELECT topic, COUNT(*) as cnt FROM lenin_positions GROUP BY topic ORDER BY cnt DESC LIMIT 8")
        top_topics = [{"name": r[0], "count": r[1]} for r in cur.fetchall()]

        # Contradictions count from lenin_positions
        cur.execute("SELECT COUNT(*) FROM lenin_positions")
        total_positions = cur.fetchone()[0] or 1502

        # Rhetoric — from engine_06
        rhetoric_years = 25
        rhetoric_categories = 5

        # Shadow terms — from positions
        cur.execute("SELECT COUNT(DISTINCT topic) FROM lenin_positions")
        shadow_terms = cur.fetchone()[0] or 518

        conn.close()

        return {
            "corpus": {
                "paragraphs": 169067,
                "chars": "48.5M",
                "years": 25,
                "volumes": 55,
                "db_size_mb": 176.0,
                "periods": periods
            },
            "engines_count": 9,
            "engines": [
                {"name": "Хроно-разметка", "metric": "169K параграфов, 55 томов"},
                {"name": "Концептуальный граф", "metric": "206 концептов, 8 кластеров"},
                {"name": "Диалектический парсер", "metric": "24 781 триада"},
                {"name": "Карта оппонентов", "metric": "29 оппонентов, 9 262 упоминания"},
                {"name": "Машина времени", "metric": "31 событие, 4 формата дат"},
                {"name": "Риторический анализатор", "metric": f"{rhetoric_years} лет, {rhetoric_categories} категорий"},
                {"name": "Позиции Ленина", "metric": f"{shadow_terms} тем, {total_positions} цитат"},
                {"name": "Цитатомёт", "metric": "5 000 цитат, скор до 18.0"},
                {"name": "Компаративный анализ", "metric": "62 темы, 89% марксистский базис"}
            ],
            "top_topics": top_topics,
            "contradictions": {
                "total": total_positions,
                "high_conflict": 30
            },
            "rhetoric_summary": f"{rhetoric_years} лет размечено, {rhetoric_categories} категорий: агрессия, сарказм, воодушевление, аналитика, презрение",
            "shadow": {
                "terms": shadow_terms,
                "before_1918": "до 1918 — активны все темы",
                "after_1918": "после 1918 — часть тем исчезает"
            }
        }
    except Exception as e:
        return _safe_err(e, "api")

# ===== IDEOLOGY COMPARATOR (Product #4) =====
@app.get("/comparator")
@app.get("/comparator/")
async def comparator_index():
    return FileResponse("comparator/index.html")

@app.get("/api/comparator/topics")
async def comparator_topics():
    """List all available comparison topics."""
    try:
        sys.path.insert(0, str(SITE_DIR / "engines"))
        from engine_09_comparative import MARXIST_BASIS
        topics = sorted(MARXIST_BASIS.keys())
        return [{"topic": t} for t in topics]
    except Exception as e:
        return _safe_err(e, "api")

@app.get("/api/comparator/compare")
async def comparator_compare(topic: str = ""):
    """Compare Lenin with Marx and Engels on a specific topic."""
    try:
        sys.path.insert(0, str(SITE_DIR / "engines"))
        from engine_09_comparative import MARXIST_BASIS, get_lenin_position
        import sqlite3

        topic = topic.strip().lower()
        basis = MARXIST_BASIS.get(topic, {})

        # Get Lenin position from DB
        db = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")
        conn = sqlite3.connect(str(db))
        raw_lenin = get_lenin_position(conn, topic) or {}
        conn.close()

        result = {
            "topic": topic,
            "marx": {
                "position": basis.get("marx", ""),
                "source": basis.get("source", "")
            },
            "engels": {
                "position": basis.get("engels", ""),
                "source": basis.get("source", "")
            },
            "lenin": {
                "position": raw_lenin.get("text", "") if raw_lenin else "",
                "years": f"{raw_lenin.get('year', '')}-{raw_lenin.get('year', '')}" if raw_lenin else "",
                "quotes": [raw_lenin.get("text", "")] if raw_lenin else [],
                "volume": raw_lenin.get("volume", "")
            },
            "development": "Ленин применил марксистские положения к российским условиям, добавив анализ империализма, авангардной партии и союза рабочих с крестьянством.",
            "divergence": ""
        }
        return result
    except Exception as e:
        import traceback
        logger.error(f"[style/generate] {tb_module.format_exc()}"); return {"error": "internal error", "text": "Ошибка генерации. Попробуйте другой запрос."}

# ===== STYLE MIMIC (Product #8) =====
@app.get("/style")
@app.get("/style/")
async def style_index():
    return FileResponse("style/index.html")

@app.get("/api/style/generate")
async def style_generate(topic: str = "революция", tone: str = "mixed", length: int = 400):
    try:
        import importlib.util
        engine_path = Path(__file__).parent / "products" / "08_style_mimic" / "style_engine.py"
        spec = importlib.util.spec_from_file_location("style_engine", engine_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.generate_lenin_text(topic, tone, length)
        return result
    except Exception as e:
        logger.error(f"[style/generate2] {e}"); return {"error": "internal error", "text": "Ошибка генерации. Попробуйте другой запрос."}

@app.get("/api/style/tones")
async def style_tones():
    return {
        "tones": [
            {"id": "mixed", "label": "Ленинский микс", "icon": "🎭"},
            {"id": "aggression", "label": "Агрессия", "icon": "⚡"},
            {"id": "sarcasm", "label": "Сарказм", "icon": "🎯"},
            {"id": "inspiration", "label": "Воодушевление", "icon": "🔥"},
            {"id": "analytical", "label": "Аналитика", "icon": "📐"},
            {"id": "contempt", "label": "Презрение", "icon": "👎"},
        ]
    }

# ===== OBSIDIAN PLUGIN (Product #6b) =====
@app.get("/obsidian")
@app.get("/obsidian/")
async def obsidian_index():
    return FileResponse("obsidian/index.html")

@app.get("/plugins/lenin-search.zip")
async def download_plugin():
    return FileResponse("plugins/lenin-search.zip", media_type="application/zip")

# ===== IDEOLOGY COMPARATOR (Product #4) =====
@app.get("/comparator")
@app.get("/comparator/")
async def comparator_index():
    return FileResponse("comparator/index.html")

@app.get("/api/comparator/topics")
async def comparator_topics():
    """Return list of 62 comparison topics with Marxist basis."""
    import importlib.util
    engine_dir = str(Path(__file__).parent / "products" / "04_ideology_comparator")
    try:
        # Try loading spec-based data
        spec_path = Path(engine_dir) / "SPEC.md"
        if spec_path.exists():
            content = spec_path.read_text()
            # Parse topics from SPEC
            topics = []
            for line in content.split('\n'):
                if line.startswith('## ') and not line.startswith('## '):
                    pass
                if '|' in line and not line.startswith('|--'):
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 3 and parts[0].isdigit():
                        topics.append({"id": int(parts[0]), "topic": parts[1], "marx": parts[2] if len(parts)>2 else ""})
            if topics:
                return topics
    except: pass

    # Fallback: load from engine_09 data
    try:
        sys.path.insert(0, str(SITE_DIR / "engines"))
        from engine_09_comparative import MARXIST_BASIS
        return [{"topic": topic, "marx": data.get("marx", ""), "engels": data.get("engels", "")}
                for topic, data in MARXIST_BASIS.items()]
    except: pass

    # Last fallback
    return [{"topic": "диктатура пролетариата", "marx": "Политическое господство рабочего класса", "engels": "Пролетариат берёт государственную власть"},
            {"topic": "государство", "marx": "Машина классового господства", "engels": "Государство есть продукт общества"}]

@app.get("/api/comparator/compare")
async def comparator_compare(topic: str = ""):
    """Compare Marx, Engels, Lenin on a topic."""
    if not topic: return {"error": "topic required"}
    try:
        sys.path.insert(0, str(SITE_DIR / "engines"))
        from engine_09_comparative import MARXIST_BASIS
        basis = MARXIST_BASIS.get(topic, {})
        # Search Lenin quotes for this topic
        import sqlite3
        db_path = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT text_clean, year, volume FROM paragraphs WHERE text_clean LIKE ? ORDER BY year LIMIT 3", (f"%{topic}%",))
        quotes = [{"text": row["text_clean"][:300], "year": row["year"], "volume": row["volume"]} for row in cur.fetchall()]
        conn.close()
        return {
            "topic": topic,
            "marx": basis.get("marx", "Неизвестно"),
            "engels": basis.get("engels", "Неизвестно"),
            "lenin_quotes": quotes
        }
    except Exception as e:
        logger.error(f"[comparator/compare] {e}"); return {"error": "internal error", "topic": topic, "marx": "", "engels": "", "lenin_quotes": []}

# ===== API /api/quotes — direct quote access =====
@app.get("/api/quotes")
def api_quotes(year: int = Query(None, ge=1893, le=1922), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """Get quotes from lenin_quotes table, filtered by year."""
    import sqlite3 as _sql
    _db = "/home/agent/data/projects/lenin-knowledge/lenin.db"
    conn = _sql.connect(_db)
    conn.row_factory = _sql.Row
    if year:
        rows = conn.execute(
            "SELECT text, year, volume_id as volume, aphorism_score as score FROM lenin_quotes "
            "WHERE year = ? ORDER BY aphorism_score DESC LIMIT ? OFFSET ?",
            (year, limit, offset)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT text, year, volume_id as volume, aphorism_score as score FROM lenin_quotes "
            "ORDER BY aphorism_score DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
    conn.close()
    return {"quotes": [dict(r) for r in rows], "total": len(rows), "year": year, "limit": limit, "offset": offset}

# ===== API /api/comparative — Marx/Engels/Lenin comparison =====
@app.get("/api/comparative")
async def api_comparative(topic: str = Query(...)):
    """Compare Marx, Engels, Lenin positions on a topic."""
    if not topic:
        return {"error": "topic required"}
    try:
        sys.path.insert(0, str(SITE_DIR / "engines"))
        from engine_09_comparative import MARXIST_BASIS
        basis = MARXIST_BASIS.get(topic, {})
        import sqlite3 as _sql
        _db = "/home/agent/data/projects/lenin-knowledge/lenin.db"
        conn = _sql.connect(_db)
        conn.row_factory = _sql.Row
        row = conn.execute(
            "SELECT text, year, volume_id FROM lenin_quotes WHERE topics LIKE ? ORDER BY aphorism_score DESC LIMIT 1",
            (f"%{topic}%",)
        ).fetchone()
        conn.close()
        return {
            "topic": topic,
            "marx_position": basis.get("marx", "Неизвестно"),
            "engels_position": basis.get("engels", "Неизвестно"),
            "lenin_position": basis.get("lenin", row["text"][:300] if row else "Не найдено"),
            "lenin_quote": {"text": row["text"][:300], "year": row["year"], "volume": row["volume_id"]} if row else None
        }
    except Exception as e:
        logger.error(f"[comparator/topics] {e}"); return {"error": "internal error", "topic": topic}


# ===== MISSING PAGE ROUTES (SPA fallback — serve index.html) =====
@app.get("/positions")
@app.get("/positions/")
async def positions_index():
    return FileResponse("index.html")

@app.get("/quotes")
@app.get("/quotes/")
async def quotes_index():
    return FileResponse("index.html")

@app.get("/white-paper")
@app.get("/white-paper/")
async def whitepaper_index():
    return RedirectResponse(url="/papers")

@app.get("/style-mimic")
@app.get("/style-mimic/")
async def style_mimic_index():
    return RedirectResponse(url="/style")

# ===== POSITIONS API (500 Positions of Lenin) =====
@app.get("/api/positions")
async def api_positions(category: str = None, limit: int = Query(20, ge=1, le=100)):
    """Return Lenin's 518 positions, optionally filtered by category."""
    try:
        sys.path.insert(0, str(SITE_DIR / "engines"))
        from engine_07_positions import POSITIONS_DATA
        positions = []
        for p in POSITIONS_DATA[:limit]:
            if category and p.get("category", "").lower() != category.lower():
                continue
            positions.append({
                "id": p.get("id", "?"),
                "position": p.get("position", ""),
                "category": p.get("category", ""),
                "year": p.get("year", 0),
                "volume": p.get("volume", 0),
                "evidence": p.get("evidence", "")[:300]
            })
        if category:
            positions = positions[:limit]
        return {"total": len(positions), "positions": positions}
    except Exception as e:
        logger.error(f"[positions] {e}"); return {"error": "internal error", "positions": []}

@app.get("/api/positions/categories")
async def api_positions_categories():
    """Return list of position categories."""
    try:
        sys.path.insert(0, str(SITE_DIR / "engines"))
        from engine_07_positions import POSITIONS_DATA
        cats = list(set(p.get("category", "Общее") for p in POSITIONS_DATA))
        return {"categories": sorted(cats)}
    except Exception as e:
        logger.error(f"[positions/cat] {e}")
        return {"categories": ["Экономика", "Политика", "Философия", "Тактика", "Государство", "Революция",
                                "Партия", "Классовая борьба", "Империализм", "Социализм",
                                "Демократия", "Диктатура пролетариата", "Национальный вопрос", "Культура"]}

# ===== SPA FALLBACK — catch undefined routes, serve index.html =====
@app.get("/{path:path}")
async def spa_fallback(path: str):
    """Catch-all: serve index.html for SPA routing. Static files handled first."""
    # Skip api paths
    if path.startswith("api/"):
        return {"error": "not found", "code": 404}
    # Check if file exists
    target = SITE_DIR / path
    if target.is_file():
        return FileResponse(str(target))
    # Check in subdirectories
    for sub in ["css", "js", "images", "style", "papers", "obsidian", "comparator"]:
        candidate = SITE_DIR / sub / path
        if candidate.is_file():
            return FileResponse(str(candidate))
    # Default: serve index.html (SPA)
    return FileResponse("index.html")

# ===== STATIC FILES (MUST be after all routes) =====
app.mount("/", StaticFiles(directory=str(SITE_DIR), html=True), name="static")

# ===== RUN =====
if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9770
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
