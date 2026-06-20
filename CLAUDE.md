# CLAUDE.md — Retail GeoAI Platform (Евроторг)

Справочный файл для Claude Code. Описывает фактическое состояние проекта, целевую архитектуру, порядок внедрения и соглашения по коду.

---

## 1. Назначение

**Autonomous Retail Site Selection Platform** — система геопространственного анализа для менеджеров по развитию сети «Евроторг».

### Текущие возможности (v1 — GIS Web App)
- Оценка локаций по адресу: геокодинг → изохроны → скоринг → модель Хаффа
- Пространственный анализ: изохроны пешком/авто, демография, конкуренты
- Скоринг 0–100 и прогноз доли рынка (модель Хаффа)
- PDF-отчёты (WeasyPrint + Jinja2)
- Пакетные загрузки адресов (Excel/CSV через Celery)
- Демография из Белстата (SDMX-JSON API)
- Рисование полигонов на карте (анализ по зоне)

### Целевое состояние (v2 — Autonomous Spatial Intelligence Platform)
- AI-оркестратор с MCP-инструментами для автономного пространственного анализа
- Spatial Feature Store (H3-индексация, агрегация, кэш)
- Competition Intelligence Engine (graph, overlap, cannibalization, white-space)
- ML-платформа (CatBoost revenue prediction, SHAP explainability)
- Mobility Engine (потоки, OD-матрицы, dwell-time)
- Scenario Simulation (что-если анализ: открытие конкурента, изменение парковки)
- Event-driven architecture (Kafka/Redis Streams)

---

## 2. Архитектура

### Три уровня (принцип: UI → FastAPI → MCP, UI никогда не вызывает MCP напрямую)

```
┌─────────────────────────────────────────────┐
│              FRONTEND (React)               │
│  Leaflet + Ant Design + Redux + AI Drawer   │
└─────────────────┬───────────────────────────┘
                  │ REST / WebSocket
┌─────────────────▼───────────────────────────┐
│           API GATEWAY (FastAPI)             │
│  Auth + Domain Services + Orchestrator      │
└──────┬──────────┬───────────────┬───────────┘
       │          │               │
       ▼          ▼               ▼
┌──────────┐ ┌──────────┐ ┌──────────────────┐
│ Domain   │ │ MCP      │ │ Async Workers    │
│ Services │ │ Layer    │ │ (Celery)         │
└──────────┘ └──────────┘ └──────────────────┘
       │          │               │
       └──────────┴───────┬───────┘
                          ▼
              ┌───────────────────┐
              │ PostgreSQL+PostGIS│
              │ Redis · MinIO     │
              └───────────────────┘
```

### Domain Services (бизнес-логика)
- `geocode_service` — геокодинг (2GIS, OSM fallback)
- `geometry_service` — контуры зданий, площадь, входы
- `isochrone_service` — изохроны через ORS
- `competitor_service` — поиск и нормализация конкурентов
- `demography_service` — население, зарплаты, плотность
- `scoring_service` — взвешенный скоринг 0–100
- `huff_service` — gravity model, market share
- `report_service` — PDF/Excel генерация
- `batch_processor` — пакетная обработка адресов

### MCP Layer (AI-инструменты, не core engine)
- **Google Maps MCP** — routing, directions, distance matrix, place details
- **OpenStreetMap MCP** — geocoding, POI, accessibility, neighborhood analysis
- **Custom Retail MCP** (будущее) — Huff, cannibalization, scoring, white-space
- **PostGIS MCP** (будущее) — spatial SQL queries через AI
- **FastAPI MCP bridge** (будущее) — expose internal endpoints as MCP tools

### AI Orchestrator (будущее)
- Принимает запрос пользователя → классифицирует intent
- Выбирает MCP-инструменты → выполняет план
- Собирает результат → объясняет → предлагает следующий шаг
- НЕ модифицирует данные без подтверждения пользователя

---

## 3. Технологический стек

### Frontend
| Технология | Версия | Роль |
|-----------|--------|------|
| React | 18.3 | UI-фреймворк |
| TypeScript | 5.4 | Типизация |
| Vite | 5.3 | Сборка и dev-сервер |
| Ant Design | 5.18 | UI-компоненты |
| Redux Toolkit | 2.2 | State management |
| **Leaflet** | 1.9 | Картографический движок (заменил 2GIS MapGL — CDN был недоступен) |
| Recharts | 2.12 | Графики (radar chart, bar) |
| Axios | 1.7 | HTTP-клиент |

