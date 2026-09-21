# Goal: paired respiratory SOFA experiments with auditable scoring and a question-led interface

Repository: `reblocke/sofa_resp_sim`  
Ticket version: 1.0, 2026-09-20  
Verified starting commit: `76ac9c3b670543380c19957450c215581b508f6f`  
Mode: implement, verify, and demonstrate. A plan alone is not completion.

## 1. Outcome and definition of success

Turn the existing simulator into a small experimental workbench that answers:

> How much does the implemented respiratory SOFA score change when measurement, documentation, support assignment, or scoring rules change, while the specified underlying oxygenation trajectory remains fixed?

A researcher must be able to select a named experiment, identify its comparator, run paired conditions on the same synthetic patients, quantify score and data-availability changes, explain an individual change from its contributing records, and export everything needed to reproduce the result.

Preserve the shared Python numerical engine and static GitHub Pages/Pyodide delivery. Extend their scientific contracts; do not replace the application framework or build an EHR integration.

Completion requires working experiments and inspectable numerical artifacts, not just new controls, documentation, passing schema tests, or a green deployment. Null findings and opposite-direction findings are valid. Do not tune seeds or assumptions to make the proposed problems appear.

## 2. Starting context and evidence boundaries

Read the repository's `AGENTS.md` and task-relevant skills. Start with:

- `src/sofa_resp_sim/core/{resp_simulation,resp_scoring,resp_utils}.py`
- `src/sofa_resp_sim/reporting/{view_model,app_services,presets,reference}.py`
- `src/sofa_resp_sim/browser_contract.py`, `src/sofa_resp_sim/workflows/cli.py`
- `web/index.html`, `web/assets/js/app.js`, `web/pyodide_worker.js`
- `scripts/stage_web_python.py`, `tests/core/`, `tests/contracts/`, `tests/e2e/`
- `docs/{DECISIONS,VALIDATION,PROVENANCE,CLINICAL_SCOPE}.md`, `artifacts/README.md`.

The audit found the following at the starting commit. Verify against the checkout; mark each finding confirmed, already fixed, or superseded with evidence. Do not repeat an unbounded repository audit.

| Finding | Required response |
|---|---|
| Latent saturation is generated on the observation grid; autocorrelation, episode initiation, and repeated desaturation subtraction therefore change with charting frequency. | Separate latent generation from sampling; define process parameters in physical time. |
| Noisy saturation assigns support and FiO2, but support does not affect subsequent saturation. | Use fixed support for primary measurement/documentation experiments; label assignment-only experiments as stress tests, not treatment effects. |
| `fio2_meas_prob` selects which column receives the same value rather than creating actual missingness. | Separate source-label choice, source disagreement, and evidence availability. |
| `altitude_factor` scales P/F thresholds, although UI help describes a conversion adjustment. | Correct the label and separate threshold-rule sensitivity from physiology at elevation. |
| The saved reference is a 200-replicate synthetic run, not empirical validation. | Preserve it as a historical synthetic benchmark; use a paired comparator by default. |
| Zero can mean a qualifying score, no qualifying data, or single-record suppression. | Preserve algorithm outputs but expose evidence status and denominators. |
| Sweep seeds depend on grid iteration order; the browser sweep starts from defaults rather than the edited scenario. | Introduce stable patient/stream identities and one experiment state. |
| Calendar-day code and admission-anchored prose conflict; generation and scoring windows differ. | Preserve legacy behavior and introduce explicit, tested window semantics. |
| Core support defaults and browser-derived thresholds differ. | Preserve legacy entry-point behavior; use one authoritative configuration for v2. |
| Existing bootstrap intervals describe finite-replicate uncertainty and can collapse at empty categories. | Use boundary-aware Monte Carlo intervals and paired contrasts. |

Source behavior is not proof of clinical validity or SQL equivalence. The original SQL and empirical calibration data have not been established by this ticket. Their absence must not block the synthetic workbench, and their existence must not be invented.

## 3. Compatibility, authority, and scope

### Required compatibility

Name the current behavior `legacy_py_v1`. Preserve existing public imports, old CLI invocation syntax, old request semantics, old golden fixtures, and historical artifacts. Keep the original fixed-seed simulation path available for reproducibility. Do not silently reinterpret its `spo2_sd`, `ar1`, desaturation probability, support thresholds, or time endpoints.

Add separately versioned v2 experiment requests and a `bounded_analysis_v2` scoring profile. The latter retains the legacy conversion, source priority, support caps, single-P/F rule, and baseline selection unless a named variant explicitly changes them; it introduces explicit acute target boundaries and evidence-status reporting. Default to calendar-day bins with a declared scoring timezone, not an undocumented change to admission anchoring. Name this an experimental implementation profile, not a corrected clinical standard.

