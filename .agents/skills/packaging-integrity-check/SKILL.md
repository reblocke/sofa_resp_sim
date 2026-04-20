---
name: packaging-integrity-check
description: Use when editing `pyproject.toml`, dependency declarations, console scripts, build backend configuration, setup instructions, CI commands, or any file that changes how the project is installed or run.
---

Checklist:

1. Ensure `pyproject.toml` has truthful metadata.
2. Ensure the build backend matches the actual package layout.
3. Ensure the README and CONTRIBUTING use the same canonical commands.
4. Ensure console scripts point at the correct modules.
5. Ensure tests do not depend on stale package names or undocumented path hacks.
6. If a lockfile is in use, refresh it in a connected environment.

Suggested commands:
```bash
uv sync --dev
uv run python -c "import sofa_resp_sim"
uv run resp-sofa-sim --help
uv run pytest -q
uv run ruff check .
```
