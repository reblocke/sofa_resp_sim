"""Finite, prespecified illustrative experiments; never a population-weighted mixture."""

from __future__ import annotations

from copy import deepcopy

from ..core.experiment_config import SCHEMA_VERSION, ScenarioConfig
from .experiment_request import normalize_experiment_request

CATALOGUE_VERSION = "illustrative_catalogue_v2.1"
REFERENCE_N = 2000
REFERENCE_SEED = 173203
STRATA = {
    "room_air": {"label": "ROOM_AIR", "fio2_fraction": 0.21, "flow_lpm": None},
    "low_flow": {"label": "LOW_FLOW", "fio2_fraction": None, "flow_lpm": 4},
    "hfnc": {"label": "HFNC", "fio2_fraction": 0.4, "flow_lpm": None},
    "imv": {"label": "IMV", "fio2_fraction": 0.5, "flow_lpm": None},
}


def condition(label, **overrides):
    return {"label": label, "overrides": overrides}


def _entry(
    experiment,
    title,
    mechanism,
    base,
    comparator,
    conditions,
    *,
    outcome="score_ge2",
    deterministic=False,
    limitation="",
):
    return {
        "experiment": experiment,
        "title": title,
        "mechanism": mechanism,
        "base_overrides": base,
        "comparator": comparator,
        "conditions": conditions,
        "primary_outcome": outcome,
        "deterministic": deterministic,
        "held_fixed": (
            "Within a comparison: patient IDs, generator and all settings not explicitly "
            "overridden."
        ),
        "limitations": "Uncalibrated illustrative simulation; strata have no population weights. "
        + limitation,
    }