Existing no-profile entry points remain legacy. The redesigned interface defaults to v2 and provides a clearly labeled legacy reproduction option. Avoid copying the scorer into independent competing engines: share computations where safe, with version-specific orchestration and differential tests. A small preserved legacy generator is acceptable when necessary for exact historical RNG behavior.

### Authorized decisions

This ticket authorizes the v2 generation model, named variants, schemas, outputs, UI changes, and tests below. Internal module boundaries and helper names are engineering choices. Use existing packages and repository conventions. SciPy may be added for the interval calculations after verifying a compatible pinned native/Pyodide configuration; avoid an additional large statistical stack.

Do not change legacy scientific semantics, assert official SOFA-version compliance, introduce empirical calibration values without sources, weaken numerical tests, publish clinical recommendations, or change repository visibility/history. New clinical models, learned calibration, unrestricted patient-data upload, cloud backends, and treatment-response physiology are out of scope. Record unrelated improvements separately.

When an ambiguity affects only a legacy interpretation, preserve it and label a research alternative. Block only the affected requirement when genuinely unresolved; continue independent milestones. Never claim an unrun test, unavailable SQL comparison, or external validation succeeded.

## 4. Scientific pipeline and configuration

Implement a typed, versioned pipeline:

`latent patient -> fixed support/FiO2 -> observation and documentation -> scoring profile -> paired estimates -> explanation/export`

Use one normalized experiment configuration across Python, CLI, and browser. Required groups are: simulation version, RNG scheme, patient generator, generation horizon, observation process, documentation process, support mode, scoring profile, comparator, condition overrides, outcomes, and run size. Store units in field names or schema metadata. Reject unknown scientific keys, non-finite inputs, fractional integer fields, contradictory settings, and invalid units. Permit zero variability for deterministic controls.

Use percent units for saturation, mmHg for PaO2, minutes for relative time, and FiO2 fractions in v2 configuration. Convert explicitly at the legacy scorer boundary, which uses percent FiO2. Never infer units from magnitude. Distinguish generation horizon, scoring target interval, and contextual records available for lookbacks.

### 4.1 Latent process, independent of charting

Required v2 stochastic baseline: a fixed one-minute internal grid and a stationary Gaussian AR(1) background parameterized by mean `mu`, pre-clipping marginal SD `sigma`, and correlation time `tau_minutes`:

```
phi = exp(-1 / tau_minutes)
x[0] = mu + sigma * z[0]
x[t] = mu + phi * (x[t-1] - mu) + sigma * sqrt(1 - phi**2) * z[t]
```

The `z` values are standard-normal draws. Use a documented independent-noise mode for zero correlation; reject negative correlation times. `sigma=0` gives a constant background. These are transparent synthetic assumptions, not empirically fitted physiology. Expose achieved clipped mean/SD and clipping fractions in diagnostics; do not describe the pre-clipping SD as the achieved saturation SD.

Generate desaturations separately from the AR state. Use an idle-state initiation rate per hour, with one-minute start probability `1-exp(-rate_per_hour/60)`. While an episode is active, do not initiate another. Apply a rectangular decrement of `depth_pct_points` for `duration_minutes`, with half-open episode intervals. Then return to the unperturbed background. Do not recursively subtract depth from the already depressed AR state. Distinguish the initiation hazard while idle from the achieved episode frequency. Emit episode start/end/depth records. Deterministic prescribed trajectories and prescribed episodes must also be supported.

Sampling occurs after generation. The primary frequency experiment samples nested schedules anchored to the same origin, such as every 5, 15, 30, or 60 minutes. Values, episodes, and support at shared times must be identical. Do not regenerate patients or round before sampling. Keep the internal grid fixed in the user-facing v2 experiments; changing it is a separately versioned numerical sensitivity study.

### 4.2 Randomness and pairing

Use explicit NumPy `SeedSequence` inputs and a named bit generator, with stable non-negative identifiers for patient, process/block, stream, and master seed. Separate at least physiology, desaturation, saturation measurement noise, support assignment, FiO2 values, SpO2 missingness, FiO2 missingness, timestamp perturbation, and source-label selection.

Do not seed shared physiology from condition order, a condition label, requested replicate count, worker index, Python `hash()`, or the full Git commit. Record the RNG scheme version separately from the commit. Shared observation times reuse shared noise draws; missingness probabilities use nested masks from shared uniforms. Add new random mechanisms through new stream IDs rather than consuming extra draws from existing streams.

The same patients must give identical results when conditions are reordered, a condition is run alone, unrelated conditions are added, computation is chunked, or N is extended. Extending 200 patients to 1,000 must leave patients 0-199 unchanged. Canonical effective configuration hashes identify conditions; display labels do not determine simulations. Include latent/cohort provenance sufficient to prove pairing, not merely a repeated seed column.

