.PHONY: install run stop test migrate lint format

install:
	cp -n .env.example .env || true
	docker-compose build

run:
	docker-compose up

run-detached:
	docker-compose up -d

stop:
	docker-compose down

test:
	docker-compose run --rm backend pytest backend/tests -v
	cd frontend && npm test -- --watchAll=false

migrate:
	docker-compose run --rm backend alembic upgrade head

migrate-create:
	docker-compose run --rm backend alembic revision --autogenerate -m "$(name)"

lint:
	docker-compose run --rm backend ruff check backend/
	cd frontend && npm run lint

format:
	docker-compose run --rm backend ruff format backend/
	cd frontend && npm run format

logs:
	docker-compose logs -f backend celery_worker

shell-backend:
	docker-compose exec backend bash

shell-db:
	docker-compose exec postgres psql -U retail_user -d retail_db