CATALOGUE = {
    "E1_density": _entry(
        "E1",
        "Observation density",
        "SpO2 sampling interval",
        {},
        condition("15 minutes", observation={"interval_minutes": 15}),
        [condition(f"{n} minutes", observation={"interval_minutes": n}) for n in (5, 30, 60)],
        limitation="Denser sampling need not increase every encounter score.",
    ),
    "E1_episode": _entry(
        "E1",
        "Deterministic sampling opportunity",
        "SpO2 sampling interval",
        {
            "generator": {
                "mean_pct": 96,
                "marginal_sd_pct": 0,
                "episode_rate_per_hour": 0,
                "prescribed_episodes": [
                    {"start_minute": 30, "end_minute": 60, "depth_pct_points": 5}
                ],
            },
            "horizon": {"start_minute": 0, "end_minute": 120},
            "observation": {"noise_sd_pct": 0},
        },
        condition("15 minutes", observation={"interval_minutes": 15}),
        [condition(f"{n} minutes", observation={"interval_minutes": n}) for n in (5, 30, 60)],
        deterministic=True,
    ),
    "E2_noise": _entry(
        "E2",
        "Measurement noise",
        "Measurement noise SD",
        {},
        condition("SD 0", observation={"noise_sd_pct": 0}),
        [condition(f"SD {n}", observation={"noise_sd_pct": n}) for n in (0.5, 1, 2)],
    ),
    "E2_bias": _entry(
        "E2",
        "Measurement bias",
        "Additive measurement bias",
        {},
        condition("Bias 0", observation={"bias_pct_points": 0}),
        [condition(f"Bias {n:+}", observation={"bias_pct_points": n}) for n in (-2, 2)],
    ),
    "E2_rounding": _entry(
        "E2",
        "Measurement rounding",
        "Documented saturation rounding",
        {},
        condition("No rounding", observation={"rounding": "none"}),
        [
            condition(label, observation={"rounding": mode})
            for label, mode in [("One decimal", "one_decimal"), ("Integer", "integer")]
        ],
    ),
    "E2_assignment": _entry(
        "E2",
        "Support assignment stress test",
        "Support assignment policy",
        {},
        condition("Fixed support", support={"mode": "fixed"}),
        [
            condition(
                "Assignment stress test",
                support={
                    "mode": "assignment_stress_test",
                    "thresholds_pct": [94, 90, 86, 82],
                    "based_on_observed": True,
                },
            )
        ],
        limitation=(
            "The stratum identifies the fixed comparator only. Stress assignment can "
            "cross support categories and is not treatment physiology."
        ),
    ),
    "E3_missing": _entry(
        "E3",
        "Missing FiO2 evidence",
        "Whole denominator evidence bundle missingness",
        {},
        condition("Complete documentation", documentation={"missing_probability": 0}),
        [
            condition(f"Missing {n:g}", documentation={"missing_probability": n})
            for n in (0.25, 0.5, 1)
        ],
        outcome="no_qualifying_data",
    ),
    "E3_timing": _entry(
        "E3",
        "Documentation timestamp boundaries",
        "Documented FiO2 timestamp error",
        {"documentation": {"interval_minutes": 60}},
        condition("Offset 0", documentation={"timestamp_offset_minutes": 0}),
        [
            condition(f"Offset {n:g} minutes", documentation={"timestamp_offset_minutes": n})
            for n in (-14.001, -14, -1, 5, 5.001)
        ],
        outcome="no_qualifying_data",
        limitation="Timestamp error differs from record availability delay.",
    ),
    "E3_sources": _entry(
        "E3",
        "FiO2 source disagreement",
        "Measured/set source disagreement",
        {"documentation": {"measured_source_probability": 0}},
        condition("No disagreement", documentation={"disagreement_fraction": 0}),
        [condition("Measured source +0.1", documentation={"disagreement_fraction": 0.1})],
        limitation=(
            "Room-air and low-flow proxies do not acquire known delivered FiO2 from this setting."
        ),
    ),
    "E3_stale": _entry(
        "E3",
        "Stale FiO2 documentation",
        "Age of documented denominator value",
        {},
        condition("Current value", documentation={"stale_minutes": 0}),
        [condition("30-minute-old value", documentation={"stale_minutes": 30})],
        limitation=(
            "Prescribed support/FiO2 step demonstrates stale values; room air is an inert control."
        ),
    ),
    "E3_labels": _entry(
        "E3",
        "FiO2 source-label control",
        "Identical values labeled measured versus set",
        {},
        condition(
            "Set source",
            documentation={"measured_source_probability": 0, "disagreement_fraction": 0},
        ),
        [
            condition(
                "Measured source",
                documentation={"measured_source_probability": 1, "disagreement_fraction": 0},
            )
        ],
        limitation=(
            "Identical values without conflict change provenance only; room-air/flow "
            "sources are unaffected."
        ),
    ),
    "E3_zero": _entry(
        "E3",
        "Zero-perturbation control",
        "Explicit zero documentation perturbations",
        {},
        condition("Original"),
        [
            condition(
                "Explicit zeros",
                documentation={
                    "missing_probability": 0,
                    "timestamp_offset_minutes": 0,
                    "stale_minutes": 0,
                    "disagreement_fraction": 0,
                    "recorded_delay_minutes": 0,
                },
            )
        ],
        limitation="Identical normalized configurations share scientific rows by construction.",
    ),
    "E4_estimated": _entry(
        "E4",
        "Threshold factors with estimated PaO2",
        "Scoring threshold factor",
        {"observation": {"measured_pao2_mmhg": None}},
        condition("Factor 1", scoring={"threshold_factor": 1}),
        [condition(f"Factor {n}", scoring={"threshold_factor": n}) for n in (0.85, 0.75)],
        limitation=(
            "Threshold scaling changes neither PaO2 nor P/F and implies no altitude in metres."
        ),
    ),
    "E4_measured": _entry(
        "E4",
        "Threshold factors with measured PaO2",
        "Scoring threshold factor",
        {"observation": {"measured_pao2_mmhg": 84}},
        condition("Factor 1", scoring={"threshold_factor": 1}),
        [condition(f"Factor {n}", scoring={"threshold_factor": n}) for n in (0.85, 0.75)],
        limitation=(
            "Fixed illustrative PaO2=84 mmHg; threshold scaling is not physiological "
            "altitude response."
        ),
    ),
    "E5_opportunity": _entry(
        "E5",
        "Independent stationary baseline opportunity",
        "Baseline exposure and observation interval",
        {
            "generator": {"episode_rate_per_hour": 0},
            "horizon": {"include_baseline": True},
            "observation": {"interval_minutes": 15},
        },
        condition(
            "24h every 15 minutes",
            observation={"baseline_exposure_minutes": 1440, "baseline_interval_minutes": 15},
        ),
        [
            condition(
                f"{hours}h every {interval} minutes",
                observation={
                    "baseline_exposure_minutes": hours * 60,
                    "baseline_interval_minutes": interval,
                },
            )
            for hours in (1, 6, 24)
            for interval in (15, 60)
            if (hours, interval) != (24, 15)
        ],
        outcome="delta_legacy_ge1",
        limitation=(
            "Independent stationary blocks can have different extrema without "
            "deterioration. Delta is not sepsis incidence."
        ),
    ),
    "E5_replay": _entry(
        "E5",
        "Six-hour exact replay control",
        "No change: identical six-hour exposure and rules",
        {
            "generator": {"episode_rate_per_hour": 0},
            "horizon": {
                "admit_dts": "2024-01-01T06:00:00Z",
                "include_baseline": True,
                "baseline_replay": True,
                "end_minute": 360,
                "baseline_generation_minutes": 360,
            },
            "observation": {
                "noise_sd_pct": 0,
                "baseline_exposure_minutes": 360,
                "baseline_interval_minutes": 15,
            },
            "documentation": {"interval_minutes": 15, "measured_source_probability": 0},
            "scoring": {"acute_begin_minute": 0, "acute_end_minute": 360},
        },
        condition("Six-hour replay"),
        [condition("Identical replay")],
        outcome="delta_legacy_ge1",
        limitation=(
            "Same full segment at the same UTC time of day within one date, "
            "contemporaneous FiO2 and at least two records; only this construction "
            "promises zero delta."
        ),
    ),
    "E6_rules": _entry(
        "E6",
        "Rule contribution",
        "One scoring rule at a time",
        {"horizon": {"include_baseline": True}, "documentation": {"recorded_delay_minutes": 5}},
        condition("Declared base rules"),
        [
            condition(label, scoring=override)
            for label, override in [
                ("No singleton suppression", {"single_record_suppression": False}),
                ("Expanded support gates", {"support_eligibility": "expanded"}),
                ("Contemporaneous first", {"lookup": "contemporaneous_first"}),
                ("As-of availability", {"availability": "as_of"}),
                ("Measured only", {"conversion": "measured_only"}),
                ("Maximum eligible baseline", {"baseline_selection": "all_eligible_max"}),
                ("Admission bins", {"binning": "admission"}),
            ]
        ],
        limitation=(
            "Rules interact; contrasts are not additive attribution. Mechanism fixtures "
            "separately cover inactive rules in dense records."
        ),
    ),
    "E6_singleton": _entry(
        "E6",
        "Singleton suppression mechanism",
        "Single-record suppression",
        {"horizon": {"end_minute": 1}, "observation": {"interval_minutes": 15}},
        condition("Suppression enabled"),
        [condition("Suppression disabled", scoring={"single_record_suppression": False})],
    ),
}


