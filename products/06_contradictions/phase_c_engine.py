#!/usr/bin/env python3
"""
Phase C Engines — Products 6, 7, 8:
  C1: Lenin vs Lenin — Contradiction Detector
  C2: Shadow Structure — Word Frequency Drift
  C3: Stylometric Passport — Text DNA by Year
"""

import sqlite3, re, math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import os

DB = os.environ.get("LENIN_DB", "/home/agent/data/projects/lenin-knowledge/lenin.db")

# =============================================================================
# UTILS
# =============================================================================

def _db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# =============================================================================
# C1: LENIN VS LENIN — CONTRADICTION DETECTOR
# =============================================================================

# Keywords to detect contradictions between positions
CONTRADICTION_KEYWORDS = {
    "negation": ["напротив", "наоборот", "нельзя сказать", "неверно что", "ошибочно", "не так"],
    "softening": ["однако", "тем не менее", "в то же время", "с другой стороны", "но это"],
    "shift_markers": ["раньше", "прежде", "теперь", "сейчас", "в настоящее время",
                      "до сих пор", "отныне", "впредь", "в новых условиях"],
    "direct_opposition": ["необходимо", "нужно", "следует", "должны"]  # for analysis of normative changes
}

POLITICAL_PIVOT_YEARS = [1905, 1914, 1917, 1921]  # Years where positions often change

@dataclass
class Contradiction:
    topic: str
    year1: int
    year2: int
    position1: str
    position2: str
    score: float          # 0–100: how strong the contradiction is
    explanation: str


def _text_similarity(t1: str, t2: str) -> float:
    """Simple Jaccard-style similarity using overlapping significant words."""
    def tokens(text):
        return set(re.findall(r'[а-яё]{4,}', text.lower()))
    s1, s2 = tokens(t1), tokens(t2)
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def _detect_negation(text: str) -> float:
    """Score how much negation/contrast this position contains."""
    neg_words = ["не ", "ни ", "нет", "нельзя", "невозможно", "ошибочно",
                 "наоборот", "напротив", "отнюдь", "вовсе"]
    count = sum(text.lower().count(w) for w in neg_words)
    return min(count / max(len(text.split()) * 0.01, 1), 1.0)


def _detect_temporal(text: str) -> bool:
    """Check if text contains temporal shift markers."""
    markers = ["раньше", "прежде", "теперь", "сейчас", "до сих пор",
               "отныне", "впредь", "в новых условиях", "после"]
    return any(m in text.lower() for m in markers)


def detect_contradictions() -> List[Contradiction]:
    """Find Lenin contradicting himself across years on the same topic."""
    db = _db()

    # Get all topics with positions in wildly different years
    rows = db.execute("""
        SELECT topic, COUNT(*) as cnt, MIN(year) as min_y, MAX(year) as max_y
        FROM lenin_positions
        GROUP BY topic
        HAVING cnt >= 2 AND max_y - min_y >= 8
        ORDER BY max_y - min_y DESC
    """).fetchall()

    results = []

    for r in rows:
        topic = r["topic"]
        # Get all positions for this topic
        positions = db.execute(
            "SELECT * FROM lenin_positions WHERE topic=? ORDER BY year",
            (topic,)
        ).fetchall()

        if len(positions) < 2:
            continue

        # Compare earliest vs latest position
        p1, p2 = positions[0], positions[-1]
        year_gap = p2["year"] - p1["year"]

        if year_gap < 8:
            continue

        # Cross one of the political pivot points?
        crossed_pivot = any(p1["year"] <= p <= p2["year"] for p in POLITICAL_PIVOT_YEARS)

        sim = _text_similarity(p1["text"], p2["text"])
        neg = _detect_negation(p2["text"])  # negation in later text
        temporal = _detect_temporal(p2["text"])

        # Score: low similarity + negation in later text = strong contradiction
        contradiction_score = ((1 - sim) * 50 + neg * 30 + (15 if temporal else 0) + (15 if crossed_pivot else 0))

        if contradiction_score < 25:
            continue

        explanation_parts = []
        if crossed_pivot:
            pivot = [p for p in POLITICAL_PIVOT_YEARS if p1["year"] <= p <= p2["year"]]
            explanation_parts.append(f"Пересекает переломный {pivot[0]} год")
        if temporal:
            explanation_parts.append("Содержит маркеры изменения позиции")
        if neg > 0.3:
            explanation_parts.append("Высокая плотность отрицаний в более позднем тексте")
        if sim < 0.2:
            explanation_parts.append("Низкая лексическая схожесть между позициями")

        results.append(Contradiction(
            topic=topic,
            year1=p1["year"],
            year2=p2["year"],
            position1=p1["text"][:400],
            position2=p2["text"][:400],
            score=round(min(contradiction_score, 100), 1),
            explanation="; ".join(explanation_parts)
        ))

    db.close()

    # Sort by score descending
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:30]


