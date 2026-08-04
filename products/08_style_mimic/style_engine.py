"""
Style Mimic Engine v2 — REAL QUOTES + TONE INJECTION
====================================================
Ищет реальные цитаты Ленина по теме через FTS5,
затем инжектирует тоновые паттерны (агрессия, сарказм и т.д.)
и собирает как связный текст в ленинском стиле.

Никаких Markov-цепей. Только реальный корпус + риторическая обработка.
"""

import sys
import os
import re
import random
from pathlib import Path
from collections import defaultdict

SITE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SITE_DIR))

from shared.lenin_core import fts5_search, get_paragraph

# ===== ТОНОВЫЕ СЛОВАРИ =====
TONE_SIGNATURES = {
    "aggression": {
        "weight": 0.35,
        "openers": [
            "Товарищи! Пора прямо сказать:",
            "Довольно! Необходимо раз и навсегда покончить с",
            "Нельзя молчать!",
            "Кто этого не понимает — тот враг рабочего дела!",
        ],
        "injections": [
            "борьба", "уничтожить", "разгром", "свергнуть", "враг", "враги",
            "подавление", "беспощадный", "сопротивление", "восстание",
            "революционный", "подавить", "в штыки", "долой"
        ],
        "closers": [
            "Таков суровый закон классовой борьбы.",
            "Другого пути нет и быть не может!",
            "В этом — железная логика революции.",
        ],
        "exclamation_rate": 0.40,
    },
    "sarcasm": {
        "weight": 0.30,
        "openers": [
            "Наши «учёные» оппортунисты, разумеется, думают иначе...",
            "Пресловутая «свобода» буржуазной печати...",
            "Господа реформисты снова «открыли»...",
            "Как это ни печально для хвалёных знатоков марксизма...",
        ],
        "injections": [
            "пресловутый", "хвалёный", "так называемый", "якобы", "господа",
            "жалкий", "ничтожный", "лакей", "прихвостень",
            "прислужник", "холоп", "оппортунист", "реформист",
            "с позволения сказать", "изволите ли видеть"
        ],
        "closers": [
            "Ну как тут не посмеяться над подобной «теорией»?",
            "Вот до чего доводит «учёное» доктринёрство.",
            "И это называется марксизмом! Поистине, убожество.",
        ],
        "question_rate": 0.35,
    },
    "inspiration": {
        "weight": 0.30,
        "openers": [
            "Товарищи! Позвольте сказать несколько слов о",
            "Великое дело — борьба за",
            "С полной уверенностью можно утверждать:",
            "История поставила перед нами великую задачу —",
        ],
        "injections": [
            "вперёд", "победа", "великий", "свобода", "будущее", "строить",
            "коммунизм", "товарищи", "да здравствует", "революция",
            "пролетариат", "социализм", "светлое будущее", "освобождение"
        ],
        "closers": [
            "Вперёд, товарищи! Победа будет за нами!",
            "Таков наш путь — и мы пройдём его до конца!",
            "Да здравствует революция! Да здравствует социализм!",
        ],
        "exclamation_rate": 0.30,
    },
    "analytical": {
        "weight": 0.25,
        "openers": [
            "Необходимо внимательно рассмотреть вопрос о",
            "С точки зрения диалектического материализма,",
            "Анализ показывает, что",
            "Рассмотрим фактическое положение дел:",
        ],
        "injections": [
            "следовательно", "таким образом", "необходимо отметить",
            "из этого следует", "во-первых", "во-вторых", "в-третьих",
            "необходимо", "анализ", "вывод", "диалектика", "противоречие",
            "объективно", "конкретно", "исторически"
        ],
        "closers": [
            "Таковы объективные данные. Выводы пусть делает читатель.",
            "В этом — диалектика данного вопроса.",
            "Факты говорят сами за себя.",
        ],
        "question_rate": 0.20,
    },
    "contempt": {
        "weight": 0.32,
        "openers": [
            "Жалкие попытки оппортунистов прикрыть свою измену...",
            "С каким ничтожеством мы имеем дело!",
            "Трудно представить более жалкое зрелище, чем",
            "Ренегаты и перебежчики снова пытаются...",
        ],
        "injections": [
            "жалкий", "ничтожный", "лакей", "прихвостень", "прислужник",
            "холоп", "пособник", "предатель", "ренегат", "оппортунист",
            "реформист", "соглашатель", "измена", "позор",
            "политический труп", "убожество"
        ],
        "closers": [
            "Вот цена их «революционности». Медный грош.",
            "История сметёт этих жалких прислужников капитала.",
            "Таким не место в рядах сознательных рабочих!",
        ],
        "exclamation_rate": 0.25,
    },
    "mixed": {
        "weight": 0.20,
        "openers": [
            "Не подлежит никакому сомнению, что",
            "Совершенно очевидно, что",
            "Необходимо подчеркнуть, что",
            "Суть дела в том, что",
            "Основной вопрос состоит в",
            "Нельзя забывать, что",
        ],
        "injections": [],
        "closers": [
            "Таковы факты.",
            "В этом суть вопроса.",
            "Это — факт.",
            "Такова действительность.",
            "Вывод ясен.",
        ],
        "exclamation_rate": 0.10,
    },
}

# ===== ЛЕНИНИЗМЫ (общие для всех тонов) =====
LENIN_TRANSITIONS = [
    "С другой стороны,", "Более того,", "Мало того,", "Иначе говоря,",
    "Другими словами,", "В сущности,", "На деле же,", "В самом деле,",
]