## 5. Observation, documentation, and support

### Primary support mode

Use a constant or prescribed piecewise support/FiO2 trajectory, generated once per patient and shared by conditions. Changing charting interval, saturation noise, missingness, or a scoring threshold must not alter it. Low-flow oxygen and its inferred FiO2 must remain identifiable as a proxy rather than known delivered FiO2.

Retain an explicit `assignment_stress_test` mode in which support labels follow latent or observed saturation. Its configuration contains all four thresholds, not a deceptively independent room-air control. Display which thresholds move together. This mode must never be labeled a treatment-effect or oxygen-response simulation. A physiological treatment feedback model is deferred.

### Required measurement and documentation mechanisms

- Saturation observation: `observed = clip(latent + bias + noise_sd*z, 0, 100)`, followed by selected Oracle-compatible integer, one-decimal, or no rounding. Bias is in percentage points. Default bias is zero.
- Independent SpO2 and FiO2 documentation schedules, each with explicit phase/interval. Missingness affects documented observations, never latent values.
- Separate missingness for saturation and the FiO2 evidence bundle. Bundle removal means removing all specified observable denominator sources, including flow and room-air evidence where applicable. Retaining a fallback must be explicit. Unknown support or FiO2 must not silently become room air in v2 data generation.
- Separate source-label selection, simultaneous set/measured FiO2 disagreement, and controlled stale values. A provenance-only change with identical values should be numerically inert in its designated control.
- Each event retains a stable ID, measurement time, recorded/available time, source type, value, and units. Specify whether scoring uses measurement or recorded timestamps. Model a charting delay separately from incorrectly timestamping a physiological event.
- Retrospective versus as-of evidence availability is explicit. A prospective/as-of variant cannot use future available information. Keep the legacy forward lookup available and labeled as retrospective.

Keep the event adapter lossless. Joining separate streams must not duplicate oxygenation measurements or multiply qualifying P/F counts. Pure support/FiO2 context events do not become new oxygenation observations. Scoring may only see documented information allowed by its profile; latent fields exist for simulation diagnostics, not hidden imputation.

Support explicit measured-PaO2 fixtures to test measured-first priority and conversion variants. Do not create a purported independent ABG gold standard by inverting the very saturation curve under evaluation.

## 6. Scoring outputs and temporal semantics

Retain algorithmic scores and add the following meanings for acute and baseline periods:

| Field/concept | Required meaning |
|---|---|
| `algorithm_score` | The selected profile's reported integer, including legacy zero-default behavior. |
| `pre_suppression_score` | Maximum qualifying score after support caps but before single-record suppression; null when no qualifying record. |
| `score_status` | Exactly one of `observed_scored`, `suppressed_only`, `no_qualifying_data`. A qualifying zero is `observed_scored`, not a no-data state. |
| Qualifying/exclusion counts | Counts with explicit denominators and reason codes; baseline counts honor the actual baseline eligibility window. |
| Selected event IDs | All ties and a deterministic displayed winner for the encounter result, with the existing tie-break order preserved in legacy mode. |
| `delta_legacy` | Nonnegative acute-minus-baseline algorithm score, preserving old zero defaults. |
| `delta_signed` | Signed acute-minus-baseline algorithm difference. |
| `delta_evaluable` | Signed difference only when both periods have qualifying evidence; otherwise null. Retain suppression status separately. |

Expose a nonnegative evaluable delta when requested, without replacing the signed value. Missing baseline information is not a normal baseline. An all-missing encounter must remain inspectable even if its algorithm score is zero.

Each scored oxygenation event must retain PaO2 source, FiO2 source event ID, chosen value, source age/time direction, inference method, P/F, threshold factor, raw rubric, each cap/suppression stage, target-period eligibility, and all exclusion reasons. Mechanism flags can overlap; any displayed funnel must use a declared mutually exclusive first-exclusion hierarchy. Reasons and source links must be computed by the scorer, not guessed from the final score.

For `bounded_analysis_v2`, default acute membership is `[admit-6h, admit+24h)`. Context outside that interval can supply evidence only when the chosen lookup/availability rules allow it, but cannot itself contribute an acute score. Preserve the existing baseline date-selection logic in the base profile and serialize its resolved boundaries. An admission-anchored binning variant is a named ablation. Use explicit timezone handling; reject mixed/invalid times and test non-midnight admission and daylight-saving transitions. Relative elapsed-minute windows and local calendar-day bins must not be conflated.

Keep legacy handling of HFNC and SURG IMV visible, including differences between intermediate and final support gates. A support-eligibility ablation must alter all relevant gating stages consistently. Do not silently call a broader support definition the correct SOFA standard.

