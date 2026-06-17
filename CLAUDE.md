# CLAUDE.md — Retail Site Selection (Евроторг)

Справочный файл для Claude Code. Описывает фактическое состояние проекта, соглашения и инструкции по работе с кодом.

---

## 1. Назначение

Веб-приложение для менеджеров по развитию сети «Евроторг». Позволяет:
- Оценивать потенциальные локации по адресу (геокодинг → изохроны → скоринг → модель Хаффа).
- Выполнять пространственный анализ: изохроны пешком/авто, демография, конкуренты.
- Рассчитывать скоринг (0–100) и прогноз доли рынка (модель Хаффа).
- Генерировать PDF-отчёты (WeasyPrint + Jinja2).
- Обрабатывать пакетные загрузки адресов (Excel/CSV через Celery).

---

## 2. Технологический стек

### Frontend
| Технология | Версия | Роль |
|-----------|--------|------|
| React | 18.3 | UI-фреймворк |
| TypeScript | 5.4 | Типизация |
| Vite | 5.3 | Сборка и dev-сервер |
| Ant Design | 5.18 | UI-компоненты |
| Redux Toolkit | 2.2 | State management |
| **@2gis/mapgl** | 1.57 | Картографический движок (2GIS MapGL JS) |
| Recharts | 2.12 | Графики (radar chart, bar) |
| Axios | 1.7 | HTTP-клиент |

> ⚠️ Mapbox НЕ используется. Карта — 2GIS MapGL JS, токен в `VITE_TWOGIS_KEY`.

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

### База данных
- **PostgreSQL 15** + расширение **PostGIS 3.4**
- **Redis 7** — кэш геокодинга (TTL 30 дней), брокер Celery

### Внешние API (реальные ключи в `.env`)
| API | Ключ | Использование |
|-----|------|--------------|
| **2GIS Geocoder API** | `TWOGIS_API_KEY` | Геокодинг адресов (основной) |
| **2GIS Places API** | `TWOGIS_API_KEY` | Поиск конкурентов в радиусе |
| **2GIS MapGL JS** | `VITE_TWOGIS_KEY` | Отображение карты (frontend) |
| **OpenRouteService** | `OPENROUTESERVICE_API_KEY` | Изохроны + матрица времён для Хаффа |
| **Overpass (OSM)** | — | Контуры зданий, парковки (бесплатно) |
| Яндекс.Геокодер | — | **НЕ используется** (ключа нет) |

> Лимиты 2GIS (бесплатный план): Geocoder 1 000 req/мес, Isochrone 30 req/день.
> Redis-кэш критически важен — геокодинг кэшируется на 30 дней.

---

## 3. Структура каталогов (фактическая)

