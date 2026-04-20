---
name: docs-sync
description: Use after any substantive change to behavior, commands, package layout, artifact generation, or public-facing outputs. Do not use for pure refactors that leave behavior and developer workflow unchanged unless docs became stale.
---

Update the smallest set of canonical docs needed to keep the repo truthful:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/VALIDATION.md`
- `docs/CLINICAL_SCOPE.md`
- `docs/PROVENANCE.md`
- `docs/TEAM_PRACTICES.md`

Rules:
- Replace stale names and paths.
- Make commands copy-pasteable.
- Prefer canonical docs over milestone scratch notes.
- Keep milestone notes if historically useful, but do not let them be the only source of truth.
