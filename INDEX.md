# ЛЕНИН-КОРПУС: ИНДЕКС ВСЕГО СОЗДАННОГО

> Последнее обновление: 2026-08-05 02:52 MSK
> Коммитов: 32 | Файлов: 121 (py/html/js/json/md)

---

## 1. ЯДРО — 10 ДВИЖКОВ (ТРЕК 1) ✅ ЗАВЕРШЁН

Все работают, API отдают живые данные, сайт обновляется.

| # | Движок | Файл | KB | Назначение |
|---|--------|------|----|------------|
| 01 | Хронология | `engines/engine_01_chronology.py` | 5 | 169 067 параграфов → год + период |
| 02 | Концепты | `engines/engine_02_concepts.py` | 50 | 206 концептов, 12 735 рёбер, 8 кластеров Louvain |
| 03 | Диалектика | `engines/engine_03_dialectics.py` | 17 | 24 781 триада (тезис→антитезис→синтез) |
| 04 | Оппоненты | `engines/engine_04_opponents.py` | 28 | 29 оппонентов, 62 связи, лагеря |
| 05 | Машина времени | `engines/engine_05_timemachine.py` | 11 | 4 формата дат, 31 событие, контексты |
| 06 | Риторика | `engines/engine_06_rhetoric.py` | 12 | 5 осей × 169K параграфов |
| 07 | Позиции | `engines/engine_07_positions.py` | 29 | 518 тем, 1 502 цитаты, 14 категорий |
| 08 | Цитаты | `engines/engine_08_quotes.py` | 12 | 5 000 цитат, скор 10.9 |
| 09 | Сравнение | `engines/engine_09_comparative.py` | 53 | 89 тем Marx/Engels/Lenin (обновлён v2.32) |
| 10 | Мастер | `engines/engine_10_master.py` | 10 | Объединяет все поиски |

---

## 2. 10 ПРОДУКТОВ — iframe-панели на lenin-book.v2.site ✅ ВСЕ РАБОТАЮТ

| # | Продукт | URL | Файл | API |
|---|---------|-----|------|-----|
| 1 | Oracle (поиск) | `/oracle/` | `oracle/index.html` (7 KB) | `/api/oracle/search`, `/api/oracle/random`, `/api/oracle/stats` |
| 2 | White Paper | `/papers/` | `papers/index.html` (7 KB) | `/api/papers/concepts`, `/api/papers/generate` |
| 3 | Противоречия | `/contradictions/` | `contradictions/index.html` (4 KB) | `/api/contradictions` (30 противоречий) |
| 4 | Тени | `/shadow/` | `shadow/index.html` (5 KB) | `/api/shadow` (дрейф частотности) |
| 5 | Паспорт ДНК | `/passport/` | `passport/index.html` (5 KB) | `/api/passport` (стилометрия) |
| 6 | Digital Twin | `/twin/` | `twin/index.html` (5 KB) | `/api/twin`, `/api/twin/ask` |
| 7 | Dashboard | `/dashboard/` | `dashboard/index.html` (8 KB) | Все метрики в реальном времени |
| 8 | Компаратор | `/comparator/` | `comparator/index.html` (6 KB) | `/api/comparator/topics`, `/api/comparator/compare` |
| 9 | Obsidian Plugin | `/obsidian/` | `obsidian/index.html` (3 KB) | ZIP: `plugins/lenin-search.zip` |
| 10 | Стиль Ленина | `/style/` | `style/index.html` (7 KB) | `/api/style/generate` (FTS5 + 6 тонов) |

---

## 3. 26 ПАНЕЛЕЙ САЙТА (index.html)

Панели 0-11: движки (аналитика)
Панели 12-21: продукты (iframe)
Панели 22-24: data/json дампы
Панель 25: полная книга (PDF)

---

## 4. API (api_v2.py) — 90+ эндпоинтов

