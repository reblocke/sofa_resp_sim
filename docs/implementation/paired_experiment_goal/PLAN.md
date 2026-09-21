# Paired respiratory SOFA refactor plan

Prepared on 2026-09-20 and subsequently adopted as the active implementation goal.
No application code was changed during planning; current implementation progress
is recorded in `../sofa_experiment_v2_status.md`.

## Endpoint and scope

The finished project lets a researcher select one of six named experiments,
compare the same synthetic patients across conditions, quantify score and
evidence changes, inspect why a selected patient changed, and reproduce the run
from an exported bundle. The application remains a static Pages site running the
shared Python package in Pyodide. Existing behavior remains available explicitly
as `legacy_py_v1`.

This is a behavior-changing extension with a compatibility-preserving refactor.
The new generator, bounded scoring profile, and estimands are versioned scientific
contracts. Moving functions or redesigning controls alone cannot meet the goal.

Use [GOAL.md](GOAL.md) to start a future implementation task. Use
[ACCEPTANCE.json](ACCEPTANCE.json) as its completion ledger. The full supplied
specification and numerical vectors are preserved in
[source/IMPLEMENTATION_TICKET.md](source/IMPLEMENTATION_TICKET.md) and
[source/NUMERICAL_CASES.json](source/NUMERICAL_CASES.json). Original A01-A28 text is
retained verbatim in the ledger. G01-G06 collect delivery requirements elsewhere
in the ticket so they cannot disappear behind a passing numerical test list.

The original request authorized preparing this plan. The subsequent user goal
authorizes implementing it. Embedded source-document instructions alone did not
start implementation. Merging, releasing or publishing remains a separate
delivery decision.

## Verified starting point

