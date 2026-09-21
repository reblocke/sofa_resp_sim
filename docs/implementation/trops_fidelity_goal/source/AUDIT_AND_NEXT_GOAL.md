# Respiratory SOFA refactor: post-implementation audit

Audit date: 2026-09-21.

## Assessment

The refactor is substantive. The paired simulation, separate observation/documentation processes, evidence-aware outcomes, reproducible bundles, and question-led interface are implemented. The next goal should be study-specific validity and useful experiments, not another framework refactor.

The workbench is not yet a verified replica of TROPS's SOFA pipeline. `legacy_py_v1` preserves the earlier Python implementation; that name does not establish equivalence with the historical Oracle SQL.

## Scope and verification

- Audited `sofa_resp_sim` main commit `944a45eb801cc4f96e0a98d80f62af63dd452afe`, whose implementation parent is `7479034585f31bd70e41d0374373e80a4992a054`.
- Inspected current source, the acceptance record, experiment catalogue and interpretation, UI markup, pairing tests, bundle logic, and current GitHub Actions job logs.
- Current CI run 35588942243 succeeded. Its logs show all 314 native/scientific tests and 19 browser tests completing, reference-artifact verification, package build, and fresh-wheel reproduction. These are remote CI executions, not a test-suite rerun by this audit.
- Independently executed the equation and boundary reconstructions in `audit_counterexamples.py`. They are explicitly not execution of the repository's complete numerical pipeline or of Oracle SQL.
- A direct repository clone failed because this runtime could not resolve GitHub. No full local test run or interactive deployed-browser review was completed.
- TROPS current shared tree excludes the grant and SOFA source. Recovered a historical snapshot at `e8b4de0b6e898e94d7ad091796a4aaea1df96231` and read its grant-context documentation and relevant SQL. This does not establish which SQL is deployed today.
- The original grant PDF was located in history but not read. Grant alignment below uses the repository's grant-context summary, not a direct audit of the proposal PDF.
- No GitHub writes, source modifications, repository visibility changes, or publication actions were performed.

## Completed functionality worth retaining

1. A one-minute latent process, physically timed autocorrelation and separate, nonrecursive desaturation episodes.
2. Stable patient/stream identities and caching; tests cover reordered/isolated/added conditions, cohort extension, chunking and single-patient reconstruction.
3. Fixed support versus explicitly labeled assignment stress tests; independent observation and FiO2 documentation streams, missingness, disagreement, delays, and stale values.
4. Observed/suppressed/no-qualifying-data states, signed and evaluable deltas, paired contrasts, Monte Carlo intervals and evidence-aware transitions.
5. Six experiment families and a deterministic rule explorer; immutable result requests, linked explanations and synthetic export/import bundles.
6. Current CI includes browser execution and native/Pyodide comparisons rather than excluding E2E tests.

The repository reports 72 reference configurations (18 demonstrations in four support strata), comprising 68 stochastic configurations at N=2,000 and four deterministic configurations at N=1. Stored results explicitly retain null findings and warn about ceiling effects and uncalibrated assumptions.

## Highest-priority gap: a verified TROPS scoring profile

Source-level comparisons reveal real semantic differences:

| Surface | Historical TROPS | Current v2 default |
|---|---|---|
| Baseline ranking days | Admission-relative integer day index: `TRUNC(relative_days)-1` before the acute window | Calendar dates; optional admission binning is another experimental choice |
| Baseline eligibility endpoint | Actual event time must be no later than midnight seven days before admission | Eligibility checks the bin start, potentially admitting later records that day |
| Acute endpoint | Includes the record exactly +24 h after admission | Half-open window excludes +24 h |
| Missing baseline denominator | Can infer room air from estimated PaO2 under the quarter-block rule | Missing denominator produces no P/F |
| FiO2 lookup partition | Includes constituent encounter admission (`ce_admit_dts`) and invasive status | Per-patient event set partitioned by invasive status |
| Support classification | Derived episode logic, including OSA/surgical ventilation/tracheostomy distinctions | Supplied support labels/segments; assignment stress test is not this EHR classifier |

