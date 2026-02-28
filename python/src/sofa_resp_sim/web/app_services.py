from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

import numpy as np
import pandas as pd

from ..resp_simulation import SimulationConfig, SupportPolicy, run_replicates
from .reference import REQUIRED_PROBABILITY_COLUMNS
from .view_model import AppletRunRequest, derive_support_thresholds, normalize_request

APPLET_CODE_VERSION = "m2-v1"
DEFAULT_CI_LEVEL = 0.95
DEFAULT_BOOTSTRAP_SAMPLES = 1000
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


def parse_request_payload(payload: str) -> AppletRunRequest:
    parsed = json.loads(payload)
    if "request" not in parsed:
        raise ValueError("Serialized request payload must include a 'request' field.")
    return normalize_request(parsed["request"])


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
