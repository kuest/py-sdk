.PHONY: sync lint format format-check typecheck test test-watch test-integration check build

sync:
	uv sync --all-extras --all-groups

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run pyright

test:
	uv run pytest -m "not integration"

test-watch:
	uv run ptw --now . -- -m "not integration"

test-integration:
	uv run pytest -m integration

check: lint format-check typecheck test

build:
	uv build
