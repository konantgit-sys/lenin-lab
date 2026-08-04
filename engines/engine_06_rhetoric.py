"""
Engine #6: Риторический отпечаток
Анализ эмоциональной дуги Ленина 1893–1923:
- Агрессия, сарказм, воодушевление, спокойствие
- Риторические приёмы (вопросы, восклицания, метафоры)
- Профиль по годам + суммарный отпечаток
"""

import json
import sqlite3
import re
from pathlib import Path
from collections import defaultdict, Counter

DB_PATH = Path("/home/agent/data/projects/lenin-knowledge/lenin.db")

# Эмоциональные маркеры
MARKERS = {
    "aggression": {
        "words": [
            "борьба", "борьбе", "борьбы", "борьбу",
            "уничтожить", "уничтожения", "уничтожение",
            "разгром", "разгромить", "разгрома",
            "свергнуть", "свержения",
            "враг", "враги", "врагов", "врагам",
            "подавление", "подавить",
            "беспощадн", "беспощадная", "беспощадный",
            "сопротивление", "сопротивления",
            "восстание", "восстания",
            "кров", "кровавый", "кровавая",
        ],
        "exclam_weight": 2.0,  # вес одного восклицательного знака
        "caps_weight": 1.5,     # вес слов в верхнем регистре
    },
    "sarcasm": {
        "words": [
            "пресловутый", "пресловут",
            "хвалёный", "хваленый",
            "так называемый", "так называемая", "так называемое",
            "якобы",
            "господа", "господин",
            "знаменитый",
            "социалист",  # ироничное использование
        ],
        "quote_weight": 1.0,  # кавычки как маркер сарказма
    },
    "inspiration": {
        "words": [
            "вперёд", "вперед",
            "победа", "победы", "победить",
            "великий", "великая", "великое",
            "свобода", "свободы",
            "будущее", "будущего",
            "строить", "строительство",
            "коммунизм", "коммунизма",
            "товарищи",
            "да здравствует",
        ],
    },
    "analytical": {
        "words": [
            "следовательно",
            "таким образом",
            "необходимо отметить",
            "из этого следует",
            "во-первых", "во-вторых", "в-третьих",
            "необходимо",
            "анализ", "анализа",
            "вывод", "выводы",
        ],
    },
    "contempt": {
        "words": [
            "жалкий", "жалкая", "жалкое",
            "ничтожный", "ничтожная", "ничтожное",
            "лакей", "лакеи",
            "прихвостень", "прихвостни",
            "прислужник", "прислужники",
            "холоп", "холопы",
            "пособник", "пособники",
            "предатель", "предатели",
            "ренегат", "ренегаты",
            "оппортунист", "оппортунисты",
        ],
    },
}

# Риторические приёмы
RHETORICAL_DEVICES = {
    "rhetorical_questions": r"\?",
    "exclamations": r"!",
    "repetition_3x": None,  # особый алгоритм
}


def get_connection():
    return sqlite3.connect(str(DB_PATH))


def analyze_paragraph(text: str) -> dict:
    """Анализирует один параграф на эмоциональные маркеры."""
    text_lower = text.lower()
    scores = defaultdict(float)

    for category, data in MARKERS.items():
        for word in data["words"]:
            count = text_lower.count(word)
            if count > 0:
                scores[category] += count

        # Специальные маркеры
        if "exclam_weight" in data:
            scores[category] += text.count("!") * data["exclam_weight"]

        if "caps_weight" in data:
            # Слова целиком в верхнем регистре (3+ букв)
            caps_words = re.findall(r'\b[А-ЯЁA-Z]{3,}\b', text)
            scores[category] += len(caps_words) * data["caps_weight"]

        if "quote_weight" in data:
            # Ироничные кавычки: «...» или "..."
            quote_blocks = len(re.findall(r'«[^»]+»', text))
            quote_blocks += len(re.findall(r'"[^"]{10,}"', text))
            scores[category] += quote_blocks * data["quote_weight"]

    # Риторические приёмы
    devices = {
        "questions": text.count("?"),
        "exclamations": text.count("!"),
        "long_sentences": len(re.findall(r'[.!?][^.!?]{200,}[.!?]', text)),
    }

    # Суммарная эмоциональная насыщенность
    total_emotional = sum(scores.values())

    return {
        "scores": dict(scores),
        "devices": devices,
        "total_emotional": total_emotional,
    }


