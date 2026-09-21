from unittest.mock import patch

import numpy as np

from sofa_resp_sim.core.experiment_config import ScenarioConfig
from sofa_resp_sim.core.observation import document_patient, support_trajectory
from sofa_resp_sim.core.paired_simulation import generate_patient


def base_config(**groups):
    return ScenarioConfig.from_dict(
        {
            "horizon": {"start_minute": 0, "end_minute": 120},
            "observation": {"start_minute": 0, "rounding": "none"},
            **groups,
        }
    )


def patient(config, patient_id=0):
    return generate_patient(config.generator, config.horizon, 42, patient_id)


def test_nested_schedules_share_patient_values():
    config = base_config()
    latent = patient(config)
    by_interval = {}
    for interval in [5, 15, 30, 60]:
        changed = config.override({"observation": {"interval_minutes": interval}})
        assert patient(changed).identity == latent.identity
        by_interval[interval] = {
            e["event_id"]: e
            for e in document_patient(latent, changed)
            if e["event_type"] == "oxygenation"
        }
    for interval in [15, 30, 60]:
        for event_id, event in by_interval[interval].items():
            assert by_interval[5][event_id] == event


def test_rounding_only_documented_samples_in_fixed_support_mode():
    from sofa_resp_sim.core import observation

    config = base_config().override({"observation": {"rounding": "integer"}})
    latent = patient(config)
    with patch.object(observation, "oracle_round", wraps=observation.oracle_round) as rounding:
        events = document_patient(latent, config)
    assert rounding.call_count == len([e for e in events if e["event_type"] == "oxygenation"])


def test_fixed_support_is_unchanged():
    config = base_config(support={"label": "IMV", "fio2_fraction": 0.5})
    latent = patient(config)
    control = support_trajectory(latent, latent.blocks[0], config)
    for overrides in [
        {"observation": {"noise_sd_pct": 5, "missing_probability": 0.5}},
        {"documentation": {"missing_probability": 1}},
        {"scoring": {"threshold_factor": 0.75}},
    ]:
        changed = config.override(overrides)
        assert patient(changed).identity == latent.identity
        actual = support_trajectory(latent, latent.blocks[0], changed)
        np.testing.assert_array_equal(actual.labels, control.labels)
        np.testing.assert_array_equal(actual.fio2_fraction, control.fio2_fraction)


def test_assignment_stress_mode_is_explicit():
    config = base_config(
        generator={"mean_pct": 93, "marginal_sd_pct": 0, "episode_rate_per_hour": 0},
        support={"mode": "assignment_stress_test"},
    )
    latent = patient(config)
    quiet = config.override({"observation": {"noise_sd_pct": 0}})
    noisy = config.override({"observation": {"noise_sd_pct": 10}})
    a = support_trajectory(latent, latent.blocks[0], quiet)
    b = support_trajectory(latent, latent.blocks[0], noisy)
    assert np.any(a.labels != b.labels)


def test_documentation_schedule_does_not_follow_observation_start_or_interval():
    config = base_config(documentation={"interval_minutes": 7, "phase_minutes": 3})
    latent = patient(config)
    a = [e for e in document_patient(latent, config) if e["event_type"] == "fio2"]
    changed = config.override({"observation": {"start_minute": 30, "interval_minutes": 60}})
    b = [e for e in document_patient(latent, changed) if e["event_type"] == "fio2"]
    assert a == b
    assert a[0]["measurement_minute"] == 3


def test_missingness_is_nested_and_removes_all_denominator_sources():
    config = base_config(support={"label": "LOW_FLOW", "fio2_fraction": None, "flow_lpm": 4})
    latent = patient(config)
    sets = []
    for probability in [0, 0.25, 0.5, 1]:
        changed = config.override({"documentation": {"missing_probability": probability}})
        events = [e for e in document_patient(latent, changed) if e["event_type"] == "fio2"]
        sets.append({e["event_id"] for e in events if e["documentation_missing"]})
        if probability == 1:
            assert all(
                e["flow_lpm"] is None
                and not e["is_room_air"]
                and e["fio2_set_fraction"] is None
                and e["fio2_meas_fraction"] is None
                and e["fio2_abg_fraction"] is None
                for e in events
            )
    assert sets[0] <= sets[1] <= sets[2] <= sets[3]


def test_source_label_changes_preserve_values_and_patient_identity():
    config = base_config(support={"label": "IMV", "fio2_fraction": 0.5})
    latent = patient(config)
    a = document_patient(
        latent, config.override({"documentation": {"measured_source_probability": 0}})
    )
    b = document_patient(
        latent, config.override({"documentation": {"measured_source_probability": 1}})
    )
    for left, right in zip(a, b, strict=True):
        if left["event_type"] == "oxygenation":
            assert left == right
        else:
            assert left["fio2_set_fraction"] == right["fio2_meas_fraction"] == 0.5


def test_patient_order_and_n_extension_preserve_earlier_patients():
    config = base_config(horizon={"start_minute": 0, "end_minute": 2})
    first = {i: patient(config, i).identity for i in range(200)}
    extended = {i: patient(config, i).identity for i in reversed(range(1000))}
    assert first == {i: extended[i] for i in range(200)}
    assert len(set(extended.values())) == 1000
