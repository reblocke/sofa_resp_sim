from __future__ import annotations

from dataclasses import replace

import pytest

from sofa_resp_sim.reporting.view_model import (
    DEFAULT_RUN_REQUEST,
    SWEEP_HEATMAP_METRICS,
    default_run_request,
    derive_support_thresholds,
    estimate_total_sweep_runs,
    normalize_request,
    normalize_sweep_request,
    parse_csv_numeric_list,
)


def test_normalize_request_applies_defaults():
    request = normalize_request({"admit_dts": "2025-02-03 04:05:06"})

    assert request.admit_dts.isoformat() == "2025-02-03T04:05:06"
    assert request.n_reps == DEFAULT_RUN_REQUEST.n_reps
    assert request.seed == DEFAULT_RUN_REQUEST.seed
    assert request.room_air_threshold == DEFAULT_RUN_REQUEST.room_air_threshold


def test_derive_support_thresholds_offsets():
    room_air, low_flow, hfnc, nippv = derive_support_thresholds(95.0)

    assert room_air == pytest.approx(95.0)
    assert low_flow == pytest.approx(91.0)
    assert hfnc == pytest.approx(87.0)
    assert nippv == pytest.approx(83.0)
    assert room_air > low_flow > hfnc > nippv


def test_parse_csv_numeric_list_deduplicates_and_sorts():
    int_values = parse_csv_numeric_list("60,15,15,30", int, "obs_freq_minutes_values")
    float_values = parse_csv_numeric_list("1.5,0.5,1.0,1.0", float, "noise_sd_values")

    assert int_values == (15, 30, 60)
    assert float_values == (0.5, 1.0, 1.5)


@pytest.mark.parametrize(
    "raw, cast, expected_message",
    [
        ("", int, "must not be empty"),
        ("15,,30", int, "empty value"),
        ("abc,30", int, "must be numeric"),
        ("0.5,abc", float, "must be numeric"),
    ],
)
def test_parse_csv_numeric_list_rejects_bad_input(raw, cast, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        parse_csv_numeric_list(raw, cast, "values")


def test_normalize_sweep_request_and_estimate_total_runs():
    base_request = replace(default_run_request(), n_reps=25)
    sweep_request = normalize_sweep_request(
        {
            "base_request": base_request,
            "obs_freq_minutes_values": "15,30,60",
            "noise_sd_values": "0.5,1.5",
            "room_air_threshold_values": "92,94",
            "heatmap_metric": "p_sofa_3plus",
        }
    )

    assert sweep_request.obs_freq_minutes_values == (15, 30, 60)
    assert sweep_request.noise_sd_values == (0.5, 1.5)
    assert sweep_request.room_air_threshold_values == (92.0, 94.0)
    assert sweep_request.heatmap_metric == "p_sofa_3plus"
    assert estimate_total_sweep_runs(sweep_request) == 3 * 2 * 2 * 25


@pytest.mark.parametrize(
    "patch, expected_message",
    [
        ({"obs_freq_minutes_values": "0,15"}, "entries must be >= 1"),
        ({"noise_sd_values": "-0.1,1.0"}, "entries must be >= 0"),
        ({"room_air_threshold_values": "nan"}, "entries must be finite"),
        ({"heatmap_metric": "not_a_metric"}, "must be one of"),
    ],
)
def test_normalize_sweep_request_rejects_invalid_values(patch, expected_message):
    payload = {
        "base_request": default_run_request(),
        "obs_freq_minutes_values": "15,30",
        "noise_sd_values": "0.5,1.0",
        "room_air_threshold_values": "92,94",
        "heatmap_metric": SWEEP_HEATMAP_METRICS[0],
    }
    payload.update(patch)

    with pytest.raises(ValueError, match=expected_message):
        normalize_sweep_request(payload)


@pytest.mark.parametrize(
    "patch, expected_message",
    [
        ({"spo2_mean": 101}, "spo2_mean must be between 0 and 100"),
        ({"spo2_sd": 0}, "spo2_sd must be > 0"),
        ({"ar1": 1.0}, "ar1 must be between -1 and 1"),
        ({"desat_prob": 1.2}, "desat_prob must be between 0 and 1"),
        ({"desat_depth": -0.1}, "desat_depth must be >= 0"),
        ({"desat_duration_minutes": 0}, "desat_duration_minutes must be > 0"),
        ({"measurement_sd": -0.1}, "measurement_sd must be >= 0"),
        ({"spo2_rounding": "bad"}, "spo2_rounding must be one of"),
        ({"room_air_threshold": "nan"}, "Derived thresholds must satisfy"),
        ({"fio2_meas_prob": 2.0}, "fio2_meas_prob must be between 0 and 1"),
        ({"oxygen_flow_min": 8, "oxygen_flow_max": 2}, "oxygen_flow_min must be less"),
        ({"n_reps": 0}, "n_reps must be >= 1"),
        ({"seed": -1}, "seed must be >= 0"),
    ],
)
def test_normalize_request_rejects_invalid_values(patch, expected_message):
    payload = {"admit_dts": "2024-01-01"}
    payload.update(patch)

    with pytest.raises(ValueError, match=expected_message):
        normalize_request(payload)