> ⚠️ Карта — Leaflet + OpenStreetMap тайлы. 2GIS MapGL убран из-за `ERR_TIMED_OUT` CDN.
> Для спутниковых тайлов используется Esri World Imagery.

### Backend
| Технология | Версия | Роль |
|-----------|--------|------|
| Python | 3.11+ | Язык |
| FastAPI | 0.111 | Web-фреймворк (async) |
| SQLAlchemy | 2.0 | ORM (async) |
| GeoAlchemy2 | 0.15 | PostGIS-поля |
| Alembic | 1.13 | Миграции БД |
| Celery | 5.4 | Очередь задач |
| Redis | 7 | Брокер + кэш |
| GeoPandas / Shapely | latest | GIS-операции |
| WeasyPrint | 62 | PDF-генерация |
| Jinja2 | 3.1 | HTML-шаблоны |
| tenacity | 8.3 | Retry для внешних API |

### Планируемые технологии (v2+)
| Технология | Роль | Фаза |
|-----------|------|------|
| H3 (Uber) | Spatial hex indexing | Phase 2 |
| DeckGL / MapLibre | Тяжёлая геовизуализация, heatmaps | Phase 4 |
| CatBoost / XGBoost | ML revenue prediction | Phase 7 |
| SHAP / LIME | Explainability | Phase 7 |
| LangGraph | AI agent orchestration | Phase 8 |
| Qdrant | Vector DB для AI memory | Phase 8 |
| Kafka / Redis Streams | Event bus | Phase 10 |
| DuckDB | OLAP для feature store | Phase 6 |
| Neo4j / NetworkX | Competition graph | Phase 4 |
| MobilityDB + Trackintel | Trajectory analysis | Phase 5 |

### База данных
- **PostgreSQL 15** + **PostGIS 3.4**
- **Redis 7** — кэш геокодинга (TTL 30 дней), брокер Celery

### Внешние API (ключи в `.env`, НЕ в git)
| API | Env-переменная | Использование |
|-----|---------------|--------------|
| 2GIS Geocoder/Places | `TWOGIS_API_KEY` | Геокодинг + поиск конкурентов |
| OpenRouteService | `OPENROUTESERVICE_API_KEY` | Изохроны + travel-time матрица |
| Google Maps Platform | `GOOGLE_MAPS_API_KEY` | MCP: routing, directions, places |
| Overpass (OSM) | — | Контуры зданий, парковки (бесплатно) |
| Белстат SDMX-JSON | — | Демография (бесплатно) |

### MCP-серверы (`.claude/settings.local.json`, НЕ в git)
| MCP | Пакет | Статус |
|-----|-------|--------|
| Google Maps | `@modelcontextprotocol/server-google-maps` | Подключён, ключ настроен |
| OpenStreetMap | `@cyanheads/openstreetmap-mcp-server` | Подключён, без ключа |

---

## 4. Структура каталогов

### Текущая (v1)
```
retail-site-selection/
├── .env                        # Ключи (НЕ в git)
├── .env.example
├── .claude/settings.local.json # MCP-серверы + API ключи (НЕ в git)
├── docker-compose.yml
├── CLAUDE.md                   # Этот файл
│
├── backend/
│   ├── main.py                 # Production FastAPI (нужен PostgreSQL)
│   ├── main_local.py           # Stub-сервер БЕЗ БД
│   ├── celery_worker.py        # Celery app + Beat schedule
│   ├── requirements.txt
│   ├── app/
│   │   ├── api/v1/endpoints/   # auth, locations, analysis, batch, reports, demographics
│   │   ├── core/               # config, database, redis, exceptions
│   │   ├── models/             # SQLAlchemy ORM (user, location, competitor, our_store, demographics, scoring_result, batch_job)
│   │   ├── schemas/            # Pydantic v2 DTO
│   │   ├── services/           # geocode, isochrone, scoring, huff, report, batch_processor, demographics
│   │   ├── integrations/       # twogis, openrouteservice, overpass, belstat, yandex(unused)
│   │   ├── tasks/              # Celery: batch, huff, report, demographics
│   │   └── templates/          # Jinja2 PDF шаблон
│   ├── migrations/             # Alembic (sync psycopg2)
│   └── tests/                  # pytest: scoring, huff, batch_processor
│
├── frontend/
│   ├── index.html
│   ├── vite.config.ts          # proxy /api → :8000
│   └── src/
│       ├── components/
│       │   ├── Layout/AppLayout.tsx
│       │   ├── Map/MapboxMap.tsx        # Leaflet (файл назван MapboxMap исторически)
│       │   ├── Map/DrawPolygonControl.tsx
│       │   └── Panels/AnalysisDrawer.tsx
│       ├── pages/              # LoginPage, Dashboard, MapPage, LocationsList, BatchUpload, Reports, Settings
│       ├── store/              # Redux: auth, map, locations, ui
│       ├── services/api.ts     # Axios + все API-функции
│       └── styles/global.css
│
└── scripts/
    └── belstat_import.py       # Одноразовый импорт демографии
```

