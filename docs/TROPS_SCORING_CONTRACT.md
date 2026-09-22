# Historical TROPS scoring contract

`trops_historical_e8b4de0_v1` maps active statements at commit
`e8b4de0b6e898e94d7ad091796a4aaea1df96231`. It is historical and **not
execution-validated**. Neither source currency nor production equivalence is
asserted. Synthetic references use UTC; the historical deployment timezone is
unknown. Configured local wall-clock DATE arithmetic is explicit in the profile.

Historical `measurement_minute` and `available_minute` are normalized offsets on
that local wall clock. Convert the supplied admission to the configured timezone
first, then remove timezone information **before** adding offsets or comparing
dates. Acute/baseline bounds, historical days/quarters, FiO2 lookup ages and
availability all use this coordinate system. The shared synthetic minute grid
and random streams are unchanged; a historical local-clock day spans 1,440
model minutes even at DST transitions. The bounded profile retains its elapsed
minutes and timezone-aware calendar bins.

Historical trace/window labels include a UTC offset only when the local value
identifies a unique instant. Values in a spring gap or repeated fall hour are
serialized as offset-free ISO local labels, with the clock declared by
`resolved_windows.timezone` (or the request's scoring timezone in bundle tables);
they must not be interpreted as UTC. They remain
valid DATE coordinates for scoring, without shifting nonexistent values or
choosing a fold. `ce_admit_dts` remains a timezone-aware, UTC-normalized encounter
partition key. Historical `bin_epoch` is a numeric local-calendar ordering key,
not a physical instant. UTC trace/window exports retain their original values.

This corrects the DST mixing of elapsed and local arithmetic identified in
[PR #12](https://github.com/reblocke/sofa_resp_sim/pull/12#discussion_r4066830538).
The intended source contract/profile ID and SQL hashes are unchanged; implementation
source hashes distinguish corrected runs. Archived bundles retain their original
source provenance and require that source for exact replay, as described below.

## Source identity and boundary

Only derived specifications and hashes are stored here. Source file names and
line locators below refer to the pinned historical commit, not current files.
Hashes cover original bytes (including comments); rule mapping uses active SQL,
excluding disabled alternatives and obsolete prose.

| Source | SHA-256 |
|---|---|
| SOFA Respiratory Detail.sql | `5275b2c92423f1b35774265458115cd82383a7a452c3cc016869a67e09cb745d` |
| Trops Measures - SOFA.sql | `0a2bc680f5d902c7e461b93d3ee17e7ab3b851869b61a93a79d7025ab3d4f170` |
| Trops Measures - Delta SOFA.sql | `9808aca5a40685b9a2b8c7aa3ad9ef77ebaf85466cfc8295b8a46ee2f1e00e65` |
| delta SOFA final.sql | `16012b237145a0e1223f948fcbe3ba6ad98456e6939ba12f88a19c38145831ab` |

Each scoring call is scoped to one patient and one cohort/admission. Inputs are
already normalized, per-timestamp oxygenation/FiO2 observations,
supplied support classifications/episodes and resolved encounter keys.
`ce_admit_dts` must be a timezone-aware resolved partition timestamp, **not** a
raw encounter ID. `invasive_ind` and `support_ind` must be independent Booleans.
`support_type` is retained separately for final support caps. OSA, therapeutic
NIPPV, HFNC, surgical IMV, and tracheostomy context must be resolved upstream;
a label is insufficient to reconstruct those flags. Supplemental context fields
survive traces. The synthetic adapter supplies flags from prescribed support;
it is not a clinical documentation classifier. Raw extraction, document
classification, constituent/meta-encounter resolution and tracheostomy episode
inference are outside this implementation.

## Rule crosswalk

Python paths below are relative to `src/sofa_resp_sim/`; fixture functions are
in `tests/experiments/test_historical_trops.py` unless another file is named.
All rows are source-mapped and synthetically tested, never study-execution certified.

| Rule and active source locator | Python function | Synthetic fixture |
|---|---|---|
| Baseline midnight minus 36 calendar months through midnight minus 7 days; acute admission minus 6h through plus 24h, both inclusive. Measures 63–66, 175–183. | `core/experiment_scoring.py:score_documented_events`, `core/historical_trops.py:historical_time` | `test_actual_baseline_cutoff`, `test_inclusive_acute_endpoints`, `test_generated_endpoint_is_documented_and_scored` |
| Historical pre-acute day index trunc(relative days) minus 1; latest day then maximum score then latest time. Exact negative integer differs from floor. Measures 175–183, baseline ranking. | `historical_time`, `experiment_scoring.py:_period_record` | `test_january_ranking_and_component_delta`, `test_exact_negative_integer_day_and_quarter` |
| Quarter = trunc(abs(relative days minus day index) ×4)+1; can be 5 at exact negative day. Detail 523. | `historical_time` | `test_exact_negative_integer_day_and_quarter` |
| Declared local DATE clock across DST; inclusive endpoints, baseline cutoffs, quarter evidence and timestamp labels agree. | `historical_time`, `historical_isoformat`, `score_documented_events` | `tests/experiments/test_historical_dst.py`; actual-worker DST cases in `tests/e2e/test_pyodide_parity.py` |
| Measured PaO2 priority; SpO2 50–96 inclusive via Ellis conversion, rounded to 0.1 mmHg. Detail 536–539. | `experiment_scoring.py:score_documented_events`, `core/resp_utils.py` | deterministic conversion grid; existing `test_scoring_profiles.py` |
| Room-air 21%; invasive set→measured→ABG; noninvasive measured→set→ABG; flow 0–15 L/min converts to (3×flow+21)%. Detail 698–709. | `experiment_scoring.py:_fio2_context` | `test_historical_source_priority`, deterministic support/PF grid |
| Partition by patient/cohort, resolved ce_admit_dts and invasive flag; back −14 to −1 min latest, then 0 to +5 min earliest; latest in prior 24h for baseline. Current room-air override. Detail 719–724. | `experiment_scoring.py:EvidenceIndex.lookup` | `test_partition_and_invasive_flags_are_explicit`, `test_historical_lookup_edges` |
| Missing denominator falls back to room air only for estimated PaO2 when no prioritized FiO2 exists in same resolved partition/day/quarter. Measured PaO2 does not receive fallback. Detail 867–870. | `experiment_scoring.py:score_documented_events` | `test_room_air_fallback_requires_estimate_and_empty_partition_quarter` |
| Detail ≥3 capped at 2 without explicit invasive/support flags; final ≥3 capped at 2 unless IMV or NIPPV; positive unsupported acute singleton becomes 0. Detail 879; Measures 129/148/203. | `experiment_scoring.py:score_documented_events`, `_period_record` | `test_support_detail_final_cap_and_singleton`, `test_flags_are_not_inferred_from_display_or_tracheostomy_context` |
| Acute maximum score, support order, earliest timestamp; baseline latest day, maximum score, latest timestamp. | `experiment_scoring.py:_period_record` | existing `test_scoring_profiles.py` ranking/tie cases; January fixture |
| Missing acute/baseline components zero-filled in algorithm; evidence remains unavailable. Measures 114–118, 276. | `experiment_scoring.py:_period_record` | 75 criterion cases, missing-evidence transitions |
| Truncate each component change at zero before sum; criterion ≥2. Delta 66/77; final criterion. | `reporting/historical_results.py:eligibility` | `test_all_75_component_criterion_cases`, `test_component_truncation_and_invalid_c` |

## Reporting and identity

Respiratory contribution is `R=max(acute_algorithm_score-baseline_algorithm_score,0)`.
Signed respiratory delta remains available. C is a supplied sum of nonnegative
changes in other organs, not a simulated population characteristic. All three
conditional views (`0`, `1`, `ge2`) use the same patients and scores. For C=0/1,
missing respiratory evidence makes evidence-supported eligibility indeterminate;
C≥2 determines eligibility regardless of respiratory evidence. Zero-filled
algorithm scores never imply observed normal physiology.

Nine paired evidence-state cells retain patient IDs. Eligible↔ineligible flips
are distinct from gains/losses involving indeterminate. Contrasts display both
probabilities on the common paired denominator, with condition-specific marginals
separately labeled. Binary uncertainty is patient-level Wilson and paired
discordance; retention is a patient fraction with Monte Carlo standard error.
Empty estimates are unavailable; N=1 carries no interval.

V3 request/bundle identities include scientific rules and the source contract
hash. Qualification prose is separate. Edited profiles expose deviations and a
modified-experiment label. V2 meanings, archived bundles and original reference
bytes remain unchanged. All new source/eligibility calculations run in Python,
including the actual browser worker.

External execution against an approved study implementation remains a separate
future milestone requiring source, runtime, adapter and fixture-bound evidence.

## Reproducing the archived reference run

The exact Python package bytes used for the 48 full references are preserved at
commit `fc1f3b142f25e6bfd5a2f72d294246ef0b782182`. Final formatting changed two
source-file hashes without changing normalized ASTs; the final integrated code
and the reference checkpoint are bound in
`artifacts/trops_sensitivity_v1/acceptance/source_revision.json` and
`source_format_equivalence.json`. The source-strict CLI intentionally rejects
reproduction/append with different package bytes. Use the reference checkpoint
and recorded runtime for those original full bundles, or run the frozen requests
into a new empty output directory with the current revision. Do not relabel old
bundles with current source hashes. Current v2/v3 bundles also reproduce in the
clean-wheel verification route.

Compact reference explanations use lossless `columnar_groups_v1` JSON. Each
group supplies columns, original row indices and typed values; grouping preserves
absent fields separately from explicit nulls. The interactive explanation retains
the ordinary per-event representation.
