"""
LENIN CORE — Shared module for all 10 products.

Provides:
- FAISS semantic search (93,711 vectors)
- FTS5 full-text search
- SQLite direct access
- Cached query helpers

All products import from here.
"""

import os
import sqlite3
import json
import numpy as np

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Path: sites/lenin-book/shared/lenin_core.py -> data/ (grandparent of sites/)
DATA_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
KNOWLEDGE_DIR = os.path.join(DATA_ROOT, "projects", "lenin-knowledge")
DB_PATH = os.path.join(KNOWLEDGE_DIR, "lenin.db")
FAISS_PATH = os.path.join(KNOWLEDGE_DIR, "embeddings", "final_faiss.index")
SITE_DIR = BASE_DIR  # lenin-book directory

# --- Lazy FAISS ---
_faiss_index = None

def get_faiss():
    global _faiss_index
    if _faiss_index is None:
        import faiss
        _faiss_index = faiss.read_index(FAISS_PATH)
    return _faiss_index

# --- SQLite connection ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- FAISS Search ---
def faiss_search(query_vector: np.ndarray, k: int = 10) -> list:
    """Returns list of (paragraph_id, distance) tuples."""
    index = get_faiss()
    if query_vector.ndim == 1:
        query_vector = query_vector.reshape(1, -1)
    distances, indices = index.search(query_vector.astype(np.float32), k)
    results = []
    for i in range(len(indices[0])):
        pid = int(indices[0][i]) + 1
        dist = float(distances[0][i])
        results.append((pid, dist))
    return results

# --- FTS5 Search ---
def fts5_search(query: str, limit: int = 20, year: int = None) -> list:
    """Full-text search returning list of dicts."""
    conn = get_db()
    # Escape FTS5 special chars
    q = query.replace('"', '').replace("'", "''")
    if year:
        rows = conn.execute(
            "SELECT p.id, p.year, p.volume_id, p.chapter, substr(p.text, 1, 200) as snippet "
            "FROM paragraphs_fts f JOIN paragraphs p ON f.rowid = p.id "
            "WHERE f.text MATCH ? AND p.year = ? LIMIT ?",
            (q, year, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT p.id, p.year, p.volume_id, p.chapter, substr(p.text, 1, 200) as snippet "
            "FROM paragraphs_fts f JOIN paragraphs p ON f.rowid = p.id "
            "WHERE f.text MATCH ? LIMIT ?",
            (q, limit)
        ).fetchall()
    return [dict(r) for r in rows]

# --- Paragraph by ID ---
def get_paragraph(pid: int) -> dict:
    conn = get_db()
    row = conn.execute("SELECT * FROM paragraphs WHERE id=?", (pid,)).fetchone()
    return dict(row) if row else None

# --- Stats ---
def get_stats() -> dict:
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM paragraphs").fetchone()[0]
    years = conn.execute("SELECT COUNT(DISTINCT year) FROM paragraphs WHERE year IS NOT NULL").fetchone()[0]
    return {"total_paragraphs": total, "years_covered": years, "volumes": 55}

# --- Cache loader ---
_cache = {}

def load_cache(filename: str) -> dict:
    if filename not in _cache:
        path = os.path.join(SITE_DIR, filename)
        with open(path) as f:
            _cache[filename] = json.load(f)
    return _cache[filename]

# --- Quick quote ---
def random_quote() -> dict:
    conn = get_db()
    row = conn.execute(
        "SELECT text, year, volume_id FROM paragraphs WHERE length(text) BETWEEN 80 AND 400 ORDER BY RANDOM() LIMIT 1"
    ).fetchone()
    return dict(row) if row else None