### Целевая (v2 — по мере внедрения)
```
retail-geoai/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/       # Существующие + ai.py
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/               # Существующие domain services
│   │   ├── integrations/           # Существующие API-клиенты
│   │   ├── tasks/
│   │   ├── orchestrator/           # NEW: analysis_orchestrator.py, pipeline.py
│   │   ├── spatial/                # NEW: h3_indexing.py, hex_aggregator.py, catchment_engine.py
│   │   ├── competition/            # NEW: overlap.py, cannibalization.py, white_space.py, market_graph.py
│   │   ├── mobility/              # NEW: trajectory.py, staypoints.py, od_matrix.py, flow_analysis.py
│   │   ├── ml/                     # NEW: feature_pipeline.py, training.py, inference.py, explainability.py
│   │   ├── mcp/                    # NEW: mcp_router.py, retail_mcp_server.py
│   │   └── feature_store/          # NEW: spatial_features.py, temporal_features.py, registry.py
│   └── ...
│
├── frontend/src/
│   ├── pages/                      # Существующие + NewAnalysis, LocationDetail, Heatmap, DataSources, AIAssistant
│   ├── components/
│   │   ├── AI/                     # NEW: AIDrawer.tsx, AIChat.tsx, QuickActions.tsx
│   │   ├── Analysis/               # NEW: ScenarioSwitcher.tsx, ParameterPanel.tsx
│   │   ├── Location/               # NEW: LocationCard.tsx, ScoringBreakdown.tsx, CompetitorTable.tsx
│   │   └── Heatmap/                # NEW: HexLayer.tsx, SaturationOverlay.tsx
│   └── store/                      # + aiSlice.ts, analysisSlice.ts
└── ...
```

---

## 5. Переменные окружения

### Backend (`.env`)
```env
POSTGRES_HOST=localhost          # "postgres" в Docker
POSTGRES_PORT=5433               # хост-порт Docker postgres (5432 занят локальным Windows PostgreSQL)
POSTGRES_DB=retail_db
POSTGRES_USER=retail_user
POSTGRES_PASSWORD=secure_password
REDIS_HOST=localhost             # "redis" в Docker
REDIS_PORT=6379
SECRET_KEY=...
TWOGIS_API_KEY=...
OPENROUTESERVICE_API_KEY=...
GOOGLE_MAPS_API_KEY=...          # NEW: для Google Maps MCP
OVERPASS_API_URL=https://overpass-api.de/api/interpreter
CELERY_BROKER_URL=redis://localhost:6379/0
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

### Frontend (`frontend/.env.development`)
```env
VITE_API_URL=http://localhost:8000
```

---

## 6. Запуск

### Локально (stub, без PostgreSQL)
```bash
.venv/Scripts/uvicorn backend.main_local:app --host 0.0.0.0 --port 8000 --reload
cd frontend && npm run dev
```

### Docker Compose (полный стек)
```bash
docker-compose up --build
docker-compose exec backend alembic -c backend/migrations/alembic.ini upgrade head
```

| Сервис | URL |
|--------|-----|
| Frontend | http://127.0.0.1:3000 |
| Backend API | http://127.0.0.1:8000 |
| Swagger UI | http://127.0.0.1:8000/docs |

---

## 7. API — ключевые эндпоинты

### Текущие (v1)
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/auth/token` | JWT логин |
| GET | `/api/v1/auth/me` | Текущий пользователь |
| GET/POST/PATCH/DELETE | `/api/v1/locations` | CRUD объектов |
| **POST** | **`/api/v1/analysis/by-address`** | **Главный pipeline** |
| POST | `/api/v1/analysis/by-polygon` | Анализ по нарисованному полигону |
| POST | `/api/v1/batch/upload` | Загрузка Excel/CSV |
| GET | `/api/v1/batch/{id}` | Статус batch-job |
| POST | `/api/v1/reports/{id}/generate` | Генерация PDF |
| GET | `/api/v1/demographics/regions` | Демография по регионам |