```
retail-site-selection/
├── .env                        # Реальные ключи (НЕ в git — см. .gitignore)
├── .env.example                # Шаблон без ключей
├── .gitignore
├── docker-compose.yml          # postgres, redis, backend, celery, frontend
├── Dockerfile.backend
├── Dockerfile.frontend
├── Makefile
├── README.md
├── CLAUDE.md                   # Этот файл
│
├── backend/
│   ├── main.py                 # Точка входа FastAPI (production, требует PostgreSQL)
│   ├── main_local.py           # Stub-сервер для локального запуска БЕЗ БД
│   ├── celery_worker.py        # Celery app + регистрация задач
│   ├── requirements.txt
│   │
│   ├── app/
│   │   ├── api/v1/
│   │   │   └── endpoints/
│   │   │       ├── auth.py         # JWT: /token, /register, /me
│   │   │       ├── locations.py    # CRUD + фото + scoring
│   │   │       ├── analysis.py     # POST /by-address — главный pipeline
│   │   │       ├── batch.py        # upload, status, results
│   │   │       └── reports.py      # generate + download PDF
│   │   │
│   │   ├── core/
│   │   │   ├── config.py           # Settings (pydantic-settings, из .env)
│   │   │   ├── database.py         # async SQLAlchemy engine + get_db()
│   │   │   ├── redis.py            # cache_get / cache_set / cache_delete
│   │   │   └── exceptions.py       # GeocodeError, IsochroneError, etc.
│   │   │
│   │   ├── models/                 # SQLAlchemy ORM (все с GeoAlchemy2)
│   │   │   ├── user.py             # users (id, email, role)
│   │   │   ├── location.py         # locations (geom POINT, building POLYGON)
│   │   │   ├── competitor.py       # competitors (geom POINT)
│   │   │   ├── our_store.py        # our_stores (geom POINT)
│   │   │   ├── demographics.py     # demographics_zones (geom MULTIPOLYGON)
│   │   │   ├── scoring_result.py   # scoring_results
│   │   │   └── batch_job.py        # batch_jobs + batch_results
│   │   │
│   │   ├── schemas/                # Pydantic v2 DTO
│   │   │   ├── auth.py
│   │   │   ├── location.py
│   │   │   ├── analysis.py         # AnalysisByAddressRequest, AnalysisResult
│   │   │   └── batch.py
│   │   │
│   │   ├── services/               # Бизнес-логика
│   │   │   ├── geocode.py          # GeocodeService (2GIS, без Яндекса)
│   │   │   ├── isochrone.py        # IsochroneService → ORS
│   │   │   ├── scoring.py          # ScoringService (0–100, веса)
│   │   │   ├── huff.py             # HuffService (gravity model, β=2)
│   │   │   ├── report.py           # ReportService (WeasyPrint)
│   │   │   └── batch_processor.py  # BatchProcessor (parse Excel/CSV)
│   │   │
│   │   ├── integrations/           # HTTP-клиенты внешних API (с retry)
│   │   │   ├── twogis_client.py    # geocode() + search_competitors()
│   │   │   ├── openrouteservice_client.py  # get_isochrones() + get_travel_times()
│   │   │   ├── overpass_client.py  # get_building_at() + get_nearby_parking()
│   │   │   └── yandex_geocoder.py  # Есть в коде, но НЕ используется
│   │   │
│   │   ├── tasks/                  # Celery-задачи
│   │   │   ├── batch_tasks.py      # process_batch
│   │   │   ├── huff_tasks.py       # calculate_huff_for_location
│   │   │   └── report_tasks.py     # generate_pdf_report
│   │   │
│   │   └── templates/
│   │       └── report.html         # Jinja2 шаблон PDF-отчёта
│   │
│   ├── migrations/
│   │   ├── alembic.ini
│   │   └── env.py                  # async Alembic env
│   │
│   └── tests/
│       ├── test_scoring.py         # 5 тестов ScoringService
│       ├── test_huff.py            # 4 теста HuffService
│       └── test_batch_processor.py # 5 тестов BatchProcessor
│
└── frontend/
    ├── index.html                  # CSS 2GIS MapGL: mapgl.2gis.com/api/css/v1
    ├── vite.config.ts              # host: 0.0.0.0, port: 3000, proxy /api → :8000
    ├── tsconfig.json
    ├── package.json
    ├── .env.development            # VITE_API_URL, VITE_TWOGIS_KEY
    │
    └── src/
        ├── index.tsx
        ├── App.tsx                 # Router, ConfigProvider (цвет #1a5276)
        │
        ├── components/
        │   ├── Layout/AppLayout.tsx    # Sidebar + Header + user menu
        │   ├── Map/MapboxMap.tsx       # 2GIS MapGL JS (файл называется Mapbox, но это 2GIS)
        │   └── Panels/AnalysisDrawer.tsx # Score, RadarChart, таблица конкурентов
        │
        ├── pages/
        │   ├── LoginPage.tsx
        │   ├── Dashboard.tsx       # KPI-карточки + список последних объектов
        │   ├── MapPage.tsx         # Карта + тулбар (поиск, слои, сохранить)
        │   ├── LocationsList.tsx   # Таблица с фильтром по статусу
        │   ├── BatchUpload.tsx     # Drag-and-drop + прогресс задач
        │   ├── Reports.tsx         # Заглушка (ссылка на страницу объектов)
        │   └── Settings.tsx        # Веса скоринга + параметры Хаффа
        │
        ├── store/
        │   ├── index.ts
        │   ├── authSlice.ts        # JWT токен, login/logout, fetchMe
        │   ├── mapSlice.ts         # coords, analysisResult, activeLayer (scheme/satellite/hybrid)
        │   ├── locationSlice.ts    # CRUD список объектов, пагинация
        │   └── uiSlice.ts          # sidebarCollapsed, analysisPanelOpen
        │
        ├── hooks/redux.ts          # useAppDispatch, useAppSelector
        ├── services/api.ts         # Axios instance + все API-функции
        └── styles/global.css
```

