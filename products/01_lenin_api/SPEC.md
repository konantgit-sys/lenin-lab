# Lenin API v1 — Спецификация продукта
# Поддомен: lenin-api.v2.site
# Статус: 🟡 SPEC READY

## АРХИТЕКТУРА

```
lenin-api.v2.site (FastAPI, порт 9780)
├── /v1/search?q=X          → FTS5 + FAISS
├── /v1/timeline/{year}     → полный портрет года
├── /v1/quotes?n=5&topic=X  → цитаты
├── /v1/concept/{name}      → концепт: частота, кластер, связи
├── /v1/stats               → статистика корпуса
├── /v1/compare?y1=X&y2=Y   → сравнение лет
├── /v1/entropy             → энтропия Шеннона
├── /v1/phantoms?year=X     → фантомные оппоненты
└── /v1/tomography?n=1000   → UMAP-проекция (сэмпл)
```

## RATE LIMITING

| Tier    | Цена/мес | Запросов/день |
|---------|----------|---------------|
| Free    | $0       | 100           |
| Basic   | $10      | 1 000         |
| Pro     | $50      | 10 000        |
| Enterprise | $500  | ∞             |

## ФАЗЫ

### Фаза 1: Ядро (день 1)
- [ ] FastAPI-приложение с CORS
- [ ] search, timeline, stats, quotes
- [ ] port.txt → 9780
- [ ] start.sh для авторестарта
- [ ] register_subdomain("lenin-api")

### Фаза 2: Авторизация (день 2)
- [ ] API-key middleware
- [ ] Rate limiting (Redis или in-memory)
- [ ] Логирование запросов

### Фаза 3: Документация (день 3)
- [ ] Swagger (auto FastAPI)
- [ ] Примеры запросов в README
- [ ] cURL-сниппеты для каждого эндпоинта