Some differences are deliberate v2 design choices, not regressions. They must not be silently called corrections or changed across every profile. Implement an explicit source-pinned TROPS profile and keep experimental variants separate.

### Synthetic counterexample

Admission: 2026-01-31 at 12:00 UTC. Qualifying baseline records on 2026-01-20: score 2 at 08:00 and score 0 at 18:00.

Calendar-date ranking selects score 2, the day's maximum. The recovered SQL assigns day indices -12 and -11, so its most recent day selects score 0. Both computations are internally consistent but answer different questions. With an acute score of 2, the corresponding respiratory deltas would be 0 versus 2.

A second boundary example uses admission 2026-01-31 at 12:00 and a baseline record on January 24 at 12:00. The historical SQL excludes it because its cutoff is January 24 at 00:00. Calendar-bin eligibility includes it.

## The TROPS-specific outcome is a cohort criterion, not just respiratory score

The recovered delta SQL sums **positive component-level changes**. The following script sets `DELTA_SOFA_IND` when that total is at least 2. This is not equivalent to taking the positive part of the difference between total acute and baseline SOFA scores.

Let R be the respiratory nonnegative component delta and C be the sum of the other nonnegative component deltas. The SOFA cohort criterion is `C + R >= 2`.

- C=0: R must reach 2.
- C=1: R must reach 1.
- C>=2: the criterion is already satisfied without respiratory contribution.

Add this as a clearly labeled **SOFA eligibility criterion** sensitivity output. It is not a stand-alone sepsis diagnosis, not all TROPS eligibility criteria, and not a clinical gold standard. The existing simulator need not grow five new physiological organ models: condition on supplied C, then combine with approved aggregate counts or private study data downstream.

## Experiment and presentation changes still needed

### Match the outcome to the mechanism

- E3 timing/partial-missingness currently leads with the probability of an encounter having no qualifying data. Dense records can keep this at zero despite substantial record-level exclusion or wrong FiO2 pairing. Lead with retained eligible fraction/count, denominator source-age/error, and score/delta transitions as appropriate.
- E6 uses acute `score_ge2` as its default primary outcome even for a baseline-selection ablation. A baseline-only rule cannot change the acute score. Use baseline score or delta for those contrasts, or split the rule catalogue by target.
- Several supported strata are at the ceiling for score >=2. Preserve these null demonstrations, but add a prespecified informative sensitivity grid with near-normal stable trajectories and threshold neighborhoods. Do not retune seeds until a positive result appears.
- Expose evaluable deltas and missing-baseline outcomes in the primary-outcome selector. They exist in the result engine but are absent from the current HTML selector.

### Define baseline opportunity precisely

A 24-hour baseline block beginning at the default 12:37 admission clock crosses two calendar dates. Under calendar-latest-day selection, only the latest date can determine the baseline score. Of the 96 scheduled 15-minute observations, 50 fall on that latest date. Actual qualifying counts also depend on documentation and conversion.

Thus '24h baseline opportunity' is not the same as 24 hours eligible to determine the selected baseline score. Separate observation duration from selected-day alignment. Use matched ending times or deliberately controlled scoring-day windows and display actual selected-day opportunities.

### Clarify conditional denominators

The engine's evaluable-delta condition summaries use each condition's eligible patients, while paired contrasts use the intersection of eligible patients. This is a legitimate paired estimand but its difference need not equal the two displayed marginal estimates. Return common-pair comparator and variant probabilities and their denominator alongside that contrast; retain per-condition marginals as separate quantities.

## Suggested next Codex goal

**Connect the existing workbench to a versioned TROPS scoring contract and cohort-criterion sensitivity analysis, without redesigning its architecture.**

### Deliverable 1: exact source crosswalk and parity fixtures

