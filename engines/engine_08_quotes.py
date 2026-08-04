"""
Engine #8: Цитатомёт
Извлечение ярких цитат Ленина для публикации.

Алгоритм:
1. Разбить параграфы на предложения (50-300 символов)
2. Скорить по афористичности (восклицания, контрасты, императивы, метафоры)
3. Категоризировать по темам из engine_07
4. Сохранить топ-5000 цитат в lenin_quotes
"""

import json
import re
import sqlite3
import time
from pathlib import Path
from collections import defaultdict

DB_PATH = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")

# Признаки афористичности
APHORISM_MARKERS = {
    "exclamation": [r"!", r"!", r"!"],  # вес = 3
    "rhetorical_question": [r"\?", r"\?$"],  # вес = 2
    "contrast": [
        r"\bне\s+\w+\s*,\s*а\s+",     # не X, а Y
        r"\bно\s+",                    # но
        r"\bоднако\b",                 # однако
        r"\bнапротив\b",               # напротив
        r"\bвопреки\b",                # вопреки
    ],
    "imperative": [
        r"^[А-Я][^.]*!$",             # восклицательное в начале
        r"\bдолжны?\b",                # должны
        r"\bнеобходимо\b",             # необходимо
        r"\bнадо\b",                   # надо
        r"\bнужно\b",                  # нужно
        r"\bследует\b",                # следует
        r"\bтребуется\b",              # требуется
    ],
    "absolute": [
        r"\bвсегда\b",                 # всегда
        r"\bникогда\b",                # никогда
        r"\bвсякий\b",                 # всякий
        r"\bникакой\b",                # никакой
        r"\bвесь\b",                   # весь
        r"\bвсё\b",                    # всё
        r"\bничего\b",                 # ничего
        r"\bабсолютно\b",              # абсолютно
        r"\bсовершенно\b",             # совершенно
        r"\bцеликом\b",                # целиком
    ],
    "metaphor": [
        r"\bкак\s+\w+\s*,\s*так\s+",   # как X, так и Y
        r"\bподобно\b",                 # подобно
        r"\bточно\s+",                 # точно (сравнение)
        r"\bсловно\b",                  # словно
        r"\bбудто\b",                   # будто
    ],
    "famous_keywords": [
        r"\bучение\s+Маркса\b",
        r"\bдиктатура\s+пролетариата\b",
        r"\bкоммунизм\b",
        r"\bреволюция\b",
        r"\bпартия\b",
        r"\bклассовая\s+борьба\b",
        r"\bимпериализм\b",
        r"\bсоциализм\b",
        r"\bсоветская\s+власть\b",
        r"\bгегемония\b",
        r"\bэксплуатация\b",
        r"\bбуржуазия\b",
        r"\bпролетариат\b",
    ],
}

MARKER_WEIGHTS = {
    "exclamation": 3,
    "rhetorical_question": 2,
    "contrast": 4,
    "imperative": 3,
    "absolute": 3,
    "metaphor": 2,
    "famous_keywords": 5,
}


def split_sentences(text: str):
    """Разбивает текст на предложения."""
    # Упрощённый сплиттер
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def score_aphorism(sentence: str) -> tuple:
    """Скоринг афористичности. Возвращает (score, categories)."""
    score = 0
    categories = []
    s_len = len(sentence)

    # Слишком короткие или длинные — не цитаты
    if s_len < 50 or s_len > 350:
        return 0, []

    for marker_type, patterns in APHORISM_MARKERS.items():
        for pat in patterns:
            if re.search(pat, sentence, re.IGNORECASE):
                score += MARKER_WEIGHTS[marker_type]
                if marker_type not in categories:
                    categories.append(marker_type)
                break

    # Бонус за идеальную длину (100-200 символов)
    if 80 <= s_len <= 250:
        score += 3
    elif 50 <= s_len <= 300:
        score += 1

    # Штраф за слишком много цифр (статистика, не цитата)
    digits_ratio = sum(c.isdigit() for c in sentence) / max(s_len, 1)
    if digits_ratio > 0.15:
        score -= 3

    # Штраф за кавычки (цитирование других)
    if sentence.count('"') > 2 or sentence.count('«') > 2:
        score -= 2

    return score, categories


def get_topic_for_quote(conn, sentence: str) -> list:
    """Определяет темы цитаты через keywords."""
    topics = []
    text_lower = sentence.lower()

    # Берём словарь тем из engine_07
    rows = conn.execute("SELECT DISTINCT topic FROM lenin_positions").fetchall()
    all_topics = [r[0] for r in rows]

    for topic in all_topics:
        if topic.lower() in text_lower:
            topics.append(topic)

    return topics[:3]  # топ-3 темы


