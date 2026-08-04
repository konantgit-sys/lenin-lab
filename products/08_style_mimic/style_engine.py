"""
Style Mimic Engine — Level A (Markov Chains + Rhetoric Injection)
Генерирует текст в стиле Ленина на заданную тему и с заданным тоном.
"""

import json
import random
import re
import sqlite3
from pathlib import Path
from collections import defaultdict, Counter

DB_PATH = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")

# Тоновые словари (унаследованы из engine_06_rhetoric)
TONE_VOCAB = {
    "aggression": [
        "борьба", "уничтожить", "разгром", "свергнуть", "враг", "враги",
        "подавление", "беспощадный", "сопротивление", "восстание",
        "кровавый", "подавить", "революционный"
    ],
    "sarcasm": [
        "пресловутый", "хвалёный", "так называемый", "якобы", "господа",
        "знаменитый", "жалкий", "ничтожный", "лакей", "прихвостень",
        "прислужник", "холоп", "оппортунист"
    ],
    "inspiration": [
        "вперёд", "победа", "великий", "свобода", "будущее", "строить",
        "коммунизм", "товарищи", "да здравствует", "революция",
        "пролетариат", "социализм"
    ],
    "analytical": [
        "следовательно", "таким образом", "необходимо отметить",
        "из этого следует", "во-первых", "во-вторых", "в-третьих",
        "необходимо", "анализ", "вывод", "диалектика", "противоречие"
    ],
    "contempt": [
        "жалкий", "ничтожный", "лакей", "прихвостень", "прислужник",
        "холоп", "пособник", "предатель", "ренегат", "оппортунист",
        "реформист", "соглашатель"
    ],
}

# Типичные ленинские конструкции
LENINISMS = {
    "openers": [
        "Не подлежит никакому сомнению, что",
        "Совершенно очевидно, что",
        "Необходимо подчеркнуть, что",
        "Самое важное — это",
        "Суть дела в том, что",
        "Основной вопрос состоит в",
        "Нельзя забывать, что",
        "Надо иметь в виду, что",
    ],
    "transitions": [
        "С другой стороны,",
        "Более того,",
        "Мало того,",
        "Иначе говоря,",
        "Другими словами,",
        "В сущности,",
        "На деле же,",
    ],
    "closers": [
        "Таковы факты.",
        "В этом суть вопроса.",
        "Это — факт.",
        "Такова действительность.",
        "Это не подлежит сомнению.",
        "Вывод ясен.",
    ],
    "exclamations": [
        "Товарищи!",
        "Вперёд!",
        "Да здравствует!",
        "Долой!",
        "Ни шагу назад!",
        "Это — позор!",
        "Какой вздор!",
        "Невероятно!",
    ],
    "questions": [
        "Спрашивается, почему?",
        "В чём же дело?",
        "Что из этого следует?",
        "Можно ли отрицать?",
        "Кто же этого не видит?",
        "Не ясно ли, что?",
    ],
}


def load_paragraphs(conn, limit=8000):
    """Загружает случайные параграфы для построения модели."""
    rows = conn.execute(
        "SELECT year, text FROM paragraphs WHERE year IS NOT NULL "
        "AND LENGTH(text) BETWEEN 200 AND 800 ORDER BY RANDOM() LIMIT ?",
        (limit,)
    ).fetchall()
    return rows


def clean_text(text):
    """Очистка текста для токенизации."""
    # Убираем сноски [1], [2]...
    text = re.sub(r'\[\d+\]', '', text)
    # Нормализуем пробелы
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def build_markov_model(paragraphs, n=2):
    """Строит Марковскую модель n-го порядка."""
    model = defaultdict(list)
    starters = []

    for _, text in paragraphs:
        text = clean_text(text)
        words = text.split()
        if len(words) < n + 3:
            continue

        starters.append(tuple(words[:n]))

        for i in range(len(words) - n):
            prefix = tuple(words[i:i + n])
            next_word = words[i + n]
            model[prefix].append(next_word)

    return model, starters


def find_tone_paragraphs(paragraphs, tone, count=50):
    """Находит параграфы с заданным тоном."""
    if not tone or tone == "mixed":
        return paragraphs

    tone_words = TONE_VOCAB.get(tone, [])
    scored = []
    for year, text in paragraphs:
        text_lower = text.lower()
        score = sum(text_lower.count(w.lower()) for w in tone_words)
        if score > 0:
            scored.append((score, year, text))

    scored.sort(reverse=True)
    return [(y, t) for _, y, t in scored[:max(count, 30)]]