### Планируемые (v2)
| Метод | Путь | Описание | Фаза |
|-------|------|----------|------|
| POST | `/api/v1/analysis/start` | Job-based анализ с stages | 3 |
| GET | `/api/v1/analysis/{id}` | Статус + прогресс job | 3 |
| POST | `/api/v1/analysis/{id}/recalculate` | Пересчёт скоринга | 3 |
| POST | `/api/v1/analysis/{id}/approve` | Одобрить локацию | 3 |
| GET | `/api/v1/analytics/heatmap` | Тепловая карта района | 9 |
| GET | `/api/v1/analytics/saturation` | Индекс насыщения | 9 |
| POST | `/api/v1/ai/chat` | AI-ассистент запрос | 8 |
| POST | `/api/v1/ai/action` | AI-approved action | 8 |
| GET | `/api/v1/ai/context/{location_id}` | Контекст для AI | 8 |

---

## 8. Алгоритмы

### Скоринг (ScoringService)
Взвешенная сумма 5 компонентов (сумма весов = 1.0):

| Компонент | Вес | Описание |
|-----------|-----|----------|
| Демография | 30% | Население, плотность, доходы в изохроне |
| Конкуренты | 25% | Количество, расстояние, форматы |
| Доступность | 20% | Пешеходная/автомобильная доступность |
| Видимость | 15% | Фасад, вход, проходимость |
| Локация (ТКП-45) | 10% | Нормативная обеспеченность |

Штраф за каннибализацию: ×0.75 если собственный магазин ближе 800 м.

### Модель Хаффа (HuffService)
```
P(i,j) = (A_j^α / T_ij^β) / Σ_k (A_k^α / T_ik^β)
```
- `A_j` — площадь магазина (м²), `T_ij` — время доступа (мин)
- `β = 2.0`, `α = 1.0` (по умолчанию, настраивается в Settings)

### Планируемые алгоритмы (v2)
- **Cannibalization Engine** — overlap ratio, revenue transfer, shared customer probability
- **White-space Detection** — зоны с низкой конкуренцией и достаточной демографией
- **Revenue Prediction** — CatBoost/XGBoost по spatial features
- **Geographically Weighted Regression** — PySAL для пространственной регрессии
- **Scenario Simulation** — what-if: открытие конкурента, изменение трафика

---

## 9. Что сделано / что планируется

### ✅ Реализовано (v1)
- SQLAlchemy-модели с GeoAlchemy2 (8 таблиц, миграция applied)
- Pydantic v2 схемы
- GeocodeService (2GIS + Redis-кэш 30 дней)
- IsochroneService (ORS + Redis-кэш 7 дней)
- ScoringService (взвешенный, 0–100)
- HuffService (gravity model)
- BatchProcessor (parse Excel/CSV)
- ReportService (WeasyPrint + Jinja2)
- DemographicsService + Belstat SDMX-JSON интеграция
- Все интеграции с retry (tenacity)
- Celery-задачи: batch, huff, report, demographics (Beat — 1-е числа)
- JWT-аутентификация (passlib bcrypt)
- Все API-эндпоинты (auth, locations, analysis, batch, reports, demographics)
- Alembic migration (sync psycopg2, 8 таблиц)
- Frontend: Leaflet карта, клик→анализ, изохроны как полигоны
- Frontend: DrawPolygonControl (лассо-инструмент)
- Frontend: 7 страниц (Dashboard, Map, Locations, Batch, Reports, Settings, Login)
- Frontend: Redux store (auth, map, locations, ui)
- Frontend: AnalysisDrawer (score, radar chart, конкуренты)
- Frontend: полноценная страница Reports (таблица объектов + генерация PDF)
- Stub-сервер main_local.py для разработки без БД
- Docker Compose (postgres, redis, backend, celery, celery-beat, frontend)
- 14 backend-тестов (pytest)
- MCP-серверы: Google Maps, OpenStreetMap (в .claude/settings.local.json)
- GitHub: https://github.com/ivanovich1071/Retail-Site-Selection

