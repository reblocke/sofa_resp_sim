---
name: streamlit-app-verification
description: Use when changing files under `python/src/sofa_resp_sim/web/`, applet presets, request validation, app exports, or app-facing runbook/docs. Do not use for math-only changes that do not touch the app layer.
---

Verification checklist:

1. Re-run the current web/service tests.
2. Run native Streamlit app smoke tests if present.
3. Check:
   - initial render succeeds,
   - representative control paths work,
   - validation failures show user-facing errors instead of crashing,
   - sweep guardrails still trigger correctly,
   - export schemas remain stable if they changed intentionally.
4. Update:
   - `README.md` app launch command if changed,
   - `docs/ARCHITECTURE.md` if app boundaries changed,
   - `docs/VALIDATION.md` if app contracts changed.

Suggested commands:
```bash
uv run pytest -q python/tests/test_web_*
uv run pytest -q python/tests/test_streamlit_app_smoke.py
```
