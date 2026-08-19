"""
Engine #3: Диалектический парсер
Извлекает диалектические тройки (тезис→антитезис→синтез) из 55 томов ПСС.

Алгоритм:
1. Внутрипараграфная диалектика: один параграф содержит оппозицию
2. Межпараграфная диалектика: последовательность из 2-3 параграфов
3. Валидация через концептуальный граф из Engine #2

Выход: таблица dialectical_triples с ~15K троек.
"""

import re
import sqlite3
import json
from pathlib import Path
from collections import defaultdict
import os

DB_PATH = Path(os.environ.get("LENIN_DB", "/home/agent/data/projects/lenin-knowledge/lenin.db"))

# Оппозиционные маркеры
# Тип 1: сильный контраст (но, однако, напротив)
STRONG_OPPOSITION = re.compile(
    r'\b(?:но|однако|напротив|наоборот|вопреки|в противовес|'
    r'в отличие|между тем|в то же время|тем не менее|'
    r'в действительности|на самом деле)\b',
    re.IGNORECASE
)

# Тип 2: условный контраст (если... то..., хотя... но...)
CONDITIONAL_OPPOSITION = re.compile(
    r'\b(?:если\b.*?\bто\b|хотя\b.*?\bно\b|'
    r'несмотря на|вопреки|не\b.*?\bа\b)',
    re.IGNORECASE
)

# Тип 3: диалектические связки (с одной стороны... с другой...)
DIALECTICAL_PAIRS = re.compile(
    r'\b(?:с одной стороны|с другой стороны|'
    r'во-первых|во-вторых|в-третьих|'
    r'прежде всего|далее|наконец)\b',
    re.IGNORECASE
)

# Тип 4: отрицание-утверждение (не X, а Y)
NEGATION_AFFIRMATION = re.compile(
    r'\bне\s+\w+(?:[\s,]+а\s+\w+|[\s,]+\bно\b)',
    re.IGNORECASE
)

# Маркеры синтеза
SYNTHESIS_MARKERS = re.compile(
    r'\b(?:таким образом|итак|следовательно|'
    r'из этого следует|отсюда|поэтому|'
    r'в итоге|в результате|значит|'
    r'иными словами|иначе говоря|'
    r'стало быть|выходит)\b',
    re.IGNORECASE
)


def get_connection():
    return sqlite3.connect(str(DB_PATH))


def find_intra_paragraph_dialectics(conn):
    """Находит диалектику внутри одного параграфа (оппозиция в одном тексте)."""
    triples = []
    
    rows = conn.execute("""
        SELECT id, volume_id, paragraph_index, text, year
        FROM paragraphs
        WHERE (text LIKE '% но %' OR text LIKE '% однако %' OR text LIKE '% напротив %'
               OR text LIKE '% с одной стороны%' OR text LIKE '% с другой стороны%'
               OR text LIKE '% не % а %')
        ORDER BY id
    """).fetchall()
    
    for row in rows:
        pid, vol, pidx, text, year = row
        
        # Ищем оппозиционные маркеры
        has_strong = bool(STRONG_OPPOSITION.search(text))
        has_dialectical = bool(DIALECTICAL_PAIRS.search(text))
        has_neg_aff = bool(NEGATION_AFFIRMATION.search(text))
        has_synthesis = bool(SYNTHESIS_MARKERS.search(text))
        
        # Рассчитываем диалектическую силу
        strength = (
            (2 if has_strong else 0) +
            (2 if has_dialectical else 0) +
            (1 if has_neg_aff else 0) +
            (1 if has_synthesis else 0)
        )
        
        if strength >= 2:
            # Извлекаем предложения для тезиса и антитезиса
            sentences = re.split(r'[.!?]+\s+', text)
            
            thesis_sent = ""
            antithesis_sent = ""
            synthesis_sent = ""
            
            for i, s in enumerate(sentences):
                s = s.strip()
                if not s:
                    continue
                if not thesis_sent:
                    thesis_sent = s
                elif STRONG_OPPOSITION.search(s) and not antithesis_sent:
                    antithesis_sent = s
                    thesis_sent = " ".join(sentences[:i]).strip() if i > 0 else sentences[0].strip()
                elif SYNTHESIS_MARKERS.search(s) and not synthesis_sent:
                    synthesis_sent = s
            
            if not antithesis_sent and len(sentences) >= 2:
                # Fallback: первая половина = тезис, вторая = антитезис
                mid = len(sentences) // 2
                thesis_sent = " ".join(sentences[:mid]).strip()
                antithesis_sent = " ".join(sentences[mid:]).strip()
                # Синтез — если есть маркер в последнем предложении
                if SYNTHESIS_MARKERS.search(sentences[-1]):
                    synthesis_sent = sentences[-1].strip()
            
            triples.append({
                "type": "intra_paragraph",
                "paragraph_id": pid,
                "volume_id": vol,
                "year": year,
                "thesis": thesis_sent[:500],
                "antithesis": antithesis_sent[:500],
                "synthesis": synthesis_sent[:500] if synthesis_sent else None,
                "strength": strength,
                "full_text_preview": text[:300],
            })
    
    return triples


