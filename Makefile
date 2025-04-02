.PHONY: install lint format typecheck check run

install:
	poetry install --with dev

lint:
	poetry run ruff check src

format:
	poetry run ruff format src

typecheck:
	poetry run mypy src

check: lint format typecheck

run:
	poetry run python src/bot.py

setup-pre-commit:
	poetry run pre-commit install
