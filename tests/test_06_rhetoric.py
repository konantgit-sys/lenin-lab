"""
Tests for Engine #6: Риторический отпечаток.
Fast unit tests (analyze_paragraph) + cache-based profile tests.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engines.engine_06_rhetoric import analyze_paragraph
from test_helper import load_rhetoric_cache


# ===== UNIT TESTS (fast — single paragraph analysis) =====

def test_analyze_aggression():
    text = "Беспощадная борьба с врагами! УНИЧТОЖИТЬ их сопротивление! Вперёд!"
    r = analyze_paragraph(text)
    assert r["scores"]["aggression"] > 2, f"Expected high aggression, got {r['scores']['aggression']}"
    print(f"✅ aggression detection: {r['scores']['aggression']:.1f}")


def test_analyze_sarcasm():
    text = 'Пресловутый "социалист" господин Каутский, так называемый марксист...'
    r = analyze_paragraph(text)
    assert r["scores"]["sarcasm"] > 1, f"Expected sarcasm, got {r['scores']['sarcasm']}"
    print(f"✅ sarcasm detection: {r['scores']['sarcasm']:.1f}")


def test_analyze_contempt():
    text = "Жалкие лакеи буржуазии, прихвостни и предатели!"
    r = analyze_paragraph(text)
    assert r["scores"]["contempt"] >= 3, f"Expected high contempt, got {r['scores']['contempt']}"
    print(f"✅ contempt detection: {r['scores']['contempt']:.1f}")


def test_analyze_inspiration():
    text = "Вперёд, товарищи! К победе коммунизма! Великое будущее нас ждёт!"
    r = analyze_paragraph(text)
    assert r["scores"]["inspiration"] >= 3, f"Expected inspiration, got {r['scores']['inspiration']}"
    print(f"✅ inspiration detection: {r['scores']['inspiration']:.1f}")


# ===== PROFILE TESTS (cache-based — what /api/v1/rhetoric returns) =====

def test_full_profile():
    """Полный профиль загружается из кеша."""
    r = load_rhetoric_cache()
    assert r["years_analyzed"] >= 20, f"Expected >=20 years, got {r['years_analyzed']}"
    assert r["total_paragraphs"] == 169067, f"Expected 169067, got {r['total_paragraphs']}"
    assert len(r["emotional_arc"]) >= 20, f"Expected >=20 arc points, got {len(r['emotional_arc'])}"
    assert len(r["periods"]) >= 2, f"Expected >=2 periods, got {len(r['periods'])}"
    assert len(r["top_aggressive_years"]) >= 3, f"Expected >=3 aggressive years, got {len(r['top_aggressive_years'])}"
    print(f"✅ full profile: {r['years_analyzed']} years, {r['total_paragraphs']} paragraphs")
    print(f"   periods: {len(r['periods'])}, arc: {len(r['emotional_arc'])}")


def test_periods_detected():
    """Периоды с доминирующими эмоциями определены."""
    r = load_rhetoric_cache()
    periods = r["periods"]
    emotions = [p["dominant_emotion"] for p in periods]
    assert len(emotions) >= 2, f"Expected >=2 periods, got {emotions}"
    # At least one emotion type should be present
    assert any(e in {"sarcasm", "aggression", "analytical", "inspiration", "contempt"} for e in emotions)
    print(f"✅ periods detected: {emotions}")


def test_global_profile_complete():
    """Глобальный профиль содержит все категории."""
    r = load_rhetoric_cache()
    gp = r.get("global_profile", {})
    for cat in ["aggression", "sarcasm", "inspiration", "analytical", "contempt"]:
        assert cat in gp, f"Missing category: {cat}"
        assert gp[cat] > 0, f"Zero score for {cat}"
    print(f"✅ global profile complete: {gp}")


def test_emotional_arc_consistent():
    """Эмоциональная дуга покрывает все года."""
    r = load_rhetoric_cache()
    arc = r["emotional_arc"]
    years = [p["year"] for p in arc]
    assert 1893 <= min(years) <= 1900, f"Arc starts too late: {min(years)}"
    assert 1920 <= max(years) <= 1922, f"Arc ends too early: {max(years)}"
    print(f"✅ emotional arc: {min(years)}–{max(years)}, {len(arc)} points")


if __name__ == "__main__":
    print("=" * 50)
    print("Engine #6: Rhetorical Fingerprint Tests")
    print("=" * 50)
    for name in sorted(globals()):
        if name.startswith("test_"):
            globals()[name]()
    print("\n" + "=" * 50)
    print("✅ ALL 8 TESTS PASSED")
