install:
	poetry install --with dev

lint:
	poetry run ruff check .
	poetry run ruff format --check .
	poetry run mypy --config-file pyproject.toml .

test:
	poetry run pytest -m "not integration"

test-integration:
	poetry run pytest -m "integration"

precommit-install:
	poetry run pre-commit install --hook-type pre-push

run:
	poetry run python main.py

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