def catalogue_metadata() -> dict:
    return {
        "version": CATALOGUE_VERSION,
        "reference_n_per_stratum": REFERENCE_N,
        "reference_seed": REFERENCE_SEED,
        "strata": list(STRATA),
        "entries": [{"id": key, **deepcopy(value)} for key, value in CATALOGUE.items()],
    }


def catalogue_request(
    entry_id: str, stratum: str, *, replicates=200, seed=REFERENCE_SEED, base: dict | None = None
):
    if entry_id not in CATALOGUE or stratum not in STRATA:
        raise ValueError("Unknown catalogue entry or support stratum")
    entry = CATALOGUE[entry_id]
    # An edited base is authoritative; expand only the declared comparison overrides.
    scenario = (
        ScenarioConfig.from_dict({})
        .override(
            {
                "horizon": {"start_minute": 0},
                "observation": {"start_minute": 0},
                "support": STRATA[stratum],
            }
        )
        .override(entry["base_overrides"])
        if base is None
        else ScenarioConfig.from_dict(base)
    )
    if base is None and entry_id == "E3_stale" and stratum != "room_air":
        support = STRATA[stratum]
        second = (
            {**support, "flow_lpm": 6}
            if stratum == "low_flow"
            else {**support, "fio2_fraction": 0.6}
        )
        scenario = scenario.override(
            {
                "support": {
                    "segments": [
                        {"start_minute": 45, "end_minute": scenario.horizon.end_minute, **second}
                    ]
                }
            }
        )
    return normalize_experiment_request(
        {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": f"{entry_id}:{stratum}",
            "base": scenario.to_dict(),
            "comparator": entry["comparator"],
            "conditions": entry["conditions"],
            "replicates": 1 if entry["deterministic"] else replicates,
            "seed": seed,
            "primary_outcome": entry["primary_outcome"],
        }
    )