## 7. Required experiment catalogue and bounded extensions

All numerical values below are illustrative experiment settings, not clinical calibration. Save actual configurations, not just prose presets. Every experiment declares its aim, generated data, held-fixed quantities, modified mechanism, comparator, outcomes, limitations, and any structural-zero expectations.

| ID | Experiment | Required comparison and controls |
|---|---|---|
| E1 | Observation density | Same latent/noise/support paths; 5, 15, 30, 60-minute schedules with 15-minute comparator. Include a deterministic sampling example and a stochastic fixed-support example. |
| E2 | Measurement error | Same observation/support schedule; noise SD 0, 0.5, 1, 2 with zero-noise comparator. Separate bias -2, 0, +2 and rounding analyses, not one unlabeled combined effect. Include a separately labeled fixed-support versus assignment-stress comparison. |
| E3 | Documentation | Same physiology/support; FiO2 bundle missingness 0, 0.25, 0.5, 1, plus separate timestamp offsets crossing the 5/14-minute boundaries and a source-disagreement/staleness example. Zero-perturbation comparator must reproduce the input exactly. |
| E4 | Threshold correction | Rescore identical records at factors 1.0, 0.85, 0.75, with 1.0 comparator. PaO2 and P/F cannot change. Demonstrate this with explicit measured-PaO2 and estimated-PaO2 cases. Do not infer an altitude in metres or a physiological altitude effect. |
| E5 | Baseline opportunity | Stationary/no-deterioration generator shared across conditions; baseline exposure 1, 6, 24 hours and baseline sampling 15 or 60 minutes, with a fixed 24-hour acute observation period and equal-opportunity comparator. Include both independent stationary baseline/acute realizations and an exact replay negative control. |
| E6 | Rule contribution | Score the same documented events with one named rule changed: single-record suppression, support eligibility, FiO2 lookup priority/availability, SpO2-conversion eligibility or measured-only mode, and baseline-selection rule. Show each contrast against the same declared base; do not claim additive attribution across interacting rules. |

For E5, independent stationary realizations can have different extrema even without modeled deterioration. Equal opportunity does not guarantee zero individual deltas, especially after truncation at zero. Only the exact replay control promises zero for equivalent scoring conditions. Implement that control using the same complete six-hour segment repeated at the same UTC time of day, wholly within one calendar day, with at least two qualifying observations, contemporaneous FiO2, identical caps, and no missingness. This avoids accidentally testing unequal baseline/acute eligibility or aggregation. State this in the result caption.

Ship a small stratified collection of illustrative room-air, low-flow, HFNC, and IMV records so the experiments exercise different gates. Show stratum-specific results. Do not produce a population-weighted total without explicit user-supplied weights and provenance. Fully specified optional mixtures may remain a later extension.

### Required deterministic rule explorer

Add a deterministic view under the experiment selector. Evaluate specified SpO2 or measured-PaO2 values, FiO2, support label, and threshold factor without Monte Carlo sampling. Show estimated P/F, rubric, support-adjusted score, and conversion-unavailable regions separately.

Distinguish event-level rules from encounter-level suppression. To show an encounter result, explicitly select one record or two identical records 15 minutes apart. Never accidentally suppress every heatmap cell by passing one unsupported record. Include conversion edges at 49/50 and 96/97 and exact P/F cutpoints. Unavailable conversion is a separate visual state, not a score-zero color.

### Calibration boundary

Provide an aggregate-reference CSV/metadata template and validator for future local calibration: source, extraction date, cohort definition, scoring profile, denominators, units, and access class. Accept valid aggregate counts without treating distributional agreement as individual-level validation. Do not require acquisition of unavailable patient data or SQL to close the synthetic implementation. Label the released model `uncalibrated illustrative simulation` until an independent evidence-backed calibration is completed.

## 8. Estimands, denominators, and Monte Carlo uncertainty

The independent Monte Carlo unit is the synthetic patient, not a timestamp. A run uses the same N patient IDs in every paired condition. Failures are separate from clinical missingness. Do not turn computation errors into zero scores or silently drop failed pairs; a failed run remains incomplete and cannot become a published reference example.

Required outputs per condition and comparison:

- P(algorithm score >=1), >=2, >=3, and =4; category probabilities 0-4; P(no qualifying data); P(suppressed_only); mean qualifying P/F count.
- Upward/downward/unchanged algorithm reclassification on all executed pairs, explicitly noting the algorithm's zero-default convention.
- Evidence-evaluable reclassification restricted to pairs with qualifying evidence in both conditions, with the restricted denominator displayed.
- A 5x5 algorithm-score transition table and a default 6x6 evidence-aware table with an additional `U` state for no qualifying information. Suppression remains score zero with its own status display. Include status-transition counts.
- E5: P(delta_legacy >=1 and >=2), signed delta distribution, corresponding evaluable quantities, and missing-baseline proportion. Never label these as sepsis incidence.

