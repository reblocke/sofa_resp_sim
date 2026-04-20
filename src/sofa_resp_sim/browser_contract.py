from __future__ import annotations

import importlib.metadata
import importlib.resources
import math
from collections.abc import Mapping
from io import StringIO
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .reporting.app_services import (
    APPLET_CODE_VERSION,
    DEFAULT_BOOTSTRAP_SAMPLES,
    DEFAULT_CI_LEVEL,
    DEFAULT_SWEEP_GUARDRAIL_RUNS,
    build_sweep_heatmap_frame,
    build_uncertainty_table,
    compute_divergence_metrics,
    extract_sofa_probabilities,
    format_sweep_replicates_for_export,
    format_sweep_summary_for_export,
    run_single_scenario,
    run_sweep_scenario,
)
from .reporting.presets import (
    APPLET_PRESET_VERSION,
    apply_run_preset,
    apply_sweep_preset,
    list_run_presets,
    list_sweep_presets,
)
from .reporting.reference import load_builtin_reference, normalize_reference_distribution
from .reporting.view_model import (
    DEFAULT_SWEEP_HEATMAP_METRIC,
    SPO2_ROUNDING_OPTIONS,
    SWEEP_HEATMAP_METRICS,
    default_run_request,
    default_sweep_request,
    estimate_total_sweep_runs,
    normalize_request,
    normalize_sweep_request,
)

REFERENCE_FILENAME = "resp_sofa_sim_summary.csv"


def get_app_config_payload() -> dict[str, Any]:
    """Return static browser configuration and reference distribution payloads."""
    try:
        reference = _load_reference_series()
        run_presets = [
            {
                "name": name,
                "request": apply_run_preset(name).to_json_dict(),
            }
            for name in list_run_presets()
        ]
        sweep_presets = [
            {
                "name": name,
                "request": apply_sweep_preset(name).to_json_dict(),
            }
            for name in list_sweep_presets()
        ]
        return _ok(
            {
                "app_version": APPLET_CODE_VERSION,
                "preset_version": APPLET_PRESET_VERSION,
                "package_version": _package_version(),
                "defaults": default_run_request().to_json_dict(),
                "sweep_defaults": default_sweep_request().to_json_dict(),
                "run_presets": run_presets,
                "sweep_presets": sweep_presets,
                "supported_sweep_metrics": list(SWEEP_HEATMAP_METRICS),
                "default_sweep_metric": DEFAULT_SWEEP_HEATMAP_METRIC,
                "spo2_rounding_options": list(SPO2_ROUNDING_OPTIONS),
                "guardrails": {
                    "default_bootstrap_samples": DEFAULT_BOOTSTRAP_SAMPLES,
                    "default_ci_level": DEFAULT_CI_LEVEL,
                    "max_sweep_runs": DEFAULT_SWEEP_GUARDRAIL_RUNS,
                },
                "reference_distribution": _probability_rows(reference),
                "browser_guardrails": [
                    "Runs are local to the browser and may take longer on low-power devices.",
                    "Sweep workloads are capped before execution.",
                    "This app is for validation and research workflows, "
                    "not bedside decision support.",
                ],
            }
        )
    except Exception as exc:  # noqa: BLE001 - public browser boundary
        return _error(exc)


