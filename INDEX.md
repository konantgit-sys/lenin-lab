# LENIN-BOOK v2.35 — Project Index

## 1. САЙТ

- **URL:** https://lenin-book.v2.site
- **Порт:** 9770 (uvicorn, single process)
- **Стек:** FastAPI + SQLite (176 MB) + FAISS + FTS5
- **Сервер:** V2Bot pod, Debian 12

## 2. 13 ПРОДУКТОВ — все живые, HTTP 200

| # | Продукт | URL | Python код | Статус |
|---|---------|-----|-----------|--------|
| 01 | Lenin API | `/api/v1/*` | `products/01_lenin_api/api_v1.py` | ✅ REST API |
| 02 | Oracle | `/oracle/` | `products/02_lenin_oracle/app.py` | ✅ FAISS+FTS5 |
| 03 | Dashboard Pro | `/dashboard/` | `products/03_dashboard_pro/routes.py` | ✅ 9 engines |
| 04 | Ideology Comparator | `/comparator/` | `products/04_ideology_comparator/routes.py` | ✅ 89 тем |
| 05 | White Paper | `/white-paper/` | `products/05_white_paper/app.py` | ✅ Papers |
| 06a | Contradictions | `/contradictions/` | `phase_c_engine.py` | ✅ Lenin vs Lenin |
| 06b | Obsidian Plugin | `/obsidian/` | Static | ✅ ZIP download |
| 07 | Digital Twin | `/twin/` | `products/07_digital_twin/twin_engine.py` | ✅ FAISS цитаты |
| 08 | Style Mimic | `/style/` | `products/08_style_mimic/style_engine.py` | ✅ FTS5 + тоны |
| 09 | Knowledge Graph | `/graph/` | Static | ✅ iframe |
| 10 | Generative Art | `/genart/` | Static | ✅ Canvas-частицы |
| 11 | Shadow | `/shadow/` | `products/11_shadow/routes.py` | ✅ Word drift |
| 12 | Passport | `/passport/` | `products/12_passport/routes.py` | ✅ Text DNA |

## 3. АРХИТЕКТУРА

```
api_v2.py (1110 lines)          ← Main server (FastAPI)
├── include_router → 03_dashboard_pro/routes.py
├── include_router → 04_ideology_comparator/routes.py
├── include_router → 11_shadow/routes.py
├── include_router → 12_passport/routes.py
├── 02_oracle         — standalone engine
├── 05_white_paper    — standalone engine
├── 07_digital_twin   — standalone engine
├── 08_style_mimic    — standalone engine
├── 06_contradictions — phase_c_engine
├── 09_graph, 10_genart, 06b_obsidian — static (FileResponse)
└── 01_lenin_api      — standalone REST API

shared/
└── lenin_core.py     — DB access, search (fts5_search, faiss_search, etc.)
```

## 4. API — 80+ эндпоинтов

- `/api/health` — liveness
- `/api/v1/*` — коммерческий API (регистрация, ключи, поиск)
- `/api/oracle/*` — поиск по текстам Ленина
- `/api/twin/*` — диалог от лица Ленина
- `/api/style/*` — генерация текста в стиле Ленина
- `/api/papers/*` — генерация white papers
- `/api/dashboard` — агрегированная статистика
- `/api/comparator/*` — сравнение Marx/Engels/Lenin
- `/api/shadow` — shadow structure (word frequency drift)
- `/api/passport` — стилометрический паспорт
- `/api/quotes`, `/api/comparative` — прямой доступ к данным
- `/api/contradictions` — противоречия
- `/api/stats`, `/api/summary`, `/api/search` и др. — легаси

## 5. GIT

- **Repo:** https://github.com/konantgit-sys/lenin-lab
- **Branch:** master
- **Latest:** v2.34 (33 коммита)

## 6. ТЕХДОЛГ (v2.35)

- ✅ Дубликаты маршрутов удалены (v2.34)
- ✅ 4 продукта вынесены в route-модули: dashboard, comparator, shadow, passport (v2.35)
- ✅ api_v2.py: 1402 → 1110 строк (-292 строки, -21%)
- ✅ shared/lenin_core.py: 7 функций
- ✅ server: single uvicorn process, port 9770
- ⬜ Оставшиеся 3 продукта (genart, obsidian, knowledge_graph) — чисто статические, не требуют Python