---

## 4. Переменные окружения

### Backend (`.env` в корне)
```env
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=retail_db
POSTGRES_USER=retail_user
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# FastAPI
SECRET_KEY=...          # openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 2GIS (основной API)
TWOGIS_API_KEY=eyJvcmci...   # в .env, НЕ публикуй

# OpenRouteService (изохроны)
OPENROUTESERVICE_API_KEY=5278f4fc-...   # в .env, НЕ публикуй

# Overpass (OSM, бесплатно)
OVERPASS_API_URL=https://overpass-api.de/api/interpreter

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Загрузки
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE_MB=50

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Frontend (`frontend/.env.development`)
```env
VITE_API_URL=http://localhost:8000
VITE_TWOGIS_KEY=eyJvcmci...   # тот же 2GIS ключ, для карты
```

---

## 5. Запуск

### Локально без Docker (текущий режим)
```bash
# Backend — stub (без PostgreSQL/Redis)
.venv/Scripts/uvicorn backend.main_local:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend && npm run dev
# → http://127.0.0.1:3000
# → http://127.0.0.1:8000/docs
```

### Полный стек через Docker Compose
```bash
cp .env.example .env      # заполнить ключи
docker-compose up --build

# После первого запуска — миграции:
docker-compose exec backend alembic -c backend/migrations/alembic.ini upgrade head
```

Сервисы:
| Сервис | URL |
|--------|-----|
| Frontend | http://127.0.0.1:3000 |
| Backend API | http://127.0.0.1:8000 |
| Swagger UI | http://127.0.0.1:8000/docs |

---

## 6. API — ключевые эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/auth/token` | Логин, получить JWT |
| POST | `/api/v1/auth/register` | Регистрация |
| GET  | `/api/v1/auth/me` | Текущий пользователь |
| GET  | `/api/v1/locations` | Список объектов (пагинация, фильтр статуса) |
| POST | `/api/v1/locations` | Создать объект |
| PATCH| `/api/v1/locations/{id}` | Обновить |
| DELETE | `/api/v1/locations/{id}` | Удалить |
| POST | `/api/v1/locations/{id}/photo` | Загрузить фото |
| GET  | `/api/v1/locations/{id}/scoring` | Последний результат скоринга |
| **POST** | **`/api/v1/analysis/by-address`** | **Главный pipeline: геокодинг → изохроны → конкуренты → скоринг → Хафф** |
| POST | `/api/v1/batch/upload` | Загрузить Excel/CSV |
| GET  | `/api/v1/batch` | Список задач |
| GET  | `/api/v1/batch/{id}` | Статус + результаты |
| POST | `/api/v1/reports/{id}/generate` | Запустить генерацию PDF |
| GET  | `/api/v1/reports/{id}/download` | Скачать PDF |

---

## 7. Алгоритмы

### Скоринг (ScoringService)
Взвешенная сумма 5 компонентов (сумма весов = 1.0):

| Компонент | Вес по умолчанию |
|-----------|-----------------|
| Демография | 30% |
| Конкуренты | 25% |
| Доступность | 20% |
| Видимость | 15% |
| Локация (ТКП-45) | 10% |

