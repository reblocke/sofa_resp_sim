from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

SPO2_ROUNDING_OPTIONS = ("int", "one_decimal", "raw")
SWEEP_HEATMAP_METRICS = ("p_sofa_3plus", "p_sofa_4", "mean_count_pf_ratio_acute")
DEFAULT_SWEEP_HEATMAP_METRIC = "p_sofa_3plus"


@dataclass(frozen=True)
class AppletRunRequest:
    admit_dts: pd.Timestamp
    acute_start_hours: float
    acute_end_hours: float
    include_baseline: bool
    baseline_days_before: int
    baseline_duration_hours: float
    obs_freq_minutes: int
    spo2_mean: float
    spo2_sd: float
    ar1: float
    desat_prob: float
    desat_depth: float
    desat_duration_minutes: int
    measurement_sd: float
    spo2_rounding: str
    room_air_threshold: float
    support_based_on_observed: bool
    fio2_meas_prob: float
    oxygen_flow_min: float
    oxygen_flow_max: float
    altitude_factor: float
    n_reps: int
    seed: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "admit_dts": self.admit_dts.isoformat(),
            "acute_start_hours": self.acute_start_hours,
            "acute_end_hours": self.acute_end_hours,
            "include_baseline": self.include_baseline,
            "baseline_days_before": self.baseline_days_before,
            "baseline_duration_hours": self.baseline_duration_hours,
            "obs_freq_minutes": self.obs_freq_minutes,
            "spo2_mean": self.spo2_mean,
            "spo2_sd": self.spo2_sd,
            "ar1": self.ar1,
            "desat_prob": self.desat_prob,
            "desat_depth": self.desat_depth,
            "desat_duration_minutes": self.desat_duration_minutes,
            "measurement_sd": self.measurement_sd,
            "spo2_rounding": self.spo2_rounding,
            "room_air_threshold": self.room_air_threshold,
            "support_based_on_observed": self.support_based_on_observed,
            "fio2_meas_prob": self.fio2_meas_prob,
            "oxygen_flow_min": self.oxygen_flow_min,
            "oxygen_flow_max": self.oxygen_flow_max,
            "altitude_factor": self.altitude_factor,
            "n_reps": self.n_reps,
            "seed": self.seed,
        }


@dataclass(frozen=True)
class AppletSweepRequest:
    base_request: AppletRunRequest
    obs_freq_minutes_values: tuple[int, ...]
    noise_sd_values: tuple[float, ...]
    room_air_threshold_values: tuple[float, ...]
    heatmap_metric: str = DEFAULT_SWEEP_HEATMAP_METRIC

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "base_request": self.base_request.to_json_dict(),
            "obs_freq_minutes_values": list(self.obs_freq_minutes_values),
            "noise_sd_values": list(self.noise_sd_values),
            "room_air_threshold_values": list(self.room_air_threshold_values),
            "heatmap_metric": self.heatmap_metric,
        }


DEFAULT_RUN_REQUEST = AppletRunRequest(
    admit_dts=pd.Timestamp("2024-01-01"),
    acute_start_hours=-6.0,
    acute_end_hours=24.0,
    include_baseline=False,
    baseline_days_before=30,
    baseline_duration_hours=6.0,
    obs_freq_minutes=15,
    spo2_mean=96.0,
    spo2_sd=1.5,
    ar1=0.6,
    desat_prob=0.01,
    desat_depth=5.0,
    desat_duration_minutes=30,
    measurement_sd=1.0,
    spo2_rounding="int",
    room_air_threshold=94.0,
    support_based_on_observed=True,
    fio2_meas_prob=0.2,
    oxygen_flow_min=2.0,
    oxygen_flow_max=6.0,
    altitude_factor=0.85,
    n_reps=1000,
    seed=0,
)

DEFAULT_SWEEP_REQUEST = AppletSweepRequest(
    base_request=DEFAULT_RUN_REQUEST,
    obs_freq_minutes_values=(15, 30, 60),
    noise_sd_values=(0.5, 1.0, 1.5),
    room_air_threshold_values=(92.0, 94.0, 96.0),
    heatmap_metric=DEFAULT_SWEEP_HEATMAP_METRIC,
)


def default_run_request() -> AppletRunRequest:
    return DEFAULT_RUN_REQUEST


