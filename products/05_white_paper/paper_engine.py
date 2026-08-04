#!/usr/bin/env python3
"""
White Paper Generator — Engine
Generates research papers on any Lenin concept.
"""

import sqlite3
import numpy as np
import json
import os
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import List, Dict, Optional

DB_PATH = "/home/agent/data/projects/lenin-knowledge/lenin.db"

@dataclass
class PaperSection:
    title: str
    content_html: str

@dataclass
class WhitePaper:
    topic: str
    title: str
    subtitle: str
    sections: List[PaperSection] = field(default_factory=list)
    images: List[str] = field(default_factory=list)


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_concept_list() -> List[str]:
    """Get all available concepts from lenin_positions."""
    db = _db()
    rows = db.execute(
        "SELECT DISTINCT topic FROM lenin_positions ORDER BY topic"
    ).fetchall()
    db.close()
    return [r["topic"] for r in rows]


def get_positions(topic: str, limit: int = 5) -> List[dict]:
    """Get Lenin's positions on a topic."""
    db = _db()
    rows = db.execute(
        """
        SELECT p.*, v.title as volume_title
        FROM lenin_positions p
        JOIN volumes v ON p.volume_id = v.id
        WHERE p.topic = ?
        ORDER BY p.rank
        LIMIT ?
        """,
        (topic, limit),
    ).fetchall()
    db.close()

    import re
    results = []
    for r in rows:
        vmatch = re.search(r'[Тт]ом\s+(\d+)', r["volume_title"] or "")
        vol = int(vmatch.group(1)) if vmatch else 0
        text = r["text"]
        if len(text) > 500:
            text = text[:497] + "..."
        results.append({
            "year": r["year"],
            "volume": vol,
            "text": text.strip(),
            "score": round(r["relevance_score"], 1),
        })
    return results


def get_quotes(topic: str, limit: int = 5) -> List[dict]:
    """Get best quotes on a topic."""
    db = _db()
    rows = db.execute(
        """
        SELECT q.*, v.title as volume_title
        FROM lenin_quotes q
        JOIN volumes v ON q.volume_id = v.id
        WHERE q.topics LIKE '%' || ? || '%'
        ORDER BY q.aphorism_score DESC
        LIMIT ?
        """,
        (topic, limit),
    ).fetchall()
    db.close()

    import re
    results = []
    for r in rows:
        vmatch = re.search(r'[Тт]ом\s+(\d+)', r["volume_title"] or "")
        vol = int(vmatch.group(1)) if vmatch else 0
        results.append({
            "year": r["year"],
            "volume": vol,
            "text": r["text"].strip(),
            "score": round(r["aphorism_score"], 1),
            "categories": r["categories"] or "",
        })
    return results


def get_timeline(topic: str) -> List[dict]:
    """Get chronological distribution of concept mentions."""
    db = _db()
    # Count paragraphs mentioning the topic by year
    rows = db.execute(
        """
        SELECT p.year, COUNT(*) as cnt
        FROM paragraphs p
        WHERE p.text LIKE '%' || ? || '%'
        GROUP BY p.year
        ORDER BY p.year
        """,
        (topic,),
    ).fetchall()
    db.close()

    return [{"year": r["year"], "count": r["cnt"]} for r in rows if r["year"]]


