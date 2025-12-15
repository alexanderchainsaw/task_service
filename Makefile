

lint:
	uv run isort ./app
	uv run black ./app

lint-tests:
	uv run isort ./tests
	uv run black ./tests

test:
	uv sync
	pytest -v --cov=app

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down


run: down build up