For a binary outcome, use `d_i = outcome_variant_i - outcome_comparator_i`. Report the mean paired difference, percentage-point difference, and `MCSE = sd(d, ddof=1)/sqrt(N)`. Do not compute its SE as though the conditions were independent. For N<2, uncertainty is unavailable with an explicit reason.

Use Wilson intervals for individual probabilities through a validated implementation. For binary paired differences, provide conservative boundary-safe pointwise 95% bounds by estimating the two discordant probabilities `p_plus=P(d=1)` and `p_minus=P(d=-1)`. Obtain exact binomial intervals for each at confidence `1-alpha/2`, then return `[L_plus-U_minus, U_plus-L_minus]` intersected with [-1,1]. At alpha=.05 this uses two 97.5% component intervals. This is a deliberate conservative construction via the union bound, not an independent-arm interval. Test it against known discordance counts.

A zero empirical MCSE or zero observed events does not establish a structural zero. Keep nonzero upper bounds unless identity is proven by construction and explicitly flagged as structural. Do not infer structural identity merely from matching observed scores. For nonbinary paired mean/count differences, report empirical MCSE; a normal-approximation interval may be secondary with its method labeled and without unsupported exact coverage claims.

Default runs use fixed, prespecified N. Preview: 200 paired patients and a small comparator/variant selection. Reproducible examples: at least 2,000 patients per required stochastic demonstration, with achieved uncertainty shown. Add append-runs functionality that preserves earlier patients. A precision-planning option may choose N before execution from bounded-outcome variance (Bernoulli <=1/4; paired binary difference <=1); do not introduce repeated fixed-sample CI peeking with an asserted sequential coverage guarantee.

All intervals are pointwise Monte Carlo intervals conditional on the chosen model, not clinical CIs, parameter-uncertainty intervals, or simultaneous bands over all grid cells. Keep assumption sensitivity separate. No significance stars, seed selection, or universal claim that denser observation must increase scores.

## 9. Presentation contract

Replace the separate Scenario/Sweep configuration states with one experiment state and three views: **Experiment**, **Explain an encounter**, **Methods and export**. A sweep extends the current experiment. Reset/preset/import modifies this one state. Every result carries an immutable normalized request; editing controls marks old results stale, including their download buttons or labels, until rerun. Never label old results with new inputs.

On the default desktop view, show the question, comparator, changed mechanism, short held-fixed summary, primary outcome with paired difference, and first useful plot without scrolling through the complete control form. Show only relevant controls; collapse advanced generation, seed, and numerical settings. Default to a small preview, not a 27,000-encounter grid. State workload before execution using both scoring evaluations and latent/event volume.

The Experiment view leads with absolute probabilities, paired percentage-point differences, data availability, and the prespecified outcome. Show a line/dot plot with pointwise MC intervals for one varying numeric factor. For two factors, use a real matrix with labeled axes and a shared color scale across comparable panels; missing cells and zero values differ. Use signed difference scales centered at zero. Keep raw table downloads available.

The paired transition matrix must expose counts and denominators and link a cell to its contributing synthetic patients. Do not rank scenarios by the largest noisy result. The saved 200-replicate reference becomes **Saved synthetic benchmark**, with its N and source configuration where known. Put Jensen-Shannon/L1 distances in optional methods diagnostics, never label them accuracy.

The encounter view shows synchronized time-aligned plots for latent/observed saturation, support/FiO2, and scoring stages. Use separate panels/axes with stated units rather than mixing quantities on a misleading scale. Show excluded points, selection/ties, source timing, caps, and suppression. Return explanations from Python reason codes. Select an example by stable patient ID or a declared rule (e.g. lowest ID in a selected transition cell), not an unlabeled dramatic example. Loading one trace must not rerun the entire cohort.

Format all values from metric metadata: probability as percent, differences as percentage points, counts as counts even below one, and P/F in mmHg. Show source labels and units in tooltips and readable table headings. Chart/export values must agree. Ship keyboard-accessible controls, non-color-only states, and a readable mobile layout.

Show a versioned precomputed example before Pyodide is ready, labeled as saved output, never as a new run. Keep cancellation, runtime-failure diagnostics, state recovery, and completed/attempted work counts. Browser progress must be real, not a cosmetic timer.

## 10. Data and reproducibility contract

Keep long-form canonical data, keyed by `(experiment_run_id, patient_id, condition_id)` for scores and by event ID for traces. Serialize the fully resolved comparator and condition overrides, not just a preset label. Include algorithm, generator, schema, RNG, preset, and reference versions; Git commit; dirty-tree flag; dependency/runtime versions; seed; target and generation windows; interval methods; completed N; and all warnings.

