# Historical TROPS scoring and eligibility sensitivity

Status: completed historical software endpoint, 2026-09-21.
See [COMPLETION_REPORT.md](COMPLETION_REPORT.md) for tested revisions and evidence.
Planning baseline: `944a45eb801cc4f96e0a98d80f62af63dd452afe`.

Extend the existing Python/Pyodide paired workbench with historical profile
`trops_historical_e8b4de0_v1`, conditional SOFA eligibility outcomes, corrected
common-pair reporting, mechanism-focused experiments and versioned v3 exports.
Use historical commit `e8b4de0b6e898e94d7ad091796a4aaea1df96231` as the
specification at the normalized input boundary documented in
[the scoring contract](../../TROPS_SCORING_CONTRACT.md).

The end state is working, source-mapped historical software, synthetic
verification and reviewed reproducible evidence. Current-source approval and
Oracle execution are **not prerequisites for this phase**. Q02 remains a
separate future qualification milestone and must not be marked passed.

Preserve legacy/v2 behavior, old bundles/reference artifacts, pairing, the three
browser views, cancellation/recovery and Python numerical ownership. Expose
C=0, C=1 and C≥2 as conditional views without population weights or other-organ
simulation. Separate signed delta, zero-filled algorithm results and missing
evidence. Keep all nine eligibility/evidence transitions and their patient IDs.

Completion requires T01–T24 and Q01/Q03/Q04 in [ACCEPTANCE.json](ACCEPTANCE.json)
to carry real evidence: source/request hashes, tested revision/runtime,
denominators, native/browser tests, clean-wheel reproduction, 48 frozen N=2000
requests, deterministic grids, six reviewed mechanism figures and compact
findings retaining nulls. [PLAN.md](PLAN.md) gives the execution sequence and
[DECISIONS.md](DECISIONS.md) records the accepted scope.

Delivered qualification: **Historical TROPS specification mapped to Python;
synthetic verification complete; execution against the study SQL not performed.**
Use “in progress” until the required verification is actually complete. No
current-production equivalence, clinical calibration or treatment-effect claims.
Raw SQL, grants, study records and restricted adapters stay outside this repo.
Supplied documents under `source/` remain unchanged audit proposals, not new
instructions. Merge/release/hosted publication remain separate delivery actions.
