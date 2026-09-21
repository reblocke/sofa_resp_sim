import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from sofa_resp_sim.core.experiment_config import GeneratorConfig, HorizonConfig
from sofa_resp_sim.core.paired_simulation import (
    generate_patient,
    patient_rng,
    stationary_background,
)

PROTOCOL = json.loads((Path(__file__).parent / "fixtures/ar_validation_protocol.json").read_text())


def test_rectangular_episode_returns_to_background():
    config = GeneratorConfig.from_dict(
        {
            "mean_pct": 96,
            "marginal_sd_pct": 0,
            "episode_rate_per_hour": 0,
            "prescribed_episodes": [{"start_minute": 30, "end_minute": 60, "depth_pct_points": 5}],
        }
    )
    block = generate_patient(config, HorizonConfig(start_minute=0, end_minute=120), 0, 0).blocks[0]
    expected = np.full(120, 96.0)
    expected[30:60] = 91
    np.testing.assert_array_equal(block.background, 96)
    np.testing.assert_array_equal(block.saturation, expected)
    for interval in [5, 15, 30, 60]:
        np.testing.assert_array_equal(block.saturation[::interval], expected[::interval])


@pytest.mark.parametrize("tau", PROTOCOL["tau_minutes"])
def test_stationary_marginal_sd_and_elapsed_correlation(tau):
    config = GeneratorConfig(
        mean_pct=PROTOCOL["mean_pct"],
        marginal_sd_pct=PROTOCOL["marginal_sd_pct"],
        tau_minutes=tau,
        episode_rate_per_hour=0,
    )
    paths = np.array(
        [
            stationary_background(
                PROTOCOL["minutes_per_patient"],
                config,
                patient_rng(PROTOCOL["seed"], patient, 0, "physiology"),
            )
            for patient in range(PROTOCOL["patients"])
        ]
    )
    relative_error = abs(paths.std() / config.marginal_sd_pct - 1)
    assert relative_error < PROTOCOL["relative_sd_tolerance"]
    for lag in PROTOCOL["lags_minutes"]:
        correlation = np.corrcoef(paths[:, :-lag].ravel(), paths[:, lag:].ravel())[0, 1]
        expected = np.exp(-lag / tau) if tau else 0
        assert abs(correlation - expected) < PROTOCOL["absolute_correlation_tolerance"]


def test_filter_matches_declared_scalar_recurrence():
    config = GeneratorConfig()
    actual = stationary_background(100, config, patient_rng(42, 0, 0, "physiology"))
    z = patient_rng(42, 0, 0, "physiology").standard_normal(100)
    phi = np.exp(-1 / config.tau_minutes)
    expected = np.empty(100)
    expected[0] = config.mean_pct + config.marginal_sd_pct * z[0]
    for i in range(1, 100):
        expected[i] = (
            config.mean_pct
            + phi * (expected[i - 1] - config.mean_pct)
            + config.marginal_sd_pct * np.sqrt(1 - phi**2) * z[i]
        )
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
    assert stationary_background(1, config, patient_rng(42, 0, 0, "physiology"))[0] == actual[0]


def test_episodes_do_not_overlap_and_background_is_independent():
    horizon = HorizonConfig(start_minute=0, end_minute=1000)
    config = GeneratorConfig(episode_rate_per_hour=100, episode_duration_minutes=30)
    block = generate_patient(config, horizon, 0, 2).blocks[0]
    no_episodes = GeneratorConfig(episode_rate_per_hour=0)
    control = generate_patient(no_episodes, horizon, 0, 2).blocks[0]
    np.testing.assert_array_equal(block.background, control.background)
    assert all(
        a["end_minute"] <= b["start_minute"]
        for a, b in zip(block.episodes, block.episodes[1:], strict=False)
    )


def test_baseline_replay_uses_exact_same_segment():
    horizon = HorizonConfig(
        start_minute=0,
        end_minute=360,
        include_baseline=True,
        baseline_generation_minutes=360,
        baseline_replay=True,
    )
    patient = generate_patient(GeneratorConfig(), horizon, 0, 0)
    np.testing.assert_array_equal(patient.blocks[0].saturation, patient.blocks[1].saturation)
    assert patient.blocks[0].rng_block_id == patient.blocks[1].rng_block_id


def test_generation_identity_is_distinct_from_runtime_content_integrity():
    patient = generate_patient(GeneratorConfig(), HorizonConfig(), 0, 0)
    block = patient.blocks[0]
    values = block.saturation.copy()
    values[0] = np.nextafter(values[0], np.inf)
    changed = replace(patient, blocks=(replace(block, saturation=values),))
    assert changed.identity == patient.identity
    assert changed.content_sha256 != patient.content_sha256


def test_independent_baseline_uses_a_distinct_stream_not_a_replay():
    horizon = HorizonConfig(
        start_minute=0,
        end_minute=360,
        include_baseline=True,
        baseline_generation_minutes=360,
        baseline_replay=False,
    )
    patient = generate_patient(GeneratorConfig(), horizon, 173203, 0)
    blocks = {block.name: block for block in patient.blocks}
    acute, baseline = blocks["acute"], blocks["baseline"]
    assert acute.rng_block_id != baseline.rng_block_id
    assert not np.array_equal(acute.background, baseline.background)
    replay = generate_patient(GeneratorConfig(), replace(horizon, baseline_replay=True), 173203, 0)
    np.testing.assert_array_equal(replay.blocks[0].saturation, replay.blocks[1].saturation)
    replay_acute = next(block for block in replay.blocks if block.name == "acute")
    np.testing.assert_array_equal(acute.saturation, replay_acute.saturation)
