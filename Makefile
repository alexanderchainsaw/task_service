
lint:
	uv run isort ./app
	uv run black ./app

test:
	pytest -v --cov=app

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down


run: down build up