### 🔲 Планируется (v2, по фазам — см. раздел 12)
**Phase 1** — Core Infrastructure hardening
**Phase 2** — Spatial Foundation (H3, isochrone engine, POI ingestion)
**Phase 3** — Location Object Analysis (job-based workflow, catchment)
**Phase 4** — Competition Intelligence (Huff engine, overlap, cannibalization, market graph)
**Phase 5** — Mobility Engine (trajectories, staypoints, OD-matrix)
**Phase 6** — Feature Store (spatial + temporal + competition features)
**Phase 7** — ML Platform (CatBoost, SHAP, MLflow)
**Phase 8** — AI Orchestrator (LangGraph, MCP tools, AI drawer)
**Phase 9** — Heatmap + Scenario Simulation
**Phase 10** — Event-Driven Architecture (Kafka)
**Phase 11** — Observability (Prometheus, Grafana, Loki)
**Phase 12** — Production Hardening (RBAC, audit, HA, CDN)

---

## 10. Пользовательские сценарии

### Сценарий A: Один адрес
1. Ввод адреса → геокодинг → координаты
2. Контур здания (OSM/Overpass)
3. Изохроны 5/10/15 мин (ORS)
4. Конкуренты в зоне (2GIS + PostGIS)
5. Демография (Белстат/PostGIS)
6. Скоринг 0–100 + Huff share
7. Результат на карте + AnalysisDrawer

### Сценарий B: Полигон на карте
1. Рисование зоны → centroid + площадь
2. Pipeline как в сценарии A от шага 3

### Сценарий C: Batch (Excel/CSV)
1. Upload файла → Celery job
2. Для каждой строки — pipeline A
3. Таблица результатов с рейтингом

### Сценарий D: Район/город (v2, Phase 9)
1. Выбор региона → макроданные
2. Heatmap дефицита обеспеченности
3. White-space detection → кандидаты
4. Микромодель по адресам внутри зоны

### Сценарий E: AI-assisted (v2, Phase 8)
1. Запрос в AI drawer: "Найди белые пятна в Минске"
2. AI → plan → MCP tools → heatmap
3. Результат на карте + объяснение + next action

---

## 11. Страницы фронтенда

### Текущие (v1)
| Страница | Путь | Статус |
|----------|------|--------|
| Login | `/login` | ✅ Работает |
| Dashboard | `/dashboard` | ✅ KPI + последние объекты |
| Map | `/map` | ✅ Leaflet + поиск + анализ + полигоны |
| Locations | `/locations` | ✅ Таблица с фильтром |
| Batch Upload | `/batch` | ✅ Drag-and-drop |
| Reports | `/reports` | ✅ Таблица + генерация PDF |
| Settings | `/settings` | ✅ Веса скоринга + Huff параметры |

### Планируемые (v2)
| Страница | Путь | Фаза | Описание |
|----------|------|------|----------|
| New Analysis | `/analysis/new` | 3 | Wizard: address/map/polygon/batch/AI |
| Location Detail | `/locations/{id}` | 3 | Вкладки: overview, map, competitors, demography, scoring, huff, history, AI notes |
| Heatmap | `/heatmap` | 9 | Тепловая карта + фильтры + white-space |
| Data Sources | `/data-sources` | 6 | Здоровье интеграций, sync logs |
| Scoring Rules | `/scoring-rules` | 7 | ML-конфиг + SHAP visualization |
| AI Assistant | drawer, не страница | 8 | Чат + quick actions + explanations |

### AI Assistant Drawer (v2, Phase 8)
- Постоянная боковая панель на любой странице
- Контекст-aware: видит текущую локацию, регион, фильтры
- Quick actions: Geocode, Analyze, Compare, Recalculate, Export, Summarize
- Intents: site analysis, competitor search, scoring explanation, report generation, batch import, white-space

---

## 12. Пошаговый план внедрения (Roadmap)

> Принцип: **vertical slices** — каждая фаза даёт работающий функционал (DB + Backend + API + Frontend + Tests).
> НЕ строить "сначала весь backend, потом frontend".

### Phase 1 — Core Infrastructure (2–3 недели)
**Цель:** Стабилизировать foundation, переключиться с stub на реальную БД

