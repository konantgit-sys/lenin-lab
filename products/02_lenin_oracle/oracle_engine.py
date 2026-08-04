#!/usr/bin/env python3
"""
Lenin Oracle Engine
Semantic search → real Lenin quotes. No LLM hallucinations.
Uses Mistral AI API for embeddings + FAISS for search.
"""

import sqlite3
import numpy as np
import faiss
import requests
import time
import os
from dataclasses import dataclass
from typing import List

# Config
MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_URL = "https://api.mistral.ai/v1/embeddings"
MODEL = "mistral-embed"
EMBEDDING_DIM = 1024

DB_PATH = "/home/agent/data/projects/lenin-knowledge/lenin.db"
FAISS_INDEX = "/home/agent/data/projects/lenin-knowledge/embeddings/final_faiss.index"
IDS_PATH = "/home/agent/data/projects/lenin-knowledge/embeddings/final_ids.npy"

# Cache
_index = None
_ids = None
_db_conn = None

@dataclass
class QuoteResult:
    paragraph_id: int
    text: str
    year: int
    volume: int
    score: float
    chapter: str = ""


def _get_index():
    global _index, _ids
    if _index is None:
        if not os.path.exists(FAISS_INDEX):
            raise FileNotFoundError(f"FAISS index not found at {FAISS_INDEX} — using FTS5 fallback")
        _index = faiss.read_index(FAISS_INDEX)
        _ids = np.load(IDS_PATH)
    return _index, _ids


def _search_fts5(query: str, k: int = 10) -> List[QuoteResult]:
    """Fallback: FTS5 search when FAISS index is unavailable."""
    db = _get_db()
    # Split query into words for FTS5
    terms = ' OR '.join(query.split())
    rows = db.execute("""
        SELECT p.id, p.text, p.year, p.volume_id,
               (LENGTH(p.text) - LENGTH(REPLACE(LOWER(p.text), LOWER(?), ''))) * 1.0 / LENGTH(p.text) as score
        FROM paragraphs p
        WHERE p.text LIKE '%' || ? || '%' AND LENGTH(p.text) > 100
        ORDER BY score DESC
        LIMIT ?
    """, (query, query, k * 3)).fetchall()

    results = []
    seen_texts = set()
    for row in rows:
        para_id, text, year, volume, score = row
        # Deduplicate similar texts
        short = text[:80]
        if short in seen_texts:
            continue
        seen_texts.add(short)
        results.append(QuoteResult(
            paragraph_id=para_id,
            text=text.strip(),
            year=year or 0,
            volume=volume or 0,
            score=min(score * 200, 0.95),
        ))
        if len(results) >= k:
            break
    return results


def _get_db():
    global _db_conn
    if _db_conn is None:
        _db_conn = sqlite3.connect(DB_PATH)
        _db_conn.row_factory = sqlite3.Row
    return _db_conn


def embed_query(text: str) -> np.ndarray:
    """Embed a query using Mistral AI API."""
    resp = requests.post(
        MISTRAL_URL,
        headers={
            "Authorization": f"Bearer {MISTRAL_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": MODEL, "input": [text]},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Mistral API error {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    vec = np.array(data["data"][0]["embedding"], dtype=np.float32)
    return vec.reshape(1, -1)


def search(query: str, k: int = 10) -> List[QuoteResult]:
    """
    Search for relevant Lenin quotes.
    Uses FAISS when available, FTS5 fallback otherwise.
    """
    db = _get_db()

    try:
        index, ids = _get_index()
        # Embed query
        q_vec = embed_query(query)
        # FAISS search
        distances, indices = index.search(q_vec, k)
    except (FileNotFoundError, RuntimeError, Exception) as e:
        # Fallback to FTS5
        return _search_fts5(query, k)

    results = []
    seen_texts = set()
    seen_volumes = set()

    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(ids):
            continue

        para_id = int(ids[idx])
        similarity = float(1.0 / (1.0 + dist))  # Convert L2 distance to 0-1 score

        # Fetch from DB
        row = db.execute(
            """
            SELECT p.id, p.text, p.year, v.title as volume_title, p.chapter, p.char_count
            FROM paragraphs p
            JOIN volumes v ON p.volume_id = v.id
            WHERE p.id = ?
            """,
            (para_id,),
        ).fetchone()

        if not row:
            continue

        text = row["text"]
        year = row["year"] or 0
        volume_str = row["volume_title"] or "?"

        # Parse volume number
        import re
        vol_match = re.search(r'[Тт]ом\s+(\d+)', volume_str)
        volume = int(vol_match.group(1)) if vol_match else 0

        # Deduplicate: skip near-identical texts and same volume
        text_key = text[:60]
        if text_key in seen_texts:
            continue
        if volume in seen_volumes and len(seen_volumes) >= 3:
            continue  # After 3 unique volumes, allow volume reuse

        seen_texts.add(text_key)
        seen_volumes.add(volume)

        results.append(QuoteResult(
            paragraph_id=para_id,
            text=text.strip(),
            year=year,
            volume=volume,
            score=similarity,
            chapter=row["chapter"] or "",
        ))

    # Sort by balance of score and diversity (year spread bonus)
    results.sort(key=lambda r: r.score, reverse=True)

    return results[:k]


def format_response(results: List[QuoteResult], query: str) -> str:
    """Format search results into a readable response."""
    if not results:
        return "Не нашёл точных цитат по вашему запросу. Попробуйте переформулировать."

    lines = []
    for i, r in enumerate(results[:5]):
        # Truncate long quotes
        text = r.text
        if len(text) > 400:
            text = text[:397] + "..."

        year_str = f"{r.year} г." if r.year else "б/д"
        lines.append(f"{year_str}, том {r.volume} (релевантность: {r.score:.0%})")
        lines.append(f"«{text}»")
        lines.append("")

    return "\n".join(lines)


def get_random_quote() -> QuoteResult:
    """Return a random high-quality quote."""
    db = _get_db()
    row = db.execute(
        """
        SELECT p.id, p.text, p.year, v.title, p.chapter
        FROM paragraphs p
        JOIN volumes v ON p.volume_id = v.id
        WHERE p.char_count > 100 AND p.char_count < 500
        ORDER BY RANDOM()
        LIMIT 1
        """
    ).fetchone()

    if not row:
        return QuoteResult(0, "Нет цитат", 0, 0, 0.0)

    import re
    vol_match = re.search(r'[Тт]ом\s+(\d+)', row["title"] or "")
    volume = int(vol_match.group(1)) if vol_match else 0

    return QuoteResult(
        paragraph_id=row["id"],
        text=row["text"].strip(),
        year=row["year"] or 0,
        volume=volume,
        score=1.0,
        chapter=row["chapter"] or "",
    )


def get_stats() -> dict:
    """Get usage statistics."""
    db = _get_db()
    total = db.execute("SELECT COUNT(*) FROM paragraphs").fetchone()[0]
    quoted = db.execute("SELECT COUNT(*) FROM lenin_quotes").fetchone()[0]
    years = db.execute("SELECT MIN(year), MAX(year) FROM paragraphs").fetchone()
    return {
        "total_paragraphs": total,
        "scored_quotes": quoted,
        "year_from": years[0],
        "year_to": years[1],
    }


if __name__ == "__main__":
    # Quick test
    results = search("Что Ленин думал о революции?", k=5)
    print(format_response(results, "революция"))
    print("\n--- STATS ---")
    print(get_stats())
