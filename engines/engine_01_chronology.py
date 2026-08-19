"""
Engine #1: Хронологическая разметка
Добавляет год и период к каждому из 169 067 параграфов.
"""

import sqlite3
import json
from pathlib import Path
import os

DB_PATH = Path(os.environ.get("LENIN_DB", "/home/agent/data/projects/lenin-knowledge/lenin.db"))

# Маппинг том → год на основе реальной хронологии ПСС (5-е издание)
VOLUME_TO_YEAR = {
    1: 1893, 2: 1895, 3: 1899, 4: 1898, 5: 1901,
    6: 1902, 7: 1903, 8: 1905, 9: 1905, 10: 1905,
    11: 1905, 12: 1906, 13: 1907, 14: 1908, 15: 1908,
    16: 1909, 17: 1910, 18: 1911, 19: 1912, 20: 1913,
    21: 1914, 22: 1914, 23: 1915, 24: 1916, 25: 1917,
    26: 1917, 27: 1917, 28: 1917, 29: 1917, 30: 1917,
    31: 1918, 32: 1918, 33: 1918, 34: 1917, 35: 1918,
    36: 1918, 37: 1918, 38: 1919, 39: 1919, 40: 1919,
    41: 1920, 42: 1920, 43: 1921, 44: 1921, 45: 1922,
    46: 1922, 47: 1914, 48: 1918, 49: 1919, 50: 1920,
    51: 1919, 52: 1921, 53: 1917, 54: 1917, 55: 1917,
}

# Периодизация
def get_period(year: int) -> str:
    if year <= 1916:
        return "дореволюционный"
    elif year == 1917:
        return "революция"
    else:
        return "советский"


def add_year_column(conn: sqlite3.Connection) -> bool:
    """Добавляет колонку year, если её ещё нет."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(paragraphs)").fetchall()]
    if "year" not in cols:
        conn.execute("ALTER TABLE paragraphs ADD COLUMN year INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_paragraphs_year ON paragraphs(year)")
        return True
    return False


def annotate_years(conn: sqlite3.Connection) -> dict:
    """Размечает все параграфы годами на основе volume_id."""
    add_year_column(conn)

    for vol, year in VOLUME_TO_YEAR.items():
        conn.execute(
            "UPDATE paragraphs SET year = ? WHERE volume_id = ? AND year IS NULL",
            (year, vol),
        )

    conn.commit()

    # Статистика
    total = conn.execute("SELECT COUNT(*) FROM paragraphs").fetchone()[0]
    with_year = conn.execute(
        "SELECT COUNT(*) FROM paragraphs WHERE year IS NOT NULL"
    ).fetchone()[0]
    without_year = total - with_year

    distribution = {}
    for row in conn.execute(
        "SELECT year, COUNT(*) FROM paragraphs WHERE year IS NOT NULL GROUP BY year ORDER BY year"
    ):
        distribution[row[0]] = row[1]

    periods = {}
    for row in conn.execute(
        "SELECT year, COUNT(*) FROM paragraphs WHERE year IS NOT NULL GROUP BY year ORDER BY year"
    ):
        period = get_period(row[0])
        periods[period] = periods.get(period, 0) + row[1]

    return {
        "total_paragraphs": total,
        "with_year": with_year,
        "without_year": without_year,
        "year_range": f"{min(distribution.keys())}-{max(distribution.keys())}",
        "distribution": distribution,
        "periods": periods,
    }


def get_chronology_stats() -> dict:
    """Возвращает статистику хронологической разметки."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        add_year_column(conn)

        total = conn.execute("SELECT COUNT(*) FROM paragraphs").fetchone()[0]
        with_year = conn.execute(
            "SELECT COUNT(*) FROM paragraphs WHERE year IS NOT NULL"
        ).fetchone()[0]

        if with_year == 0:
            return {"status": "not_annotated", "total_paragraphs": total}

        distribution = {}
        for row in conn.execute(
            "SELECT year, COUNT(*) FROM paragraphs WHERE year IS NOT NULL GROUP BY year ORDER BY year"
        ):
            distribution[row[0]] = row[1]

        periods = {}
        for y, cnt in distribution.items():
            period = get_period(y)
            periods[period] = periods.get(period, 0) + cnt

        return {
            "status": "annotated",
            "total_paragraphs": total,
            "with_year": with_year,
            "without_year": total - with_year,
            "year_range": f"{min(distribution.keys())}-{max(distribution.keys())}",
            "volumes": 55,
            "years_covered": len(distribution),
            "distribution": distribution,
            "periods": periods,
        }
    finally:
        conn.close()


def run_annotation() -> dict:
    """Запускает полную хронологическую разметку."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        return annotate_years(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    result = run_annotation()
    print(json.dumps(result, indent=2, ensure_ascii=False))