def get_rhetoric_profile(years: List[int]) -> dict:
    """Get rhetoric summary for given years."""
    if not years:
        return {"dominant": "n/a", "avg_density": 0, "periods": []}

    # Use precomputed rhetoric data
    RHETORIC = [
        {"year":1893,"density":2.239,"dominant":"sarcasm"},
        {"year":1895,"density":2.526,"dominant":"sarcasm"},
        {"year":1898,"density":2.671,"dominant":"sarcasm"},
        {"year":1899,"density":1.895,"dominant":"sarcasm"},
        {"year":1901,"density":2.473,"dominant":"sarcasm"},
        {"year":1902,"density":3.049,"dominant":"sarcasm"},
        {"year":1903,"density":1.995,"dominant":"sarcasm"},
        {"year":1905,"density":2.71,"dominant":"sarcasm"},
        {"year":1906,"density":2.334,"dominant":"sarcasm"},
        {"year":1907,"density":2.415,"dominant":"sarcasm"},
        {"year":1908,"density":2.184,"dominant":"sarcasm"},
        {"year":1909,"density":2.419,"dominant":"sarcasm"},
        {"year":1910,"density":2.518,"dominant":"sarcasm"},
        {"year":1911,"density":2.748,"dominant":"sarcasm"},
        {"year":1912,"density":2.093,"dominant":"sarcasm"},
        {"year":1913,"density":2.456,"dominant":"sarcasm"},
        {"year":1914,"density":2.31,"dominant":"sarcasm"},
        {"year":1915,"density":2.267,"dominant":"sarcasm"},
        {"year":1916,"density":2.098,"dominant":"sarcasm"},
        {"year":1917,"density":2.516,"dominant":"sarcasm"},
        {"year":1918,"density":2.245,"dominant":"sarcasm"},
        {"year":1919,"density":2.057,"dominant":"aggression"},
        {"year":1920,"density":1.876,"dominant":"aggression"},
        {"year":1921,"density":1.622,"dominant":"aggression"},
        {"year":1922,"density":1.403,"dominant":"aggression"},
    ]

    matching = [r for r in RHETORIC if r["year"] in years]
    if not matching:
        return {"dominant": "n/a", "avg_density": 0, "periods": []}

    avg = sum(r["density"] for r in matching) / len(matching)
    doms = Counter(r["dominant"] for r in matching)

    pre_1919 = [r for r in matching if r["year"] < 1919]
    post_1918 = [r for r in matching if r["year"] >= 1919]

    return {
        "dominant": doms.most_common(1)[0][0],
        "avg_density": round(avg, 2),
        "periods": [
            {
                "label": "До 1919",
                "dominant": Counter(r["dominant"] for r in pre_1919).most_common(1)[0][0] if pre_1919 else "n/a",
                "avg_density": round(sum(r["density"] for r in pre_1919) / len(pre_1919), 2) if pre_1919 else 0,
            },
            {
                "label": "1919–1922",
                "dominant": Counter(r["dominant"] for r in post_1918).most_common(1)[0][0] if post_1918 else "n/a",
                "avg_density": round(sum(r["density"] for r in post_1918) / len(post_1918), 2) if post_1918 else 0,
            },
        ],
    }


def get_dialectics(topic: str, limit: int = 3) -> List[dict]:
    """Get dialectical triads on this topic."""
    db = _db()
    rows = db.execute(
        """
        SELECT d.thesis, d.antithesis, d.synthesis, d.year
        FROM dialectical_triples d
        WHERE d.thesis LIKE '%' || ? || '%'
           OR d.antithesis LIKE '%' || ? || '%'
           OR d.synthesis LIKE '%' || ? || '%'
        LIMIT ?
        """,
        (topic, topic, topic, limit),
    ).fetchall()
    db.close()

    return [
        {
            "thesis": r["thesis"],
            "antithesis": r["antithesis"],
            "synthesis": r["synthesis"],
            "year": r["year"],
        }
        for r in rows
    ]


def get_related_concepts(topic: str, limit: int = 8) -> List[str]:
    """Get related concepts from lenin_positions."""
    db = _db()
    # Find other topics that co-occur in paragraphs with this topic
    rows = db.execute(
        """
        SELECT lp2.topic, COUNT(*) as cnt
        FROM lenin_positions lp1
        JOIN lenin_positions lp2 ON lp1.paragraph_id = lp2.paragraph_id
        WHERE lp1.topic = ? AND lp2.topic != ?
        GROUP BY lp2.topic
        ORDER BY cnt DESC
        LIMIT ?
        """,
        (topic, topic, limit),
    ).fetchall()
    db.close()
    return [r["topic"] for r in rows]