Штраф за каннибализацию: ×0.75 если собственный магазин ближе 800 м.

### Модель Хаффа (HuffService)
```
P(i,j) = (A_j^α / T_ij^β) / Σ_k (A_k^α / T_ik^β)
```
- `A_j` — площадь магазина (м²)
- `T_ij` — время доступа (мин) из зоны `i` до магазина `j`
- `β = 2.0` (параметр затухания по умолчанию)
- `α = 1.0`

### Изохроны
Строятся через **OpenRouteService** (не 2GIS Isochrone API — лимит 30/день).
Профили: `foot-walking`, `driving-car`, `cycling-regular`.
Кэш: Redis, TTL = 7 дней.

---

## 8. Что сделано / что не сделано

### ✅ Реализовано
- Все SQLAlchemy-модели с GeoAlchemy2
- Все Pydantic-схемы (v2)
- GeocodeService (2GIS, с Redis-кэшем 30 дней)
- IsochroneService (ORS, с Redis-кэшем 7 дней)
- ScoringService (взвешенный, 0–100)
- HuffService (gravity model)
- BatchProcessor (parse Excel/CSV)
- ReportService (WeasyPrint + Jinja2)
- Все интеграции с retry (tenacity): 2GIS, ORS, Overpass
- Celery-задачи: process_batch, calculate_huff, generate_pdf
- JWT-аутентификация (passlib bcrypt)
- Все API-эндпоинты (auth, locations, analysis, batch, reports)
- Alembic migration env (async)
- Frontend: 2GIS MapGL JS карта, клик→анализ, изохроны как слои
- Frontend: все 6 страниц (Dashboard, Map, Locations, Batch, Reports, Settings)
- Frontend: Redux store (auth, map, locations, ui)
- Frontend: AnalysisDrawer (score, radar chart, конкуренты)
- Stub-сервер `main_local.py` для локального запуска без БД
- Docker Compose (6 сервисов), Dockerfile × 2
- 14 backend-тестов (pytest)

### ❌ Не реализовано (следующие итерации)
- `scripts/belstat_parser.py` — импорт демографии из Белстата
- `services/demographics.py` — пространственные запросы к demographics_zones
- `repositories/` — DAO-слой для геозапросов (location_repo, competitor_repo и др.)
- `services/osm.py` — преобразование OSM-данных в GeoJSON
- `services/competitor.py` — синхронизация конкурентов из 2GIS в БД
- `utils/geometry_utils.py`, `utils/logger.py`, `utils/validators.py`
- Draw-инструмент «Лассо» на карте (выделение района)
- Тепловая карта дефицита/избытка площадей (ТКП-45)
- WebSocket для real-time прогресса batch (сейчас polling)
- Frontend-тесты (Jest + React Testing Library)
- `alembic revision --autogenerate` — первая миграция (нужна БД)
- CI/CD (GitHub Actions)
- Панорама (вкладка в AnalysisDrawer)

---

## 9. Соглашения по коду

- **Python:** PEP 8, типизация mypy, линтер `ruff`
- **TypeScript/React:** ESLint + Prettier, функциональные компоненты, хуки
- **Коммиты:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`)
- **Ветки:** `main` — продакшн, `develop` — разработка, `feature/*` — новые фичи
- **Комментарии:** только если WHY неочевиден; не описывать WHAT

---

## 10. Тестирование

```bash
# Backend (без БД, только unit-тесты)
cd "Retail Site Selection"
.venv/Scripts/pytest backend/tests -v

# Frontend
cd frontend && npm test
```

Покрытые модули: `ScoringService`, `HuffService`, `BatchProcessor`.

---

## 11. Контакты и деплой

- **Локально (stub):** `http://127.0.0.1:3000` / `http://127.0.0.1:8000`
- **Докер:** `docker-compose up --build`
- **Продакшн:** Docker Swarm / Kubernetes, секреты через `.env` или Vault
- **Мониторинг (планируется):** Sentry + Prometheus + Grafana
