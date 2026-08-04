"""
Tests for Engine #1: Хронологическая разметка
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_01_chronology import (
    add_year_column,
    annotate_years,
    get_chronology_stats,
    get_period,
    DB_PATH,
    VOLUME_TO_YEAR,
)


def test_period_classification():
    """Периодизация корректна."""
    assert get_period(1895) == "дореволюционный"
    assert get_period(1916) == "дореволюционный"
    assert get_period(1917) == "революция"
    assert get_period(1918) == "советский"
    assert get_period(1923) == "советский"
    print("✅ test_period_classification passed")


def test_volume_year_mapping():
    """Маппинг покрывает все 55 томов."""
    assert len(VOLUME_TO_YEAR) == 55, f"Expected 55, got {len(VOLUME_TO_YEAR)}"
    assert min(VOLUME_TO_YEAR.keys()) == 1
    assert max(VOLUME_TO_YEAR.keys()) == 55
    all_years = set(VOLUME_TO_YEAR.values())
    assert min(all_years) >= 1893, f"Min year {min(all_years)}"
    assert max(all_years) <= 1923, f"Max year {max(all_years)}"
    print("✅ test_volume_year_mapping passed")


def test_year_column_added():
    """Колонка year существует."""
    conn = sqlite3.connect(str(DB_PATH))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(paragraphs)").fetchall()]
    conn.close()
    assert "year" in cols, "Column 'year' not found in paragraphs table"
    print("✅ test_year_column_added passed")


def test_all_paragraphs_have_year():
    """Все 169 067 параграфов имеют год."""
    conn = sqlite3.connect(str(DB_PATH))
    total = conn.execute("SELECT COUNT(*) FROM paragraphs").fetchone()[0]
    with_year = conn.execute(
        "SELECT COUNT(*) FROM paragraphs WHERE year IS NOT NULL"
    ).fetchone()[0]
    without_year = total - with_year
    conn.close()

    assert total == with_year, f"{without_year} paragraphs missing year"
    print(f"✅ test_all_paragraphs_have_year passed ({total} paragraphs, all annotated)")


def test_years_in_range():
    """Все года в диапазоне 1893–1923."""
    conn = sqlite3.connect(str(DB_PATH))
    bad = conn.execute(
        "SELECT COUNT(*) FROM paragraphs WHERE year < 1893 OR year > 1923"
    ).fetchone()[0]
    conn.close()
    assert bad == 0, f"{bad} paragraphs have invalid years"
    print("✅ test_years_in_range passed")


def test_distribution_matches_volumes():
    """Распределение параграфов по годам совпадает с ожидаемым."""
    conn = sqlite3.connect(str(DB_PATH))
    vol_counts = {}
    for row in conn.execute(
        "SELECT volume_id, COUNT(*) FROM paragraphs GROUP BY volume_id"
    ):
        vol_counts[row[0]] = row[1]
    conn.close()

    # Группируем по годам
    year_from_vol = {}
    for vol, year in VOLUME_TO_YEAR.items():
        if vol in vol_counts:
            year_from_vol[year] = year_from_vol.get(year, 0) + vol_counts[vol]

    # Сравниваем с фактическим распределением
    conn = sqlite3.connect(str(DB_PATH))
    year_actual = {}
    for row in conn.execute(
        "SELECT year, COUNT(*) FROM paragraphs GROUP BY year"
    ):
        year_actual[row[0]] = row[1]
    conn.close()

    for year, expected in year_from_vol.items():
        actual = year_actual.get(year, 0)
        assert actual == expected, (
            f"Year {year}: expected {expected} paragraphs, got {actual}"
        )

    print("✅ test_distribution_matches_volumes passed")


def test_get_chronology_stats():
    """Статистика возвращает корректные данные."""
    stats = get_chronology_stats()
    assert stats["status"] == "annotated"
    assert stats["total_paragraphs"] == 169067
    assert stats["with_year"] == 169067
    assert stats["volumes"] == 55
    assert stats["year_range"] == "1893-1922"  # Последний том 1922
    assert stats["years_covered"] > 20

    assert "дореволюционный" in stats["periods"]
    assert "революция" in stats["periods"]
    assert "советский" in stats["periods"]

    period_sum = sum(stats["periods"].values())
    assert period_sum == stats["total_paragraphs"]

    print("✅ test_get_chronology_stats passed")


if __name__ == "__main__":
    print("=" * 50)
    print("Engine #1: Chronology Tests")
    print("=" * 50)

    test_period_classification()
    test_volume_year_mapping()
    test_year_column_added()
    test_all_paragraphs_have_year()
    test_years_in_range()
    test_distribution_matches_volumes()
    test_get_chronology_stats()

    print("\n" + "=" * 50)
    print("✅ ALL 7 TESTS PASSED")
    print("=" * 50)
