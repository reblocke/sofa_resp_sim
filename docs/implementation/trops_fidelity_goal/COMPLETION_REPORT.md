# Historical TROPS sensitivity completion

The accepted historical software phase is complete. T01–T24 and Q01/Q03/Q04
pass in [ACCEPTANCE.json](ACCEPTANCE.json). Q02 remains unperformed future work.

**Historical TROPS specification mapped to Python; synthetic verification
complete; execution against the study SQL not performed.**

## Delivered behavior

The new `trops_historical_e8b4de0_v1` profile uses normalized timestamp values,
supplied independent support flags and resolved encounter partitions. It
implements historical day ranking, event-time cutoffs and inclusive acute
endpoints, quarter fallback, source hierarchy/partitions, caps, suppression and
zero-filled component conventions. Evidence availability remains separate.

V3 requests and bundles expose conditional C=0/1/≥2 criterion outcomes, signed
and evaluable deltas, all nine evidence transitions, common-pair probabilities
and separate marginals. The browser refreshes its catalogue after Python starts,
preserves the saved v2 example, and changes C using already scored patients.
Patient explanations show source IDs/ages, partitions/flags, eligibility and
actual observation opportunities. E3 measures retention; E5 separates density,
matched-end history and boundary alignment; E6 separates acute/baseline rules.

Legacy/v2 scoring, the original requests, archived reference bytes and bundles
remain preserved. No SQL, grants, real records or restricted adapters were added.

## Verification and reproducibility

- Scientific and browser code checkpoint: `3640987c8ca9d63443afa9fc03af89d0af67bfd6`.
- Exact full-reference package checkpoint: `fc1f3b142f25e6bfd5a2f72d294246ef0b782182`.
  References ran from identical uncommitted package bytes before that checkpoint
  was created. Final formatting/import ordering changed two byte hashes;
  normalized AST equivalence and final integration checks are recorded.
- 432 native cases covered by the 429-case full suite and three added acceptance
  cases. The added CLI/evidence run passed four cases, including one overlap.
- All 21 browser cases covered. The initial full run had one historical selector
  failure; the catalogue-refresh repair passed the historical workflow and three
  startup/export/cancel/recovery regressions. The historical test also passed
  after adding an evaluable-outcome selection/run.
- Actual Pyodide 0.29.0 executed v2 and v3 generation/scoring, summaries, traces and
  bundles. Discrete/null fields matched exactly; float tolerance was 1e-10.
- Staging, Ruff formatting/lint, old catalogue freeze, both artifact namespaces,
  source-packet hashes and `git diff --check` passed. A fresh locked wheel outside
  the checkout exactly reproduced both v2 and v3 bundles.

[Verification receipts](../../../artifacts/trops_sensitivity_v1/acceptance/verification_runs.json)
retain commands, logs, runtime/source hashes and the resolved initial browser
failure. [Source revisions](../../../artifacts/trops_sensitivity_v1/acceptance/source_revision.json)
identify exact reproduction requirements. Compact CSV line endings and SVG trailing whitespace were subsequently normalized
for Git-portable hashes; artifact checks and both evidence tests passed again.
No push, merge or deployment was
performed for this phase; remote CI is not claimed.

## Reference findings

All 48 frozen requests completed with 2,000 paired patients each, seed 173203,
stationary mean96%/SD0.5-point saturation, 30-minute correlation time and no
episodes or support drift. Six reviewed mechanism figures, 336 deterministic
P/F cells, 16 conversion cells, 75 score/C cases, all transitions and selected
patient explanations are in [the new evidence namespace](../../../artifacts/trops_sensitivity_v1/FINDINGS.md).

The prespecified eligibility/delta primary contrasts are null in these stable
scenarios. Missingness and timestamp shifts reduce observation retention;
baseline density/alignment can alter evidence availability without changing
common-pair eligibility. These findings were retained without tuning seeds or
replacing scenarios. C≥2 is invariant by construction. They do not establish
clinical calibration, current-production equivalence or treatment effects.

Comparison with a currently approved study implementation, execution through the
study SQL, upstream documentation reconstruction and clinical qualification are
separate future milestones.