def generate_paper(topic: str) -> WhitePaper:
    """Generate a full white paper on a concept."""
    paper = WhitePaper(
        topic=topic,
        title=f"Ленин о {topic}: аналитический обзор",
        subtitle=f"Автоматически сгенерированный исследовательский документ на основе 55 томов ПСС",
    )

    # Collect all data
    positions = get_positions(topic)
    quotes = get_quotes(topic)
    timeline = get_timeline(topic)
    years = [t["year"] for t in timeline if t["year"]]
    rhetoric = get_rhetoric_profile(years)
    dialectics = get_dialectics(topic)
    related = get_related_concepts(topic)

    total_mentions = sum(t["count"] for t in timeline)

    # --- Section 1: Summary ---
    summary_html = f"""
    <div style="margin-bottom:20px">
      <p style="font-size:18px;line-height:1.8;color:#2a1a1a">
        Концепт <strong>«{topic}»</strong> встречается в <strong>{total_mentions:,}</strong> параграфах,
        охватывающих {len(years)} лет (с {min(years) if years else '?'} по {max(years) if years else '?'}).
        Обнаружено <strong>{len(positions)}</strong> ключевых позиций Ленина по данной теме
        и <strong>{len(quotes)}</strong> наиболее афористичных цитат.
      </p>
      <div style="display:flex;gap:20px;margin-top:16px;flex-wrap:wrap">
        <div style="background:#f5f0eb;padding:16px;border-radius:8px;flex:1;min-width:150px">
          <div style="font-size:28px;font-weight:bold;color:#c0392b">{len(positions)}</div>
          <div style="font-size:13px;color:#6a5a5a">ключевых позиций</div>
        </div>
        <div style="background:#f5f0eb;padding:16px;border-radius:8px;flex:1;min-width:150px">
          <div style="font-size:28px;font-weight:bold;color:#c0392b">{total_mentions:,}</div>
          <div style="font-size:13px;color:#6a5a5a">упоминаний</div>
        </div>
        <div style="background:#f5f0eb;padding:16px;border-radius:8px;flex:1;min-width:150px">
          <div style="font-size:28px;font-weight:bold;color:#c0392b">{len(years)}</div>
          <div style="font-size:13px;color:#6a5a5a">лет охвата</div>
        </div>
        <div style="background:#f5f0eb;padding:16px;border-radius:8px;flex:1;min-width:150px">
          <div style="font-size:28px;font-weight:bold;color:#c0392b">{rhetoric['avg_density']}</div>
          <div style="font-size:13px;color:#6a5a5a">ср. ритор. плотность</div>
        </div>
      </div>
    </div>
    """
    paper.sections.append(PaperSection("Аннотация", summary_html))

    # --- Section 2: Chronology ---
    if timeline:
        max_count = max(t["count"] for t in timeline)
        bars = ""
        for t in timeline:
            pct = int(t["count"] / max_count * 100) if max_count else 0
            bars += f"""
            <div style="display:flex;align-items:center;margin-bottom:6px;gap:10px">
              <div style="width:50px;text-align:right;font-size:13px;color:#6a5a5a">{t['year']}</div>
              <div style="flex:1;background:#e8ddd0;border-radius:4px;height:20px;overflow:hidden">
                <div style="background:linear-gradient(90deg,#c0392b,#e74c3c);height:100%;width:{pct}%;border-radius:4px"></div>
              </div>
              <div style="width:60px;font-size:13px;color:#6a5a5a">{t['count']:,}</div>
            </div>
            """

        timeline_html = f"""
        <p style="margin-bottom:14px;color:#4a3a3a">Частота упоминаний концепта «{topic}» по годам:</p>
        <div style="max-width:700px">{bars}</div>
        """
        paper.sections.append(PaperSection("Хронология упоминаний", timeline_html))

    # --- Section 3: Key Positions ---
    if positions:
        pos_html = ""
        for i, p in enumerate(positions):
            pos_html += f"""
            <div style="background:#faf7f3;padding:16px;margin-bottom:12px;border-left:4px solid #c0392b;border-radius:0 8px 8px 0">
              <div style="color:#8a6a5a;font-size:13px;margin-bottom:6px">
                Позиция #{i+1} &nbsp;|&nbsp; {p['year']} г., том {p['volume']} &nbsp;|&nbsp; релевантность: {p['score']}
              </div>
              <div style="line-height:1.7;color:#2a1a1a">«{p['text']}»</div>
            </div>
            """
        paper.sections.append(PaperSection("Ключевые позиции Ленина", pos_html))

    # --- Section 4: Best Quotes ---
    if quotes:
        quote_html = ""
        for i, q in enumerate(quotes):
            categories = q['categories'].replace(',', ', ')
            quote_html += f"""
            <div style="background:#fff;padding:16px;margin-bottom:10px;border:1px solid #e8ddd0;border-radius:8px">
              <div style="font-size:14px;line-height:1.7;color:#2a1a1a;font-style:italic">«{q['text']}»</div>
              <div style="margin-top:8px;font-size:12px;color:#8a6a6a">
                {q['year']} г., том {q['volume']} &nbsp;|&nbsp; афористичность: {q['score']}/18 &nbsp;|&nbsp; {categories}
              </div>
            </div>
            """
        paper.sections.append(PaperSection("Наиболее яркие цитаты", quote_html))

    # --- Section 5: Rhetoric Profile ---
    if rhetoric["periods"]:
        rhet_html = f"""
        <p style="margin-bottom:14px;color:#4a3a3a">Риторический профиль в годы упоминания «{topic}»:</p>
        <div style="display:flex;gap:20px;flex-wrap:wrap">
        """
        for period in rhetoric["periods"]:
            dom = period["dominant"]
            dom_ru = {"sarcasm": "Сарказм", "aggression": "Агрессия", "inspiration": "Воодушевление", "analytical": "Анализ", "contempt": "Презрение"}.get(dom, dom)
            rhet_html += f"""
            <div style="flex:1;min-width:200px;background:#f5f0eb;padding:16px;border-radius:8px">
              <div style="font-size:14px;color:#6a5a5a;margin-bottom:6px">{period['label']}</div>
              <div style="font-size:24px;font-weight:bold;color:#c0392b">{dom_ru}</div>
              <div style="font-size:13px;color:#8a7a6a">плотность: {period['avg_density']}</div>
            </div>
            """
        rhet_html += "</div>"
        paper.sections.append(PaperSection("Риторический профиль", rhet_html))

    # --- Section 6: Dialectics ---
    if dialectics:
        di_html = ""
        for d in dialectics:
            di_html += f"""
            <div style="background:#faf7f3;padding:14px;margin-bottom:8px;border-radius:8px">
              <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:14px">
                <span style="background:#c0392b;color:#fff;padding:2px 10px;border-radius:4px">ТЕЗИС</span>
                <span style="color:#2a1a1a">{d['thesis']}</span>
              </div>
              <div style="display:flex;gap:10px;align-items:center;margin-top:6px;flex-wrap:wrap;font-size:14px">
                <span style="background:#8b4513;color:#fff;padding:2px 10px;border-radius:4px">АНТИТЕЗИС</span>
                <span style="color:#2a1a1a">{d['antithesis']}</span>
              </div>
              <div style="display:flex;gap:10px;align-items:center;margin-top:6px;flex-wrap:wrap;font-size:14px">
                <span style="background:#2a6496;color:#fff;padding:2px 10px;border-radius:4px">СИНТЕЗ</span>
                <span style="color:#2a1a1a">{d['synthesis']}</span>
              </div>
              <div style="font-size:12px;color:#8a6a6a;margin-top:6px">{d['year']} г.</div>
            </div>
            """
        paper.sections.append(PaperSection("Диалектический анализ", di_html))

    # --- Section 7: Related Concepts ---
    if related:
        tags = " ".join(f'<span style="display:inline-block;background:#e8ddd0;padding:4px 12px;border-radius:16px;margin:4px;font-size:13px;color:#4a3a3a">{c}</span>' for c in related)
        rel_html = f"""
        <p style="margin-bottom:10px;color:#4a3a3a">Связанные концепты (по совстречаемости в текстах):</p>
        <div>{tags}</div>
        """
        paper.sections.append(PaperSection("Связанные концепты", rel_html))

    # --- Section 8: Bibliography ---
    # Find which volumes are most relevant
    db = _db()
    vols = db.execute(
        """
        SELECT v.title, COUNT(*) as cnt
        FROM lenin_positions lp
        JOIN volumes v ON lp.volume_id = v.id
        WHERE lp.topic = ?
        GROUP BY v.title
        ORDER BY cnt DESC
        LIMIT 5
        """,
        (topic,),
    ).fetchall()
    db.close()

    bib_html = "<p style='color:#4a3a3a'>Основные источники:</p><ul style='color:#6a5a5a;line-height:2'>"
    for v in vols:
        bib_html += f"<li>{v['title']} ({v['cnt']} позиций)</li>"
    bib_html += f"<li>Всего проанализировано 169 067 параграфов из 55 томов ПСС (5-е издание)</li>"
    bib_html += "<li>Метод: семантический поиск FAISS (93 711 векторов), лингвистический анализ, диалектическая разметка</li>"
    bib_html += "</ul>"

    paper.sections.append(PaperSection("Источники и методология", bib_html))

    return paper


