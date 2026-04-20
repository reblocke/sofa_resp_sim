from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from itertools import product

import numpy as np
import pandas as pd

from .resp_scoring import RespScoringConfig, score_respiratory
from .resp_utils import oracle_round


@dataclass(frozen=True)
class SupportPolicy:
    room_air_threshold: float = 94.0
    low_flow_threshold: float = 90.0
    hfnc_threshold: float = 85.0
    nippv_threshold: float = 80.0

    def classify(self, spo2_value: float | int | None) -> str:
        if spo2_value is None or (isinstance(spo2_value, float) and np.isnan(spo2_value)):
            return "ROOM_AIR"
        if spo2_value >= self.room_air_threshold:
            return "ROOM_AIR"
        if spo2_value >= self.low_flow_threshold:
            return "LOW_FLOW"
        if spo2_value >= self.hfnc_threshold:
            return "HFNC"
        if spo2_value >= self.nippv_threshold:
            return "NIPPV"
        return "IMV"


@dataclass(frozen=True)
class SimulationConfig:
    admit_dts: pd.Timestamp
    acute_start_hours: float = -6.0
    acute_end_hours: float = 24.0
    obs_freq_minutes: int = 15
    include_baseline: bool = False
    baseline_days_before: int = 30
    baseline_duration_hours: float = 6.0
    spo2_mean: float = 96.0
    spo2_sd: float = 1.5
    ar1: float = 0.6
    desat_prob: float = 0.01
    desat_depth: float = 5.0
    desat_duration_minutes: int = 30
    measurement_sd: float = 1.0
    spo2_rounding: str = "int"
    support_policy: SupportPolicy = field(default_factory=SupportPolicy)
    fio2_settings: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "HFNC": (40.0, 5.0),
            "NIPPV": (50.0, 5.0),
            "IMV": (60.0, 8.0),
        }
    )
    fio2_meas_prob: float = 0.2
    oxygen_flow_range: tuple[float, float] = (2.0, 6.0)
    support_based_on_observed: bool = True
    altitude_factor: float = 0.85


def simulate_encounter(config: SimulationConfig, rng: np.random.Generator) -> pd.DataFrame:
    acute_df = _simulate_block(
        config,
        rng,
        start=config.admit_dts + pd.Timedelta(hours=config.acute_start_hours),
        end=config.admit_dts + pd.Timedelta(hours=config.acute_end_hours),
    )

    if not config.include_baseline:
        return acute_df

    baseline_start = config.admit_dts - pd.Timedelta(days=config.baseline_days_before)
    baseline_end = baseline_start + pd.Timedelta(hours=config.baseline_duration_hours)
    baseline_df = _simulate_block(
        config,
        rng,
        start=baseline_start,
        end=baseline_end,
    )

    return (
        pd.concat([baseline_df, acute_df], ignore_index=True)
        .sort_values("etime_ts")
        .reset_index(drop=True)
    )


