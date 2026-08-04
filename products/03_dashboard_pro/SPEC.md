# Lenin Dashboard Pro — Спецификация
# Поддомен: lenin-dash.v2.site
# Статус: 🟡 SPEC READY

## ФАЗЫ

### Фаза 1: Каркас (дни 1-2)
- [ ] HTML/CSS сетка: sidebar + 3-колоночный layout
- [ ] Тёмная/светлая тема (CSS variables)
- [ ] Навигация: 10 секций
- [ ] Загрузка данных через /api/* (прокси к API-серверу)

### Фаза 2: Базовые секции (дни 3-4)
- [ ] Overview: ключевые метрики (карточки)
- [ ] Timeline Explorer: D3.js шкала с brush-зумом
- [ ] Quote Studio: поиск + фильтры + копирование
- [ ] Concept Mapper: heatmap частота × год
- [ ] Stats: круговая диаграмма по периодам

### Фаза 3: Продвинутые секции (дни 5-6)
- [ ] Rhetoric Lab: 5 осей на одном графике с переключателями
- [ ] Dialectic Viewer: список триад с фильтрацией по году + теме
- [ ] Opponent Network: force-directed граф (D3.js)
- [ ] Tomography Lab: canvas с зумом + drag

### Фаза 4: Экспорт (день 7)
- [ ] PDF-отчёт (render_document)
- [ ] CSV-выгрузка для каждой секции
- [ ] Share link (create_share_link)
- [ ] JSON API для внешних запросов
