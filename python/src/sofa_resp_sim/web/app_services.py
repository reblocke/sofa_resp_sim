from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

import numpy as np
import pandas as pd

from ..resp_simulation import (
    SimulationConfig,
    SupportPolicy,
    run_parameter_sweep,
    run_replicates,
)
from .reference import REQUIRED_PROBABILITY_COLUMNS
from .view_model import (
    SWEEP_HEATMAP_METRICS,
    AppletRunRequest,
    AppletSweepRequest,
    derive_support_thresholds,
    estimate_total_sweep_runs,
    normalize_request,
    normalize_sweep_request,
)

APPLET_CODE_VERSION = "m3-v1"
DEFAULT_CI_LEVEL = 0.95
DEFAULT_BOOTSTRAP_SAMPLES = 1000
DEFAULT_SWEEP_GUARDRAIL_RUNS = 50_000
JENSEN_SHANNON_EPSILON = 1e-12

SUMMARY_COLUMNS = [
    "obs_freq_minutes",
    "noise_sd",
    "room_air_threshold",
    "n_reps",
    "mean_count_pf_ratio_acute",
    "p_single_pf_suppressed",
    "p_sofa_0",
    "p_sofa_1",
    "p_sofa_2",
    "p_sofa_3",
    "p_sofa_4",
]

SWEEP_SUMMARY_EXPORT_COLUMNS = [
    *SUMMARY_COLUMNS,
    "p_sofa_3plus",
]

SWEEP_REPLICATE_EXPORT_COLUMNS = [
    "obs_freq_minutes",
    "noise_sd",
    "room_air_threshold",
    "replicate",
    "seed",
    "sofa_pulm",
    "sofa_pulm_bl",
    "sofa_pulm_delta",
    "count_pf_ratio_acute",
    "n_qualifying_pf_records_acute",
    "n_qualifying_pf_records_baseline",
    "single_pf_suppressed",
]

UNCERTAINTY_COLUMNS = [
    "score",
    "p_scenario",
    "ci_lower",
    "ci_upper",
    "p_reference",
    "delta_vs_reference",
]


def build_simulation_config(request: AppletRunRequest) -> SimulationConfig:
    normalized = normalize_request(request)
    room_air, low_flow, hfnc, nippv = derive_support_thresholds(
        normalized.room_air_threshold
    )
    policy = SupportPolicy(
        room_air_threshold=room_air,
        low_flow_threshold=low_flow,
        hfnc_threshold=hfnc,
        nippv_threshold=nippv,
    )

    return SimulationConfig(
        admit_dts=normalized.admit_dts,
        acute_start_hours=normalized.acute_start_hours,
        acute_end_hours=normalized.acute_end_hours,
        obs_freq_minutes=normalized.obs_freq_minutes,
        include_baseline=normalized.include_baseline,
        baseline_days_before=normalized.baseline_days_before,
        baseline_duration_hours=normalized.baseline_duration_hours,
        spo2_mean=normalized.spo2_mean,
        spo2_sd=normalized.spo2_sd,
        ar1=normalized.ar1,
        desat_prob=normalized.desat_prob,
        desat_depth=normalized.desat_depth,
        desat_duration_minutes=normalized.desat_duration_minutes,
        measurement_sd=normalized.measurement_sd,
        spo2_rounding=normalized.spo2_rounding,
        support_policy=policy,
        fio2_meas_prob=normalized.fio2_meas_prob,
        oxygen_flow_range=(normalized.oxygen_flow_min, normalized.oxygen_flow_max),
        support_based_on_observed=normalized.support_based_on_observed,
        altitude_factor=normalized.altitude_factor,
    )


def run_single_scenario(request: AppletRunRequest) -> tuple[pd.DataFrame, pd.DataFrame]:
    normalized = normalize_request(request)
    config = build_simulation_config(normalized)
    replicates = run_replicates(config=config, n_reps=normalized.n_reps, seed=normalized.seed)
    summary = _summarize_replicates(replicates, normalized)
    return summary, replicates


