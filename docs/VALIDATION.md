# Validation

## Purpose

This file maps system invariants to tests, generated browser assets, and
checked-in evidence.

## Core invariants

| Invariant | Primary evidence |
|---|---|
| SpO2-to-PaO2 conversion behavior is stable | `tests/core/test_resp_scoring.py`, `tests/core/test_resp_scoring_golden_fixtures.py` |
| FiO2 prioritization and lookback logic are stable | `tests/core/test_resp_scoring.py`, golden fixtures |
| PF ratio scoring and support gating are stable | golden fixtures |
| Acute single-PF suppression is stable | golden fixtures |
| Simulation outputs are deterministic under fixed seeds | `tests/contracts/test_reporting_services.py` |
| Reference normalization is stable | `tests/contracts/test_reporting_reference.py` |
| Sweep shapes and metrics are stable | `tests/contracts/test_reporting_sweep.py` |
| Preset serialization is stable | `tests/contracts/test_reporting_presets.py` |
| Uncertainty table schema is stable | `tests/contracts/test_reporting_uncertainty.py` |
| Browser payloads are JSON serializable and structured | `tests/contracts/test_browser_contract.py` |
| Web staging is allowlist-based and reproducible | `tests/contracts/test_stage_web_python.py` |
| Tracked tree, staged app data, and browser-visible keys remain public-safe | `tests/contracts/test_public_release_hygiene.py` |
| CLI help, happy-path, and invalid-input contracts remain valid | `tests/workflows/test_cli_contract.py` |
| Root docs and metadata do not drift to stale identities | `tests/contracts/test_repository_contract.py` |
| Static app initializes and runs scenario/sweep workflows | `tests/e2e/test_web_app.py` |

## Canonical commands

```bash
uv sync --dev
make stage-web
make test
make e2e
make verify
uv run python -m build
uv run resp-sofa-sim --help
```

`make test` excludes browser e2e tests. `make e2e` stages web assets first and
then runs the Playwright static-app smoke test.

## Artifact evidence

Paired v2 foundation coverage is under `tests/experiments/`: frozen legacy
snapshots, strict request validation, stationary AR statistics, exact episode
shape, independent schedules, nested missingness and shared patient values.
Scoring tests cover bounded membership, source lookup endpoints, support gates,
suppression, evidence statuses, timezone/DST bins and named rule variants.
Paired results tests reconcile all transition cells and contributor IDs, reject
incomplete/duplicate pairs, and check Wilson and exact-discordance interval
anchors including small N and zero discordances.
The AR validation protocol is prespecified in
`tests/experiments/fixtures/ar_validation_protocol.json`.

`tests/e2e/test_pyodide_parity.py` executes staged generation, documentation,
scoring and SciPy interval components plus the production paired worker API.
Discrete scientific fields and logical IDs must match exactly; unrounded floats
use the prespecified absolute/relative tolerance of 1e-10. Raw content checksums
are runtime provenance and are checked against regeneration within each runtime.
This is current API coverage, not proof that future UI/catalogue/bundles pass. Install the pinned Playwright browser with
`uv run playwright install chromium` before browser tests.

Checked-in validation artifacts live under:
- `artifacts/`

See:
- `artifacts/README.md`

Generated browser staging outputs live under:
- `web/assets/py/`
- `web/assets/data/`

Those generated outputs are ignored because `scripts/stage_web_python.py`
recreates them from tracked Python source and checked-in aggregate artifacts.

## Release-oriented checks

Before a release or public visibility change:
- run `make verify`,
- run `uv run python -m build`,
- run `uv run resp-sofa-sim --help`,
- confirm `git status --short --branch --ignored=matching` has no unexpected
  tracked or untracked changes,
- inspect `docs/PUBLIC_RELEASE_AUDIT.md` for PHI/confidentiality and history
  cleanup notes,
- regenerate or document any changed artifacts in `artifacts/README.md`.

## When to update this file

Update this file when:
- a new invariant is added,
- a validation artifact becomes canonical,
- test layout changes,
- public output schemas change,
- the browser contract or static app gains a new stable behavior.

The aggregate-reference interchange has separate strict coverage in
`tests/experiments/test_reference_template.py`: provenance metadata, complete
score/status cells, integer counts, duplicate rejection and denominator
reconciliation. Its examples are invented counts under `docs/templates/`.

## Finite catalogue and deterministic explorer

`tests/experiments/test_catalogue.py` executes all 72 entry/stratum requests at
small N, checks exact saved normalization, edited-base preservation, record
identity for rule-only changes and the replay negative control. These smoke
runs do not satisfy the 2,000-patient reference-demonstration requirement.
`tests/experiments/test_rule_explorer.py` checks conversion edges, measured
cutpoints and explicit singleton versus two-record scoring. Actual Pyodide
parity includes catalogue expansion and the deterministic explorer API.

Freeze or verify configuration snapshots without running simulations:

```bash
uv run python scripts/freeze_experiment_catalogue.py
uv run python scripts/freeze_experiment_catalogue.py --check
```

## Bundles, append and installed reproduction

`tests/experiments/test_bundle.py` checks typed null/zero/string roundtrips,
scientific versus environment identity, corruption/version errors and paired
append without regenerating earlier patients. The CLI test executes directory
and ZIP workflows outside the checkout. The actual Pyodide parity test exports
and imports a browser ZIP and imports it natively.