Export one bundle containing:

```
request.json              # complete, normalized, reloadable experiment
manifest.json             # versions, environment, hashes, status, exact run identity
condition_summary.csv     # counts, denominators, probabilities, intervals
paired_contrasts.csv       # direction, target, paired N, estimate, MCSE, interval method
transitions.csv           # comparator/variant states, counts, denominator
scores.csv                # paired patient-level synthetic summaries
selected_events.csv       # selected diagnostic traces, including IDs and source timing
episodes.csv              # selected latent episode records
metric_dictionary.json    # field meanings, units, denominators
README.md                 # question, assumptions, limitations, exact reproduction command
SHA256SUMS                # content hashes; exclude this file from its own hash list
```

Additional full traces may be opt-in. Do not retain every patient's minute-level DataFrame solely to support one explanation. Permit regeneration of one trace from the configuration and patient/stream identity; verify it matches that patient's saved score.

Bundles import in the browser and rerun through the CLI. Unknown versions fail clearly rather than silently migrating assumptions. Separate scientific-data identity from timestamps/durations/environment metadata: test exact scientific reproducibility in the same locked environment, not byte identity of ZIP timestamps. Across native and Pyodide runtimes, require exact IDs/categories/counts and predeclared floating tolerances; investigate any changed discrete score rather than concealing it inside a float tolerance.

Keep synthetic data labeled as synthetic. No PHI, restricted inputs, or publisher PDFs in Git or staged assets. The aggregate-reference adapter is not a patient-data ingestion feature.

## 11. Acceptance tests that must exist and pass

Names below are outcome contracts; internal test filenames are flexible. Preserve existing tests and add direct numerical/mechanism tests, not only payload-shape assertions.

| ID | Given / when | Required evidence |
|---|---|---|
| A01 | Existing entry points and fixed legacy fixtures run. | Historical scores/intermediates and seeded legacy outputs are preserved in the pinned environment; intentional nonlegacy differences are separately versioned. |
| A02 | E1 samples one cohort at 5/15/30/60 minutes. | Latent/support/episode identities match; shared sampled times have identical underlying and noise values. |
| A03 | A constant 96% background has one 5-point episode lasting 30 minutes. | Latent values are 91% during that interval and 96% outside it at every observation schedule; no accumulated decrement. |
| A04 | Long unclipped AR background, no desaturations. | Empirical marginal SD and correlation at fixed elapsed lags agree with declared values within prespecified stochastic tolerances, not tolerances tuned after failure. |
| A05 | Conditions reordered/isolated/extended; chunks changed; N increased. | Same patient-condition rows remain identical; first 200 patients do not change in a 1,000-patient run. |
| A06 | Noise, missingness, or threshold factor changes in fixed-support mode. | Latent oxygenation and support/FiO2 are unchanged. A separate stress mode explicitly permits assignment changes. |
| A07 | Identical FiO2 moves between set/measured columns with no conflicts. | Provenance changes but all numerical scores and P/F values remain identical. |
| A08 | All FiO2 evidence is removed in a designated non-room-air fixture. | No hidden latent value, surviving flow/room-air fallback, or adapter artifact supplies it; eligibility follows the documented profile. |
| A09 | All oxygenation evidence is missing; compare with observed normal data and a suppressed abnormal singleton. | Three distinct statuses; old algorithm zeros preserved; tables reconcile without calling no-data records normal. |
| A10 | Two records, SpO2=96, room air, no measured PaO2, at t=0 and +15min. | Conversion PaO2=81.9 and P/F=390.00 unchanged across factors; algorithm score 1 at factor 1.0 and 0 at .85. |
| A11 | Same two-record fixture has measured PaO2=84 at both times. | Measured-first P/F=400.00 and score 0 at factor 1.0; exact threshold ties use the implemented strict inequalities. |
| A12 | SpO2 49,50,96,97 without measured PaO2. | Conversion unavailable at 49/97, available at 50/96. UI represents unavailable explicitly; no high-saturation PaO2 is fabricated. |
| A13 | One low-flow record: SpO2=90, flow=4 L/min, factor=1.0. Then add an identical record 15min later. | Inferred FiO2=33%, P/F=177.88, presuppression score 2; legacy singleton reported 0 with suppression, two records reported 2. |
| A14 | HFNC, NIPPV, IMV, SURG IMV fixtures exercise both support gates. | Legacy behavior retained. Named support ablation changes all relevant gates, with an event-level explanation. |
| A15 | FiO2 context at exact and just-outside 1/5/14-minute and 24-hour boundaries; conflicting current/previous values. | Source event IDs and chosen priority match the versioned rule; no future unavailable evidence in as-of mode. |
| A16 | Admit at 12:37, target endpoints, midnight and DST boundaries. | v2 acute membership is explicit and bounded; calendar versus admission bins demonstrably differ when expected; legacy fixture results remain unchanged. |
| A17 | Separate observation and documentation streams with duplicate or coincident timestamps. | No Cartesian joins or duplicated P/F counts. Distinct genuine measurements remain distinct; ties use stable event IDs. |
| A18 | Exact replay baseline/acute control with matching exposure and equivalent scoring rules. | Signed/evaluable delta is exactly zero. Independent stationary realizations are not falsely constrained to zero. |
| A19 | Binomial counts k=0 and k=N. | Wilson intervals have valid nonzero uncertainty width unless structural identity is explicitly proven elsewhere. |
| A20 | Paired binary table has n_plus=30, n_minus=10, N=100. | Difference is 0.20 = 20 percentage points; sample MCSE is sqrt((40-100*.2**2)/(99*100)); interval uses paired discordance counts. |
| A21 | No observed discordances between nonidentical stochastic conditions. | Observed MCSE may be zero, but reported boundary-safe interval is not asserted to prove equality. |
| A22 | Threshold probability, mean count .5, paired change -.02, and an unscorable cell render. | Display 50%, 0.5 records, -2 percentage points, and U/not evaluable respectively; no magnitude-based unit guessing. |
| A23 | User edits a base scenario then expands a sweep or changes controls after a run. | Sweep inherits the actual base. Old results are marked stale and exports retain their original immutable request. |
| A24 | User selects a transition cell and a patient. | Trace score matches the summary; explanations identify actual determining/excluded evidence without rerunning the cohort. |
| A25 | Export/import/reproduce in a clean pinned environment. | Scientific tables match, hashes validate, schema/versions preserved; unsupported versions produce actionable errors. |
| A26 | Same small fixtures run natively and through actual Pyodide. | Exact discrete outputs and matching floats within predeclared tolerances; this is not replaced by a Python-only contract test. |
| A27 | Every advertised control/variant is exercised by a relevant fixture. | It affects the claimed mechanism or is explicitly documented as provenance-only/inactive; no dead controls or hidden default resets. |
| A28 | Six named experiments and deterministic explorer complete. | Real output tables, configurations, selected traces, plots, and a findings/limitations note exist. No invented positive findings. |

