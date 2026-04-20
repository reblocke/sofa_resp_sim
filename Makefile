.PHONY: sync lint format test check app sim-help build

UV ?= uv

sync:
	$(UV) sync --dev

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

test:
	$(UV) run pytest -q

check: lint test

app:
	$(UV) run streamlit run python/src/sofa_resp_sim/web/applet_streamlit.py

sim-help:
	$(UV) run resp-sofa-sim --help

build:
	$(UV) run python -m build