LENIN_QUESTIONS = [
    "Спрашивается, почему?", "В чём же дело?", "Что из этого следует?",
    "Можно ли отрицать?", "Кто же этого не видит?", "Не ясно ли, что?",
]

LENIN_EXCLAMATIONS = [
    "Какой вздор!", "Невероятно!", "Это — позор!", "Ни шагу назад!",
    "Вот где корень вопроса!", "В том-то и дело!",
]


def search_topic_quotes(topic: str, limit: int = 15) -> list:
    """Ищет параграфы по теме через FTS5."""
    results = fts5_search(topic, limit=limit)
    quotes = []
    for r in results:
        pid = r.get('id') or r.get('para_id')
        text = r.get('snippet', '') or r.get('text', '') or get_paragraph(pid)
        if text and len(text) > 40:
            quotes.append({
                'text': text.strip(),
                'year': r.get('year', '?'),
                'volume': r.get('volume_id', r.get('volume', '?')),
            })
    return quotes


def extract_topic_keywords(topic: str) -> list:
    """Извлекает ключевые слова темы."""
    words = re.findall(r'[а-яё]{3,}', topic.lower())
    # Убираем стоп-слова
    stop = {'для', 'это', 'что', 'как', 'есть', 'или', 'еще', 'уже'}
    return [w for w in words if w not in stop][:5]


def inject_tone_between(text: str, tone: str, sig: dict) -> str:
    """Добавляет тоновые вставки МЕЖДУ предложениями, не трогая цитаты."""
    if tone == "mixed":
        return text
    
    injections = sig.get('injections', [])
    if not injections:
        return text
    
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) <= 2:
        return text
    
    result = []
    for i, sent in enumerate(sentences):
        result.append(sent)
        # Каждые 2-3 предложения вставляем тоновый маркер
        if i > 0 and i % 3 == 0:
            marker = random.choice(injections)
            result.append(f"({marker})")
    
    return ' '.join(result)


def assemble_style_text(topic: str, tone: str, quotes: list, target_length: int = 400) -> str:
    """Собирает связный текст из цитат с тоновым обрамлением."""
    sig = TONE_SIGNATURES.get(tone, TONE_SIGNATURES['mixed'])
    
    if not quotes:
        opener = random.choice(sig['openers'])
        closer = random.choice(sig['closers'])
        return f"{opener} вопрос о {topic}. {closer}"
    
    parts = []
    total_len = 0
    
    # 1. Открытие в выбранном тоне
    opener = random.choice(sig['openers'])
    parts.append(opener)
    total_len += len(opener)
    
    # 2. Основной текст из цитат
    max_quotes = min(len(quotes), 6)
    for i, q in enumerate(quotes[:max_quotes]):
        text = q['text']
        # Ограничиваем длину одного фрагмента
        if len(text) > 180:
            # Обрезаем до последней точки в пределах 180
            cut = text[:180]
            last_dot = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
            if last_dot > 60:
                text = text[:last_dot + 1]
            else:
                text = cut.rsplit(' ', 1)[0] + '...'
        
        # Инжектируем тон между предложениями
        toned_text = inject_tone_between(text, tone, sig)
        
        # Добавляем переход между цитатами
        if i > 0:
            transition = random.choice(LENIN_TRANSITIONS)
            parts.append(transition)
            total_len += len(transition) + 1
        
        parts.append(toned_text)
        total_len += len(toned_text) + 1
        
        # 3. Вопрос или восклицание (вероятностно)
        if random.random() < sig.get('question_rate', 0.15):
            q_text = random.choice(LENIN_QUESTIONS)
            parts.append(q_text)
            total_len += len(q_text) + 1
        
        if random.random() < sig.get('exclamation_rate', 0.15):
            ex = random.choice(LENIN_EXCLAMATIONS)
            parts.append(ex)
            total_len += len(ex) + 1
        
        if total_len >= target_length * 0.8:
            break
    
    # 4. Закрытие
    closer = random.choice(sig['closers'])
    parts.append(closer)
    
    return '\n\n'.join(parts)


def generate_lenin_text(topic: str, tone: str = "mixed", length: int = 400) -> dict:
    """
    Генерирует текст в стиле Ленина на заданную тему.
    Использует РЕАЛЬНЫЕ цитаты + тоновую обработку.
    """
    # Validate tone
    valid_tones = set(TONE_SIGNATURES.keys())
    if tone not in valid_tones:
        tone = "mixed"
    
    # Validate length
    length = max(100, min(length, 2000))
    
    try:
        # 1. Ищем цитаты по теме
        quotes = search_topic_quotes(topic, limit=10)
        
        # 2. Собираем текст
        text = assemble_style_text(topic, tone, quotes, length)
        
        # 3. Пост-обработка: убираем мусор
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # 4. Обрезаем до целевой длины (по последнему предложению)
        if len(text) > length:
            cut = text[:length]
            last_dot = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
            if last_dot > 50:
                text = text[:last_dot + 1]
            else:
                text = cut.rsplit(' ', 1)[0] + '...'
        
        quote_count = len(quotes)
        
        return {
            "topic": topic,
            "tone": tone,
            "text": text,
            "length": len(text),
            "quotes_used": min(quote_count, 6),
            "total_quotes_found": quote_count,
            "method": "fts5+tone_injection",
        }
        
    except Exception as e:
        return {
            "topic": topic,
            "tone": tone,
            "text": f"[Ошибка генерации: {str(e)[:100]}]",
            "length": 0,
            "error": str(e)
        }
