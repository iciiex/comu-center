.PHONY: setup run test lint check seed clean docs docs-check graph doctor

# Inside .venv/ on purpose: git, doctor, pytest and workspace snapshots already skip that directory.
GRAPH_VENV ?= .venv/graph
GRAPHIFY_VERSION ?= 0.9.106

setup:  ## Create venv and install dev dependencies
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"

run:  ## Run the prototype on http://0.0.0.0:8000
	.venv/bin/uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload

test:  ## Run the test suite (includes the generated-docs freshness check)
	.venv/bin/pytest

lint:  ## Ruff on app and tests
	.venv/bin/ruff check app tests

check: lint test  ## Lint + tests: run before every handoff

seed:  ## Rebuild the demo database from scratch
	rm -f var/kiloos.db
	.venv/bin/python -m app.seed

docs:  ## Regenerate docs/agent-guide/code-map.md and traceability.md from the code
	python3 .agent/tools/knowledge_map.py

docs-check:  ## Fail when the generated docs are stale; also reports the graph state
	python3 .agent/tools/knowledge_map.py --check

graph:  ## Rebuild graphify-out/ (installs graphify into $(GRAPH_VENV) on first use)
	test -x $(GRAPH_VENV)/bin/graphify || (python3 -m venv $(GRAPH_VENV) && $(GRAPH_VENV)/bin/pip install --quiet "graphifyy[sql]==$(GRAPHIFY_VERSION)")
	$(GRAPH_VENV)/bin/python .agent/tools/knowledge_map.py --graph

doctor:  ## Repository health check: structure, decisions, handoff freshness, secrets
	python3 .agent/tools/doctor.py --root . --strict

clean:  ## Remove virtualenvs (app and graph), runtime data and caches
	rm -rf .venv var .pytest_cache .ruff_cache build dist *.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