For deterministic scored intermediates use existing rounding exactly. For unrounded cross-runtime floats start with `atol=1e-10, rtol=1e-10`; quantities with an explicitly coarser stored precision use that contract. Do not loosen tolerances to make a discrete-score disagreement pass. A qualified numerical exception requires evidence and review.

## 12. Implementation milestones and closure evidence

Implement as cohesive increments under one goal. File names below are suggested locations, not mandatory fragmentation into many modules.

| Milestone | Required increment | Exit evidence |
|---|---|---|
| M0: freeze and clarify | Baseline reproduction fixtures; legacy/v2 profile registry; concise decision log and confirmed issue inventory. | A01 and targeted current-state reproductions. Move on to implementation; a planning-only PR does not close the goal. |
| M1: paired engine | Fixed-grid process, isolated streams, prescribed support, independent observation/documentation, v2 windows. | A02-A08, A15-A18 plus latent/episode comparison artifacts. |
| M2: interpretable results | Evidence statuses, rule traces/variants, paired outcomes and MC intervals. | A09-A21, transition reconciliation, numerical estimates from paired rows. |
| M3: investigation interface | One experiment state, six templates, deterministic explorer, linked encounter explanations, typed chart formatting. | A22-A24, A27; actual browser screenshots and user-flow tests. |
| M4: reproducibility and verification | Bundles, CLI, native/Pyodide parity, complete example generation, performance diagnostics and release report. | A25-A28, clean-install reproduction, full acceptance-to-evidence mapping. |

Maintain `docs/implementation/sofa_experiment_v2_status.md` (or equivalent) with milestone status and acceptance IDs mapped to tests/artifacts. Keep it short and factual. Prefer tests and outputs over repeated prose status reports. Run targeted checks during changes and full verification at meaningful integration boundaries.

### Existing verification commands

```
uv sync --locked --dev
make stage-web
make test
make e2e
make verify
uv run python -m build
uv run resp-sofa-sim --help
```

### New command contracts to implement, not commands available at the starting commit

```
uv run resp-sofa-experiment list
uv run resp-sofa-experiment run --config experiments/observation_density.json --replicates 200 --out artifacts/local/density
uv run resp-sofa-experiment explain --bundle artifacts/local/density --patient-id 0 --out artifacts/local/patient_0
uv run resp-sofa-experiment verify-bundle --bundle artifacts/local/density
uv run resp-sofa-experiment reproduce --bundle artifacts/local/density --out artifacts/local/density_reproduced
make experiments-smoke
make experiments-reference
```