| # | Задача | Тип |
|---|--------|-----|
| 1.1 | Docker infrastructure: PostgreSQL+PostGIS, Redis, backend, frontend, Celery, nginx | infra |
| 1.2 | Alembic: autogenerate миграции для всех 8 таблиц, upgrade head | backend |
| 1.3 | Переключить main.py на реальную БД (убрать зависимость от main_local.py) | backend |
| 1.4 | CI/CD: GitHub Actions (lint ruff, pytest, tsc --noEmit) | infra |
| 1.5 | Healthcheck endpoints для всех сервисов | backend |
| 1.6 | Frontend: RTK Query или react-query вместо ручных axios-вызовов | frontend |
| 1.7 | Frontend: Error boundaries, loading states, empty states для всех страниц | frontend |
| 1.8 | Тесты: integration tests для API endpoints (TestClient + test DB) | tests |

**Результат:** Полностью рабочий проект на реальной БД с CI/CD.

### Phase 2 — Spatial Foundation (3–4 недели)
**Цель:** H3-индексация, улучшенные изохроны, нормализованный POI ingestion

| # | Задача | Тип |
|---|--------|-----|
| 2.1 | `spatial/h3_indexing.py` — H3 hex grid (pip install h3) | backend |
| 2.2 | `spatial/hex_aggregator.py` — агрегация population/density по hex | backend |
| 2.3 | API: `POST /h3/polyfill`, `GET /h3/neighbors` | backend |
| 2.4 | Isochrone Engine: OSMnx fallback если ORS лимит исчерпан | backend |
| 2.5 | POI ingestion pipeline: OSM → normalize → deduplicate → PostGIS | backend |
| 2.6 | Frontend: H3 hex layer на карте (DeckGL HexagonLayer) | frontend |
| 2.7 | Frontend: zoom-dependent aggregation (мелкий зум = крупные hex) | frontend |
| 2.8 | Тесты: polygon→H3, aggregation, spatial joins | tests |

**Результат:** Spatial indexing, быстрые spatial joins, hex-визуализация.

### Phase 3 — Location Object Analysis (3–4 недели)
**Цель:** Job-based analysis workflow, полная карточка объекта

| # | Задача | Тип |
|---|--------|-----|
| 3.1 | `orchestrator/analysis_orchestrator.py` — stage-based pipeline | backend |
| 3.2 | Модель `AnalysisJob` (status: queued→geocoding→routing→scoring→completed) | backend |
| 3.3 | API: `POST /analysis/start`, `GET /analysis/{id}`, WebSocket progress | backend |
| 3.4 | `catchment_engine.py` — walk/drive/radius catchment | backend |
| 3.5 | Frontend: New Analysis page (scenario switcher: address/map/polygon/batch) | frontend |
| 3.6 | Frontend: Location Detail page (вкладки: overview, map, competitors, demography, scoring, huff, history) | frontend |
| 3.7 | Frontend: job progress bar с stages | frontend |
| 3.8 | Approve/Reject workflow для локаций | full-stack |
| 3.9 | Тесты: pipeline stages, job state transitions | tests |

**Результат:** Полноценный аналитический workflow с прогрессом и детальной карточкой.

### Phase 4 — Competition Intelligence (4–5 недель)
**Цель:** Competition graph, cannibalization, overlap, white-space

| # | Задача | Тип |
|---|--------|-----|
| 4.1 | `competition/huff_engine.py` — расширенный Huff с калибровкой | backend |
| 4.2 | `competition/overlap.py` — overlap ratio между зонами обслуживания | backend |
| 4.3 | `competition/cannibalization.py` — revenue transfer, shared customers | backend |
| 4.4 | `competition/white_space.py` — зоны с дефицитом торговых площадей | backend |
| 4.5 | `competition/market_graph.py` — граф конкуренции (NetworkX) | backend |
| 4.6 | API: `GET /locations/{id}/competitors`, `GET /analytics/white-space` | backend |
| 4.7 | Frontend: competitor influence zones на карте | frontend |
| 4.8 | Frontend: cannibalization overlay (красная зона overlap) | frontend |
| 4.9 | Frontend: таблица конкурентов (brand, distance, format, overlap%) | frontend |
| 4.10 | Тесты: probability normalization, overlap edge cases | tests |

**Результат:** Полноценный competition intelligence с визуализацией.

### Phase 5 — Mobility Engine (5–6 недель)
**Цель:** Анализ пешеходных/автомобильных потоков

