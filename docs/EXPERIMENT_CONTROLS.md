# Experiment controls and their scope

Every browser edit changes the current request. Completed results keep their
original request and become stale after edits. Choosing a preset or support
stratum deliberately loads that preset's defaults. Expanding comparisons after
an advanced edit uses the edited base. Controls varied by the selected comparison
are disabled and labeled accordingly; their values come from the listed conditions.

| Control | Mechanism | Conditional scope |
|---|---|---|
| Background SpO2 mean | Center of the latent oxygenation generator | A prescribed trajectory supplies its own values; measured-PaO2 scoring does not infer PaO2 from latent SpO2 |
| Marginal SD | Stationary latent variation before episodes and clipping | Zero gives a constant background; boundary clipping can change observed marginal variation |
| Correlation time | Correlation of the background process across elapsed minutes | Has no numerical effect on a zero-variance background |
| Episode initiation rate | Independent episode starts | Zero disables stochastic episodes; prescribed episodes remain explicit |
| Episode depth | Oxygenation decrement during stochastic episodes | Inactive when no stochastic episode occurs; prescribed episodes carry their own depths |
| Episode duration | Length of stochastic episodes | Inactive when no stochastic episode occurs; prescribed episodes carry their own endpoints |
| Observation interval | Scheduled oxygenation measurements | Changes recorded opportunity, not the underlying patient trajectory |
| Measurement noise SD | Noise added at observed times | Does not change the latent trajectory or fixed support |
| Measurement bias | Offset applied to observed oxygenation | Does not change the latent trajectory; rounding/clipping can mask small offsets |
| Missing oxygenation probability | Removal of sampled oxygenation evidence | Does not remove latent points or change fixed support |
| FiO2 documentation interval | Scheduled denominator-source records | Separate from the oxygenation schedule; lookup rules determine which records are used |
| Missing FiO2 bundle probability | Removal of all specified observable denominator evidence | Latent delivered support is not a hidden fallback |
| Threshold factor | Multiplication of rubric thresholds | Does not change conversion or the P/F ratio; discrete scores may remain unchanged between thresholds |
| Seed | Versioned patient/block/stream draws | Provenance changes in deterministic zero-noise prescribed cases may leave all values unchanged |
| Paired patients | Number of independent synthetic patients | Earlier patient identities and values are retained when N is extended |
| Primary outcome | Which existing metric the main figure displays | Does not alter generated patients or per-patient scores |
| Included comparisons | Selected fully resolved condition configurations | Does not change the shared comparator or retained patient streams |

An unchanged score is not proof that a control is dead: generation, measurement,
source selection and scoring thresholds are distinct stages. The request and
encounter trace expose intermediate values needed to check the claimed stage.
Conversely, an unchanged intermediate at the claimed stage needs investigation;
provenance alone does not demonstrate a numerical mechanism.

The deterministic rule explorer directly specifies evidence source, oxygenation
value, support label, FiO2 fraction/flow proxy, threshold factor and one versus
two records. These bypass cohort sampling. The conversion output is explicitly
unused for measured PaO2. One versus two records can change singleton suppression
without changing the event-level rubric. A low-flow FiO2 estimate is a proxy,
not a measured delivered fraction.

Relevant implementation coverage lives in `tests/experiments/test_latent.py`,
`test_observation.py`, `test_scoring_profiles.py`, `test_catalogue.py` and the investigation
browser tests. This inventory describes scope; final A27 acceptance also requires
checking the actual rendered controls and their submitted normalized requests.

## Historical sensitivity extension

The v3 historical profile, normalized context boundary, conditional C views and
qualification limits are documented in [TROPS_SCORING_CONTRACT.md](TROPS_SCORING_CONTRACT.md).
The original v2 contract and reference evidence remain preserved. New frozen
requests live in `experiments/trops_v1/`; new evidence uses
`artifacts/trops_sensitivity_v1/`. Historical mapping is not SQL execution
validation or current-production equivalence.