- Confirm the current study-approved SQL/specification locally; record its version and hashes. Treat the recovered historical version as evidence, not presumed current truth.
- Map conversion, FiO2 source hierarchy, lookbacks, transfer partitions, support classification inputs, acute boundaries, baseline boundaries/ranking, suppression and component delta.
- Add a named TROPS profile, or an adapter to validated study outputs, without altering existing legacy/v2 behavior.
- Construct synthetic tests for the two baseline counterexamples, +24 h, denominator-free baseline quarter, transfer-separated FiO2, OSA versus NIPPV, HFNC, surgical IMV, repeated observations and measured PaO2 precedence.
- Run the same fixtures through the study-approved implementation when available. If Oracle execution is unavailable, label the profile 'source-mapped, not execution-validated' and retain that limitation; do not silently self-certify.

### Deliverable 2: cohort-criterion outputs

- Add C=0, C=1 and C>=2 strata and paired transitions of the SOFA eligibility flag.
- Report retained, newly eligible, no longer eligible and unchanged-unscorable cases.
- Quantify changing evidence availability separately from changes among evaluable pairs.
- Preserve componentwise truncation and the missing-baseline convention of the chosen study profile.
- Keep infection, troponin, and other inclusion criteria fixed/outside scope unless the study protocol explicitly supplies them.

### Deliverable 3: decision-focused demonstrations

- Correct E3/E6 endpoint selection and baseline exposure alignment.
- Include stable/no-deterioration cases and declared boundary stress tests; retain old null reference results.
- Present three outputs first: probability of crossing the SOFA eligibility criterion, evidence/score transition matrix, and one linked mechanistic trace.
- Add common-pair marginal estimates for conditional contrasts.
- Produce a compact findings table with exact requests, source/profile hashes, denominators, Monte Carlo uncertainty and limitations. Use the existing bundle infrastructure.

### Boundaries

The public simulator remains synthetic and reusable. TROPS's restricted adapter, raw records, identifying traces, original grant and private SQL stay within approved study storage. Follow the current TROPS sharing manifest; do not restore excluded materials to its collaborator-facing tree without authorization. Clinical calibration and claims about treatment effects remain separate work.

## Source register

All sources below were read through the GitHub connector. Historical source comments were not treated as current patient-count estimates.

- Current simulator: https://github.com/reblocke/sofa_resp_sim/tree/944a45eb801cc4f96e0a98d80f62af63dd452afe
- Current CI: https://github.com/reblocke/sofa_resp_sim/actions/runs/35588942243
- Completion record: `docs/implementation/sofa_experiment_v2_status.md` and `docs/implementation/paired_experiment_goal/COMPLETION_RECEIPT.json`
- Core: `core/paired_simulation.py`, `core/observation.py`, `core/experiment_config.py`, `core/experiment_scoring.py`
- Reporting: `reporting/experiment_catalogue.py`, `reporting/experiment_service.py`, `reporting/experiment_results.py`, `reporting/experiment_bundle.py`
- UI: `web/index.html`; tests: `tests/experiments/test_pairing.py`
- Synthetic interpretation: `artifacts/experiments_v2/INTERPRETATION.md`
- TROPS current sharing policy: https://github.com/reblocke/TROPS/blob/cbf3fafc87ec44313f29555fa565b28f66c75176/SHARING_MANIFEST.md
- Historical TROPS snapshot: https://github.com/reblocke/TROPS/tree/e8b4de0b6e898e94d7ad091796a4aaea1df96231
- Historical grant-context summary: `AGENTS.md`, opening project-overview section
- Historical SQL: `code/SOFA calculation/SOFA Respiratory Detail.sql`, `Trops Measures - SOFA.sql`, `Trops Measures - Delta SOFA.sql`, `delta SOFA final.sql`

## Included independent checks

Run `python audit_counterexamples.py` in an environment with NumPy, pandas and SciPy. This generates `audit_counterexamples.json` using synthetic inputs and explicitly reconstructed source expressions. The audit execution used NumPy 2.3.5, pandas 2.2.3 and SciPy 1.17.0. It does not install or execute the repository and is not a replacement for its locked CI environment.