def build_rhetorical_profile(conn) -> dict:
    """Строит полный риторический профиль по годам."""

    rows = conn.execute(
        "SELECT year, text FROM paragraphs WHERE year IS NOT NULL"
    ).fetchall()

    # Агрегация по годам
    by_year = defaultdict(lambda: {
        "paragraphs": 0,
        "scores": defaultdict(float),
        "devices": defaultdict(int),
        "total_emotional": 0.0,
    })

    for year, text in rows:
        analysis = analyze_paragraph(text)
        ydata = by_year[year]
        ydata["paragraphs"] += 1

        for cat, score in analysis["scores"].items():
            ydata["scores"][cat] += score

        for dev, count in analysis["devices"].items():
            ydata["devices"][dev] += count

        ydata["total_emotional"] += analysis["total_emotional"]

    # Нормализация: на параграф и на 1000 параграфов
    yearly_profile = {}
    for year, data in sorted(by_year.items()):
        n = max(data["paragraphs"], 1)
        yearly_profile[year] = {
            "paragraphs": data["paragraphs"],
            "scores_per_para": {k: round(v / n, 3) for k, v in data["scores"].items()},
            "scores_per_1000": {k: round(v * 1000 / n, 1) for k, v in data["scores"].items()},
            "devices_per_1000": {k: round(v * 1000 / n, 1) for k, v in data["devices"].items()},
            "emotional_density": round(data["total_emotional"] / n, 3),
        }

    # Определяем доминирующую эмоцию для каждого года
    for year, data in yearly_profile.items():
        scores = data["scores_per_para"]
        if scores:
            dominant = max(scores, key=scores.get)
            data["dominant_emotion"] = dominant
        else:
            data["dominant_emotion"] = "neutral"

    # Строим эмоциональную дугу (сглаженную)
    years_sorted = sorted(yearly_profile.keys())
    emotional_arc = []
    for year in years_sorted:
        emotional_arc.append({
            "year": year,
            "density": yearly_profile[year]["emotional_density"],
            "dominant": yearly_profile[year]["dominant_emotion"],
        })

    # Глобальная статистика
    global_scores = defaultdict(float)
    global_paragraphs = 0
    for data in by_year.values():
        global_paragraphs += data["paragraphs"]
        for cat, score in data["scores"].items():
            global_scores[cat] += score

    global_profile = {
        k: round(v / max(global_paragraphs, 1), 3)
        for k, v in global_scores.items()
    }

    # Определяем эмоциональные периоды
    periods = detect_emotional_periods(yearly_profile)

    # Топ-10 самых агрессивных/спокойных лет
    top_aggressive = sorted(
        yearly_profile.items(),
        key=lambda x: x[1]["scores_per_para"].get("aggression", 0),
        reverse=True,
    )[:5]

    top_inspirational = sorted(
        yearly_profile.items(),
        key=lambda x: x[1]["scores_per_para"].get("inspiration", 0),
        reverse=True,
    )[:5]

    return {
        "years_analyzed": len(yearly_profile),
        "total_paragraphs": global_paragraphs,
        "global_profile": global_profile,
        "emotional_arc": emotional_arc,
        "periods": periods,
        "top_aggressive_years": [{"year": y, "score": d["scores_per_para"].get("aggression", 0)} for y, d in top_aggressive],
        "top_inspirational_years": [{"year": y, "score": d["scores_per_para"].get("inspiration", 0)} for y, d in top_inspirational],
        "yearly_detail": {str(y): d for y, d in yearly_profile.items()},
    }


def detect_emotional_periods(yearly_profile: dict) -> list:
    """Делит 1893-1923 на эмоциональные периоды."""
    # Простая кластеризация по доминирующей эмоции
    periods = []
    current_emotion = None
    current_start = None

    for year in sorted(yearly_profile.keys()):
        emotion = yearly_profile[year]["dominant_emotion"]
        if emotion != current_emotion:
            if current_emotion is not None:
                periods.append({
                    "start": current_start,
                    "end": year - 1,
                    "dominant_emotion": current_emotion,
                })
            current_emotion = emotion
            current_start = year

    if current_emotion is not None:
        periods.append({
            "start": current_start,
            "end": max(yearly_profile.keys()),
            "dominant_emotion": current_emotion,
        })

    return periods


def get_rhetorical_fingerprint(date_str: str = None) -> dict:
    """
    Возвращает риторический отпечаток. Если date_str указан — только за тот год.
    """
    conn = get_connection()
    try:
        if date_str:
            year = int(date_str)
            rows = conn.execute(
                "SELECT text FROM paragraphs WHERE year = ?",
                (year,),
            ).fetchall()

            scores = defaultdict(float)
            devices = defaultdict(int)
            for (text,) in rows:
                a = analyze_paragraph(text)
                for cat, s in a["scores"].items():
                    scores[cat] += s
                for dev, c in a["devices"].items():
                    devices[dev] += c

            n = max(len(rows), 1)
            return {
                "year": year,
                "paragraphs": len(rows),
                "scores_per_para": {k: round(v / n, 3) for k, v in scores.items()},
                "devices_per_1000": {k: round(v * 1000 / n, 1) for k, v in devices.items()},
                "dominant": max(scores, key=scores.get) if scores else "neutral",
            }

        return build_rhetorical_profile(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    year = sys.argv[1] if len(sys.argv) > 1 else None
    profile = get_rhetorical_fingerprint(year)
    print(json.dumps(profile, indent=2, ensure_ascii=False))