def inject_topic(model, topic_words, bias=1):
    """Внедряет слова темы в Марковскую модель — очень осторожно."""
    if not topic_words:
        return

    # Добавляем слова темы только к 10% случайных префиксов, по 1 копии
    keys = list(model.keys())
    if not keys:
        return
    target_keys = random.sample(keys, min(len(keys) // 10, 200))
    for key in target_keys:
        for word in topic_words[:3]:  # максимум 3 ключевых слова
            if len(word) > 2 and word not in TONE_VOCAB.get("analytical", []):
                model[key].append(word)


def generate(model, starters, tone, length=300, topic=None):
    """Генерирует текст в стиле Ленина."""
    if not model:
        return "База данных пуста. Невозможно построить модель."

    max_words = max(30, length // 3)

    # Выбираем случайный стартер
    if not starters:
        return "Недостаточно данных для генерации."

    prefix = random.choice(starters)
    words = list(prefix)

    tone_vocab = TONE_VOCAB.get(tone, []) if tone else []
    topic_words = re.findall(r'\w+', topic.lower()) if topic else []

    # Внедрение темы в модель (на лету) — минимальное
    local_model = defaultdict(list, model)
    if topic_words:
        inject_topic(local_model, topic_words[:3])

    attempts = 0
    while len(words) < max_words and attempts < max_words * 3:
        current = tuple(words[-len(prefix):])

        if current in local_model:
            candidates = local_model[current]
            # Если есть тоновые слова — увеличиваем их вес
            if tone_vocab:
                weighted = candidates + [
                    w for w in candidates
                    if any(t in w.lower() for t in tone_vocab)
                ] * 5
                next_word = random.choice(weighted if random.random() < 0.6 else candidates)
            else:
                next_word = random.choice(candidates)
        else:
            # Fallback: случайное слово из модели
            try:
                next_word = random.choice(random.choice(list(local_model.values())))
            except (IndexError, ValueError):
                break

        words.append(next_word)
        attempts += 1

    # Формирование текста с ленинскими конструкциями
    return assemble_text(words, tone, topic)


def assemble_text(words, tone, topic):
    """Собирает сырой поток слов в осмысленный ленинский текст."""
    sentences = []
    current = []
    sentence_len = 0

    for word in words:
        current.append(word)
        sentence_len += 1

        # Конец предложения: знаки препинания или длина
        end_markers = word.endswith(('.', '!', '?', ':', ';'))
        if end_markers or sentence_len > 18:
            if sentence_len > 18 and not end_markers:
                current.append('.')
            sentences.append(' '.join(current))
            current = []
            sentence_len = 0

    if current:
        current.append('.')
        sentences.append(' '.join(current))

    # Внедрение ленинских конструкций
    result = []

    # Вступление
    if len(sentences) > 2:
        opener = random.choice(LENINISMS["openers"])
        topic_ref = f" вопроса о {topic}" if topic else ""
        result.append(f"{opener}{topic_ref} {sentences[0]}")

        # Основная часть
        for i, s in enumerate(sentences[1:-2]):
            if i % 3 == 0 and random.random() < 0.4:
                result.append(f"{random.choice(LENINISMS['transitions'])} {s}")
            elif i % 5 == 0 and random.random() < 0.3:
                result.append(f"{random.choice(LENINISMS['questions'])} {s}")
            else:
                result.append(s)

        # Вставка эмоциональных восклицаний
        if tone in ("aggression", "inspiration") and len(sentences) > 4:
            mid = len(result) // 2
            exclam = random.choice(LENINISMS["exclamations"])
            result.insert(mid, exclam)

        # Заключение
        result.append(sentences[-2] if len(sentences) > 1 else sentences[-1])
        result.append(random.choice(LENINISMS["closers"]))

    else:
        result = sentences

    return ' '.join(result)


def generate_lenin_text(topic="революция", tone="mixed", length=400):
    """Основной интерфейс генерации."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        # Загружаем параграфы
        all_paragraphs = load_paragraphs(conn, limit=6000)

        if not all_paragraphs:
            return {"error": "База данных пуста"}

        # Фильтруем по тону
        tone_paragraphs = find_tone_paragraphs(all_paragraphs, tone, count=300)

        # Строим модель
        model, starters = build_markov_model(tone_paragraphs, n=3)

        # Генерируем
        text = generate(model, starters, tone, length, topic)

        # Собираем статистику
        tones_used = list(TONE_VOCAB.keys()) if tone == "mixed" else [tone]
        sampled_years = [y for y, _ in tone_paragraphs[:100]]

        return {
            "topic": topic,
            "tone": tone,
            "text": text,
            "word_count": len(text.split()),
            "model_paragraphs": len(tone_paragraphs),
            "year_range": f"{min(sampled_years)}–{max(sampled_years)}" if sampled_years else "1893–1922",
            "tones_available": list(TONE_VOCAB.keys()),
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else "революция"
    tone = sys.argv[2] if len(sys.argv) > 2 else "mixed"
    result = generate_lenin_text(topic, tone)
    print(json.dumps(result, indent=2, ensure_ascii=False))