def run_sweep_scenario(
    request: AppletSweepRequest,
    return_replicates: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    normalized = normalize_sweep_request(request)
    total_runs = estimate_total_sweep_runs(normalized)
    combinations = (
        len(normalized.obs_freq_minutes_values)
        * len(normalized.noise_sd_values)
        * len(normalized.room_air_threshold_values)
    )
    if total_runs > DEFAULT_SWEEP_GUARDRAIL_RUNS:
        raise ValueError(
            "Sweep workload exceeds guardrail "
            f"({total_runs} runs > {DEFAULT_SWEEP_GUARDRAIL_RUNS}). "
            f"Combinations={combinations}, n_reps={normalized.base_request.n_reps}."
        )

    base_config = build_simulation_config(normalized.base_request)
    summary_df, replicate_df_or_none = run_parameter_sweep(
        base_config=base_config,
        obs_freq_minutes=normalized.obs_freq_minutes_values,
        noise_sd=normalized.noise_sd_values,
        room_air_thresholds=normalized.room_air_threshold_values,
        n_reps=normalized.base_request.n_reps,
        seed=normalized.base_request.seed,
        return_replicates=return_replicates,
    )

    summary_df = add_sweep_derived_metrics(summary_df)
    if return_replicates and replicate_df_or_none is not None:
        replicate_df = replicate_df_or_none
    else:
        replicate_df = pd.DataFrame(columns=SWEEP_REPLICATE_EXPORT_COLUMNS)

    return summary_df, replicate_df


def add_sweep_derived_metrics(summary_df: pd.DataFrame) -> pd.DataFrame:
    required_columns = {"p_sofa_3", "p_sofa_4"}
    missing = [column for column in required_columns if column not in summary_df.columns]
    if missing:
        raise ValueError(
            "Sweep summary is missing required columns for derived metrics: "
            + ", ".join(sorted(missing))
        )

    augmented = summary_df.copy()
    augmented["p_sofa_3plus"] = augmented["p_sofa_3"] + augmented["p_sofa_4"]
    return augmented


def format_sweep_summary_for_export(summary_df: pd.DataFrame) -> pd.DataFrame:
    augmented = add_sweep_derived_metrics(summary_df)

    ordered_columns = [
        column for column in SWEEP_SUMMARY_EXPORT_COLUMNS if column in augmented.columns
    ]
    remaining_columns = [
        column for column in augmented.columns if column not in ordered_columns
    ]

    formatted = augmented.loc[:, ordered_columns + remaining_columns].copy()
    sort_columns = [
        column
        for column in ["obs_freq_minutes", "noise_sd", "room_air_threshold"]
        if column in formatted.columns
    ]
    if sort_columns:
        formatted = formatted.sort_values(sort_columns).reset_index(drop=True)
    return formatted


def format_sweep_replicates_for_export(replicates_df: pd.DataFrame) -> pd.DataFrame:
    if replicates_df.empty:
        return pd.DataFrame(columns=SWEEP_REPLICATE_EXPORT_COLUMNS)

    formatted = replicates_df.copy()
    for column in SWEEP_REPLICATE_EXPORT_COLUMNS:
        if column not in formatted.columns:
            formatted[column] = np.nan

    remaining_columns = [
        column for column in formatted.columns if column not in SWEEP_REPLICATE_EXPORT_COLUMNS
    ]
    formatted = formatted.loc[:, SWEEP_REPLICATE_EXPORT_COLUMNS + remaining_columns]
    formatted = formatted.sort_values(
        ["obs_freq_minutes", "noise_sd", "room_air_threshold", "replicate"]
    ).reset_index(drop=True)
    return formatted


def build_sweep_heatmap_frame(summary_df: pd.DataFrame, metric: str) -> pd.DataFrame:
    if metric not in SWEEP_HEATMAP_METRICS:
        raise ValueError(f"metric must be one of {SWEEP_HEATMAP_METRICS}.")

    augmented = add_sweep_derived_metrics(summary_df)
    required = ["room_air_threshold", "obs_freq_minutes", "noise_sd", metric]
    missing = [column for column in required if column not in augmented.columns]
    if missing:
        raise ValueError(
            "Sweep summary is missing required heatmap columns: "
            + ", ".join(sorted(missing))
        )

    heatmap_frame = (
        augmented.loc[:, required]
        .rename(columns={metric: "metric_value"})
        .sort_values(["room_air_threshold", "obs_freq_minutes", "noise_sd"])
        .reset_index(drop=True)
    )
    return heatmap_frame


def extract_sofa_probabilities(replicates: pd.DataFrame) -> pd.Series:
    if "sofa_pulm" not in replicates.columns:
        raise ValueError("replicates must include a 'sofa_pulm' column.")
    if replicates.empty:
        raise ValueError("replicates must contain at least one row.")

    scores = pd.to_numeric(replicates["sofa_pulm"], errors="coerce")
    if scores.isna().any():
        raise ValueError("sofa_pulm values must be numeric.")
    if ((scores < 0) | (scores > 4)).any():
        raise ValueError("sofa_pulm values must be in [0, 4].")

    counts = scores.astype(int).value_counts().reindex(range(5), fill_value=0).astype(float)
    total = float(counts.sum())
    if total <= 0:
        raise ValueError("replicates must contain at least one valid sofa_pulm record.")

    probabilities = counts / total
    probabilities.index = REQUIRED_PROBABILITY_COLUMNS
    return probabilities


def compute_divergence_metrics(
    scenario_probs: pd.Series,
    reference_probs: pd.Series,
) -> dict[str, float]:
    scenario = _coerce_probability_series(scenario_probs, "scenario_probs")
    reference = _coerce_probability_series(reference_probs, "reference_probs")

    l1_distance = float(np.abs(scenario - reference).sum())
    js_distance = _jensen_shannon_distance(
        scenario.to_numpy(dtype=float),
        reference.to_numpy(dtype=float),
    )

    return {
        "l1_distance": l1_distance,
        "jensen_shannon_distance": js_distance,
    }


def bootstrap_sofa_probability_ci(
    replicates: pd.DataFrame,
    n_bootstrap: int = DEFAULT_BOOTSTRAP_SAMPLES,
    ci_level: float = DEFAULT_CI_LEVEL,
    seed: int = 0,
) -> pd.DataFrame:
    if n_bootstrap < 1:
        raise ValueError("n_bootstrap must be >= 1.")
    if not (0 < ci_level < 1):
        raise ValueError("ci_level must be between 0 and 1.")
    if seed < 0:
        raise ValueError("seed must be >= 0.")

    probabilities = extract_sofa_probabilities(replicates)
    scores = pd.to_numeric(replicates["sofa_pulm"], errors="coerce")
    score_values = scores.astype(int).to_numpy()

    n_rows = score_values.shape[0]
    rng = np.random.default_rng(seed)
    bootstrap_probs = np.empty((n_bootstrap, 5), dtype=float)

    for bootstrap_idx in range(n_bootstrap):
        sampled_idx = rng.integers(0, n_rows, size=n_rows)
        sampled_scores = score_values[sampled_idx]
        counts = np.bincount(sampled_scores, minlength=5)[:5]
        bootstrap_probs[bootstrap_idx, :] = counts / n_rows

    lower_q = (1 - ci_level) / 2
    upper_q = 1 - lower_q
    ci_lower = np.quantile(bootstrap_probs, lower_q, axis=0)
    ci_upper = np.quantile(bootstrap_probs, upper_q, axis=0)
    scenario_values = np.array(
        [float(probabilities[f"p_sofa_{score}"]) for score in range(5)],
        dtype=float,
    )
    ci_lower = np.minimum(ci_lower, scenario_values)
    ci_upper = np.maximum(ci_upper, scenario_values)

    return pd.DataFrame(
        {
            "score": list(range(5)),
            "p_scenario": scenario_values,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
        }
    )


def build_uncertainty_table(
    replicates: pd.DataFrame,
    reference_probs: pd.Series,
    n_bootstrap: int = DEFAULT_BOOTSTRAP_SAMPLES,
    ci_level: float = DEFAULT_CI_LEVEL,
    seed: int = 0,
) -> pd.DataFrame:
    ci_table = bootstrap_sofa_probability_ci(
        replicates=replicates,
        n_bootstrap=n_bootstrap,
        ci_level=ci_level,
        seed=seed,
    )

    reference = _coerce_probability_series(reference_probs, "reference_probs")
    ci_table = ci_table.copy()
    ci_table["p_reference"] = [
        float(reference[f"p_sofa_{score}"])
        for score in ci_table["score"].astype(int).tolist()
    ]
    ci_table["delta_vs_reference"] = ci_table["p_scenario"] - ci_table["p_reference"]

    return ci_table.loc[:, UNCERTAINTY_COLUMNS]


def build_cache_key(request: AppletRunRequest, code_version: str = APPLET_CODE_VERSION) -> str:
    normalized = normalize_request(request)
    payload = {
        "code_version": code_version,
        "request": normalized.to_json_dict(),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_sweep_cache_key(
    request: AppletSweepRequest,
    code_version: str = APPLET_CODE_VERSION,
) -> str:
    normalized = normalize_sweep_request(request)
    payload = {
        "code_version": code_version,
        "sweep_request": normalized.to_json_dict(),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def serialize_request_payload(
    request: AppletRunRequest,
    code_version: str = APPLET_CODE_VERSION,
) -> str:
    normalized = normalize_request(request)
    payload: Mapping[str, object] = {
        "code_version": code_version,
        "request": normalized.to_json_dict(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def serialize_sweep_payload(
    request: AppletSweepRequest,
    code_version: str = APPLET_CODE_VERSION,
) -> str:
    normalized = normalize_sweep_request(request)
    payload: Mapping[str, object] = {
        "code_version": code_version,
        "sweep_request": normalized.to_json_dict(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def parse_request_payload(payload: str) -> AppletRunRequest:
    parsed = json.loads(payload)
    if "request" not in parsed:
        raise ValueError("Serialized request payload must include a 'request' field.")
    return normalize_request(parsed["request"])


def parse_sweep_payload(payload: str) -> AppletSweepRequest:
    parsed = json.loads(payload)
    if "sweep_request" not in parsed:
        raise ValueError("Serialized sweep payload must include a 'sweep_request' field.")
    return normalize_sweep_request(parsed["sweep_request"])


def _coerce_probability_series(values: pd.Series, name: str) -> pd.Series:
    if not isinstance(values, pd.Series):
        values = pd.Series(values)

    if all(column in values.index for column in REQUIRED_PROBABILITY_COLUMNS):
        ordered = pd.to_numeric(values.loc[REQUIRED_PROBABILITY_COLUMNS], errors="coerce")
    else:
        index_lookup = {str(idx): value for idx, value in values.items()}
        try:
            ordered = pd.Series(
                [
                    index_lookup[str(score)]
                    for score in range(5)
                ],
                index=REQUIRED_PROBABILITY_COLUMNS,
                dtype=float,
            )
        except KeyError as exc:
            raise ValueError(
                f"{name} must contain probability values for scores 0..4 or p_sofa_0..p_sofa_4."
            ) from exc
        ordered = pd.to_numeric(ordered, errors="coerce")

    if ordered.isna().any():
        raise ValueError(f"{name} contains non-numeric probability values.")
    if (ordered < 0).any():
        raise ValueError(f"{name} contains negative probability values.")

    total = float(ordered.sum())
    if total <= 0:
        raise ValueError(f"{name} must sum to a positive value.")

    normalized = (ordered / total).astype(float)
    normalized.index = REQUIRED_PROBABILITY_COLUMNS
    return normalized


def _jensen_shannon_distance(
    scenario: np.ndarray,
    reference: np.ndarray,
    epsilon: float = JENSEN_SHANNON_EPSILON,
) -> float:
    p = np.clip(scenario.astype(float), epsilon, None)
    q = np.clip(reference.astype(float), epsilon, None)
    p /= p.sum()
    q /= q.sum()

    m = 0.5 * (p + q)
    kl_pm = float(np.sum(p * np.log(p / m)))
    kl_qm = float(np.sum(q * np.log(q / m)))
    js_divergence = 0.5 * (kl_pm + kl_qm)

    if js_divergence < 0 and abs(js_divergence) < 1e-12:
        js_divergence = 0.0
    return float(np.sqrt(max(js_divergence, 0.0)))


def _summarize_replicates(
    replicates: pd.DataFrame,
    request: AppletRunRequest,
) -> pd.DataFrame:
    probabilities = extract_sofa_probabilities(replicates)

    summary: dict[str, float | int] = {
        "obs_freq_minutes": request.obs_freq_minutes,
        "noise_sd": request.measurement_sd,
        "room_air_threshold": request.room_air_threshold,
        "n_reps": int(len(replicates)),
        "mean_count_pf_ratio_acute": float(replicates["count_pf_ratio_acute"].mean()),
        "p_single_pf_suppressed": float(replicates["single_pf_suppressed"].mean()),
    }
    for score in range(5):
        summary[f"p_sofa_{score}"] = float(probabilities[f"p_sofa_{score}"])

    return pd.DataFrame([summary], columns=SUMMARY_COLUMNS)