def default_sweep_request() -> AppletSweepRequest:
    return DEFAULT_SWEEP_REQUEST


def derive_support_thresholds(room_air_threshold: float) -> tuple[float, float, float, float]:
    room_air = _as_float(room_air_threshold, "room_air_threshold")
    low_flow = room_air - 4.0
    hfnc = room_air - 8.0
    nippv = room_air - 12.0
    if not (room_air > low_flow > hfnc > nippv):
        raise ValueError(
            "Derived thresholds must satisfy room_air > low_flow > hfnc > nippv."
        )
    return room_air, low_flow, hfnc, nippv


def normalize_request(raw: Mapping[str, Any] | AppletRunRequest) -> AppletRunRequest:
    if isinstance(raw, AppletRunRequest):
        request = raw
    else:
        defaults = DEFAULT_RUN_REQUEST
        request = AppletRunRequest(
            admit_dts=_as_timestamp(
                _raw_or_default(raw, "admit_dts", defaults.admit_dts),
                "admit_dts",
            ),
            acute_start_hours=_as_float(
                _raw_or_default(raw, "acute_start_hours", defaults.acute_start_hours),
                "acute_start_hours",
            ),
            acute_end_hours=_as_float(
                _raw_or_default(raw, "acute_end_hours", defaults.acute_end_hours),
                "acute_end_hours",
            ),
            include_baseline=_as_bool(
                _raw_or_default(raw, "include_baseline", defaults.include_baseline),
                "include_baseline",
            ),
            baseline_days_before=_as_int(
                _raw_or_default(raw, "baseline_days_before", defaults.baseline_days_before),
                "baseline_days_before",
            ),
            baseline_duration_hours=_as_float(
                _raw_or_default(raw, "baseline_duration_hours", defaults.baseline_duration_hours),
                "baseline_duration_hours",
            ),
            obs_freq_minutes=_as_int(
                _raw_or_default(raw, "obs_freq_minutes", defaults.obs_freq_minutes),
                "obs_freq_minutes",
            ),
            spo2_mean=_as_float(_raw_or_default(raw, "spo2_mean", defaults.spo2_mean), "spo2_mean"),
            spo2_sd=_as_float(_raw_or_default(raw, "spo2_sd", defaults.spo2_sd), "spo2_sd"),
            ar1=_as_float(_raw_or_default(raw, "ar1", defaults.ar1), "ar1"),
            desat_prob=_as_float(
                _raw_or_default(raw, "desat_prob", defaults.desat_prob),
                "desat_prob",
            ),
            desat_depth=_as_float(
                _raw_or_default(raw, "desat_depth", defaults.desat_depth),
                "desat_depth",
            ),
            desat_duration_minutes=_as_int(
                _raw_or_default(raw, "desat_duration_minutes", defaults.desat_duration_minutes),
                "desat_duration_minutes",
            ),
            measurement_sd=_as_float(
                _raw_or_default(raw, "measurement_sd", defaults.measurement_sd),
                "measurement_sd",
            ),
            spo2_rounding=str(
                _raw_or_default(raw, "spo2_rounding", defaults.spo2_rounding)
            ).strip(),
            room_air_threshold=_as_float(
                _raw_or_default(raw, "room_air_threshold", defaults.room_air_threshold),
                "room_air_threshold",
            ),
            support_based_on_observed=_as_bool(
                _raw_or_default(
                    raw,
                    "support_based_on_observed",
                    defaults.support_based_on_observed,
                ),
                "support_based_on_observed",
            ),
            fio2_meas_prob=_as_float(
                _raw_or_default(raw, "fio2_meas_prob", defaults.fio2_meas_prob),
                "fio2_meas_prob",
            ),
            oxygen_flow_min=_as_float(
                _raw_or_default(raw, "oxygen_flow_min", defaults.oxygen_flow_min),
                "oxygen_flow_min",
            ),
            oxygen_flow_max=_as_float(
                _raw_or_default(raw, "oxygen_flow_max", defaults.oxygen_flow_max),
                "oxygen_flow_max",
            ),
            altitude_factor=_as_float(
                _raw_or_default(raw, "altitude_factor", defaults.altitude_factor),
                "altitude_factor",
            ),
            n_reps=_as_int(_raw_or_default(raw, "n_reps", defaults.n_reps), "n_reps"),
            seed=_as_int(_raw_or_default(raw, "seed", defaults.seed), "seed"),
        )

    _validate_request(request)
    return request


