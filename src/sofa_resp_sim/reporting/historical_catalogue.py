"""Finite historical/experimental sensitivity catalogue, fixed before reference runs."""

from ..core.historical_trops import PROFILE, ScenarioV3
from .experiment_catalogue import REFERENCE_SEED, STRATA, condition
from .experiment_request import V3, normalize_experiment_request

VERSION = "trops_sensitivity_v1"
MECHANISMS = {
    "density": (
        "E1: Stable observation density",
        "Acute observation interval",
        "sofa_eligibility_C0",
    ),
    "missing": (
        "E3: Oxygenation retention",
        "Oxygenation missing probability",
        "eligible_observation_fraction",
    ),
    "timing": (
        "E3: FiO2 timestamp shift",
        "FiO2 timestamp offset",
        "eligible_observation_fraction",
    ),
    "baseline_density": (
        "E5: Fixed-window baseline density",
        "Interval in one fixed baseline window",
        "delta_evaluable_ge1",
    ),
    "history": (
        "E5: Matched-end history",
        "Earlier history; unchanged selected-day opportunities",
        "delta_evaluable_ge1",
    ),
    "alignment": (
        "E5: Scoring-day alignment",
        "Fixed six-hour schedule shifted across a scoring-day boundary",
        "delta_evaluable_ge1",
    ),
}
PROFILES = {"historical": PROFILE, "experimental": "bounded_analysis_v2"}
REFERENCE_ENTRIES = tuple(
    f"H_{mechanism}_{profile}" for mechanism in MECHANISMS for profile in PROFILES
)


def metadata_entries():
    entries = []
    for entry in (*REFERENCE_ENTRIES, "H_rules_acute_historical", "H_rules_baseline_historical"):
        mechanism, profile = entry[2:].rsplit("_", 1)
        title, changed, outcome = MECHANISMS.get(
            mechanism,
            (
                "E6: " + mechanism.replace("_", " "),
                "One scoring rule at a time",
                "baseline_score" if mechanism == "rules_baseline" else "score_ge2",
            ),
        )
        entries.append(
            {
                "id": entry,
                "experiment": title.split(":")[0],
                "title": f"{title} ({profile})",
                "mechanism": changed,
                "primary_outcome": outcome,
                "deterministic": False,
                "held_fixed": (
                    "Same synthetic patients, fixed support and stationary latent paths; "
                    "only named overrides vary."
                ),
                "limitations": (
                    "Historical source-mapped, not execution-validated. "
                    "Conditional C scenarios, no population weights; "
                    "pointwise Monte Carlo uncertainty only."
                ),
            }
        )
    return entries


def historical_request(entry_id, stratum, *, replicates=200, seed=REFERENCE_SEED, base=None):
    if entry_id not in {e["id"] for e in metadata_entries()} or stratum not in STRATA:
        raise ValueError("Unknown historical sensitivity entry or stratum")
    mechanism, profile = entry_id[2:].rsplit("_", 1)
    historical = profile == "historical"
    scenario = (
        ScenarioV3.from_dict(base)
        if base is not None
        else ScenarioV3.from_dict(
            {
                "generator": {
                    "mean_pct": 96,
                    "marginal_sd_pct": 0.5,
                    "tau_minutes": 30,
                    "episode_rate_per_hour": 0,
                },
                "horizon": {
                    "admit_dts": "2024-01-01T06:00:00Z",
                    "start_minute": 0,
                    "end_minute": 1441,
                    "include_baseline": True,
                    "baseline_generation_minutes": 1800,
                },
                "observation": {"start_minute": 0, "noise_sd_pct": 0, "rounding": "one_decimal"},
                "documentation": {"measured_source_probability": 0},
                "support": STRATA[stratum],
                "scoring": {"profile": PROFILES[profile]},
            }
        )
    )
    if mechanism == "density":
        comparator, variants = (
            condition("Every 15 minutes", observation={"interval_minutes": 15}),
            [condition("Every 60 minutes", observation={"interval_minutes": 60})],
        )
    elif mechanism == "missing":
        comparator, variants = (
            condition("No missing oxygenation", observation={"missing_probability": 0}),
            [condition("50% missing oxygenation", observation={"missing_probability": 0.5})],
        )
    elif mechanism == "timing":
        comparator, variants = (
            condition("Accurate timestamps", documentation={"timestamp_offset_minutes": 0}),
            [
                condition(
                    "FiO2 recorded +15 minutes", documentation={"timestamp_offset_minutes": 15}
                )
            ],
        )
    elif mechanism == "baseline_density":
        window = {
            "baseline_exposure_minutes": 360,
            "baseline_start_offset_minutes": 15 if historical else 1080,
        }
        comparator = condition(
            "Fixed window every 15 minutes", observation={**window, "baseline_interval_minutes": 15}
        )
        variants = [
            condition(
                "Fixed window every 60 minutes",
                observation={**window, "baseline_interval_minutes": 60},
            )
        ]
    elif mechanism == "history":
        end = 1800 if historical else 1440
        comparator = condition(
            "6h history, matched end",
            observation={
                "baseline_start_offset_minutes": end - 360,
                "baseline_exposure_minutes": 360,
            },
        )
        variants = [
            condition(
                "24h history, matched end",
                observation={
                    "baseline_start_offset_minutes": end - 1440,
                    "baseline_exposure_minutes": 1440,
                },
            )
        ]
    elif mechanism == "alignment":
        comparator = condition(
            "6h within scoring day",
            observation={
                "baseline_exposure_minutes": 360,
                "baseline_start_offset_minutes": 15 if historical else 1080,
            },
        )
        variants = [
            condition(
                "6h across scoring-day boundary",
                observation={
                    "baseline_exposure_minutes": 360,
                    "baseline_start_offset_minutes": 1260 if historical else 900,
                },
            )
        ]
    else:
        comparator = condition("Declared base rules")
        changes = (
            [
                ("Maximum baseline", {"baseline_selection": "all_eligible_max"}),
                ("Admission floor bins", {"binning": "admission"}),
            ]
            if mechanism == "rules_baseline"
            else [
                ("No singleton suppression", {"single_record_suppression": False}),
                ("Expanded support", {"support_eligibility": "expanded"}),
                ("Contemporaneous FiO2", {"lookup": "contemporaneous_first"}),
                ("As-of evidence", {"availability": "as_of"}),
            ]
        )
        variants = [condition(label, scoring=change) for label, change in changes]
    outcome = next(e["primary_outcome"] for e in metadata_entries() if e["id"] == entry_id)
    return normalize_experiment_request(
        {
            "schema_version": V3,
            "experiment_id": f"{entry_id}:{stratum}",
            "base": scenario.to_dict(),
            "comparator": comparator,
            "conditions": variants,
            "replicates": replicates,
            "seed": seed,
            "primary_outcome": outcome,
            "nonrespiratory_contribution": "0",
        }
    )
