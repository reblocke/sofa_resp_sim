from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

import pandas as pd

from ..resp_simulation import SimulationConfig, SupportPolicy, run_replicates
from .view_model import AppletRunRequest, derive_support_thresholds, normalize_request

APPLET_CODE_VERSION = "m1-v1"
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


def _summarize_replicates(
    replicates: pd.DataFrame,
    request: AppletRunRequest,
) -> pd.DataFrame:
    counts = replicates["sofa_pulm"].value_counts().to_dict()
    total = len(replicates)
    summary: dict[str, float | int] = {
        "obs_freq_minutes": request.obs_freq_minutes,
        "noise_sd": request.measurement_sd,
        "room_air_threshold": request.room_air_threshold,
        "n_reps": total,
        "mean_count_pf_ratio_acute": float(replicates["count_pf_ratio_acute"].mean()),
        "p_single_pf_suppressed": float(replicates["single_pf_suppressed"].mean()),
    }
    for score in range(5):
        summary[f"p_sofa_{score}"] = counts.get(score, 0) / total if total else 0.0

    return pd.DataFrame([summary], columns=SUMMARY_COLUMNS)