The example directory is ignored local output. Bundles support a directory and a downloadable ZIP representation. `experiments-smoke` runs all required modes with small fixtures. `experiments-reference` produces the versioned demonstration tables and plot data with declared N and configurations; only small approved summaries/selected traces are checked in. Include a machine-readable figure-to-data manifest.

### Runtime and deployment

Profile before optimizing. Vectorize numerical transforms and replace repeated row-wise scans only with differential tests proving priority/time semantics. Keep detailed traces opt-in. A run budget accounts for patient-condition scores, latent steps, documentation volume, and export size rather than only replicate count. Oversized browser jobs fail before allocation with a CLI alternative; local batch limits are separately explicit.

Record native and browser cold-start versus warm-run benchmarks, configuration, completed work, hardware/runtime, and peak memory where measurable. Set and publish a concrete browser preview budget after the first representative measurement; do not reuse an unverified two-second target. Saved examples must render without waiting for simulation. Cancellation/state recovery and no-main-thread blocking are required, independent of absolute machine speed. Do not claim a speedup from changing the scientific workload.

CI must actually run relevant browser E2E tests, a native/Pyodide parity fixture, legacy regression tests, package build/smoke checks, and numerical acceptance cases. Pages deployment requires successful checks for the same commit; avoid deploying separately from a failing scientific test run. Pin the tested browser runtime/dependencies and include their identities in outputs. Do not assume `uv.lock` controls Pyodide's NumPy/pandas versions.

### Final handoff and completion gate

Deliver functioning code, tests, updated docs, small generated examples, bundle reproduction instructions, and a concise report containing: commit, baseline comparison, acceptance matrix, commands and results, screenshots, runtime evidence, experiment findings including nulls, assumptions, deviations, and remaining external-validation limits.

Provide a table for each experiment: comparator/variant, executed paired N, primary estimate and MC interval, data-availability change, one mechanism explanation, and what the result cannot establish. Mark unrun/blocked checks explicitly. External clinical calibration and independent SQL confirmation remain limitations, not accomplished results.

Do not close this goal until all required milestones have observable evidence. Any scope reduction needs an explicit owner decision; do not relabel deferred functionality as implemented. Preserve unrelated user work and do not force-push, change visibility, rewrite history, or release automatically.

## 13. Sources and design provenance

The repository findings come from the audited commit; the v2 model, experiment settings, interface requirements, and acceptance criteria are proposed design requirements, not assertions that these capabilities already exist.

Repository sources (pin all to the starting commit):

- [Core simulation](https://github.com/reblocke/sofa_resp_sim/blob/76ac9c3b670543380c19957450c215581b508f6f/src/sofa_resp_sim/core/resp_simulation.py)
- [Core scoring](https://github.com/reblocke/sofa_resp_sim/blob/76ac9c3b670543380c19957450c215581b508f6f/src/sofa_resp_sim/core/resp_scoring.py)
- [Conversion](https://github.com/reblocke/sofa_resp_sim/blob/76ac9c3b670543380c19957450c215581b508f6f/src/sofa_resp_sim/core/resp_utils.py)
- [Reporting calculations](https://github.com/reblocke/sofa_resp_sim/blob/76ac9c3b670543380c19957450c215581b508f6f/src/sofa_resp_sim/reporting/app_services.py)
- [Browser presentation](https://github.com/reblocke/sofa_resp_sim/blob/76ac9c3b670543380c19957450c215581b508f6f/web/assets/js/app.js)
- [Golden fixtures](https://github.com/reblocke/sofa_resp_sim/blob/76ac9c3b670543380c19957450c215581b508f6f/tests/core/test_resp_scoring_golden_fixtures.py)
- [Historical synthetic benchmark](https://github.com/reblocke/sofa_resp_sim/blob/76ac9c3b670543380c19957450c215581b508f6f/artifacts/resp_sofa_sim_summary.csv)

Methodological references verified when preparing this ticket:

- Morris, White, Crowther. *Using simulation studies to evaluate statistical methods*. Statistics in Medicine 2019;38:2074-2102. [doi:10.1002/sim.8086](https://doi.org/10.1002/sim.8086). Supports explicit simulation aims, data generation, estimands, comparison methods, and Monte Carlo error reporting. It does not validate this respiratory model.
- [NumPy parallel random-number generation](https://numpy.org/doc/stable/reference/random/parallel.html). Supports explicit deterministic IDs and independent stream construction. Pin implementation/runtime versions rather than promising cross-version bitwise identity.
- [SciPy binomial proportion intervals](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html). Supplies Wilson and exact interval components. The paired conservative interval above is the specified composition of discordance-probability bounds, not an independent-samples test.
