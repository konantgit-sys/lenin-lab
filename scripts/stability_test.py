#!/usr/bin/env python3
"""
Фаза 2.3 v3 — Устойчивость концептов по периодам.
Стратегия: один проход по каждому периоду, считаем все концепты за один запрос.
"""
import json, sqlite3, sys, re
from collections import defaultdict, Counter

DB_PATH = os.environ.get("LENIN_DB", "/home/agent/data/projects/lenin-knowledge/lenin.db")
db = sqlite3.connect(DB_PATH)

print("=" * 60)
print("ФАЗА 2.3: УСТОЙЧИВОСТЬ КЛАСТЕРОВ")
print("=" * 60)

# Baseline
with open("concept_cache.json") as f:
    cache = json.load(f)
baseline_nodes = cache["graph"]["nodes_data"]
baseline = {n["id"]: n["cluster_name"] for n in baseline_nodes}
baseline_clusters = Counter(n["cluster_name"] for n in baseline_nodes)

# Загружаем концепты
sys.path.insert(0, ".")
from engines.engine_02_concepts import CONCEPTS
import os

# Строим regex для всех 206 концептов (только основные формы)
concept_regexes = {}
for cid, forms in CONCEPTS.items():
    # Берём первую форму (основную), экранируем
    pattern = re.compile(re.escape(forms[0]), re.IGNORECASE)
    concept_regexes[cid] = pattern

PERIODS = [
    ("1893-1905", 1893, 1905),
    ("1906-1914", 1906, 1914),
    ("1915-1922", 1915, 1922),
]

print("\nBaseline:", len(baseline_clusters), "кластеров,", len(baseline_nodes), "концептов")
print("Метод: один SQL-запрос на период + regex в Python\n")

period_results = {}

for name, yf, yt in PERIODS:
    print(f"[{name}] Загрузка параграфов...")
    cur = db.cursor()
    cur.execute(
        "SELECT text FROM paragraphs WHERE year >= ? AND year <= ?",
        (yf, yt)
    )
    
    freqs = Counter()
    total_chars = 0
    row_count = 0
    
    for (text,) in cur:
        row_count += 1
        total_chars += len(text)
        for cid, pattern in concept_regexes.items():
            if pattern.search(text):
                freqs[cid] += 1
        
        if row_count % 30000 == 0:
            print(f"  ... {row_count} строк обработано")
    
    period_results[name] = {
        "total_paragraphs": row_count,
        "total_chars": total_chars,
        "concepts_found": len(freqs),
        "top10": freqs.most_common(10),
        "top30": freqs.most_common(30)
    }
    print(f"  → {row_count} параграфов, {len(freqs)} концептов найдено")
    top3 = freqs.most_common(3)
    print(f"  → Топ-3: {', '.join([f'{c}({n})' for c,n in top3])}")

# Сравнение overlap
print(f"\n{'='*60}")
print("JACCARD OVERLAP МЕЖДУ ПЕРИОДАМИ")
print(f"{'='*60}")

def jaccard(set1, set2):
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

periods_list = list(PERIODS)
for top_n in [10, 30]:
    print(f"\n--- Топ-{top_n} ---")
    overlaps = []
    for i in range(len(periods_list)):
        for j in range(i+1, len(periods_list)):
            n1, n2 = periods_list[i][0], periods_list[j][0]
            s1 = set(c[0] for c in period_results[n1][f"top{top_n}"])
            s2 = set(c[0] for c in period_results[n2][f"top{top_n}"])
            j = jaccard(s1, s2)
            overlaps.append(j)
            common = s1 & s2
            print(f"  {n1} vs {n2}: overlap={len(common)}/{top_n}, Jaccard={j:.2%}")
            if common:
                print(f"    Общие: {', '.join(sorted(common)[:8])}")
    
    avg = sum(overlaps) / len(overlaps)
    passed = avg >= 0.70
    print(f"  Средний Jaccard: {avg:.2%} → {'✅ ПРОЙДЕН' if passed else '❌ НЕ ПРОЙДЕН'}")

# Смотрим: какие концепты в топ-30 всех трёх периодов
all_periods_top30 = []
for _, pf in period_results.items():
    all_periods_top30.append(set(c[0] for c in pf["top30"]))
stable_concepts = all_periods_top30[0] & all_periods_top30[1] & all_periods_top30[2]
print(f"\nСтабильные концепты (в топ-30 всех 3 периодов): {len(stable_concepts)}")
print(f"  {', '.join(sorted(stable_concepts))}")

# Итог
print(f"\n{'='*60}")
print("ИТОГОВАЯ ОЦЕНКА УСТОЙЧИВОСТИ")
print(f"{'='*60}")

avg10 = sum(jaccard(set(c[0] for c in period_results[periods_list[i][0]]["top10"]),
                     set(c[0] for c in period_results[periods_list[j][0]]["top10"]))
            for i in range(len(periods_list)) for j in range(i+1, len(periods_list))) / 3

avg30 = sum(jaccard(set(c[0] for c in period_results[periods_list[i][0]]["top30"]),
                     set(c[0] for c in period_results[periods_list[j][0]]["top30"]))
            for i in range(len(periods_list)) for j in range(i+1, len(periods_list))) / 3

print(f"  Jaccard топ-10: {avg10:.2%} → {'✅' if avg10>=0.70 else '❌'}")
print(f"  Jaccard топ-30: {avg30:.2%} → {'✅' if avg30>=0.70 else '❌'}")
print(f"  Стабильных концептов: {len(stable_concepts)} (присутствуют в топ-30 всех периодов)")

# Сохраняем
out = {
    "baseline": {"clusters": len(baseline_clusters), "concepts": len(baseline_nodes)},
    "periods": {
        name: {
            "paragraphs": pf["total_paragraphs"],
            "concepts_found": pf["concepts_found"],
            "top10": pf["top10"],
            "top30": pf["top30"]
        }
        for name, pf in period_results.items()
    },
    "jaccard_top10": round(avg10, 4),
    "jaccard_top30": round(avg30, 4),
    "stable_concepts_count": len(stable_concepts),
    "stable_concepts": sorted(stable_concepts),
    "criterion_passed": avg30 >= 0.70
}

with open("stability_test_results.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# TXT
lines = ["ОТЧЁТ: УСТОЙЧИВОСТЬ КЛАСТЕРОВ КОНЦЕПТОВ\n"]
lines.append(f"Метод: сравнение топ-концептов по 3 периодам (1893-1905, 1906-1914, 1915-1922)\n")
for name, pf in period_results.items():
    lines.append(f"{name} ({pf['total_paragraphs']} параграфов):")
    lines.append(f"  Топ-10: {', '.join([f'{c}({n})' for c,n in pf['top10']])}")
lines.append(f"\nJaccard overlap топ-10: {avg10:.2%}")
lines.append(f"Jaccard overlap топ-30: {avg30:.2%}")
lines.append(f"Стабильных концептов: {len(stable_concepts)}")
lines.append(f"Критерий 70%: {'ПРОЙДЕН' if avg30>=0.70 else 'НЕ ПРОЙДЕН'}")
with open("stability_test_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\n✅ stability_test_results.json + stability_test_report.txt")