def parse_csv_numeric_list(raw: str, cast: type, field_name: str) -> tuple[int | float, ...]:
    if not isinstance(raw, str):
        raise ValueError(f"{field_name} must be a comma-separated string.")
    stripped_input = raw.strip()
    if not stripped_input:
        raise ValueError(f"{field_name} must not be empty.")

    values: list[int | float] = []
    for idx, token in enumerate(raw.split(","), start=1):
        stripped = token.strip()
        if not stripped:
            raise ValueError(f"{field_name} contains an empty value at position {idx}.")
        if cast is int:
            value = _as_int(stripped, field_name)
        elif cast is float:
            value = _as_float(stripped, field_name)
        else:
            raise ValueError(f"Unsupported cast type for {field_name}: {cast}")
        values.append(value)

    return _dedupe_sorted(values)


def normalize_sweep_request(
    raw: Mapping[str, Any] | AppletSweepRequest,
) -> AppletSweepRequest:
    if isinstance(raw, AppletSweepRequest):
        request = raw
    else:
        defaults = DEFAULT_SWEEP_REQUEST
        base_input = _raw_or_default(raw, "base_request", defaults.base_request)
        base_request = normalize_request(base_input)

        request = AppletSweepRequest(
            base_request=base_request,
            obs_freq_minutes_values=_normalize_sweep_axis(
                _raw_or_default(raw, "obs_freq_minutes_values", defaults.obs_freq_minutes_values),
                int,
                "obs_freq_minutes_values",
            ),
            noise_sd_values=_normalize_sweep_axis(
                _raw_or_default(raw, "noise_sd_values", defaults.noise_sd_values),
                float,
                "noise_sd_values",
            ),
            room_air_threshold_values=_normalize_sweep_axis(
                _raw_or_default(
                    raw,
                    "room_air_threshold_values",
                    defaults.room_air_threshold_values,
                ),
                float,
                "room_air_threshold_values",
            ),
            heatmap_metric=str(
                _raw_or_default(raw, "heatmap_metric", defaults.heatmap_metric)
            ).strip(),
        )

    _validate_sweep_request(request)
    return request


def estimate_total_sweep_runs(request: AppletSweepRequest) -> int:
    normalized = normalize_sweep_request(request)
    combinations = (
        len(normalized.obs_freq_minutes_values)
        * len(normalized.noise_sd_values)
        * len(normalized.room_air_threshold_values)
    )
    return combinations * normalized.base_request.n_reps


def _validate_request(request: AppletRunRequest) -> None:
    if pd.isna(request.admit_dts):
        raise ValueError("admit_dts must be a valid timestamp.")
    if request.acute_end_hours <= request.acute_start_hours:
        raise ValueError("acute_end_hours must be greater than acute_start_hours.")
    if request.include_baseline and request.baseline_days_before <= 0:
        raise ValueError("baseline_days_before must be > 0 when include_baseline is True.")
    if request.baseline_duration_hours <= 0:
        raise ValueError("baseline_duration_hours must be > 0.")
    if request.obs_freq_minutes <= 0:
        raise ValueError("obs_freq_minutes must be >= 1.")
    if not (0 <= request.spo2_mean <= 100):
        raise ValueError("spo2_mean must be between 0 and 100.")
    if request.spo2_sd <= 0:
        raise ValueError("spo2_sd must be > 0.")
    if not (-1 < request.ar1 < 1):
        raise ValueError("ar1 must be between -1 and 1 (exclusive).")
    if not (0 <= request.desat_prob <= 1):
        raise ValueError("desat_prob must be between 0 and 1.")
    if request.desat_depth < 0:
        raise ValueError("desat_depth must be >= 0.")
    if request.desat_duration_minutes <= 0:
        raise ValueError("desat_duration_minutes must be > 0.")
    if request.measurement_sd < 0:
        raise ValueError("measurement_sd must be >= 0.")
    if request.spo2_rounding not in SPO2_ROUNDING_OPTIONS:
        raise ValueError(
            f"spo2_rounding must be one of {SPO2_ROUNDING_OPTIONS}."
        )
    _, low_flow, hfnc, nippv = derive_support_thresholds(request.room_air_threshold)
    if not (request.room_air_threshold > low_flow > hfnc > nippv):
        raise ValueError(
            "Derived thresholds must satisfy room_air > low_flow > hfnc > nippv."
        )
    if not (0 <= request.fio2_meas_prob <= 1):
        raise ValueError("fio2_meas_prob must be between 0 and 1.")
    if not request.oxygen_flow_min < request.oxygen_flow_max:
        raise ValueError("oxygen_flow_min must be less than oxygen_flow_max.")
    if request.n_reps < 1:
        raise ValueError("n_reps must be >= 1.")
    if request.seed < 0:
        raise ValueError("seed must be >= 0.")
    for field_name in (
        "acute_start_hours",
        "acute_end_hours",
        "baseline_duration_hours",
        "spo2_mean",
        "spo2_sd",
        "ar1",
        "desat_prob",
        "desat_depth",
        "measurement_sd",
        "room_air_threshold",
        "fio2_meas_prob",
        "oxygen_flow_min",
        "oxygen_flow_max",
        "altitude_factor",
    ):
        value = getattr(request, field_name)
        if not math.isfinite(float(value)):
            raise ValueError(f"{field_name} must be finite.")


