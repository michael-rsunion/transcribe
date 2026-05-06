.PHONY: install test lint run docker-build docker-run guard-crm

install:
	uv sync

test:
	uv run pytest -v --cov=app --cov-report=term-missing

lint:
	uv run ruff check app tests
	uv run ruff format --check app tests

run:
	uv run uvicorn app.main:app --reload --port 8000

docker-build:
	docker build -t transcribe:dev .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env transcribe:dev

guard-crm:
	@bash scripts/guard_crm_uuid.sh
