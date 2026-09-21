.PHONY: sync stage-web lint format fmt-check test e2e serve verify check sim-help build experiment-help experiments-smoke experiments-install-check

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

experiment-help:
	$(UV) run resp-sofa-experiment --help

experiments-smoke:
	$(PYTHON) scripts/freeze_experiment_catalogue.py --check
	$(UV) run pytest -q tests/experiments tests/workflows/test_experiment_cli.py

experiments-install-check: build
	$(PYTHON) scripts/check_experiment_install.py

.PHONY: experiments-reference
experiments-reference:
	$(PYTHON) scripts/freeze_experiment_catalogue.py --check
	$(PYTHON) scripts/run_experiment_references.py

.PHONY: historical-reference historical-evidence
historical-reference:
	$(PYTHON) scripts/run_historical_references.py --workers 4

historical-evidence:
	$(UV) run --group figures python scripts/build_historical_evidence.py
	$(PYTHON) scripts/verify_experiment_evidence.py