# =============================================================================
# C2: SHADOW STRUCTURE — WORD FREQUENCY DRIFT
# =============================================================================

# Key ideological terms to track
TRACKED_TERMS = [
    "демократия", "свобода", "товарищ", "диктатура", "революция",
    "партия", "социализм", "коммунизм", "буржуазия", "пролетариат",
    "крестьянство", "совет", "террор", "насилие", "государство",
    "кооперация", "нэп", "концессия", "империализм", "война",
    "мир", "класс", "борьба", "власть", "народ",
    "интеллигенция", "бюрократия", "дисциплина", "учёт", "контроль"
]

@dataclass
class ShadowEvent:
    term: str
    pre_1919_freq: float   # mentions per 1000 paragraphs before 1919
    post_1918_freq: float  # mentions per 1000 paragraphs after 1918
    ratio: float           # post/pre ratio (>1 = grew, <1 = declined)
    trend: str             # "рост", "падение", "стабильно"


def shadow_analysis() -> List[ShadowEvent]:
    """Analyze frequency drift of key terms before/after 1918. OPTIMIZED: batch queries + totals once."""
    db = _db()

    # Query totals ONCE (was 60 queries before)
    pre_total = db.execute("SELECT COUNT(*) as cnt FROM paragraphs WHERE year < 1919").fetchone()["cnt"]
    post_total = db.execute("SELECT COUNT(*) as cnt FROM paragraphs WHERE year >= 1919").fetchone()["cnt"]

    # Batch query: get counts for all terms in 2 queries (was 120 queries before)
    terms_like = ' OR '.join([f'text LIKE \'%{t}%\'' for t in TRACKED_TERMS])
    
    # Pre-1919 counts grouped by term
    pre_rows = db.execute(f"""
        SELECT CASE {''.join([f"WHEN text LIKE '%{t}%' THEN '{t}' " for t in TRACKED_TERMS])} END as term,
               COUNT(*) as cnt
        FROM paragraphs WHERE year < 1919 AND ({terms_like})
        GROUP BY term
    """).fetchall()
    pre_dict = {r["term"]: r["cnt"] for r in pre_rows}

    # Post-1918 counts
    post_rows = db.execute(f"""
        SELECT CASE {''.join([f"WHEN text LIKE '%{t}%' THEN '{t}' " for t in TRACKED_TERMS])} END as term,
               COUNT(*) as cnt
        FROM paragraphs WHERE year >= 1919 AND ({terms_like})
        GROUP BY term
    """).fetchall()
    post_dict = {r["term"]: r["cnt"] for r in post_rows}

    db.close()

    results = []
    for term in TRACKED_TERMS:
        pre = pre_dict.get(term, 0)
        post = post_dict.get(term, 0)

        pre_freq = pre / pre_total * 1000 if pre_total else 0
        post_freq = post / post_total * 1000 if post_total else 0

        if pre_freq < 0.01 and post_freq < 0.01:
            continue

        if pre_freq > 0:
            ratio = post_freq / pre_freq
        else:
            ratio = 999 if post_freq > 0 else 1

        if ratio > 1.5:
            trend = "рост"
        elif ratio < 0.67:
            trend = "падение"
        else:
            trend = "стабильно"

        results.append(ShadowEvent(
            term=term,
            pre_1919_freq=round(pre_freq, 2),
            post_1918_freq=round(post_freq, 2),
            ratio=round(ratio, 2),
            trend=trend
        ))

    results.sort(key=lambda x: abs(x.ratio - 1), reverse=True)
    return results


# =============================================================================
# C3: STYLOMETRIC PASSPORT — TEXT DNA
# =============================================================================

@dataclass
class YearStats:
    year: int
    paragraph_count: int
    avg_sentence_len: float      # chars per sentence
    lexical_diversity: float     # unique words / total words
    caps_ratio: float            # % of uppercase letters
    exclamation_ratio: float     # ! per 100 sentences
    question_ratio: float        # ? per 100 sentences
    avg_paragraph_len: float     # chars per paragraph
    quotative_density: float     # quoted material density
    parenthetical_density: float # parenthetical insertions