def find_inter_paragraph_dialectics(conn):
    """Находит диалектику между соседними параграфами."""
    triples = []
    
    # Ищем цепочки: параграф N (утверждение) → N+1 (контраргумент) → N+2 (синтез)
    rows = conn.execute("""
        SELECT p1.id, p1.volume_id, p1.paragraph_index, p1.text, p1.year,
               p2.id, p2.text,
               p3.id, p3.text
        FROM paragraphs p1
        JOIN paragraphs p2 ON p1.volume_id = p2.volume_id 
            AND p2.paragraph_index = p1.paragraph_index + 1
        LEFT JOIN paragraphs p3 ON p1.volume_id = p3.volume_id 
            AND p3.paragraph_index = p1.paragraph_index + 2
        WHERE (p2.text LIKE '% но %' OR p2.text LIKE '% однако %' OR p2.text LIKE '% напротив %'
               OR p2.text LIKE '% между тем%' OR p2.text LIKE '% в отличие%'
               OR p2.text LIKE '% наоборот%')
        LIMIT 20000
    """).fetchall()
    
    for row in rows:
        p1_id, vol, p1_idx, p1_text, year, p2_id, p2_text, p3_id, p3_text = row
        
        # P1 = тезис, P2 = антитезис, P3 = синтез
        synthesis = None
        if p3_text and SYNTHESIS_MARKERS.search(p3_text):
            synthesis = p3_text[:500]
        
        # Сила: маркер в P2 + наличие синтеза в P3
        strength = 3
        if synthesis:
            strength += 2
        
        triples.append({
            "type": "inter_paragraph",
            "paragraph_ids": [p1_id, p2_id, p3_id] if p3_id else [p1_id, p2_id],
            "volume_id": vol,
            "paragraph_index": p1_idx,
            "year": year,
            "thesis": p1_text[:500],
            "antithesis": p2_text[:500],
            "synthesis": synthesis,
            "strength": strength,
        })
    
    return triples


def validate_with_concept_graph(triples, conn):
    """Валидирует диалектические тройки через концептуальный граф."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from engines.engine_02_concepts import CONCEPTS
    
    concept_patterns = {}
    for name, keywords in CONCEPTS.items():
        for kw in keywords[:3]:  # первые 3 ключевых слова
            concept_patterns[kw] = name
    
    def extract_concepts(text):
        found = set()
        text_lower = text.lower()
        for pattern, name in concept_patterns.items():
            if pattern.lower() in text_lower:
                found.add(name)
        return found
    
    validated = []
    for triple in triples:
        thesis_concepts = extract_concepts(triple.get("thesis", "") or "")
        antithesis_concepts = extract_concepts(triple.get("antithesis", "") or "")
        synth_concepts = extract_concepts(triple.get("synthesis", "") or "") if triple.get("synthesis") else set()
        
        # Диалектика подтверждена если:
        # 1. В тезисе и антитезисе разные концепты (контраст)
        # 2. В синтезе — новый концепт или объединение
        contrast = len(thesis_concepts - antithesis_concepts) + len(antithesis_concepts - thesis_concepts)
        synthesis_novelty = len(synth_concepts - thesis_concepts - antithesis_concepts) if synth_concepts else 0
        
        validated_triple = dict(triple)
        validated_triple["thesis_concepts"] = list(thesis_concepts)
        validated_triple["antithesis_concepts"] = list(antithesis_concepts)
        validated_triple["synthesis_concepts"] = list(synth_concepts)
        validated_triple["contrast_score"] = contrast
        validated_triple["novelty_score"] = synthesis_novelty
        validated_triple["dialectical_score"] = triple["strength"] + contrast + synthesis_novelty
        
        validated.append(validated_triple)
    
    return validated


def store_triples(conn, triples):
    """Сохраняет тройки в БД."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dialectical_triples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            paragraph_ids TEXT,
            volume_id INTEGER,
            paragraph_index INTEGER,
            year INTEGER,
            thesis TEXT,
            antithesis TEXT,
            synthesis TEXT,
            thesis_concepts TEXT,
            antithesis_concepts TEXT,
            synthesis_concepts TEXT,
            contrast_score INTEGER DEFAULT 0,
            novelty_score INTEGER DEFAULT 0,
            dialectical_score INTEGER DEFAULT 0,
            strength INTEGER DEFAULT 0
        )
    """)
    
    conn.execute("DELETE FROM dialectical_triples")
    
    for t in triples:
        conn.execute("""
            INSERT INTO dialectical_triples (
                type, paragraph_ids, volume_id, paragraph_index, year,
                thesis, antithesis, synthesis,
                thesis_concepts, antithesis_concepts, synthesis_concepts,
                contrast_score, novelty_score, dialectical_score, strength
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t["type"],
            json.dumps(t.get("paragraph_ids", [t.get("paragraph_id")])),
            t.get("volume_id"),
            t.get("paragraph_index"),
            t.get("year"),
            t.get("thesis"),
            t.get("antithesis"),
            t.get("synthesis"),
            json.dumps(t.get("thesis_concepts", [])),
            json.dumps(t.get("antithesis_concepts", [])),
            json.dumps(t.get("synthesis_concepts", [])),
            t.get("contrast_score", 0),
            t.get("novelty_score", 0),
            t.get("dialectical_score", 0),
            t.get("strength", 0),
        ))
    
    conn.commit()