| Группа | Эндпоинты |
|--------|-----------|
| Ядро | `/api/stats`, `/api/summary`, `/api/search`, `/api/health` |
| Движки | `/api/timeline`, `/api/rhetoric`, `/api/concepts`, `/api/opponents`, `/api/entropy`, `/api/phantoms`, `/api/tomography`, `/api/legend`, `/api/quote` |
| Продукты | `/api/oracle/*`, `/api/papers/*`, `/api/contradictions`, `/api/shadow`, `/api/passport`, `/api/twin/*`, `/api/style/*` |
| v1 API | `/api/v1/health`, `/api/v1/register`, `/api/v1/stats`, `/api/v1/analytics`, `/api/v1/rotate-key`, `/api/v1/search`, `/api/v1/timeline/{year}`, `/api/v1/quotes`, `/api/v1/concepts`, `/api/v1/concept/{name}`, `/api/v1/compare`, `/api/v1/entropy`, `/api/v1/phantoms` |
| Компаратор | `/api/comparator/*` |

---

## 5. ТЕХНИЧЕСКИЙ СТЕК

| Слой | Технология |
|------|-----------|
| БД | SQLite 3 + FTS5 (`lenin.db`, ~300 MB) |
| Векторный поиск | FAISS (93 711 × 1024d, 367 MB) |
| Бэкенд | Python 3.11, FastAPI (uvicorn, порт 9770) |
| Фронтенд | Vanilla JS, Canvas, SVG, D3.js |
| Визуализация | UMAP, Matplotlib |
| NLP | NLTK, pymorphy2, custom parsers |
| Деплой | lenin-book.v2.site, port.txt, start.sh |

---

## 6. ИСТОРИЯ КОММИТОВ (32)

| # | SHA | Описание |
|---|-----|----------|
| 1-10 | — | Трек 1: 10 движков (хронология → мастер) |
| 11 | 6b74b27 | Исправление: старый контент |
| 12 | b583d07 | Визуал + интерактив |
| 13 | — | Вкладки 1-9 |
| 14 | a9f96a9 | Томография + Фантомы + Энтропия |
| 15 | 4ab8905 | v2.25 — Triple audit fixes |
| 16 | cb5c170 | v2.26 — Analytics + Key rotation |
| 17 | c2bbd8c | v2.27 — API docs |
| 18 | 325a84c | v2.27 — OpenAPI spec |
| 19 | 94cc245 | v2.28 — Methodology page |
| 20 | ec0613e | v2.29 — Honest concept graph audit |
| 21 | 711df89 | v2.31 — Validated concept graph + security |
| 22 | 2d190b2 | v2.31 — Release notes: 8 corrections |
| 23 | ccd659a | v2.31 — Methodology page + blog post |
| 24 | 8f1b6cb | v2.31 — Add methodology link |
| 25 | d348bf6 | v2.32 — 10 iframe panels + Comparator 89/89 + Style FTS5 |

---

## 7. КЛЮЧЕВЫЕ МЕТРИКИ

| Метрика | Значение |
|---------|----------|
| Параграфов | 169 067 |
| Томов | 55 |
| Лет охвата | 25 (1893–1922) |
| Символов | 48.5M |
| Векторов FAISS | 93 711 |
| Концептов | 206 |
| Кластеров | 8 |
| Оппонентов | 29 |
| Диалектических триад | 24 781 |
| Цитат с оценкой | 5 000 |
| Позиций | 518 |
| API-эндпоинтов | 90+ |
| Панелей на сайте | 26 |
| Продуктов (iframe) | 10 |
| Движков | 10 |

---

## 8. ЧТО ОСТАЛОСЬ (РЕАЛЬНЫЕ ЗАДАЧИ, НЕ СПЕКА)

1. **GitHub sync** — часть файлов лежит только на live, нужно досинхронизировать
2. **API-ключи** — Mistral переведён на env var, нужен `.env` на сервере
3. **Интерпретационные движки** — семантический поиск противоречий, cross-engine linking
4. **Продактизация** — вынос продуктов на отдельные поддомены (lenin-oracle.v2.site и т.д.)
5. **Монетизация** — API-ключи, rate limiting, тарифы
