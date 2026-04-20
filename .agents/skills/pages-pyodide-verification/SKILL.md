---
name: pages-pyodide-verification
description: Use when changing `web/`, `scripts/stage_web_python.py`, `src/sofa_resp_sim/browser_contract.py`, browser presets/defaults, request validation, app exports, or Pages/Pyodide docs. Do not use for math-only changes that do not touch the browser-facing layer.
---

Verification checklist:

1. Re-run browser contract and staging tests.
2. Re-stage web assets from source.
3. Run the Playwright static-app smoke test when browser UI, worker, staging, or
   browser payloads changed.
4. Check:
   - Pyodide worker initializes,
   - scenario run completes with rendered chart/table output,
   - small sweep completes with rendered heatmap/table output,
   - validation failures return structured errors,
   - sweep guardrails still trigger,
   - export schemas remain stable if changed intentionally.
5. Update:
   - `README.md` app commands if changed,
   - `docs/WEB_APP.md` or `docs/DEPLOY_PAGES.md` if runtime/deploy behavior changed,
   - `docs/ARCHITECTURE.md` if app boundaries changed,
   - `docs/VALIDATION.md` if app contracts changed.

Suggested commands:

```bash
make stage-web
uv run pytest -q tests/contracts/test_browser_contract.py tests/contracts/test_stage_web_python.py
make e2e
```
