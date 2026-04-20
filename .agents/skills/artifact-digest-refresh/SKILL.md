---
name: artifact-digest-refresh
description: Use when a code change affects checked-in validation artifacts, simulation summary tables, milestone evidence files, or any documented evidence in `artifacts/`. Do not use for changes that do not affect generated evidence.
---

Checklist:

1. Identify which checked-in artifacts are affected.
2. Regenerate or update only the small artifacts that remain intentionally version-controlled.
3. Update `artifacts/README.md` with:
   - source command/script,
   - status,
   - purpose,
   - whether the artifact is release evidence or milestone scratch work.
4. Remove or deprecate obsolete artifacts rather than silently leaving them ambiguous.
