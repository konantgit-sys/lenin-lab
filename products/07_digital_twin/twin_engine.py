"""
PRODUCT #7 — DIGITAL TWIN (ЦИФРОВОЙ ДВОЙНИК ЛЕНИНА)
====================================================
Отвечает на вопросы ТОЛЬКО реальными цитатами из корпуса.
Никаких LLM-галлюцинаций. FAISS-поиск + сборка ответа.
"""
import sys
import os
import json
import re
import numpy as np
from pathlib import Path
from collections import defaultdict

SITE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SITE_DIR))

from shared.lenin_core import fts5_search, get_paragraph, random_quote

# Пытаемся загрузить FAISS
try:
    import faiss
    HAVE_FAISS = True
except ImportError:
    HAVE_FAISS = False

# ===== КОНФИГУРАЦИЯ =====
MAX_QUOTES = 6          # Сколько цитат искать
MIN_SIMILARITY = 0.35   # Минимальный порог релевантности
MAX_RESPONSE_LEN = 1200 # Макс длина ответа в символах
CONTEXT_WINDOW = 2      # Сколько соседних параграфов брать

# ===== ШАБЛОНЫ ВСТУПЛЕНИЙ =====
INTRO_TEMPLATES = [
    "По этому вопросу в моих работах говорится следующее:",
    "Я неоднократно обращался к этой теме. Вот что писал:",
    "Этот вопрос затрагивается в ряде моих трудов:",
    "Позвольте процитировать соответствующие места из моих работ:",
    "В моих сочинениях можно найти такие строки по данному вопросу:",
]

# ===== ЗАГРУЗКА FAISS =====
faiss_index = None
paragraphs_meta = None

def _load_faiss():
    global faiss_index, paragraphs_meta
    if not HAVE_FAISS:
        return False
    try:
        idx_path = SITE_DIR / "data" / "faiss_index.bin"
        meta_path = SITE_DIR / "data" / "paragraphs_meta.json"
        if idx_path.exists() and meta_path.exists():
            faiss_index = faiss.read_index(str(idx_path))
            with open(meta_path) as f:
                paragraphs_meta = json.load(f)
            return True
    except Exception:
        pass
    return False


def twin_search(query: str, top_k: int = MAX_QUOTES) -> list:
    """
    Ищет релевантные цитаты через FAISS + FTS5 (гибрид).
    Возвращает список {text, year, volume, similarity, para_id}.
    """
    results = []
    
    # 1. FAISS-поиск
    if _load_faiss() or (faiss_index is not None):
        try:
            from shared.lenin_core import load_cache
            embedder = load_cache('embedder')
            if embedder:
                vec = embedder.encode([query])[0]
                vec = np.array([vec]).astype('float32')
                D, I = faiss_index.search(vec, top_k * 2)
                
                for dist, idx in zip(D[0], I[0]):
                    if idx >= len(paragraphs_meta):
                        continue
                    sim = float(1.0 / (1.0 + dist))
                    if sim < MIN_SIMILARITY:
                        continue
                    meta = paragraphs_meta[idx]
                    text = get_paragraph(meta.get('para_id', idx))
                    if text:
                        results.append({
                            'text': text.strip(),
                            'year': meta.get('year', '?'),
                            'volume': meta.get('volume', '?'),
                            'similarity': round(sim * 100, 1),
                            'para_id': meta.get('para_id', idx),
                            'source': 'faiss'
                        })
        except Exception:
            pass
    
    # 2. FTS5-поиск (дополняет FAISS)
    fts_results = fts5_search(query, limit=top_k)
    for r in fts_results:
        pid = r.get('id') or r.get('para_id')
        text = r.get('snippet', '') or r.get('text', '') or get_paragraph(pid)
        if text:
            results.append({
                'text': text.strip(),
                'year': r.get('year', '?'),
                'volume': r.get('volume_id', r.get('volume', '?')),
                'similarity': 50.0,
                'para_id': pid,
                'source': 'fts5'
            })
    
    # 3. Дедупликация и сортировка
    seen = set()
    unique = []
    for r in sorted(results, key=lambda x: x['similarity'], reverse=True):
        key = r['text'][:50]
        if key not in seen:
            seen.add(key)
            unique.append(r)
        if len(unique) >= top_k:
            break
    
    return unique


def assemble_response(query: str, quotes: list) -> dict:
    """
    Собирает ответ из найденных цитат.
    Возвращает {answer, citations, direct_match}.
    """
    if not quotes:
        # Ничего не нашли — честно говорим
        return {
            'answer': 'В моих работах нет прямых высказываний по этому вопросу. '
                      'Возможно, он не обсуждался в тех трудах, что вошли в собрание сочинений.',
            'citations': [],
            'direct_match': False
        }
    
    # Сортируем: сначала источники с similarity > 60%
    strong = [q for q in quotes if q['similarity'] >= 60]
    weak = [q for q in quotes if q['similarity'] < 60]
    
    # Выбираем вступление
    intro = INTRO_TEMPLATES[hash(query) % len(INTRO_TEMPLATES)]
    
    # Собираем ответ
    parts = [intro, ""]
    citations = []
    total_len = len(intro)
    
    selected = strong[:4] + weak[:2]  # максимум 6 цитат
    
    for i, q in enumerate(selected, 1):
        quote_text = q['text']
        # Ограничиваем длину одной цитаты
        if len(quote_text) > 400:
            quote_text = quote_text[:397] + "..."
        
        citation = f"[{i}] Том {q['volume']}, {q['year']} г. (совпадение {q['similarity']}%)"
        
        parts.append(f"«{quote_text}»")
        parts.append(citation)
        parts.append("")
        
        citations.append({
            'num': i,
            'text': q['text'][:200],
            'year': q['year'],
            'volume': q['volume'],
            'similarity': q['similarity']
        })
        
        total_len += len(quote_text) + len(citation) + 5
        if total_len > MAX_RESPONSE_LEN:
            break
    
    return {
        'answer': '\n'.join(parts).strip(),
        'citations': citations,
        'direct_match': len(strong) > 0,
        'total_found': len(quotes)
    }
