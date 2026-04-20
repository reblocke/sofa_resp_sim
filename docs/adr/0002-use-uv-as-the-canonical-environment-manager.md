# Use uv as the canonical environment manager

- Status: accepted
- Date: 2026-04-20

## Context and Problem Statement

The repository currently mixes a package-oriented Python layout with a conda-first setup story and no lockfile-driven primary workflow.

## Decision Drivers

- one canonical setup path,
- modern Python project workflow,
- reproducible dependency management,
- simpler CI and contributor onboarding.

## Considered Options

- keep conda/mamba as primary
- use uv as primary and optionally keep conda as secondary
- support multiple equally canonical setup paths

## Decision Outcome

Chosen option: use `uv` as the canonical environment manager.

## Consequences

### Positive
- simpler contributor instructions
- better fit with `pyproject.toml`
- clearer CI story

### Negative
- maintainers who prefer conda may need a secondary convenience path
