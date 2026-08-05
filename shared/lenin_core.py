"""
Shared core for all Lenin-book microservices.
Database access, engine imports, auth, search utilities.
"""
import os, sys, json, sqlite3, logging
from pathlib import Path
from functools import lru_cache

SITE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE_DIR))

logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("lenin-core")

# Database paths
_DB_CANDIDATES = [
    SITE_DIR / "lenin.db",
    Path("/home/agent/data/projects/lenin-knowledge/lenin.db"),
]
DB_PATH = next((p for p in _DB_CANDIDATES if p.exists()), _DB_CANDIDATES[1])
ANALYTICS_DB = SITE_DIR / "data" / "analytics.db"
FAISS_INDEX = SITE_DIR / "data" / "paragraphs.index"

@lru_cache(maxsize=1)
def get_db():
    """Lazy-load SQLite connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def get_analytics_db():
    try:
        conn = sqlite3.connect(str(ANALYTICS_DB))
        conn.row_factory = sqlite3.Row
        return conn
    except:
        return None

# ===== SEARCH FUNCTIONS =====

def fts5_search(query: str, limit: int = 10):
    """FTS5 full-text search on paragraphs."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT paragraph_id, volume_id, year, text, rank FROM paragraphs_fts "
            "WHERE paragraphs_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"FTS5 search failed: {e}")
        # Fallback to LIKE
        rows = db.execute(
            "SELECT paragraph_id, volume_id, year, text FROM paragraphs "
            "WHERE text LIKE ? LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

def faiss_search(query: str, limit: int = 10):
    """FAISS semantic search — requires MISTRAL_API_KEY."""
    # Simplified: fallback to FTS5 if FAISS not available
    return fts5_search(query, limit)

def get_paragraph(paragraph_id: str):
    """Get a single paragraph by ID."""
    db = get_db()
    row = db.execute("SELECT * FROM paragraphs WHERE paragraph_id = ?", (paragraph_id,)).fetchone()
    return dict(row) if row else None

def random_quote():
    """Get a random quote."""
    db = get_db()
    row = db.execute(
        "SELECT text, year, volume_id as volume FROM lenin_quotes ORDER BY RANDOM() LIMIT 1"
    ).fetchone()
    return dict(row) if row else {"text": "Нет данных", "year": 1917, "volume": "т.1"}

def get_stats():
    """Basic corpus statistics."""
    db = get_db()
    total = db.execute("SELECT COUNT(*) as c FROM paragraphs").fetchone()["c"]
    volumes = db.execute("SELECT COUNT(DISTINCT volume_id) as c FROM paragraphs").fetchone()["c"]
    years = db.execute("SELECT MIN(year) as min_y, MAX(year) as max_y FROM paragraphs WHERE year IS NOT NULL").fetchone()
    return {
        "total_paragraphs": total,
        "volumes": volumes,
        "date_range": f"{years['min_y']}–{years['max_y']}" if years['min_y'] else "N/A"
    }

# ===== CACHE =====

_cache = {}

def load_cache(name: str):
    """Load JSON cache file from data/ directory."""
    if name in _cache:
        return _cache[name]
    path = SITE_DIR / "data" / name
    if path.exists():
        try:
            with open(path) as f:
                _cache[name] = json.load(f)
            return _cache[name]
        except Exception:
            pass
    return {}

# Verify API key
def verify_api_key(x_api_key: str = None) -> bool:
    if not x_api_key:
        return False
    valid = x_api_key.startswith("lenin-") and len(x_api_key) > 20
    return valid

# Common headers
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-API-Key",
}
