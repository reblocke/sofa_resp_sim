# Decisions

This file summarizes active implementation decisions. Longer-lived decisions are
recorded as ADRs under `docs/adr/`.

## Active decisions

- Python remains the only source of truth for scoring, simulation, uncertainty,
  and reference comparison.
- The package layout is root `src/`, with tests under root `tests/`.
- Top-level `sofa_resp_sim.resp_scoring`, `resp_simulation`, and `resp_utils`
  wrappers preserve existing imports.
- The static browser app uses Pyodide in a web worker and calls only
  `sofa_resp_sim.browser_contract`.
- Generated browser staging outputs are ignored and recreated with
  `make stage-web`.
- Streamlit is no longer an active runtime or dependency.
- `uv` is the canonical environment and lockfile workflow.

## Paired experiment v2 contracts

The paired-workbench implementation goal adopts the plan under
`docs/implementation/paired_experiment_goal/`. The scientific choices below are
versioned experimental assumptions, not a clinical standard or calibration.

- Existing no-profile entry points retain `legacy_py_v1` behavior. Regression
  inputs and seeded outputs were frozen before implementation in
  `tests/experiments/fixtures/legacy_py_v1.json` at commit `76ac9c3`.
- v2 uses a one-minute stationary Gaussian AR background with pre-clipping
  marginal SD and elapsed correlation time. `tau_minutes=0` means independent
  noise. Episodes are non-overlapping half-open rectangular decrements of the
  unperturbed background; initiation probability is `1-exp(-rate_per_hour/60)`
  only while idle. Prescribed trajectories/episodes are explicit alternatives.
- `SeedSequence([patient_id, block_id, stream_id, seed])` with PCG64 separates
  physiology, episodes, measurement noise, support assignment, FiO2 values,
  SpO2/FiO2 missingness, timestamp perturbation and source labels. Stream IDs are
  stable. Run size, condition order/labels and chunk size never seed physiology.
- Requests use SpO2 percent, PaO2 mmHg, minutes and FiO2 fractions. Low-flow FiO2
  remains an inferred proxy. Unknown support supplies no room-air evidence.
- The v2 base profile uses UTC/calendar bins and acute `[admit-6h, admit+24h)`.
  Generation and documentation context do not expand target eligibility.
  Baseline date selection remains the legacy latest eligible day rule.
- Retrospective lookup uses measurement time; the as-of variant only considers
  evidence available by the oxygenation event's recorded time. Recorded delay
  and erroneous measurement timestamps are separate mechanisms.
- Without documented denominator evidence, v2 reports no qualifying P/F and
  a missing-evidence status. Any legacy implicit-0.21 intermediate is restricted
  to explicitly labeled legacy diagnostics, never presented as measured FiO2.
- Named ablations disable singleton suppression, expand all support gates to
  HFNC/NIPPV/IMV/SURG IMV, prioritize contemporaneous FiO2, impose as-of
  availability, require measured PaO2, maximize over all eligible baseline dates,
  or use admission-anchored bins. Their exact fixtures accompany implementation.
- E5 varies baseline observation opportunity on fixed generated blocks. Its
  exact-replay control repeats a complete six-hour segment at identical UTC clock
  times; it is separate from independent stationary baseline/acute realizations.
- Reference stochastic demonstrations use 2,000 paired patients per reported
  stratum. Previews use 200 in one stratum. No population-weighted aggregate is
  inferred from the illustrative strata.
- AR stochastic tolerances were fixed before their first test run in
  `tests/experiments/fixtures/ar_validation_protocol.json`. They are not adjusted
  to fit observed failures. Cross-runtime unrounded comparisons use
  `atol=rtol=1e-10`, with exact discrete values and existing rounded-value rules.
- SciPy provides interval components and an AR recurrence filter. Native and
  browser dependency versions are recorded separately; the native lockfile is
  not a browser runtime lock.

## Deferred delivery decisions

- Public repository publication from a clean history remains separate from this
  migration; see `docs/PUBLIC_RELEASE_AUDIT.md`.
- Release/Zenodo automation remains deferred.
- Any model changes, new simulation assumptions, or clinical interpretation
  changes require separate validation and documentation.

### Logical identity and runtime integrity

A patient generation ID hashes the versioned scientific configuration, seed and
patient identity; it does not hash unrounded floating-point bytes. A production
Pyodide comparison found three latent values differing by 1.42e-14 while discrete
scores matched. Raw little-endian float checksums are retained separately as
runtime-specific integrity metadata. Support identity follows the same split.
Cross-runtime scientific comparisons retain exact discrete matching and the
prespecified float tolerance; hashes are not substituted for those comparisons.

The worker uses JSON serialization in both directions to preserve nullable
scientific fields. Pyodide also loads tzdata for explicit timezone/DST rules.

Paired summaries use patients as independent Monte Carlo units, Wilson intervals
for absolute probabilities and exact discordance component intervals at 97.5%
combined by the union bound for pointwise 95% paired differences. Empirical
MCSE uses sample variance; N<2 uncertainty is unavailable. Nonbinary mean/count
estimates report MCSE without an asserted exact interval. Matching observed
scores do not prove structural identity; only identical scientific condition
IDs set that flag. Evidence-evaluable pairs have their own explicit denominator.

### Prespecified finite catalogue

Catalogue `illustrative_catalogue_v2.1` defines 18 demonstrations across room-air,
low-flow, HFNC and IMV strata. Seed 173203 and 2,000 paired patients per stratum
are fixed before reference execution; the deterministic sampling demonstration
uses one patient. Full normalized requests are saved in `experiments/E1.json`
through `E6.json`. Metadata distinguishes noise, bias, rounding, assignment,
missingness, timing, source disagreement, stale values, source-only and zero
controls. Independent stationary baseline opportunity and exact replay are
separate demonstrations. Dense E6 contrasts are supplemented by a singleton
mechanism case; null effects in other settings must be reported honestly.

A stratum in the assignment-stress comparison names the fixed comparator. The
stress condition may cross support labels; it is not a population stratum or
physiological treatment response. Constant room air is an inert control for
stale values, and room-air/flow evidence does not become known delivered FiO2
through a source-label or disagreement setting. No population total is inferred.

The deterministic explorer exposes event traces and encounter results separately.
Default encounters have two records. Conversion-unavailable cells carry their
own flag and evidence status even when the algorithm's fallback is zero.

### Synthetic bundle interchange

Bundle v2 contains the eleven specified members plus `reclassification.csv`,
so restricted-denominator reclassification is not lost on export. SHA256SUMS
covers every other member. A separate scientific hash covers request/data/metric
files and excludes environment, creation time and ZIP metadata. Selected traces
are regenerated for one patient across conditions and checked against saved scores.

CSV types are declared per column in the manifest. Blank cells mean null; empty
strings use \e and leading backslashes are escaped. Nested and mixed-type cells
use JSON. Integral JSON numbers compare exactly across `1.0`/`1` representations;
that equivalence does not apply tolerance to changed count values.

Appending increases N without changing the original request otherwise, preserves
old scientific rows, and generates only the added patient IDs. The new run ID
and parent run ID explicitly record the extension. CLI exact reproduction and
append require the recorded runtime and package source. Explicit cross-runtime
reproduction retains exact discrete comparisons and atol/rtol=1e-10 for floats;
its method and source scientific identity are saved in the new manifest.