def paper_to_html(paper: WhitePaper) -> str:
    """Convert paper to complete HTML for PDF rendering."""
    sections_html = ""
    toc_html = '<div style="margin:20px 0;padding:16px;background:#f5f0eb;border-radius:8px"><h3 style="color:#c0392b;margin-bottom:12px">Содержание</h3><ol style="color:#4a3a3a;line-height:2">'
    for i, sec in enumerate(paper.sections):
        toc_html += f'<li>{sec.title}</li>'
    toc_html += "</ol></div>"

    for sec in paper.sections:
        sections_html += f"""
        <div style="page-break-before:always;margin-bottom:30px">
          <h2 style="color:#c0392b;border-bottom:2px solid #c0392b;padding-bottom:8px;margin-bottom:16px">{sec.title}</h2>
          {sec.content_html}
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
      <meta charset="UTF-8">
      <style>
        @page {{ size: A4; margin: 20mm 18mm; }}
        body {{ font-family: 'PT Serif', Georgia, serif; color: #2a1a1a; font-size: 13pt; line-height: 1.6; max-width: 180mm; margin: 0 auto; }}
        h1 {{ font-size: 26pt; color: #c0392b; text-align: center; margin-bottom: 5mm; }}
        .subtitle {{ text-align: center; color: #6a5a5a; font-size: 11pt; margin-bottom: 15mm; }}
        .footer {{ text-align: center; color: #aaa; font-size: 9pt; margin-top: 10mm; border-top: 1px solid #ddd; padding-top: 5mm; }}
      </style>
    </head>
    <body>
      <div style="text-align:center;padding:30mm 0 20mm">
        <h1>{paper.title}</h1>
        <p class="subtitle">{paper.subtitle}</p>
        <p style="color:#8a6a5a;font-size:11pt;margin-top:10mm">Дата генерации: {__import__('datetime').datetime.now().strftime('%d.%m.%Y')}</p>
      </div>
      {toc_html}
      {sections_html}
      <div class="footer">
        Lenin White Paper Generator &bull; {paper.topic} &bull; Автоматическая генерация на основе 169 067 параграфов
      </div>
    </body>
    </html>
    """


if __name__ == "__main__":
    # Quick test
    paper = generate_paper("кооперация")
    html = paper_to_html(paper)
    with open("/tmp/test_paper.html", "w") as f:
        f.write(html)
    print(f"Generated paper on '{paper.topic}': {len(paper.sections)} sections, {len(html):,} chars")
    print(f"Sections: {[s.title for s in paper.sections]}")