| # | Задача | Тип |
|---|--------|-----|
| 5.1 | `mobility/trajectory.py` — GPS cleaning, Trackintel integration | backend |
| 5.2 | `mobility/staypoints.py` — detection + dwell time | backend |
| 5.3 | `mobility/od_matrix.py` — origin-destination матрица | backend |
| 5.4 | `mobility/flow_analysis.py` — directional flow, commuter ratio | backend |
| 5.5 | MobilityDB extension в PostGIS | infra |
| 5.6 | Frontend: animated flow lines на карте | frontend |
| 5.7 | Frontend: time slider для temporal patterns | frontend |
| 5.8 | Тесты: trajectory cleaning, stop detection | tests |

**Результат:** Mobility intelligence — потоки, dwell-time, OD-матрицы.

### Phase 6 — Feature Store (3–4 недели)
**Цель:** Централизованное хранилище пространственных фичей

| # | Задача | Тип |
|---|--------|-----|
| 6.1 | `feature_store/spatial_features.py` — density, footfall, walkability, parking | backend |
| 6.2 | `feature_store/temporal_features.py` — seasonality, weekday patterns | backend |
| 6.3 | `feature_store/competition_features.py` — overlap, saturation, LQ | backend |
| 6.4 | `feature_store/registry.py` — feature metadata + versioning | backend |
| 6.5 | Redis cache layer для hot features | backend |
| 6.6 | DuckDB для OLAP-агрегаций | backend |
| 6.7 | Frontend: Data Sources page (sync status, coverage, health) | frontend |
| 6.8 | Тесты: cache invalidation, aggregation consistency | tests |

**Результат:** Feature vectors для каждого H3-hex, готовые к ML.

### Phase 7 — ML Platform (4–5 недель)
**Цель:** Revenue prediction, explainability

| # | Задача | Тип |
|---|--------|-----|
| 7.1 | `ml/feature_pipeline.py` — feature extraction из feature store | backend |
| 7.2 | `ml/training.py` — CatBoost revenue model | backend |
| 7.3 | `ml/inference.py` — prediction API | backend |
| 7.4 | `ml/explainability.py` — SHAP values per prediction | backend |
| 7.5 | MLflow для experiment tracking | infra |
| 7.6 | API: `GET /locations/{id}/prediction`, `GET /locations/{id}/explanation` | backend |
| 7.7 | Frontend: Scoring Rules page (SHAP waterfall chart, feature importance) | frontend |
| 7.8 | Frontend: prediction panel в Location Detail | frontend |
| 7.9 | Тесты: drift detection, prediction consistency | tests |

**Результат:** ML-driven scoring с объяснениями.

### Phase 8 — AI Orchestrator + MCP (4–5 недель)
**Цель:** AI-ассистент с MCP-инструментами

| # | Задача | Тип |
|---|--------|-----|
| 8.1 | `mcp/mcp_router.py` — tool router (retry, cache, timeout, fallback) | backend |
| 8.2 | `mcp/retail_mcp_server.py` — custom tools: huff, score, cannibalization, white-space | backend |
| 8.3 | `orchestrator/ai_agent.py` — LangGraph agent с approved actions | backend |
| 8.4 | API: `POST /ai/chat`, `POST /ai/action`, `GET /ai/context/{id}` | backend |
| 8.5 | FastAPI MCP bridge (fastapi_mcp) для expose internal endpoints | backend |
| 8.6 | Frontend: AI Drawer (чат, quick actions, context-aware suggestions) | frontend |
| 8.7 | Frontend: inline AI explanations в Location Detail | frontend |
| 8.8 | Тесты: tool calling, spatial reasoning consistency | tests |

**Результат:** AI copilot для геоанализа.

### Phase 9 — Heatmap + Scenario Simulation (3–4 недели)
**Цель:** Макроаналитика и what-if сценарии

| # | Задача | Тип |
|---|--------|-----|
| 9.1 | `simulation/scenarios.py` — competitor opening, parking change, economic shock | backend |
| 9.2 | API: `GET /analytics/heatmap`, `POST /simulation/run` | backend |
| 9.3 | Frontend: Heatmap page (region/format/threshold filters, deficit overlay) | frontend |
| 9.4 | Frontend: Scenario comparison panel | frontend |
| 9.5 | Тесты: simulation consistency, heatmap data | tests |

**Результат:** Стратегический инструмент для выбора районов.