def stylometric_passport() -> List[YearStats]:
    """Generate text DNA for each year."""
    db = _db()

    # Get all years
    years = [r[0] for r in db.execute("SELECT DISTINCT year FROM paragraphs ORDER BY year").fetchall()]

    results = []
    for year in years:
        rows = db.execute(
            "SELECT text, char_count FROM paragraphs WHERE year=?",
            (year,)
        ).fetchall()

        if not rows:
            continue

        n = len(rows)
        total_chars = sum(r["char_count"] or 0 for r in rows)

        all_text = " ".join(r["text"] or "" for r in rows)
        words = re.findall(r'\b[а-яё]+\b', all_text.lower())
        unique_words = len(set(words))
        total_words = len(words)

        # Sentence metrics
        sentences = re.split(r'[.!?]+\s+', all_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        total_sent_chars = sum(len(s) for s in sentences)
        avg_sent_len = total_sent_chars / len(sentences) if sentences else 0

        # Caps
        caps = sum(1 for c in all_text if c.isupper() or c in 'Ё')
        caps_ratio = caps / len(all_text) if all_text else 0

        # Exclamations
        excl = all_text.count("!")
        quest = all_text.count("?")
        excl_ratio = excl / len(sentences) * 100 if sentences else 0
        quest_ratio = quest / len(sentences) * 100 if sentences else 0

        # Lexical diversity (type-token ratio, normalized per 1000 words)
        lexical_div = unique_words / total_words if total_words else 0

        # Parenthetical density
        paren = len(re.findall(r'\([^)]+\)', all_text))
        paren_ratio = paren / len(sentences) * 100 if sentences else 0

        # Quotative density
        quotes = len(re.findall(r'«[^»]+»', all_text))
        quotes_ratio = quotes / len(sentences) * 100 if sentences else 0

        results.append(YearStats(
            year=year,
            paragraph_count=n,
            avg_sentence_len=round(avg_sent_len, 1),
            lexical_diversity=round(lexical_div, 4),
            caps_ratio=round(caps_ratio * 100, 3),
            exclamation_ratio=round(excl_ratio, 2),
            question_ratio=round(quest_ratio, 2),
            avg_paragraph_len=round(total_chars / n, 0) if n else 0,
            quotative_density=round(quotes_ratio, 2),
            parenthetical_density=round(paren_ratio, 2),
        ))

    db.close()
    return results


# =============================================================================
# API WRAPPERS
# =============================================================================

def get_contradictions_json() -> List[dict]:
    contras = detect_contradictions()
    return [
        {
            "topic": c.topic,
            "year1": c.year1,
            "year2": c.year2,
            "position1": c.position1,
            "position2": c.position2,
            "score": c.score,
            "explanation": c.explanation,
        }
        for c in contras
    ]


def get_shadow_json() -> List[dict]:
    events = shadow_analysis()
    return [
        {
            "term": e.term,
            "pre_1919_freq": e.pre_1919_freq,
            "post_1918_freq": e.post_1918_freq,
            "ratio": e.ratio,
            "trend": e.trend,
        }
        for e in events
    ]


def get_passport_json() -> List[dict]:
    stats = stylometric_passport()
    return [
        {
            "year": s.year,
            "paragraph_count": s.paragraph_count,
            "avg_sentence_len": s.avg_sentence_len,
            "lexical_diversity": s.lexical_diversity,
            "caps_ratio": s.caps_ratio,
            "exclamation_ratio": s.exclamation_ratio,
            "question_ratio": s.question_ratio,
            "avg_paragraph_len": s.avg_paragraph_len,
            "quotative_density": s.quotative_density,
            "parenthetical_density": s.parenthetical_density,
        }
        for s in stats
    ]


if __name__ == "__main__":
    print("=== CONTRADICTIONS ===")
    for c in detect_contradictions()[:5]:
        print(f"  {c.topic}: {c.year1}→{c.year2} score={c.score}")

    print("\n=== SHADOW STRUCTURE ===")
    for e in shadow_analysis():
        arrow = "⬆" if e.trend == "рост" else ("⬇" if e.trend == "падение" else "→")
        print(f"  {e.term}: {e.pre_1919_freq} → {e.post_1918_freq} ({e.ratio}x) {arrow}")

    print("\n=== STYLOMETRIC ===")
    for s in stylometric_passport():
        print(f"  {s.year}: {s.paragraph_count} pars, sent={s.avg_sentence_len}c, lex_div={s.lexical_diversity}")
