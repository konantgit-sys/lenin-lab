"""Ideology Comparator routes — Product #4."""
import sys, sqlite3
from pathlib import Path
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

SITE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SITE_ROOT))

from shared.lenin_core import DB_PATH, logger

router = APIRouter(tags=["Ideology Comparator"])

@router.get("/comparator")
@router.get("/comparator/")
async def comparator_index():
    return FileResponse(str(SITE_ROOT / "products" / "04_ideology_comparator" / "index.html"))

@router.get("/api/comparator/topics")
async def comparator_topics():
    """List all available comparison topics."""
    try:
        sys.path.insert(0, str(SITE_ROOT / "engines"))
        from engine_09_comparative import MARXIST_BASIS
        topics = sorted(MARXIST_BASIS.keys())
        return [{"topic": t} for t in topics]
    except Exception as e:
        logger.error(f"[comparator/topics] {e}")
        return {"error": str(e)}

@router.get("/api/comparator/compare")
async def comparator_compare(topic: str = Query(default="")):
    """Compare Lenin with Marx and Engels on a specific topic."""
    if not topic.strip():
        return {"error": "topic required"}
    
    try:
        sys.path.insert(0, str(SITE_ROOT / "engines"))
        from engine_09_comparative import MARXIST_BASIS, get_lenin_position

        topic_lower = topic.strip().lower()

        # Case-insensitive lookup in MARXIST_BASIS
        basis = {}
        for k, v in MARXIST_BASIS.items():
            if k.lower() == topic_lower:
                basis = v
                break

        db = Path(DB_PATH)
        conn = sqlite3.connect(str(db))
        raw_lenin = get_lenin_position(conn, topic_lower) or {}

        marx_mentions = 0
        engels_mentions = 0
        if topic_lower:
            patterns = [f"%{topic_lower}%"]
            words = topic_lower.split()
            if len(words) > 1:
                patterns += [f"%{w}%" for w in words if len(w) > 3]

            for pat in patterns:
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM paragraphs WHERE (text LIKE '%Маркс%' OR text LIKE '%Маркса%') AND text LIKE ?",
                    (pat,)
                ).fetchone()[0]
                if cnt > 0:
                    marx_mentions = max(marx_mentions, cnt)

                cnt = conn.execute(
                    "SELECT COUNT(*) FROM paragraphs WHERE text LIKE '%Энгельс%' AND text LIKE ?",
                    (pat,)
                ).fetchone()[0]
                if cnt > 0:
                    engels_mentions = max(engels_mentions, cnt)

        total_mentions = marx_mentions + engels_mentions

        base_match = 0
        if raw_lenin and basis:
            l_text = raw_lenin.get("text", "").lower()
            m_text = (basis.get("marx", "") + " " + basis.get("engels", "")).lower()
            m_words = set(m_text.split())
            if m_words:
                l_words = set(l_text.split())
                overlap = len(l_words & m_words)
                base_match = min(95, round(overlap / len(m_words) * 100))

        conn.close()

        return {
            "topic": topic_lower,
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
                "years": str(raw_lenin.get("year", "")) if raw_lenin else "",
                "quotes": [raw_lenin.get("text", "")] if raw_lenin else [],
                "volume": raw_lenin.get("volume", ""),
                "mentions": total_mentions,
                "base_match": base_match
            },
            "development": "Ленин применил марксистские положения к российским условиям, добавив анализ империализма, авангардной партии и союза рабочих с крестьянством.",
            "divergence": ""
        }
    except Exception as e:
        logger.error(f"[comparator/compare] {e}")
        return {"error": str(e)}
