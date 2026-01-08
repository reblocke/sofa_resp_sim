# TcCO2 Accuracy — Python Port (Codex instructions)

## Continuity Ledger (compaction-safe)
Maintain a single Continuity Ledger for this workspace in `http://CONTINUITY.md`. The ledger is the canonical session briefing designed to survive context compaction; do not rely on earlier chat text unless it’s reflected in the ledger.

### How it works
- At the start of every assistant turn: read `http://CONTINUITY.md`, update it to reflect the latest goal/constraints/decisions/state, then proceed with the work.
- Update `http://CONTINUITY.md` again whenever any of these change: goal, constraints/assumptions, key decisions, progress state (Done/Now/Next), or important tool outcomes.
- Keep it short and stable: facts only, no transcripts. Prefer bullets. Mark uncertainty as `UNCONFIRMED` (never guess).
- If you notice missing recall or a compaction/summary event: refresh/rebuild the ledger from visible context, mark gaps `UNCONFIRMED`, ask up to 1–3 targeted questions, then continue.

### `functions.update_plan` vs the Ledger
- `functions.update_plan` is for short-term execution scaffolding while you work (a small 3–7 step plan with pending/in_progress/completed).
- `http://CONTINUITY.md` is for long-running continuity across compaction (the “what/why/current state”), not a step-by-step task list.
- Keep them consistent: when the plan or state changes, update the ledger at the intent/progress level (not every micro-step).

### In replies
- Begin with a brief “Ledger Snapshot” (Goal + Now/Next + Open Questions). Print the full ledger only when it materially changes or when the user asks.

### `http://CONTINUITY.md` format (keep headings)
- Goal (incl. success criteria):
- Constraints/Assumptions:
- Key decisions:
- State:
- Done:
- Now:
- Next:
- Open questions (UNCONFIRMED if needed):
- Working set (files/ids/commands):


## Goal
Port the TcCO2↔PaCO2 agreement meta-analysis + TriNetX/in-silico simulation pipeline to Python, producing:
1) validated reproduction of Conway (Thorax 2019) meta-analysis outputs,
2) uncertainty-propagated simulation outputs, and
3) an inference function: TcCO2 → interval for PaCO2 (with parameter uncertainty).

## Authority hierarchy (resolve conflicts in this order)
1) Conway Thorax 2019 paper + supplementary methods/code in `Conway Meta/`
2) `docs/SPEC.md` + `docs/DECISIONS.md` (intended behavior for this project)
3) Stata legacy code in `Code/` (reference only; may contain bugs)

When Stata conflicts with (1) or (2):
- implement (1)+(2),
- document the divergence in `docs/DECISIONS.md` with file/line references.

## Non-negotiables
- Difference definition: follow Conway. (Bias/difference is defined as PaCO2 − TcCO2 in the paper.)
- Parameter uncertainty must be propagated via **route-1 study-level bootstrap** (cluster bootstrap over studies).
- Every milestone ends with:
  - run `pytest`,
  - update small artifacts under `artifacts/` (markdown + small tables),
  - `git commit` with a clear message.

## Reproducibility & safety
- Do NOT modify `Code/Legacy/` or `Drafts/`.
- Do NOT commit patient-level or large raw extracts. Use small, de-identified fixtures (e.g., summary tables, tiny sampled rows) under `tests/fixtures/`.
- Prefer validated libraries (numpy/pandas/scipy/statsmodels) over custom re-implementations.

## Python layout
- All new Python code lives under `python/`:
  - `python/src/tcco2_accuracy/`
  - `python/tests/`
- Keep core math pure (no I/O), and isolate I/O to `io.py`/`data.py` modules.

## Definition of done (per milestone)
- Tests pass locally.
- Outputs match validation targets (Conway Table 1 + invariants).
- Artifacts updated.
- Commit created.
