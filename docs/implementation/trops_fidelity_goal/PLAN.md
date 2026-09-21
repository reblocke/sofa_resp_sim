# Implementation and verification plan

This is the accepted historical software endpoint. Source documents under
`source/` are preserved audit inputs; the user's accepted plan controls scope.

1. Preserve legacy/v2 behavior. Pin active historical source hashes and write the
   normalized input/rule/function/fixture crosswalk. Keep source SQL outside Git.
2. Implement historical temporal, partition, denominator, cap, suppression and
   component rules in Python; preserve separate algorithm and evidence values.
3. Add v3 conditional eligibility and all nine evidence transitions; calculate
   both contrast probabilities on common pairs beside separate marginals.
4. Repair E3 retention diagnostics, split E5 density/history/alignment and E6
   acute/baseline rules. Keep old replay/96-total-50-latest-day examples and nulls.
5. Integrate CLI, browser, explanations and v3 bundles; keep existing stale,
   cancellation, recovery and v2 import behavior. Changing C is a view of already
   scored patients. Edited profiles carry explicit deviations.
6. Freeze and run `experiments/trops_v1/manifest.json`: six mechanisms × four fixed
   supports × historical/experimental profiles = 48 requests, N=2000, seed 173203.
   Stationary mean96%, SD0.5 points, tau30min, no episodes/support drift. Previews
   N=200. Generate 336 PF/support/singleton cells, 16 conversion cells and 75 C
   algebra cases, plus focused source/partition/OSA fixtures.
7. Produce compact findings, six mechanism figures, deterministic appendix and
   selected patient explanations. Retain patient0 and lowest-ID members of each
   nonempty eligibility transition; no effect-selected seed or request changes.
8. Run relevant/full verification, review figures, record exact tested source,
   runtime, request and artifact hashes, and resolve every required ledger item.

Canonical integration commands:

```sh
make stage-web
make fmt-check lint test e2e
uv run python scripts/freeze_experiment_catalogue.py --check
uv run python scripts/run_historical_references.py --workers 4
uv run --group figures python scripts/build_historical_evidence.py
uv run python scripts/verify_experiment_evidence.py
make experiments-install-check
git diff --check
```

The reference builder must reject incomplete inventories, changed frozen
requests, unverified bundles or unreviewed/stale figures. It writes only the new
namespace; original `artifacts/experiments_v2` and v2 requests remain unchanged.

Acceptance is T01–T24 plus Q01/Q03/Q04. Q04 binds local delivery to the tested
revision; remote CI is checked if pushed, without inferring deployment. Q02 is
explicit future work, not a software completion prerequisite. The final report
states historical source mapping, synthetic verification and no SQL execution.
