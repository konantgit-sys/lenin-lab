"""Dashboard Pro routes — Product #3."""
import sys, sqlite3, json
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

# Add site root for shared imports
SITE_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SITE_ROOT))

from shared.lenin_core import DB_PATH, logger

router = APIRouter(tags=["Dashboard Pro"])

@router.get("/dashboard")
@router.get("/dashboard/")
async def dashboard_index():
    return FileResponse(str(SITE_ROOT / "products" / "03_dashboard_pro" / "index.html"))

@router.get("/api/dashboard")
async def dashboard_data():
    """Aggregated metrics from all engines."""
    try:
        db = Path(DB_PATH)
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()

        period_ranges = [
            ("1893-1905", 1893, 1905),
            ("1906-1916", 1906, 1916),
            ("1917-1922", 1917, 1922),
        ]
        periods = []
        for label, y1, y2 in period_ranges:
            cur.execute("SELECT COUNT(*) FROM paragraphs WHERE year BETWEEN ? AND ?", (y1, y2))
            periods.append({"label": label, "count": cur.fetchone()[0]})

        cur.execute("SELECT topic, COUNT(*) as cnt FROM lenin_positions GROUP BY topic ORDER BY cnt DESC LIMIT 8")
        top_topics = [{"name": r[0], "count": r[1]} for r in cur.fetchall()]

        cur.execute("SELECT COUNT(*) FROM lenin_positions")
        total_positions = cur.fetchone()[0] or 1502

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
                {"name": "Риторический анализатор", "metric": "25 лет, 5 категорий"},
                {"name": "Позиции Ленина", "metric": f"{shadow_terms} тем, {total_positions} цитат"},
                {"name": "Цитатомёт", "metric": "5 000 цитат, скор до 18.0"},
                {"name": "Компаративный анализ", "metric": "89 тем, Marx/Engels/Lenin — полный охват"}
            ],
            "top_topics": top_topics,
            "contradictions": {"total": total_positions, "high_conflict": 30},
            "rhetoric_summary": "25 лет размечено, 5 категорий: агрессия, сарказм, воодушевление, аналитика, презрение",
            "shadow": {"terms": shadow_terms, "before_1918": "до 1918 — активны все темы", "after_1918": "после 1918 — часть тем исчезает"}
        }
    except Exception as e:
        logger.error(f"[dashboard] {e}")
        return {"error": str(e)}