def run_scenario_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Run a single scenario from a JSON-like request payload."""
    try:
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping.")

        request_payload = payload.get("request", payload)
        request = normalize_request(request_payload)
        summary, replicates = run_single_scenario(request)

        reference = _load_reference_series()
        scenario_probs = extract_sofa_probabilities(replicates)
        uncertainty = build_uncertainty_table(
            replicates=replicates,
            reference_probs=reference,
            n_bootstrap=_positive_int(
                payload.get("n_bootstrap", DEFAULT_BOOTSTRAP_SAMPLES),
                "n_bootstrap",
            ),
            ci_level=_ci_level(payload.get("ci_level", DEFAULT_CI_LEVEL)),
            seed=_nonnegative_int(
                payload.get("uncertainty_seed", request.seed), "uncertainty_seed"
            ),
        )

        return _ok(
            {
                "request": request.to_json_dict(),
                "summary_rows": _records(summary),
                "sofa_probabilities": _probability_rows(scenario_probs),
                "reference_comparison": _comparison_rows(scenario_probs, reference),
                "divergence_metrics": _json_ready(
                    compute_divergence_metrics(scenario_probs, reference)
                ),
                "uncertainty_rows": _records(uncertainty),
                "export_rows": _records(summary),
                "summary_csv": _csv_text(summary),
                "replicates_csv": _csv_text(replicates),
            }
        )
    except Exception as exc:  # noqa: BLE001 - public browser boundary
        return _error(exc)


def run_sweep_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Run a deterministic sweep from a JSON-like request payload."""
    try:
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping.")

        request_payload = payload.get("sweep_request", payload)
        request = normalize_sweep_request(request_payload)
        total_runs = estimate_total_sweep_runs(request)
        summary, replicates = run_sweep_scenario(request, return_replicates=True)

        selected_metric = request.heatmap_metric
        summary_export = format_sweep_summary_for_export(summary)
        replicates_export = format_sweep_replicates_for_export(replicates)
        heatmap = build_sweep_heatmap_frame(summary, metric=selected_metric)

        return _ok(
            {
                "sweep_request": request.to_json_dict(),
                "workload_estimate": {
                    "combinations": int(
                        len(request.obs_freq_minutes_values)
                        * len(request.noise_sd_values)
                        * len(request.room_air_threshold_values)
                    ),
                    "total_runs": int(total_runs),
                    "max_runs": DEFAULT_SWEEP_GUARDRAIL_RUNS,
                },
                "summary_rows": _records(summary_export),
                "heatmap_rows": _records(heatmap),
                "replicate_export_rows": _records(replicates_export),
                "selected_metric": selected_metric,
                "summary_csv": _csv_text(summary_export),
                "replicates_csv": _csv_text(replicates_export),
            }
        )
    except Exception as exc:  # noqa: BLE001 - public browser boundary
        return _error(exc)


def _load_reference_series() -> pd.Series:
    for path in _reference_candidates():
        if path.exists():
            return load_builtin_reference(path).loc[0]
    package_resource = importlib.resources.files("sofa_resp_sim.data").joinpath(REFERENCE_FILENAME)
    if package_resource.is_file():
        frame = pd.read_csv(StringIO(package_resource.read_text(encoding="utf-8")))
        return normalize_reference_distribution(frame).loc[0]
    candidates = ", ".join(str(path) for path in _reference_candidates())
    raise FileNotFoundError(
        "Reference file not found in filesystem candidates or package resources: "
        f"{candidates}, sofa_resp_sim.data/{REFERENCE_FILENAME}"
    )


def _reference_candidates() -> tuple[Path, ...]:
    repo_or_pyodide_root = Path(__file__).resolve().parents[2]
    return (
        repo_or_pyodide_root / "assets" / "data" / REFERENCE_FILENAME,
        repo_or_pyodide_root / "artifacts" / REFERENCE_FILENAME,
        Path("/home/pyodide/assets/data") / REFERENCE_FILENAME,
    )


def _comparison_rows(
    scenario: pd.Series,
    reference: pd.Series,
) -> list[dict[str, float | int]]:
    rows = []
    for score in range(5):
        scenario_value = float(scenario[f"p_sofa_{score}"])
        reference_value = float(reference[f"p_sofa_{score}"])
        rows.append(
            {
                "score": score,
                "p_scenario": scenario_value,
                "p_reference": reference_value,
                "delta_vs_reference": scenario_value - reference_value,
            }
        )
    return rows


def _probability_rows(probabilities: pd.Series) -> list[dict[str, float | int]]:
    return [
        {
            "score": score,
            "probability": float(probabilities[f"p_sofa_{score}"]),
        }
        for score in range(5)
    ]


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return _json_ready(frame.to_dict(orient="records"))


def _csv_text(frame: pd.DataFrame) -> str:
    buffer = StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue()


def _ok(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {"ok": True, **_json_ready(dict(payload))}


def _error(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "type": type(exc).__name__,
            "message": str(exc),
        },
    }


def _positive_int(value: Any, field_name: str) -> int:
    parsed = _nonnegative_int(value, field_name)
    if parsed < 1:
        raise ValueError(f"{field_name} must be >= 1.")
    return parsed


def _nonnegative_int(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be >= 0.")
    return parsed


def _ci_level(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("ci_level must be numeric.") from exc
    if not (0 < parsed < 1):
        raise ValueError("ci_level must be between 0 and 1.")
    return parsed


def _package_version() -> str:
    try:
        return importlib.metadata.version("sofa-resp-sim")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        as_float = float(value)
        return as_float if math.isfinite(as_float) else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value
