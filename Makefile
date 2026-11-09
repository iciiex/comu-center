.PHONY: setup run test lint check seed clean

setup:  ## Create venv and install dev dependencies
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"

run:  ## Run the prototype on http://0.0.0.0:8000
	.venv/bin/uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check app tests

check: lint test

seed:  ## Rebuild the demo database from scratch
	rm -f var/kiloos.db
	.venv/bin/python -m app.seed

clean:
	rm -rf .venv var .pytest_cache .ruff_cache build dist *.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
