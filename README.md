# Retail Site Selection — Евроторг

Веб-приложение для автоматизации выбора торговых объектов.

## Быстрый старт

```bash
# 1. Скопировать конфиг и добавить API-ключи
cp .env.example .env

# 2. Собрать и запустить все сервисы
docker-compose up --build

# 3. Применить миграции БД (в отдельном терминале)
docker-compose exec backend alembic -c backend/migrations/alembic.ini upgrade head
```

| Сервис | URL |
|--------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

## Стек

- **Frontend:** React 18 + TypeScript, Ant Design, Redux Toolkit, Mapbox GL JS
- **Backend:** FastAPI (Python 3.11), SQLAlchemy 2 + GeoAlchemy2, Celery + Redis
- **DB:** PostgreSQL 15 + PostGIS 3.4

## Ключевые переменные `.env`

| Переменная | Описание |
|-----------|----------|
| `YANDEX_GEOCODER_API_KEY` | Геокодинг (основной) |
| `TWOGIS_API_KEY` | Поиск конкурентов + fallback геокодинг |
| `OPENROUTESERVICE_API_KEY` | Изохроны и матрица времени |
| `VITE_MAPBOX_TOKEN` | Токен Mapbox GL JS (в `frontend/.env.development`) |
| `SECRET_KEY` | JWT-ключ (генерировать через `openssl rand -hex 32`) |

## Разработка без Docker

```bash
# Backend
cd backend
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload

# Celery worker
celery -A backend.celery_worker worker --loglevel=info

# Frontend
cd frontend
npm install
npm run dev
```

## Тесты

```bash
# Backend
pytest backend/tests -v

# Frontend
cd frontend && npm test
```

## Архитектура

```
┌─────────────┐     REST/WS     ┌──────────────┐
│  React SPA  │◄──────────────►│  FastAPI     │
│  (Mapbox)   │                 │  + Celery    │
└─────────────┘                 └──────┬───────┘
                                       │
                          ┌────────────┼────────────┐
                          ▼            ▼             ▼
                      PostgreSQL    Redis        External APIs
                      + PostGIS    (cache/      (ORS, 2GIS,
                                   broker)       Yandex, OSM)
```
