from __future__ import annotations

import json
from dataclasses import replace

import pytest

from sofa_resp_sim.browser_contract import (
    get_app_config_payload,
    run_scenario_payload,
    run_sweep_payload,
)
from sofa_resp_sim.reporting.app_services import run_single_scenario
from sofa_resp_sim.reporting.view_model import default_run_request


def test_config_payload_is_json_serializable() -> None:
    payload = get_app_config_payload()

    assert payload["ok"] is True
    assert payload["defaults"]["n_reps"] == 1000
    assert payload["reference_distribution"]
    json.dumps(payload)


def test_scenario_payload_matches_reporting_service_summary() -> None:
    request = replace(default_run_request(), n_reps=12, seed=17)
    direct_summary, _ = run_single_scenario(request)

    payload = run_scenario_payload(
        {
            "request": request.to_json_dict(),
            "n_bootstrap": 20,
            "ci_level": 0.9,
            "uncertainty_seed": 4,
        }
    )

    assert payload["ok"] is True
    expected_summary = direct_summary.to_dict(orient="records")[0]
    assert len(payload["summary_rows"]) == 1
    for key, expected_value in expected_summary.items():
        assert payload["summary_rows"][0][key] == pytest.approx(expected_value)
    assert len(payload["sofa_probabilities"]) == 5
    assert len(payload["reference_comparison"]) == 5
    assert len(payload["uncertainty_rows"]) == 5
    assert payload["summary_csv"].startswith("obs_freq_minutes,noise_sd")
    json.dumps(payload)


def test_sweep_payload_returns_heatmap_and_exports() -> None:
    base = replace(default_run_request(), n_reps=3, seed=21)
    payload = run_sweep_payload(
        {
            "base_request": base.to_json_dict(),
            "obs_freq_minutes_values": [15, 60],
            "noise_sd_values": [0.5],
            "room_air_threshold_values": [92.0, 94.0],
            "heatmap_metric": "p_sofa_3plus",
        }
    )

    assert payload["ok"] is True
    assert payload["workload_estimate"]["combinations"] == 4
    assert payload["workload_estimate"]["total_runs"] == 12
    assert len(payload["summary_rows"]) == 4
    assert len(payload["heatmap_rows"]) == 4
    assert len(payload["replicate_export_rows"]) == 12
    assert payload["selected_metric"] == "p_sofa_3plus"
    assert payload["summary_csv"].startswith("obs_freq_minutes,noise_sd")
    assert payload["replicates_csv"].startswith("obs_freq_minutes,noise_sd")
    json.dumps(payload)


def test_invalid_payload_returns_structured_error() -> None:
    payload = run_scenario_payload({"n_reps": 0})

    assert payload["ok"] is False
    assert payload["error"]["type"] == "ValueError"
    assert "n_reps must be >= 1" in payload["error"]["message"]
