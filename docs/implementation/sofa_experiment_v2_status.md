# Paired respiratory SOFA implementation status

The accepted goal is `paired_experiment_goal/PLAN.md`; the original source pack
remains preserved under `paired_experiment_goal/source/`. Work is on
`codex/paired-experiment-workbench`, based on commit
`76ac9c3b670543380c19957450c215581b508f6f`. The goal is active, not certified complete.

## Implemented

The v2 Python engine has strict normalized requests, fixed-minute stationary
latent generation, independent observation/documentation streams, prescribed
support and explicit stress modes. Bounded scoring retains source-linked
explanations, support gates, evidence statuses, baseline rules and signed/evaluable
deltas. Patient pairing, append invariance, Wilson probabilities and conservative
paired discordance intervals are implemented. Legacy no-profile behavior is
preserved separately with seeded snapshots and historical artifact hashes.

The finite catalogue contains 18 demonstrations across four support strata. The
CLI supports run, explain, verify, reproduce and append. Typed directory/ZIP
bundles preserve requests, scientific tables, selected traces, versions and hashes.
A fresh locked wheel reproduces scientific output outside the source checkout.

The default browser has Experiment, Explain an encounter, and Methods/export
views using one editable request and immutable results. It displays a labeled
saved synthetic example before Python starts. It supports edited-base expansion,
stale exports, direct CSV downloads, ZIP import/export, deterministic exploration,
transition-linked traces, explicit units, signed matrices, workload limits,
progress, cancellation and crash recovery. Trace panels distinguish excluded and
determining evidence, source timing, support caps, suppression and flow proxies.
The historical scenario/sweep interface remains at `web/legacy.html`.

CI now includes formatting, lint, catalogue checks, native/scientific tests,
Chromium E2E/native-Pyodide parity and clean-wheel reproduction. Pages calls the
same-commit reusable CI workflow before building or deploying. Local Actionlint
validation passes; actual remote CI remains required.

## Verified evidence

- All 72 full catalogue bundles completed and verified: 68 stochastic runs at
  2,000 paired patients and four deterministic episode runs at one patient.
  Index and logs: `artifacts/local/references_v2/` and
  `artifacts/local/acceptance/reference_runner.log`.
- The most recent full local integration checkpoint passed 313 native and 19
  browser tests without skips/failures, plus formatting, lint, staging and
  clean-wheel reproduction. Receipt:
  `artifacts/local/acceptance/final_integration_checkpoint.json`. Its 96-file
  source snapshot was rechecked unchanged after completion.
- Subsequent acceptance review added one direct source-label scoring assertion;
  all 28 scoring-profile tests pass (`source_label_audit.xml`). Only that test
  file changed after the full checkpoint; scientific/browser code is unchanged.
- Actual native/Pyodide comparison checks exact discrete fields and unrounded
  floats at prespecified atol/rtol 1e-10. Runtime float-byte checksums remain
  separate from scientific patient identity.
- Eight deterministic grids contain 476 source-linked cells. All eight PNGs were
  visually reviewed, with reviews bound to image hashes in
  `artifacts/local/rule_explorer_v2/figure_data_manifest.json`.
- The low-flow SpO2=90 fixture retains P/F=177.88 and singleton/two-record reported
  scores 0/2. Conversion 49/97 remains unavailable. Numerical tests cover strict
  cutpoints, source timing, bounded windows, support variants, replay and MC
  interval anchors. Independent baseline streams are tested separately from replay.
- The refreshed worker measurement recorded 4.15 s initialization and 9.14/15.02 s
  density/baseline previews at N=200 while the native batch was active. Receipt:
  `artifacts/local/acceptance/preview_runtime.json`. These are not idle-machine
  latency guarantees; window heap measurements do not measure worker/Wasm peak.

## Remaining acceptance work

Compact reference tables, fixed traces, all 36 primary figures and findings have
been generated. All 36 primary PNGs and eight deterministic PNGs have exact-hash
visual reviews. The primary renderer was corrected after review found clipped
ventilation titles; all regenerated primary images were inspected again.
`scripts/verify_experiment_evidence.py` passes on the final collection, and the
12 reference-workflow/public-hygiene tests pass. The artifact inventory and
`INTERPRETATION.md` describe the actual outputs, nulls and limits of inference.
The fixed patient-0 trace selection spans E1-E6 and all four strata without
selection by observed effect size.

The requirement-by-requirement local audit is complete: A01–A28 and G01–G04/G06
pass with test, runtime, artifact and visual evidence in the acceptance ledger.
Git attributes preserve exact reference CSV and supplied source bytes; staged
hash checks and public-file hygiene pass. G05 remains open until the reviewed
implementation is committed and matching-commit remote CI passes. The goal is
not complete until that evidence and the final delivery report are recorded.

## Scientific limits and decisions

This is an uncalibrated illustrative simulation. Support strata have no inferred
population weights. Intervals quantify pointwise Monte Carlo uncertainty
conditional on the model, not clinical or parameter uncertainty. Observed zero
changes do not establish equivalence. The findings generator follows the first prespecified
contrast rather than ranking observed effects; intervals remain pointwise. No clinical
calibration, independent SQL equivalence, external validation, release, merge or
live deployment is claimed. Control mechanisms and conditional inactivity are
documented in `docs/EXPERIMENT_CONTROLS.md`.