def extract_quotes(limit_per_scan=200):
    """Извлекает лучшие цитаты из всех параграфов."""
    conn = sqlite3.connect(str(DB_PATH))

    # Создаём таблицу
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lenin_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paragraph_id INTEGER,
            volume_id INTEGER,
            year INTEGER,
            text TEXT NOT NULL,
            char_length INTEGER,
            aphorism_score REAL,
            categories TEXT,
            topics TEXT,
            best_rank INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quotes_score ON lenin_quotes(aphorism_score DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quotes_year ON lenin_quotes(year)")

    conn.execute("DELETE FROM lenin_quotes")

    # Загружаем все параграфы
    total = conn.execute("SELECT COUNT(*) FROM paragraphs").fetchone()[0]
    print(f"Scanning {total} paragraphs...")

    all_quotes = []
    scanned = 0
    batch_size = 10000

    for offset in range(0, total, batch_size):
        rows = conn.execute(
            "SELECT id, volume_id, year, text FROM paragraphs LIMIT ? OFFSET ?",
            (batch_size, offset),
        ).fetchall()

        for pid, vid, year, text in rows:
            sentences = split_sentences(text)
            for s in sentences:
                score, cat = score_aphorism(s)
                if score >= 5:  # порог — минимум 5 баллов
                    all_quotes.append((pid, vid, year, s, len(s), score, ",".join(cat)))

        scanned += len(rows)
        if scanned % 50000 == 0:
            print(f"  Scanned {scanned}/{total}, quotes found: {len(all_quotes)}")

    print(f"Total candidates: {len(all_quotes)}")

    # Сортируем по скору, берём топ-5000
    all_quotes.sort(key=lambda x: x[5], reverse=True)
    top_n = min(5000, len(all_quotes))
    top_quotes = all_quotes[:top_n]

    print(f"Inserting top {top_n} quotes...")

    # Привязываем темы
    for i, (pid, vid, year, text, length, score, cat) in enumerate(top_quotes):
        topics = get_topic_for_quote(conn, text)
        conn.execute(
            """INSERT INTO lenin_quotes (paragraph_id, volume_id, year, text, char_length, aphorism_score, categories, topics, best_rank)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pid, vid, year, text, length, score, cat, ",".join(topics), i + 1),
        )

    conn.commit()

    # Статистика
    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            ROUND(AVG(aphorism_score), 1) as avg_score,
            MAX(aphorism_score) as max_score,
            ROUND(AVG(char_length), 1) as avg_len,
            COUNT(DISTINCT year) as years
        FROM lenin_quotes
    """).fetchone()

    top_cat = conn.execute("""
        SELECT categories, COUNT(*) as cnt
        FROM lenin_quotes
        GROUP BY categories
        ORDER BY cnt DESC LIMIT 10
    """).fetchall()

    year_top = conn.execute("""
        SELECT year, COUNT(*) as cnt
        FROM lenin_quotes
        WHERE year IS NOT NULL
        GROUP BY year
        ORDER BY cnt DESC LIMIT 10
    """).fetchall()

    conn.close()

    return {
        "quotes_extracted": stats[0],
        "avg_score": stats[1],
        "max_score": stats[2],
        "avg_length": stats[3],
        "years_covered": stats[4],
        "top_categories": [{"categories": c, "count": n} for c, n in top_cat],
        "year_distribution": [{"year": y, "quotes": n} for y, n in year_top],
    }


def search_quotes(topic: str = None, year: int = None, limit=10):
    """Поиск цитат по теме или году."""
    conn = sqlite3.connect(str(DB_PATH))

    if topic and year:
        rows = conn.execute(
            """SELECT text, year, volume_id, aphorism_score, topics
               FROM lenin_quotes
               WHERE topics LIKE ? AND year = ?
               ORDER BY aphorism_score DESC LIMIT ?""",
            (f"%{topic}%", year, limit),
        ).fetchall()
    elif topic:
        rows = conn.execute(
            """SELECT text, year, volume_id, aphorism_score, topics
               FROM lenin_quotes
               WHERE topics LIKE ?
               ORDER BY aphorism_score DESC LIMIT ?""",
            (f"%{topic}%", limit),
        ).fetchall()
    elif year:
        rows = conn.execute(
            """SELECT text, year, volume_id, aphorism_score, topics
               FROM lenin_quotes
               WHERE year = ?
               ORDER BY aphorism_score DESC LIMIT ?""",
            (year, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT text, year, volume_id, aphorism_score, topics
               FROM lenin_quotes
               ORDER BY aphorism_score DESC LIMIT ?""",
            (limit,),
        ).fetchall()

    conn.close()

    return [
        {"text": r[0], "year": r[1], "volume": r[2], "score": r[3], "topics": r[4]}
        for r in rows
    ]


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--build":
            print("Extracting Lenin quotes...")
            start = time.time()
            result = extract_quotes()
            elapsed = time.time() - start
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print(f"\nBuilt in {elapsed:.1f}s")
        elif cmd == "--top":
            results = search_quotes(limit=5)
            for i, r in enumerate(results, 1):
                print(f"\n#{i} [score={r['score']}, {r['year']}, т.{r['volume']}]:")
                print(r["text"][:200])
        elif cmd == "--search" and len(sys.argv) > 2:
            results = search_quotes(topic=sys.argv[2], limit=5)
            for r in results:
                print(f"[{r['year']}] {r['text'][:200]}")
        else:
            results = search_quotes(year=int(cmd), limit=5) if cmd.isdigit() else search_quotes(topic=cmd, limit=5)
            for r in results:
                print(f"[{r['year']}] {r['text'][:200]}")
    else:
        results = search_quotes(limit=5)
        for r in results:
            print(f"[{r['year']}] {r['text'][:200]}")
