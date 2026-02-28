from __future__ import annotations

from dataclasses import replace

import pandas as pd
from sofa_resp_sim.resp_simulation import run_replicates
from sofa_resp_sim.web.app_services import (
    SUMMARY_COLUMNS,
    build_cache_key,
    build_simulation_config,
    run_single_scenario,
)
from sofa_resp_sim.web.view_model import default_run_request


def _manual_summary(replicates: pd.DataFrame, *, obs_freq: int, noise_sd: float, room_air: float):
    counts = replicates["sofa_pulm"].value_counts().to_dict()
    total = len(replicates)
    row = {
        "obs_freq_minutes": obs_freq,
        "noise_sd": noise_sd,
        "room_air_threshold": room_air,
        "n_reps": total,
        "mean_count_pf_ratio_acute": float(replicates["count_pf_ratio_acute"].mean()),
        "p_single_pf_suppressed": float(replicates["single_pf_suppressed"].mean()),
    }
    for score in range(5):
        row[f"p_sofa_{score}"] = counts.get(score, 0) / total if total else 0.0
    return pd.DataFrame([row], columns=SUMMARY_COLUMNS)


def test_run_single_scenario_is_deterministic_for_seed():
    request = replace(default_run_request(), n_reps=20, seed=77)

    summary_a, replicates_a = run_single_scenario(request)
    summary_b, replicates_b = run_single_scenario(request)

    pd.testing.assert_frame_equal(summary_a, summary_b)
    pd.testing.assert_frame_equal(replicates_a, replicates_b)


def test_run_single_scenario_matches_direct_replicate_aggregation():
    request = replace(
        default_run_request(),
        n_reps=25,
        seed=11,
        obs_freq_minutes=60,
        measurement_sd=0.8,
        room_air_threshold=93.0,
    )

    summary, replicates = run_single_scenario(request)

    config = build_simulation_config(request)
    direct_replicates = run_replicates(config=config, n_reps=request.n_reps, seed=request.seed)
    expected_summary = _manual_summary(
        direct_replicates,
        obs_freq=request.obs_freq_minutes,
        noise_sd=request.measurement_sd,
        room_air=request.room_air_threshold,
    )

    pd.testing.assert_frame_equal(replicates, direct_replicates)
    pd.testing.assert_frame_equal(summary, expected_summary)


def test_build_cache_key_changes_when_request_changes():
    request = replace(default_run_request(), n_reps=10, seed=3)

    key_a = build_cache_key(request)
    key_b = build_cache_key(request)
    key_c = build_cache_key(replace(request, seed=4))

    assert key_a == key_b
    assert key_a != key_c
