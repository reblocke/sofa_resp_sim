from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from .view_model import (
    AppletRunRequest,
    AppletSweepRequest,
    default_run_request,
    default_sweep_request,
    normalize_request,
    normalize_sweep_request,
)

APPLET_PRESET_VERSION = "m4-v1"

RUN_PRESET_NAMES = (
    "Default",
    "High noise",
    "Sparse observations",
    "Conservative oxygen policy",
)

SWEEP_PRESET_NAMES = (
    "Quick",
    "Broad",
    "Custom",
)

_RUN_PRESET_PATCHES: Mapping[str, Mapping[str, Any]] = {
    "Default": {},
    "High noise": {
        "measurement_sd": 2.0,
    },
    "Sparse observations": {
        "obs_freq_minutes": 60,
    },
    "Conservative oxygen policy": {
        "room_air_threshold": 96.0,
    },
}

_SWEEP_PRESET_AXES: Mapping[str, Mapping[str, tuple[int | float, ...]]] = {
    "Quick": {
        "obs_freq_minutes_values": (15, 30, 60),
        "noise_sd_values": (0.5, 1.0, 1.5),
        "room_air_threshold_values": (92.0, 94.0, 96.0),
    },
    "Broad": {
        "obs_freq_minutes_values": (5, 15, 30, 60),
        "noise_sd_values": (0.5, 1.0, 1.5, 2.0),
        "room_air_threshold_values": (90.0, 92.0, 94.0),
    },
    "Custom": {},
}


def list_run_presets() -> tuple[str, ...]:
    return RUN_PRESET_NAMES


def list_sweep_presets() -> tuple[str, ...]:
    return SWEEP_PRESET_NAMES


def apply_run_preset(name: str) -> AppletRunRequest:
    if name not in RUN_PRESET_NAMES:
        raise ValueError(f"Unknown run preset '{name}'.")

    base_request = default_run_request()
    patch = dict(_RUN_PRESET_PATCHES[name])
    if not patch:
        return base_request
    return normalize_request(replace(base_request, **patch))


def apply_sweep_preset(
    name: str,
    base_request: AppletRunRequest | None = None,
) -> AppletSweepRequest:
    if name not in SWEEP_PRESET_NAMES:
        raise ValueError(f"Unknown sweep preset '{name}'.")

    normalized_base = normalize_request(base_request or default_run_request())
    default_sweep = default_sweep_request()
    axis_patch = _SWEEP_PRESET_AXES[name]

    if not axis_patch:
        return normalize_sweep_request(
            AppletSweepRequest(
                base_request=normalized_base,
                obs_freq_minutes_values=default_sweep.obs_freq_minutes_values,
                noise_sd_values=default_sweep.noise_sd_values,
                room_air_threshold_values=default_sweep.room_air_threshold_values,
                heatmap_metric=default_sweep.heatmap_metric,
            )
        )

    return normalize_sweep_request(
        AppletSweepRequest(
            base_request=normalized_base,
            obs_freq_minutes_values=tuple(
                axis_patch["obs_freq_minutes_values"]  # type: ignore[arg-type]
            ),
            noise_sd_values=tuple(axis_patch["noise_sd_values"]),  # type: ignore[arg-type]
            room_air_threshold_values=tuple(
                axis_patch["room_air_threshold_values"]  # type: ignore[arg-type]
            ),
            heatmap_metric=default_sweep.heatmap_metric,
        )
    )


def serialize_preset_selection(
    run_preset_name: str,
    sweep_preset_name: str,
    preset_version: str = APPLET_PRESET_VERSION,
) -> str:
    _validate_preset_version(preset_version)
    _validate_run_preset_name(run_preset_name)
    _validate_sweep_preset_name(sweep_preset_name)

    payload: Mapping[str, object] = {
        "preset_version": preset_version,
        "run_preset_name": run_preset_name,
        "sweep_preset_name": sweep_preset_name,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def parse_preset_selection(payload: str) -> dict[str, str]:
    parsed = json.loads(payload)
    _validate_serialized_version(parsed)

    run_preset_name = parsed.get("run_preset_name")
    sweep_preset_name = parsed.get("sweep_preset_name")
    _validate_run_preset_name(run_preset_name)
    _validate_sweep_preset_name(sweep_preset_name)
    return {
        "run_preset_name": run_preset_name,
        "sweep_preset_name": sweep_preset_name,
    }


def serialize_run_preset_request(
    preset_name: str,
    request: AppletRunRequest,
    preset_version: str = APPLET_PRESET_VERSION,
) -> str:
    _validate_preset_version(preset_version)
    _validate_run_preset_name(preset_name)
    normalized_request = normalize_request(request)

    payload: Mapping[str, object] = {
        "preset_version": preset_version,
        "preset_name": preset_name,
        "request": normalized_request.to_json_dict(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def parse_run_preset_request(payload: str) -> tuple[str, AppletRunRequest]:
    parsed = json.loads(payload)
    _validate_serialized_version(parsed)

    preset_name = parsed.get("preset_name")
    _validate_run_preset_name(preset_name)
    if "request" not in parsed:
        raise ValueError("Serialized run preset payload must include a 'request' field.")

    request = normalize_request(parsed["request"])
    return preset_name, request


def serialize_sweep_preset_request(
    preset_name: str,
    request: AppletSweepRequest,
    preset_version: str = APPLET_PRESET_VERSION,
) -> str:
    _validate_preset_version(preset_version)
    _validate_sweep_preset_name(preset_name)
    normalized_request = normalize_sweep_request(request)

    payload: Mapping[str, object] = {
        "preset_version": preset_version,
        "preset_name": preset_name,
        "sweep_request": normalized_request.to_json_dict(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def parse_sweep_preset_request(payload: str) -> tuple[str, AppletSweepRequest]:
    parsed = json.loads(payload)
    _validate_serialized_version(parsed)

    preset_name = parsed.get("preset_name")
    _validate_sweep_preset_name(preset_name)
    if "sweep_request" not in parsed:
        raise ValueError("Serialized sweep preset payload must include a 'sweep_request' field.")

    request = normalize_sweep_request(parsed["sweep_request"])
    return preset_name, request


def _validate_preset_version(value: str) -> None:
    if value != APPLET_PRESET_VERSION:
        raise ValueError(
            f"Unsupported preset_version '{value}'. Expected '{APPLET_PRESET_VERSION}'."
        )


def _validate_serialized_version(parsed: Mapping[str, Any]) -> None:
    if "preset_version" not in parsed:
        raise ValueError("Serialized preset payload must include a 'preset_version' field.")
    _validate_preset_version(str(parsed["preset_version"]))


def _validate_run_preset_name(value: Any) -> None:
    if not isinstance(value, str) or value not in RUN_PRESET_NAMES:
        raise ValueError(f"run preset must be one of {RUN_PRESET_NAMES}.")


def _validate_sweep_preset_name(value: Any) -> None:
    if not isinstance(value, str) or value not in SWEEP_PRESET_NAMES:
        raise ValueError(f"sweep preset must be one of {SWEEP_PRESET_NAMES}.")
