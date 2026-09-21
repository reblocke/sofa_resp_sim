# Interpretation of the reference collection

This review covers the 72 requests identified in `table_provenance.json`, the
primary absolute and paired figures, and the eight deterministic rule grids.
The paired-table SHA256 is
`03b10d11db0cae9da335ec910db5a106d8ec01ac31c7f2815771aac8971b84dd`.
It is a review of synthetic model behavior, not independent clinical validation.
Image-specific review records are bound to the current PNG hashes in the two
figure manifests.

## What the demonstrations show

- **Observation density and episodes (E1):** In the stochastic room-air preset,
  hourly sampling yields fewer encounters with score ≥2 than sampling every
  15 minutes. The supported strata are at the ceiling for this outcome. The
  deterministic room-air episode is detected at the denser schedules but not
  hourly; its N=1 display illustrates timing, not an estimated population risk.
- **Measurement error (E2):** Noise, bias, and rounding operate on observations
  from shared latent patients. In these presets, the room-air threshold outcome
  changes more than the supported-stratum outcomes, which are already at 100%.
  Positive saturation bias lowers the room-air score ≥2 frequency. Small noise
  and rounding contrasts have intervals spanning zero. The assignment stress
  test can change support categories; the panel names identify the comparator
  strata and do not describe physiological responses to treatment.
- **Documentation (E3):** Complete removal of denominator evidence produces
  no qualifying data. Partial removal and the timestamp offsets do not produce
  encounters with entirely absent qualifying data in these dense reference runs.
  That encounter-level outcome cannot establish that every record remains
  eligible. Source disagreement and stale values likewise show no change in
  score ≥2 here; inspect record provenance and other exported outcomes to study
  their mechanisms. Identical source labels/values and explicit zero perturbation
  are controls, not evidence that conflicting sources are interchangeable.
- **Threshold factors (E4):** The estimated-PaO2 room-air example crosses the
  score ≥2 boundary as thresholds decrease. The measured example fixes PaO2 at
  84 mmHg: the low-flow stratum changes at factor 0.75, while several other
  strata remain on the same side of the threshold. These settings change scoring
  thresholds, not PaO2, P/F, or a physiological response to altitude.
- **Baseline opportunity (E5):** Shorter and less frequently observed independent
  baseline blocks can increase the reported acute-minus-baseline threshold
  frequency even under stationary physiology. The exposure-by-frequency panels
  retain every prespecified cell and its uncertainty. These deltas use the legacy
  zero convention and are not sepsis incidence. The exact six-hour replay control
  yields zero positive deltas; independent stationary blocks need not do so.
- **Rules and singletons (E6):** Dense records can make singleton suppression
  inactive. Under the separate single-record construction, disabling it changes
  room-air, low-flow and HFNC outcomes, while the IMV result is unchanged under
  the specified support rules. In the dense rule comparison, measured-only and
  as-of-availability settings eliminate qualifying evidence in this construction;
  their algorithmic zeros must not be interpreted as documented normal function.
  One-at-a-time rule contrasts are not additive contributions.
- **Deterministic explorer:** The grids separate raw, support-adjusted, and
  reported scores at conversion limits and threshold neighborhoods. The low-flow
  SpO2=90% fixture gives P/F=177.88 and reported scores 0 versus 2 with one versus
  two records. SpO2 49% and 97% are outside the conversion domain. Unavailable
  evidence is marked separately even where the algorithm retains a numeric zero.

## Limits of inference

Many primary outcomes are near 0% or 100%; a null threshold contrast can conceal
changes in continuous P/F, qualifying-record counts, or other score categories.
Presets and their first contrasts remain in declared order. Results have not been
ranked to select favorable comparisons, and null demonstrations have not been
retuned after seeing these runs. Full tables retain all metrics and contrasts.

The Monte Carlo intervals describe simulation sampling uncertainty conditional
on fixed assumptions. They do not include parameter uncertainty, clinical
measurement validity, or between-setting transportability. They are pointwise,
not simultaneous across the catalogue. Zero observed differences do not prove
equivalence. Identity in the replay and normalized-zero controls is established
by their construction and invariance tests, rather than a zero point estimate.

The four strata have no population weights. Shared patients support paired
comparisons within each request; the collection is not a calibrated clinical
cohort. Validation against clinical data or an independently executed SQL scoring
system remains outside this implementation's evidence.