def run_replicates(
    config: SimulationConfig,
    n_reps: int,
    seed: int = 0,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    results: list[dict[str, float | int | str]] = []
    scoring_config = RespScoringConfig(altitude_factor=config.altitude_factor)
    for rep in range(n_reps):
        rep_seed = int(rng.integers(0, 2**32 - 1))
        rep_rng = np.random.default_rng(rep_seed)
        obs = simulate_encounter(config, rep_rng)
        scoring = score_respiratory(obs, config.admit_dts, scoring_config)
        results.append(
            {
                "replicate": rep,
                "seed": rep_seed,
                "sofa_pulm": scoring.sofa_pulm,
                "sofa_pulm_bl": scoring.sofa_pulm_bl,
                "sofa_pulm_delta": scoring.sofa_pulm_delta,
                "count_pf_ratio_acute": scoring.count_pf_ratio_acute,
                "n_qualifying_pf_records_acute": scoring.n_qualifying_pf_records_acute,
                "n_qualifying_pf_records_baseline": scoring.n_qualifying_pf_records_baseline,
                "single_pf_suppressed": scoring.single_pf_suppressed,
            }
        )
    return pd.DataFrame(results)


def run_parameter_sweep(
    base_config: SimulationConfig,
    obs_freq_minutes: Iterable[int],
    noise_sd: Iterable[float],
    room_air_thresholds: Iterable[float],
    n_reps: int,
    seed: int = 0,
    return_replicates: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    rng = np.random.default_rng(seed)
    summary_rows: list[dict[str, float | int]] = []
    replicate_frames: list[pd.DataFrame] = []

    for obs_freq, noise, room_air in product(obs_freq_minutes, noise_sd, room_air_thresholds):
        policy = SupportPolicy(
            room_air_threshold=room_air,
            low_flow_threshold=room_air - 4,
            hfnc_threshold=room_air - 8,
            nippv_threshold=room_air - 12,
        )
        config = replace(
            base_config,
            obs_freq_minutes=obs_freq,
            measurement_sd=noise,
            support_policy=policy,
        )
        rep_seed = int(rng.integers(0, 2**32 - 1))
        replicates = run_replicates(config, n_reps=n_reps, seed=rep_seed)
        if return_replicates:
            replicates = replicates.assign(
                obs_freq_minutes=obs_freq,
                noise_sd=noise,
                room_air_threshold=room_air,
            )
            replicate_frames.append(replicates)
        summary_rows.append(_summarize_replicates(replicates, obs_freq, noise, room_air))

    summary_df = pd.DataFrame(summary_rows)
    full_replicates = pd.concat(replicate_frames, ignore_index=True) if return_replicates else None
    return summary_df, full_replicates


def _simulate_block(
    config: SimulationConfig,
    rng: np.random.Generator,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    times = pd.date_range(start=start, end=end, freq=f"{config.obs_freq_minutes}min")
    n = len(times)
    spo2_true = _generate_spo2_true(n, config, rng)
    spo2_obs = _apply_measurement_noise(spo2_true, config, rng)

    basis = spo2_obs if config.support_based_on_observed else spo2_true
    support_categories = [config.support_policy.classify(val) for val in basis]
    support_fields = [_support_fields(cat, config, rng) for cat in support_categories]
    support_df = pd.DataFrame(support_fields)

    return pd.DataFrame(
        {
            "etime_ts": times,
            "spo2_obs": spo2_obs,
            "spo2_true": spo2_true,
        }
    ).join(support_df)


def _generate_spo2_true(
    n: int,
    config: SimulationConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    values = np.empty(n)
    values[0] = rng.normal(config.spo2_mean, config.spo2_sd)
    desat_steps_remaining = 0
    desat_steps = max(1, int(config.desat_duration_minutes / config.obs_freq_minutes))
    for i in range(1, n):
        innovation = rng.normal(0, config.spo2_sd)
        values[i] = config.spo2_mean + config.ar1 * (values[i - 1] - config.spo2_mean) + innovation
        if desat_steps_remaining > 0:
            values[i] -= config.desat_depth
            desat_steps_remaining -= 1
        elif rng.random() < config.desat_prob:
            values[i] -= config.desat_depth
            desat_steps_remaining = desat_steps - 1
    return np.clip(values, 0, 100)


def _apply_measurement_noise(
    spo2_true: np.ndarray,
    config: SimulationConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    noisy = spo2_true + rng.normal(0, config.measurement_sd, size=spo2_true.shape)
    noisy = np.clip(noisy, 0, 100)
    if config.spo2_rounding == "int":
        return np.array([oracle_round(val, 0) for val in noisy])
    if config.spo2_rounding == "one_decimal":
        return np.array([oracle_round(val, 1) for val in noisy])
    return noisy


def _support_fields(
    category: str,
    config: SimulationConfig,
    rng: np.random.Generator,
) -> dict[str, float | str | None | bool]:
    fio2_set = np.nan
    fio2_meas = np.nan
    oxygen_flow_rate = np.nan
    support_type = None
    is_room_air = False

    if category == "ROOM_AIR":
        is_room_air = True
    elif category == "LOW_FLOW":
        oxygen_flow_rate = float(rng.uniform(*config.oxygen_flow_range))
    else:
        support_type = category
        mean, sd = config.fio2_settings.get(category, (40.0, 5.0))
        fio2_value = _sample_fio2(mean, sd, rng)
        if rng.random() < config.fio2_meas_prob:
            fio2_meas = fio2_value
        else:
            fio2_set = fio2_value

    return {
        "support_type": support_type,
        "is_room_air": is_room_air,
        "oxygen_flow_rate": oxygen_flow_rate,
        "fio2_set": fio2_set,
        "fio2_meas": fio2_meas,
        "fio2_abg": np.nan,
    }


def _sample_fio2(mean: float, sd: float, rng: np.random.Generator) -> float:
    value = rng.normal(mean, sd)
    return float(np.clip(value, 21, 100))


def _summarize_replicates(
    replicates: pd.DataFrame,
    obs_freq: int,
    noise_sd: float,
    room_air_threshold: float,
) -> dict[str, float | int]:
    counts = replicates["sofa_pulm"].value_counts().to_dict()
    total = len(replicates)
    summary = {
        "obs_freq_minutes": obs_freq,
        "noise_sd": noise_sd,
        "room_air_threshold": room_air_threshold,
        "n_reps": total,
        "mean_count_pf_ratio_acute": float(replicates["count_pf_ratio_acute"].mean()),
        "p_single_pf_suppressed": float(replicates["single_pf_suppressed"].mean()),
    }
    for score in range(0, 5):
        summary[f"p_sofa_{score}"] = counts.get(score, 0) / total if total else 0
    return summary
