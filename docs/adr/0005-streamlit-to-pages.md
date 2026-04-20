# Migrate from Streamlit to static GitHub Pages with Pyodide

- Status: accepted
- Date: 2026-04-20

## Context and Problem Statement

The project had a functioning Streamlit applet, but the desired publication
target is a static GitHub Pages site. The repository also needed to preserve
Python as the source of truth for respiratory SOFA scoring and simulation.

## Decision Drivers

- deploy without a backend,
- keep scoring and simulation logic centralized in Python,
- make browser outputs reproducible from staged source and aggregate artifacts,
- avoid maintaining parallel Streamlit and static app runtimes,
- keep public documentation aligned with the active runtime.

## Considered Options

- keep Streamlit as the only app surface,
- maintain both Streamlit and a static app,
- migrate to a static Pyodide app and remove Streamlit runtime code.

## Decision Outcome

Chosen option: migrate to a static GitHub Pages app using Pyodide in a web
worker, and remove Streamlit from active dependencies and commands.

Consequences:
- the app can deploy through GitHub Pages,
- browser runtime is slower than native Python for large sweeps,
- Pyodide staging must be tested as a first-class contract,
- JavaScript must remain presentation-only and call Python for all model logic.

## Supersedes

- `docs/adr/0003-keep-python-src-layout-for-now.md`
- `docs/adr/0004-keep-streamlit-as-the-validated-reference-ui.md`
