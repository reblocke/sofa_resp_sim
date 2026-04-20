.PHONY: sync stage-web lint format fmt-check test e2e serve verify check sim-help build

UV ?= uv
PYTHON ?= $(UV) run python
RUFF_TARGETS := src tests scripts

sync:
	$(UV) sync --locked --dev

stage-web:
	$(PYTHON) scripts/stage_web_python.py

lint:
	$(UV) run ruff check $(RUFF_TARGETS)

format:
	$(UV) run ruff format $(RUFF_TARGETS)

fmt-check:
	$(UV) run ruff format --check $(RUFF_TARGETS)

test:
	$(UV) run pytest -q --ignore=tests/e2e

e2e: stage-web
	$(UV) run pytest -q tests/e2e

serve: stage-web
	cd web && python3 -m http.server 8000

verify: stage-web fmt-check lint test e2e

check: lint test

sim-help:
	$(UV) run resp-sofa-sim --help

build:
	$(UV) run python -m build
