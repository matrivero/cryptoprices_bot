.PHONY: install lint format typecheck check run tests

install:
	poetry install

lint:
	poetry run ruff check src

format:
	poetry run ruff format src

typecheck:
	poetry run mypy src

check: lint format typecheck

run:
	poetry run python src/bot.py

tests:
	poetry run pytest

setup-pre-commit:
	poetry run pre-commit install
