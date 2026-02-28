from __future__ import annotations

import pytest
from sofa_resp_sim.web.view_model import (
    DEFAULT_RUN_REQUEST,
    derive_support_thresholds,
    normalize_request,
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