`make experiments-install-check` builds a wheel, creates a temporary environment
with dependencies exported from the lockfile, confirms imports come from that
environment, and reproduces a native bundle exactly outside the checkout.
Receipts are written to `artifacts/local/acceptance/clean_experiment_install.*`.
Cross-runtime reproduction is explicit: exact request/discrete fields,
atol=rtol=1e-10 for floats, and no claim of byte-identical runtime metadata.

## Full catalogue reference bundles

`make experiments-reference` checks the frozen catalogue and runs all 18
prespecified demonstrations in all four strata. Each stochastic stratum uses
2,000 paired patients with seed 173203; the deterministic episode uses one.
Verified ZIP bundles and per-run logs are retained in
`artifacts/local/references_v2/`. The runner verifies completed N, immutable
requests, table reconciliation and hashes before recording a completed bundle.
On resume, Python, dependency versions and package source must match; mismatches
require a new output directory. Corrupt results are rejected and preserved.

`run_index.json` records progress and bundle identities. Subsets or smaller N
are explicitly marked partial/smoke and cannot certify full reference coverage.
A completed bundle index alone does not certify the figure/findings deliverables
or the final acceptance gates. Figure data and interpretation remain separately
required. Run only one reference runner against an output directory at a time.

After the full bundle run completes, extract compact source-linked summaries:

```bash
uv run python scripts/summarize_experiment_references.py
```

The extractor requires all 72 current requests at the minimum stochastic N,
verifies bundle/archive and scientific hashes, and preserves numeric CSV values.
Its default output is a new `artifacts/experiments_v2/` directory containing the
absolute and paired tables plus `table_provenance.json`. That provenance records
exact bundle, request, and source-table identities, plus six prespecified
patient-0 event/episode trace pairs. Rendered figures have a separate figure-data
manifest; substantive interpretation is recorded in `INTERPRETATION.md`.

Render the primary-outcome absolute and paired figures from those verified tables:

```bash
uv run --group figures python scripts/plot_experiment_references.py
```

The separate locked `figures` dependency group provides Matplotlib; it is not
required by the scientific package or staged browser runtime. Rendering checks
input-table hashes, uses common within-figure scales across the four support
strata, and records each exact row selection and image hash in
`figure_data_manifest.json`. SVG preserves text for inspection; PNG supports
visual review. The manifest starts with visual review pending. Rendering alone
cannot certify figure readability or the complete examples gate.

```bash
uv run python scripts/write_experiment_findings.py
```

This writes a new `FINDINGS.md` from hash-checked paired tables. It describes the
first prespecified primary-outcome contrast within each stratum, explicitly reports
zero-change comparisons and unavailable uncertainty, and links the complete
absolute/paired figures. Contrasts follow preset order, not observed magnitude.
Pointwise intervals are not simultaneous intervals across all comparisons.

The current compact collection contains all 72 source requests, 36 primary
absolute/paired figures, and eight deterministic grids. Each PNG has an exact-hash
visual-review record. Run `uv run python scripts/verify_experiment_evidence.py`
to check completeness and freshness, and the public-release hygiene tests to
check the selected synthetic trace inventory. These checks do not establish
clinical validity. See `artifacts/README.md` for the full artifact inventory.
The generated readout requires scientific review before acceptance.

## Deterministic explorer evidence

```bash
uv run python scripts/build_rule_explorer_evidence.py
uv run --group figures python scripts/plot_rule_explorer_evidence.py
```

These commands create eight explicit grids (476 cells) under
`artifacts/local/rule_explorer_v2/`: saturation conversion edges and measured-PaO2
cutpoint neighborhoods, threshold factors 1.0/0.85, and one/two records. Seven
support categories include unknown support with no supplied FiO2. Every case
retains its normalized request and detailed Python trace, with a flat cell CSV,
content hashes and figure-to-source links. This is deterministic evidence with
no Monte Carlo uncertainty. The low-flow SpO2=90 anchor has P/F=177.88 and reported
scores 0 versus 2 for one versus two records; 49/97 remain conversion-unavailable.

The figures distinguish raw rubric, support-adjusted score and reported encounter
score. Unavailable evidence is gray U; suppressed singleton zero is marked 0*.
Unknown-evidence algorithm zeros are retained in the exported table but displayed
as U in the evidence-aware figure. Visual review is not automatically certified
by rendering. Local outputs must be reviewed and inventoried before promotion to
the final small checked-in evidence collection.

The compact trace collection uses a fixed patient-0 selection: E1 episode/room
air, E2 bias/low flow, E3 timing/HFNC, E4 measured-PaO2/IMV, E5 replay/room air,
and E6 singleton/low flow. It is declared in the extractor rather than chosen
from observed effect sizes. Original event and episode CSVs are copied unchanged
from verified bundles, with hashes and the selection rule recorded in table
provenance. Complete bundles retain the other selected-patient condition traces.

Once the reviewed deterministic collection is placed under
`artifacts/experiments_v2/rule_explorer/`, verify the complete compact evidence:

```bash
uv run python scripts/verify_experiment_evidence.py
```

This requires all 72 source runs at the declared N, complete primary and
deterministic figure sets, the fixed trace collection, source and image hashes,
findings coverage, and visual reviews bound to current PNG hashes. Both PNG and
SVG files must exist. The verifier checks completeness and freshness; it does
not infer scientific validity or replace the requirement-by-requirement audit.
