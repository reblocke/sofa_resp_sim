from __future__ import annotations

from dataclasses import replace

import pytest

from sofa_resp_sim.reporting.presets import (
    APPLET_PRESET_VERSION,
    RUN_PRESET_NAMES,
    SWEEP_PRESET_NAMES,
    apply_run_preset,
    apply_sweep_preset,
    list_run_presets,
    list_sweep_presets,
    parse_preset_selection,
    parse_run_preset_request,
    parse_sweep_preset_request,
    serialize_preset_selection,
    serialize_run_preset_request,
    serialize_sweep_preset_request,
)
from sofa_resp_sim.reporting.view_model import default_run_request


def test_list_presets_expose_supported_names():
    assert list_run_presets() == RUN_PRESET_NAMES
    assert list_sweep_presets() == SWEEP_PRESET_NAMES


def test_apply_run_preset_overrides_expected_fields():
    default_request = apply_run_preset("Default")
    high_noise = apply_run_preset("High noise")
    sparse_observations = apply_run_preset("Sparse observations")
    conservative_oxygen = apply_run_preset("Conservative oxygen policy")

    assert default_request.measurement_sd == pytest.approx(1.0)
    assert high_noise.measurement_sd == pytest.approx(2.0)
    assert sparse_observations.obs_freq_minutes == 60
    assert conservative_oxygen.room_air_threshold == pytest.approx(96.0)


def test_apply_sweep_preset_uses_selected_base_request():
    base = replace(default_run_request(), n_reps=77, seed=99)

    quick = apply_sweep_preset("Quick", base_request=base)
    broad = apply_sweep_preset("Broad", base_request=base)
    custom = apply_sweep_preset("Custom", base_request=base)

    assert quick.base_request.n_reps == 77
    assert quick.base_request.seed == 99
    assert quick.obs_freq_minutes_values == (15, 30, 60)
    assert broad.noise_sd_values == (0.5, 1.0, 1.5, 2.0)
    assert broad.room_air_threshold_values == (90.0, 92.0, 94.0)
    assert custom.obs_freq_minutes_values == (15, 30, 60)
    assert custom.noise_sd_values == (0.5, 1.0, 1.5)


def test_preset_selection_serialization_roundtrip():
    payload = serialize_preset_selection("High noise", "Broad")
    parsed = parse_preset_selection(payload)

    assert parsed == {
        "run_preset_name": "High noise",
        "sweep_preset_name": "Broad",
    }


def test_run_preset_request_serialization_roundtrip():
    request = replace(default_run_request(), n_reps=123, seed=45)
    payload = serialize_run_preset_request("Sparse observations", request)
    preset_name, parsed_request = parse_run_preset_request(payload)

    assert preset_name == "Sparse observations"
    assert parsed_request.to_json_dict() == request.to_json_dict()


def test_sweep_preset_request_serialization_roundtrip():
    request = apply_sweep_preset("Quick", base_request=replace(default_run_request(), n_reps=88))
    payload = serialize_sweep_preset_request("Quick", request)
    preset_name, parsed_request = parse_sweep_preset_request(payload)

    assert preset_name == "Quick"
    assert parsed_request.to_json_dict() == request.to_json_dict()


@pytest.mark.parametrize(
    "fn,args,expected_message",
    [
        (serialize_preset_selection, ("Unknown", "Quick"), "run preset must be one of"),
        (serialize_preset_selection, ("Default", "Unknown"), "sweep preset must be one of"),
        (
            serialize_preset_selection,
            ("Default", "Quick", "legacy-v0"),
            "Unsupported preset_version",
        ),
    ],
)
def test_preset_serialization_rejects_invalid_inputs(fn, args, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        fn(*args)


def test_preset_parse_rejects_wrong_version():
    payload = (
        '{"preset_version":"legacy-v0","run_preset_name":"Default","sweep_preset_name":"Quick"}'
    )
    with pytest.raises(ValueError, match="Unsupported preset_version"):
        parse_preset_selection(payload)


def test_preset_version_constant_is_stable():
    assert APPLET_PRESET_VERSION == "m4-v1"