### Phase 10 — Event-Driven Architecture (2–3 недели)
**Цель:** Реактивная система

| # | Задача | Тип |
|---|--------|-----|
| 10.1 | Kafka / Redis Streams event bus | infra |
| 10.2 | Events: location.created, score.changed, competitor.added, mobility.updated | backend |
| 10.3 | Event-triggered recalculations | backend |
| 10.4 | Frontend: real-time updates через WebSocket | frontend |

### Phase 11 — Observability (2 недели)
| # | Задача | Тип |
|---|--------|-----|
| 11.1 | Prometheus metrics | infra |
| 11.2 | Grafana dashboards | infra |
| 11.3 | Loki logs | infra |
| 11.4 | OpenTelemetry tracing | backend |

### Phase 12 — Production Hardening (3–4 недели)
| # | Задача | Тип |
|---|--------|-----|
| 12.1 | RBAC (role-based access control) | full-stack |
| 12.2 | Audit logs | backend |
| 12.3 | Rate limiting | backend |
| 12.4 | Automated backups | infra |
| 12.5 | HA PostgreSQL | infra |
| 12.6 | CDN для static assets | infra |

---

## 13. Принципы разработки

### Архитектурные
- **UI → FastAPI → MCP** — frontend никогда не вызывает MCP напрямую
- **MCP = augmentation, не core engine** — MCP нестабилен (timeouts, rate limits), core logic всегда в domain services
- **Job-based architecture** — тяжёлые операции через Celery, stage-based status
- **Vertical slices** — каждая фича = DB + Backend + API + Frontend + Tests
- **Immutable analysis history** — каждый анализ сохраняется, не перезаписывается
- **Confidence tracking** — каждый результат имеет source + confidence score

### Код
- **Python:** PEP 8, типизация mypy, линтер `ruff`
- **TypeScript/React:** ESLint + Prettier, функциональные компоненты, хуки
- **Коммиты:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`)
- **Ветки:** `main` — продакшн, `develop` — разработка, `feature/*` — фичи
- **Комментарии:** только если WHY неочевиден

### AI Agent
- AI = геоаналитический помощник, НЕ заменяет бизнес-правила
- AI НЕ модифицирует данные без подтверждения пользователя
- AI объясняет score, сравнивает, рекомендует, генерирует отчёты
- AI НЕ выполняет arbitrary SQL, НЕ изобретает данные

---

## 14. Тестирование

```bash
# Backend — unit + integration (37 тестов)
.venv/Scripts/python -m pytest backend/tests -v

# Frontend
cd frontend && npx tsc --noEmit

# Lint (конфиг в ruff.toml: select E,F,W; ignore E501,E741)
ruff check backend/

# E2E (планируется)
npx playwright test
```

**Unit-тесты** (без БД): `ScoringService`, `HuffService`, `BatchProcessor`, H3-модуль.

**Integration-тесты** (`backend/tests/test_api_*.py`, нужен PostgreSQL+PostGIS):
- TestClient + asyncpg на тестовой БД `retail_test_db`.
- `conftest.py`: на Windows ставит `WindowsSelectorEventLoopPolicy` (иначе asyncpg
  падает с `WinError 64`), переопределяет `get_db` на NullPool-engine.
- Если БД недоступна — DB-тесты пропускаются (`requires_db`), unit-тесты идут.
- Внешние API (2GIS, ORS) мокаются через `unittest.mock.AsyncMock`.

> ⚠️ `bcrypt` закреплён на `4.0.1` — `passlib` 1.7.4 несовместим с `bcrypt>=4.1`
> (auth-эндпоинты падают на проверке длины пароля).

> ⚠️ Alembic на Windows падает с `UnicodeDecodeError` (psycopg2 + русская локаль).
> Обход: генерировать SQL через `alembic upgrade head --sql` и применять
> `docker exec retail_postgres psql`. В CI (Linux) `alembic upgrade head` работает напрямую.

---

## 15. Деплой

- **Локально (stub):** http://127.0.0.1:3000 / http://127.0.0.1:8000
- **Docker:** `docker-compose up --build`
- **Продакшн:** Docker Swarm / Kubernetes
- **Секреты:** `.env` (dev), Vault (prod)
- **Мониторинг:** Sentry + Prometheus + Grafana (Phase 11)
- **GitHub:** https://github.com/ivanovich1071/Retail-Site-Selection
