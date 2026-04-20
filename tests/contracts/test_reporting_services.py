from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from sofa_resp_sim.reporting.app_services import (
    DEFAULT_SWEEP_GUARDRAIL_RUNS,
    SUMMARY_COLUMNS,
    SWEEP_REPLICATE_EXPORT_COLUMNS,
    SWEEP_SUMMARY_EXPORT_COLUMNS,
    bootstrap_sofa_probability_ci,
    build_cache_key,
    build_simulation_config,
    compute_divergence_metrics,
    extract_sofa_probabilities,
    format_sweep_replicates_for_export,
    format_sweep_summary_for_export,
    run_single_scenario,
    run_sweep_scenario,
)
from sofa_resp_sim.reporting.view_model import default_run_request, normalize_sweep_request
from sofa_resp_sim.resp_simulation import run_replicates


def _manual_summary(
    replicates: pd.DataFrame,
    *,
    obs_freq: int,
    noise_sd: float,
    room_air: float,
):
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


def _small_sweep_request(n_reps: int = 5):
    base = replace(default_run_request(), n_reps=n_reps, seed=77)
    return normalize_sweep_request(
        {
            "base_request": base,
            "obs_freq_minutes_values": "15,60",
            "noise_sd_values": "0.5,1.0",
            "room_air_threshold_values": "92,94",
            "heatmap_metric": "p_sofa_3plus",
        }
    )


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


def test_bootstrap_ci_is_deterministic_for_seed():
    request = replace(default_run_request(), n_reps=50, seed=9)
    _, replicates = run_single_scenario(request)

    ci_a = bootstrap_sofa_probability_ci(
        replicates,
        n_bootstrap=200,
        ci_level=0.95,
        seed=123,
    )
    ci_b = bootstrap_sofa_probability_ci(
        replicates,
        n_bootstrap=200,
        ci_level=0.95,
        seed=123,
    )

    pd.testing.assert_frame_equal(ci_a, ci_b)


def test_bootstrap_ci_invariants():
    request = replace(default_run_request(), n_reps=60, seed=5)
    _, replicates = run_single_scenario(request)

    ci = bootstrap_sofa_probability_ci(
        replicates,
        n_bootstrap=200,
        ci_level=0.95,
        seed=42,
    )

    assert ci["score"].tolist() == [0, 1, 2, 3, 4]
    assert ((ci["p_scenario"] >= 0) & (ci["p_scenario"] <= 1)).all()
    assert ((ci["ci_lower"] >= 0) & (ci["ci_upper"] <= 1)).all()
    assert (ci["ci_lower"] <= ci["ci_upper"]).all()
    assert (ci["ci_lower"] <= ci["p_scenario"]).all()
    assert (ci["p_scenario"] <= ci["ci_upper"]).all()


def test_divergence_metrics_invariants_and_identity_zero():
    request = replace(default_run_request(), n_reps=80, seed=21)
    _, replicates = run_single_scenario(request)
    scenario = extract_sofa_probabilities(replicates)

    identical_metrics = compute_divergence_metrics(scenario, scenario)
    assert identical_metrics["l1_distance"] == pytest.approx(0.0)
    assert identical_metrics["jensen_shannon_distance"] == pytest.approx(0.0)

    shifted_reference = pd.Series(
        [0.05, 0.05, 0.2, 0.4, 0.3],
        index=[f"p_sofa_{score}" for score in range(5)],
    )
    shifted_metrics = compute_divergence_metrics(scenario, shifted_reference)

    assert shifted_metrics["l1_distance"] >= 0
    assert shifted_metrics["jensen_shannon_distance"] >= 0


def test_run_sweep_scenario_is_deterministic_for_seed():
    request = _small_sweep_request(n_reps=4)

    summary_a, reps_a = run_sweep_scenario(request, return_replicates=True)
    summary_b, reps_b = run_sweep_scenario(request, return_replicates=True)

    pd.testing.assert_frame_equal(summary_a, summary_b)
    pd.testing.assert_frame_equal(reps_a, reps_b)


def test_run_sweep_row_count_and_derived_metric():
    request = _small_sweep_request(n_reps=3)
    product_size = (
        len(request.obs_freq_minutes_values)
        * len(request.noise_sd_values)
        * len(request.room_air_threshold_values)
    )

    summary, replicates = run_sweep_scenario(request, return_replicates=True)

    assert summary.shape[0] == product_size
    assert replicates.shape[0] == product_size * request.base_request.n_reps
    assert (summary["p_sofa_3plus"] == summary["p_sofa_3"] + summary["p_sofa_4"]).all()


def test_run_sweep_scenario_guardrail_blocks_large_workloads():
    request = _small_sweep_request(n_reps=10000)

    with pytest.raises(ValueError, match="exceeds guardrail"):
        run_sweep_scenario(request, return_replicates=True)

    total_runs = (
        len(request.obs_freq_minutes_values)
        * len(request.noise_sd_values)
        * len(request.room_air_threshold_values)
        * request.base_request.n_reps
    )
    assert total_runs > DEFAULT_SWEEP_GUARDRAIL_RUNS


def test_sweep_export_formatters_return_stable_columns():
    request = _small_sweep_request(n_reps=3)
    summary, replicates = run_sweep_scenario(request, return_replicates=True)

    summary_export = format_sweep_summary_for_export(summary)
    replicates_export = format_sweep_replicates_for_export(replicates)

    assert summary_export.columns[: len(SWEEP_SUMMARY_EXPORT_COLUMNS)].tolist() == (
        SWEEP_SUMMARY_EXPORT_COLUMNS
    )
    assert replicates_export.columns[: len(SWEEP_REPLICATE_EXPORT_COLUMNS)].tolist() == (
        SWEEP_REPLICATE_EXPORT_COLUMNS
    )