def _validate_sweep_request(request: AppletSweepRequest) -> None:
    _validate_request(request.base_request)

    if request.heatmap_metric not in SWEEP_HEATMAP_METRICS:
        raise ValueError(
            f"heatmap_metric must be one of {SWEEP_HEATMAP_METRICS}."
        )

    if not request.obs_freq_minutes_values:
        raise ValueError("obs_freq_minutes_values must contain at least one value.")
    if not request.noise_sd_values:
        raise ValueError("noise_sd_values must contain at least one value.")
    if not request.room_air_threshold_values:
        raise ValueError("room_air_threshold_values must contain at least one value.")

    for value in request.obs_freq_minutes_values:
        if value < 1:
            raise ValueError("obs_freq_minutes_values entries must be >= 1.")

    for value in request.noise_sd_values:
        if value < 0:
            raise ValueError("noise_sd_values entries must be >= 0.")
        if not math.isfinite(float(value)):
            raise ValueError("noise_sd_values entries must be finite.")

    for value in request.room_air_threshold_values:
        if not math.isfinite(float(value)):
            raise ValueError("room_air_threshold_values entries must be finite.")
        derive_support_thresholds(float(value))


def _normalize_sweep_axis(
    raw_values: Any,
    cast: type,
    field_name: str,
) -> tuple[int | float, ...]:
    if isinstance(raw_values, str):
        values = parse_csv_numeric_list(raw_values, cast, field_name)
    elif isinstance(raw_values, Sequence) and not isinstance(raw_values, (str, bytes)):
        if len(raw_values) == 0:
            raise ValueError(f"{field_name} must not be empty.")
        parsed: list[int | float] = []
        for value in raw_values:
            if cast is int:
                parsed.append(_as_int(value, field_name))
            elif cast is float:
                parsed.append(_as_float(value, field_name))
            else:
                raise ValueError(f"Unsupported cast type for {field_name}: {cast}")
        values = _dedupe_sorted(parsed)
    else:
        raise ValueError(
            f"{field_name} must be a comma-separated string or a sequence of numeric values."
        )

    if not values:
        raise ValueError(f"{field_name} must contain at least one value.")
    return values


def _dedupe_sorted(values: Sequence[int | float]) -> tuple[int | float, ...]:
    unique_sorted = sorted(set(values))
    return tuple(unique_sorted)


def _raw_or_default(raw: Mapping[str, Any], key: str, default: Any) -> Any:
    value = raw.get(key, default)
    return default if value is None else value


def _as_timestamp(value: Any, field_name: str) -> pd.Timestamp:
    try:
        return pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid datetime.") from exc


def _as_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric.") from exc


def _as_int(value: Any, field_name: str) -> int:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric.") from exc
    if not numeric_value.is_integer():
        raise ValueError(f"{field_name} must be an integer.")
    return int(numeric_value)


def _as_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    raise ValueError(f"{field_name} must be a boolean.")