def count_pattern_matches(conn):
    """Подсчитывает параграфы с разными типами оппозиций."""
    stats = {}
    
    stats["strong_opposition"] = conn.execute(
        "SELECT COUNT(*) FROM paragraphs WHERE text LIKE '% но %' OR text LIKE '% однако %' "
        "OR text LIKE '% напротив %' OR text LIKE '% наоборот %'"
    ).fetchone()[0]
    
    stats["dialectical_pairs"] = conn.execute(
        "SELECT COUNT(*) FROM paragraphs WHERE text LIKE '%с одной стороны%' OR text LIKE '%с другой стороны%'"
    ).fetchone()[0]
    
    stats["negation_affirmation"] = conn.execute(
        "SELECT COUNT(*) FROM paragraphs WHERE text LIKE '% не % а %'"
    ).fetchone()[0]
    
    stats["synthesis_markers"] = conn.execute(
        "SELECT COUNT(*) FROM paragraphs WHERE text LIKE '%таким образом%' OR text LIKE '%следовательно%' OR text LIKE '%итак%'"
    ).fetchone()[0]
    
    return stats


def run_dialectical_parser() -> dict:
    """Запускает полный парсинг диалектических троек."""
    conn = get_connection()
    
    try:
        # Шаг 1: внутрипараграфная диалектика
        intra = find_intra_paragraph_dialectics(conn)
        
        # Шаг 2: межпараграфная диалектика
        inter = find_inter_paragraph_dialectics(conn)
        
        # Шаг 3: объединяем и валидируем
        all_triples = intra + inter
        validated = validate_with_concept_graph(all_triples, conn)
        
        # Сортируем по диалектическому скору
        validated.sort(key=lambda x: x["dialectical_score"], reverse=True)
        
        # Шаг 4: сохраняем
        store_triples(conn, validated)
        
        # Статистика
        pattern_stats = count_pattern_matches(conn)
        
        # Распределение по годам
        year_dist = {}
        for t in validated:
            y = t.get("year")
            if y:
                year_dist[y] = year_dist.get(y, 0) + 1
        
        # Распределение по типам
        type_dist = defaultdict(int)
        for t in validated:
            type_dist[t["type"]] += 1
        
        # Топ-10 по скору
        top10 = validated[:10]
        
        return {
            "total_triples": len(validated),
            "intra_paragraph": type_dist.get("intra_paragraph", 0),
            "inter_paragraph": type_dist.get("inter_paragraph", 0),
            "avg_dialectical_score": round(
                sum(t["dialectical_score"] for t in validated) / max(len(validated), 1), 1
            ),
            "with_synthesis": sum(1 for t in validated if t.get("synthesis")),
            "pattern_distribution": pattern_stats,
            "year_distribution": dict(sorted(year_dist.items())),
            "top_triples": [
                {
                    "type": t["type"],
                    "volume": t.get("volume_id"),
                    "year": t.get("year"),
                    "thesis_preview": (t.get("thesis") or "")[:150],
                    "antithesis_preview": (t.get("antithesis") or "")[:150],
                    "synthesis_preview": (t.get("synthesis") or "")[:150] if t.get("synthesis") else None,
                    "score": t["dialectical_score"],
                    "contrast": t.get("contrast_score", 0),
                    "novelty": t.get("novelty_score", 0),
                }
                for t in top10
            ],
        }
    finally:
        conn.close()


def get_dialectical_stats() -> dict:
    """Возвращает статистику без перегенерации."""
    conn = get_connection()
    try:
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='dialectical_triples'"
        ).fetchone()
        
        if not exists:
            return {"status": "not_built", "total_triples": 0}
        
        total = conn.execute("SELECT COUNT(*) FROM dialectical_triples").fetchone()[0]
        intra = conn.execute(
            "SELECT COUNT(*) FROM dialectical_triples WHERE type='intra_paragraph'"
        ).fetchone()[0]
        inter = total - intra
        with_synth = conn.execute(
            "SELECT COUNT(*) FROM dialectical_triples WHERE synthesis IS NOT NULL AND synthesis != ''"
        ).fetchone()[0]
        avg_score = conn.execute(
            "SELECT AVG(dialectical_score) FROM dialectical_triples"
        ).fetchone()[0]
        
        year_dist = {}
        for row in conn.execute(
            "SELECT year, COUNT(*) FROM dialectical_triples WHERE year IS NOT NULL GROUP BY year ORDER BY year"
        ):
            year_dist[row[0]] = row[1]
        
        return {
            "status": "built",
            "total_triples": total,
            "intra_paragraph": intra,
            "inter_paragraph": inter,
            "with_synthesis": with_synth,
            "avg_dialectical_score": round(avg_score, 1) if avg_score else 0,
            "year_distribution": year_dist,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    result = run_dialectical_parser()
    print(json.dumps(result, indent=2, ensure_ascii=False))