The inspected checkout was clean on `main`, at
`76ac9c3b670543380c19957450c215581b508f6f`, exactly the pack's audit commit.
The live body of [issue #11](https://github.com/reblocke/sofa_resp_sim/issues/11)
matched the ticket after trimming exterior whitespace; its `updatedAt` was
`2026-09-21T02:03:31Z`. All six file checksums in the archive passed.

Archive SHA-256:
`bf865462b6334ea8b56227b25d15bc9048b61a324e4c59cc4c62dabe8c70e567`.

The existing native test suite passed with `make test`. A separate native probe
confirmed the pack's existing-scoring anchors A10-A13: P/F 390 and scores 1/0
at factors 1/.85; measured PaO2 84 gives P/F 400 and score 0; conversion is
unavailable at SpO2 49/97; low flow gives P/F 177.88 with single-record
suppression and score 2 after adding the second record. These are baseline
observations, not completed v2 criteria. Browser, clean-install, reference-run,
and v2 acceptance verification were not performed during planning.

The baseline environment was Python 3.11.10, NumPy 2.4.4, pandas 3.0.2;
`uv.lock` SHA-256 was
`2780cf965564665584f98f0c2d48715a91e83a909914326c1998ce00d7f2eccd`.

| Confirmed source behavior | Refactor consequence |
|---|---|
| `_simulate_block` generates on the observation grid; `_generate_spo2_true` subtracts episodes from the recursive state. | Create a separate one-minute latent process and sample it afterward. |
| Support is assigned from saturation and does not feed back into physiology. | Prescribed support is primary; saturation-driven assignment is a named stress mode. |
| `_support_fields` places the same FiO2 value in set or measured columns. | Separate source labels, disagreement, and missing evidence. |
| `run_parameter_sweep` consumes seeds in grid order. | Derive stable patient/process stream IDs independent of condition ordering. |
| `collectSweepRequest` constructs the base from defaults. | Use one normalized experiment state and immutable result requests. |
| Thresholds are multiplied by `altitude_factor`; UI help describes conversion adjustment. | Label v2 controls as threshold-rule sensitivity. |
| Scoring floors timestamps to calendar days; acute qualification has no upper bound. | Preserve legacy; add explicit v2 target bounds and timezone/binning rules. |
| Qualifying zeros, missing evidence, and suppressed singletons can all report zero. | Add status and source-linked explanations without erasing the algorithm score. |
| Core and browser support thresholds differ; bootstrap category intervals can collapse. | Freeze entry-point-specific legacy defaults; use one v2 contract and specified intervals. |
| CI runs lint/native tests; Pages stages and deploys without depending on scientific checks. | Add actual browser/parity/build gates and require successful checks for the deployed SHA. |

This inventory is bounded by the supplied findings. M0 confirms its relevant
details and captures regression evidence; it is not an open-ended repository audit.

## Observable end state

1. **Paired engine:** one latent/support identity per patient, stable streams,
   independent observation and documentation, strict versioned requests, and
   reproducible extension from N=200 to N=1,000.
2. **Auditable scorer:** versioned profiles; source IDs, timing and reason codes;
   explicit qualifying counts, suppression, statuses, and signed/evaluable deltas.
3. **Experiment results:** absolute probabilities, paired differences in percentage
   points, MC uncertainty, data availability, 5x5 algorithm transitions and 6x6
   evidence-aware transitions including `U`, with stratum-specific denominators.
4. **Investigation UI:** Experiment, Explain an encounter, and Methods and export
   views sharing one state; a deterministic rule explorer; saved examples before
   runtime readiness; linked traces and honest stale-result/cancellation handling.
5. **Reproducible delivery:** six experiment configurations, all required submodes,
   directory/ZIP bundles, CLI commands, small generated evidence, actual Pyodide
   parity, clean installation, and an acceptance report tied to tested code.

No cloud service, framework replacement, EHR/patient-data ingestion, treatment
feedback model, learned calibration, official scoring-standard compliance claim,
or acquisition of unavailable SQL/clinical data is part of this endpoint.

## Decisions to fix before dependent code

These are proposed resolutions, not changes already authorized or implemented.
When the goal is adopted, record their resolved definitions in `docs/DECISIONS.md`
and serializable fixtures. Preserve the source ticket; identify any approved
deviation in the ledger. Do not repeatedly ask about ordinary file organization.

| Decision | Proposed resolution and acceptance consequence |
|---|---|
| Version boundary | No-profile imports/CLI/requests stay legacy. New interface defaults to v2 with a visible legacy reproduction path. Share numerical primitives; preserve a small legacy generator if exact RNG behavior needs it. |
| Run versus patient identity | Use a versioned `SeedSequence`/PCG64 stream registry. Patient/block/stream IDs and the master seed determine shared draws. Condition IDs hash effective scientific settings excluding labels, N and chunk size; run IDs identify complete executions. Increasing N can change run metadata but cannot change earlier patients or their condition IDs. |
| v2 units and time | SpO2 percent, PaO2 mmHg, time minutes, FiO2 fraction; adapt explicitly to legacy percent inputs. Default scoring timezone UTC and calendar bins. Acute target is `[admit-6h, admit+24h)`; serialize resolved baseline date bounds. Generation/context can extend beyond targets without expanding scoring eligibility. |
| Evidence clock | Default retrospective scoring uses measurement time. Record available time separately. Proposed as-of variant evaluates evidence available by the oxygenation event's recorded time; freeze this cutoff and delay semantics before A15. |
| Missing denominator | A08 removes every observable denominator source in its designated non-room-air fixture. Require no qualifying P/F and an explicit missing-evidence status. A legacy implicit room-air candidate, if retained in diagnostics, must be labeled and cannot count as documented evidence. Fix its exact display/null contract before scoring/UI work. |
| E5 exposure | Main experiment observes acute `[admit, admit+24h)` within the broader target; baseline exposure/sampling varies explicitly. Separate replay control uses the same complete six-hour segment at the same UTC clock times, wholly within a day, with at least two qualifying records and contemporaneous FiO2. Do not equate the replay with independent stationary draws. |
| Named E6 alternatives | Propose suppression disabled; expanded HFNC/NIPPV/IMV/SURG IMV eligibility at every gate; contemporaneous-first lookup and separately as-of availability; measured-PaO2-only conversion; maximum over all eligible baseline dates. Keep admission-anchored binning as a separate temporal ablation. Record exact priority/tie/window rules before fixtures; no generic rule plug-in system is needed. |
| Examples and estimands | Freeze the finite experiment/submode registry, comparator, primary outcome, support strata and seeds before reference runs. Proposed allocation: N=2,000 paired patients per reported stratum for each required stochastic demonstration, with the same IDs across that demonstration's conditions. This conservative reading of the ticket removes the per-stratum/per-experiment ambiguity. Report strata separately with no inferred population weights. |
| Stochastic validation | Before running A04, fix seed set, unclipped trajectory length, tau/sigma cases, elapsed lags, numeric tolerances and their sampling-error rationale in a fixture/protocol. Missing numeric tolerances fail the gate; they cannot be selected after observing failure. |
| Native/browser statistics | Prefer SciPy's validated interval components if the pinned Pyodide runtime supports them. Verify compatibility early; an alternative implementation needs independent numerical validation, not a weaker interval method. `uv.lock` does not pin browser packages. |
| Performance and delivery | Measure a representative preview before setting numeric time/memory/work budgets; freeze those budgets before final testing. Keep cold-start and warm-run measurements separate. Remote CI execution needs an authorized branch/PR delivery; if unavailable, keep G05 pending. Live deployment is not required to build and validate the workbench. |

Version boundaries, identity, units, evidence timing, missingness, baseline
comparisons, rule alternatives and example allocation affect scientific/public
contracts. Resolve any disagreement before dependent work. Internal helper names,
chunk implementation, plot library choices and file splits are engineering choices.

## Implementation sequence

Use additive v2 modules and thin adapters. Avoid a scorer rewrite and avoid
general-purpose experiment frameworks. Proposed filenames below are targets,
not claims that those files exist. Equivalent smaller arrangements are acceptable
if the ledger is updated and dependency direction stays intact.

| Phase | Concrete increment and likely files | Exit evidence |
|---|---|---|
| M0: freeze contracts | Capture legacy inputs/outputs at the starting tree; retain existing `tests/core/`, contract and CLI coverage. Add `tests/experiments/test_legacy_compatibility.py`, strict request/profile definitions in `reporting/experiment_request.py`, and the short decision/variant registry. Pin test protocols and trial the required statistical dependency in Pyodide. | A01 baseline fixtures and hashes; resolved scientific decisions; G01 request-validation fixtures; bounded issue inventory. |
| M1: paired vertical slice | Add v2 latent/event orchestration under `core/` (suggested `paired_simulation.py`, `observation.py`); adapt existing scoring via `core/experiment_scoring.py`; add `reporting/experiment_service.py`. Prove deterministic and small stochastic E1 through the browser contract/worker before broad UI work. | A02-A08, A15-A17; latent/episode/support identity evidence; zero-perturbation and time-boundary fixtures; a small actual-Pyodide comparison. |
| M2: results and explanations | Instrument shared scoring stages safely; add named profile variants and status/selection evidence. Implement paired summaries in `reporting/experiment_results.py`, patient explanation, transition membership and all experiment configurations under `experiments/`. | A09-A14, A18-A21; counts reconcile to patient rows; numeric anchors pass; all E1-E6 mechanisms run natively on small fixtures. |
| M3: investigation interface | Extend `browser_contract.py`, `web/index.html`, `web/assets/js/app.js`, CSS and worker. Replace separate scenario/sweep state in v2. Add experiment selector, typed plots, rule explorer, transition-to-patient links, stale exports, saved example and state recovery. Update staging through its generator. | A22-A24, A27; real browser flows/screenshots at desktop/mobile sizes; keyboard and non-color state checks; workload/cancellation checks. |
| M4: reproducible evidence | Add `reporting/experiment_bundle.py`, `workflows/experiment_cli.py`, script entrypoint, smoke/reference targets, figure-data manifest and evidence inventory. Extend CI/Pages gating and canonical docs. Produce complete reference demonstrations and reproduce bundles in a fresh pinned environment. | A25-A26, A28 and all G gates; full acceptance report, actual Pyodide parity, installed-package checks, reference outputs, runtime evidence and applicable CI results. |

Dependency order is M0 -> M1 -> M2 -> M3 -> M4. M1's first browser slice and M0's
runtime check deliberately find portability problems early. Create the minimal
bundle/request format while building M2 so M3 does not invent an incompatible
export shape; finish reproducibility and command contracts in M4. At each phase,
rerun affected legacy checks. Full integration reruns the complete matrix.

Legacy numerical fixtures and public-call assertions stay intact. UI tests tied
to obsolete v2 pane structure may be replaced with equivalent/new user-flow
assertions, with the reason recorded; this does not permit relaxing scientific
or compatibility assertions. Keep the legacy reproduction workflow tested.

## Finite experiment catalogue

Save actual normalized JSON configurations and a catalogue enumerating every
required submode. There is no requirement for the Cartesian product of unrelated
sensitivity axes. Primary comparisons vary one named mechanism at a time.

| ID / proposed config | Required run set and comparator | Completion evidence |
|---|---|---|
| E1 / `experiments/observation_density.json` | Nested 5/15/30/60-minute schedules, comparator 15. Deterministic episode and stochastic fixed-support cases. | Shared-time identities, score/availability contrasts, one trace illustrating sampling opportunity without presuming effect direction. |
| E2 / `experiments/measurement_error.json` | SD 0/.5/1/2 against 0; separate bias -2/0/+2 against 0; separate rounding modes; explicit fixed-support versus assignment-stress comparison. | Each submode has its own comparator/outcome; held-fixed trajectories match; assignment changes are labeled. |
| E3 / `experiments/documentation.json` | FiO2-bundle missingness 0/.25/.5/1 against 0; separate timing offsets crossing 5/14-minute boundaries; source disagreement/staleness; independent schedules; source-label-only and zero-perturbation controls. | Nested masks, removed-source audit, source/time links, availability changes and exact zero-perturbation reproduction. |
| E4 / `experiments/threshold_correction.json` | Factors 1/.85/.75 against 1; explicit measured- and estimated-PaO2 cases. | Identical PaO2/P/F with changed thresholds; ties and conversion limits remain visible. |
| E5 / `experiments/baseline_opportunity.json` | Baseline 1/6/24 hours at 15/60 minutes; fixed 24-hour acute observation; declared equal-opportunity comparator, proposed 24 hours at 15 minutes. Independent stationary blocks and separate six-hour exact replay control. | Signed/evaluable/legacy delta outputs, missing-baseline rate and exact replay zero; no forced zero for independent paths. |
| E6 / `experiments/rule_contribution.json` | Same events scored with each named suppression/support/lookup-availability/conversion/baseline rule changed against the same base. | Event-level explanation for each rule, effects at every relevant gate, no additive attribution claim. |
| Deterministic explorer | Explicit SpO2 or measured PaO2, FiO2, support and factor; event rubric versus one/two-record encounter mode. | Edges 49/50/96/97, exact P/F cutpoints, explicit unavailable cells, no hidden singleton suppression of event maps. |

Exercise room air, low flow, HFNC and IMV as separate illustrative strata; use
NIPPV/SURG IMV additionally in gating fixtures. Each experiment produces a table
of comparator/variant, actual paired N, primary estimate and MC interval,
availability change, mechanism explanation and limitations. Preselect a stable
patient-selection rule, such as lowest ID in a selected transition cell.

Preview defaults to 200 paired patients in one selected stratum and a small
condition selection. Reference runs use 2,000 paired patients per reported
stratum for each required stochastic demonstration. The catalogue records the
allocation and actual N for every comparison. Deterministic controls need exact
checks rather than artificial Monte Carlo replication.

## Acceptance and evidence contract

The ledger assigns one primary milestone to every A criterion while allowing
later integration reruns. `test_targets` are proposed tests to create;
`existing_coverage` identifies baseline coverage to preserve. Neither field
constitutes a passing test. Replace target names with actual node IDs as built.

Each passing entry must include tested implementation identity, command, exit
status, runtime, and durable test/artifact links. Evidence generated before a
relevant code/configuration change must be refreshed. For an uncommitted delivery,
record the base commit and a digest of the tested implementation diff/source
snapshot, not just `dirty=true`. Empty evidence, skipped tests, missing files or
`blocked` status prevent completion. Owner-approved scope changes must name the
requirement and retain its original wording; they cannot silently turn it green.

| Gate | Required evidence in addition to A01-A28 |
|---|---|
| G01: normalized scientific contracts | Reject unknown keys, non-finite values, invalid fractions/times, fractional integers and contradictions; allow zero variance. Roundtrip normalized requests across Python/CLI/browser. Freeze clocks, rule registry, units, versions and stochastic tolerances. Validate the future aggregate-reference template and metadata without accepting patient-level inputs. |
| G02: complete examples | All catalogue submodes, controls and required strata run; reference N meets the fixed minimum. Real tables, plots, traces and null/contrary findings exist. Every plot links to exact source data/configuration via a figure-data manifest. No unrequested full-factorial expansion is needed. |
| G03: operational browser behavior | Saved labeled output renders before Pyodide; actual progress/completed/attempted counts, pre-allocation workload checks, cancellation, recoverable errors and state preservation work. Freeze and meet measured preview budgets; record cold/warm runtime and memory where measurable. Worker failures remain failed runs, not missing clinical data. |
| G04: reproducible bundles and packaging | All required bundle members and hashes; browser import; directory/ZIP validation; CLI list/run/explain/verify/reproduce; append preserves earlier patients. A clean locked environment and installed wheel/sdist reproduce scientific tables; unsupported versions fail clearly. Detailed all-patient minute traces remain opt-in. |
| G05: integration and delivery checks | Full native/scientific tests, lint/format, build/install smoke, real browser E2E and native/Pyodide numerical parity pass for the tested implementation. CI actually executes these jobs on an authorized branch; Pages depends on successful checks for the same SHA. A missing remote run remains pending, even if local equivalent checks passed. |
| G06: truthful docs and evidence | Canonical docs, artifact inventory and runtime identities match behavior. Preserve the historical synthetic benchmark; label new examples uncalibrated and synthetic. State MC uncertainty, model assumptions and external-validation limits accurately. Staging excludes restricted inputs/publisher PDFs and includes only approved source/example data. |

Important exact anchors include A03's 96/91/96 episode; A10-A13 in the preserved
numerical file; A20's paired difference .20 and MCSE .06030226891555272; A19's
Wilson upper bound .018845326377266575 at 0/200; and A21's nonzero bounds
[-.042874030238438485, .042874030238438485] with no observed discordances.
Use exact integer/status/ID/count comparisons and the existing rounded-value
contracts. For unrounded native/Pyodide floats, use `atol=1e-10, rtol=1e-10`
unless a reviewed, documented numerical exception is necessary. A changed
discrete score never passes by increasing a floating tolerance.

The independent MC unit is the patient. Use Wilson individual-probability
intervals and the ticket's conservative paired discordance interval; MCSE uses
paired differences with `ddof=1`. N<2 has unavailable uncertainty. Zero observed
events or empirical MCSE cannot prove identity. Report failures separately and
leave incomplete runs ineligible as reference examples. All intervals are
pointwise MC uncertainty conditional on the synthetic assumptions.

Required bundle members are `request.json`, `manifest.json`,
`condition_summary.csv`, `paired_contrasts.csv`, `transitions.csv`, `scores.csv`,
`selected_events.csv`, `episodes.csv`, `metric_dictionary.json`, `README.md`,
and `SHA256SUMS`. The checksum file excludes itself. Preserve scientific table
identity independently of archive timestamps and runtime metadata. Include all
specified schema/algorithm/generator/RNG/preset/reference versions, runtime
versions, windows, seed, completed N, warnings and code identity.

## Verification commands and output locations

Existing commands, valid at the inspected commit:

```bash
uv sync --locked --dev
make test
make stage-web
make e2e
make verify
uv run python -m build
uv run resp-sofa-sim --help
```

Select focused commands from the ledger during development. The implemented CLI
uses `--request` for normalized JSON, `--output` for new output paths, and a
positional bundle argument. These operational examples supersede the planning
flag spellings; the scientific and evidence requirements remain unchanged:

```bash
uv run resp-sofa-experiment list
uv run resp-sofa-experiment run --entry E1_density --stratum room_air --replicates 200 --output artifacts/local/density
uv run resp-sofa-experiment explain artifacts/local/density --patient 0 --condition CONDITION_ID
uv run resp-sofa-experiment verify-bundle artifacts/local/density
uv run resp-sofa-experiment reproduce artifacts/local/density --output artifacts/local/density_reproduced
make experiments-smoke
make experiments-reference
```

`experiments-smoke` must enumerate every required experiment/submode and fail on
omissions. `experiments-reference` generates the prespecified full demonstrations
and source figure data in verified bundles. The summarization and rendering
commands in `docs/VALIDATION.md` create the compact reviewed collection.
`CONDITION_ID` is taken from the bundle request or scores table; `explain` writes
the selected trace as JSON to stdout. Full bundles/logs belong in ignored
`artifacts/local/` outputs.
Small reproducible summaries, chosen traces and figure-data manifests belong in
`artifacts/experiments_v2/` with inventory and generation instructions. Put the
final human-readable report in `docs/implementation/sofa_experiment_v2_status.md`;
keep this package's acceptance JSON as the machine-readable ledger.

Use the repository's numerical, Pages/Pyodide, packaging, docs, artifact and
governance skills when their surfaces change. Update canonical documentation
alongside its implementation phase: `docs/ARCHITECTURE.md`, `docs/VALIDATION.md`,
`docs/WEB_APP.md`, `docs/DEPLOY_PAGES.md`, `docs/DECISIONS.md`,
`docs/CLINICAL_SCOPE.md`, `docs/PROVENANCE.md`, `README.md`, and
`artifacts/README.md` as applicable. Do not edit generated staged Python by hand.

## Completion rule

The proposed implementation goal is complete only when M0-M4 have observable
evidence, every A01-A28 and G01-G06 entry passes, and the final report links the
actual output of every required experiment to its configuration and tests.
Report baseline compatibility, paired estimates, availability effects, diagnostic
examples, browser/runtime evidence and remaining external-validation limits.

Do not stop after the planning milestone, one successful demonstration, passing
schemas, native-only checks, or an unverified deployment. A blocked requirement
keeps the full goal incomplete while independent work continues. Clinical
calibration, unavailable original SQL, and actual release/deployment are outside
the scientific implementation endpoint and must not be claimed as accomplished.
