.PHONY: setup test lint typecheck check config-check compose-config clean

setup:  ## Create venv and install dev dependencies
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip setuptools wheel
	.venv/bin/pip install -e ".[dev]"

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check src tests

typecheck:
	.venv/bin/mypy

config-check:  ## Validate configuration from the environment (secrets are redacted)
	.venv/bin/python -m invar_comms config-check

check: lint typecheck test config-check

compose-config:  ## Validate Docker Compose file (requires Docker)
	docker compose config

clean:
	rm -rf .venv .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info src/*.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
