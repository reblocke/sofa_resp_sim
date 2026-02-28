from __future__ import annotations

from dataclasses import replace

from sofa_resp_sim.web.app_services import build_sweep_heatmap_frame, run_sweep_scenario
from sofa_resp_sim.web.view_model import default_run_request, normalize_sweep_request


def _build_request():
    base = replace(default_run_request(), n_reps=4, seed=101)
    return normalize_sweep_request(
        {
            "base_request": base,
            "obs_freq_minutes_values": "15,30,60",
            "noise_sd_values": "0.5,1.0",
            "room_air_threshold_values": "92,94",
            "heatmap_metric": "p_sofa_3plus",
        }
    )


def test_build_sweep_heatmap_frame_shape_and_axis_coverage():
    request = _build_request()
    summary, _ = run_sweep_scenario(request, return_replicates=False)
    heatmap = build_sweep_heatmap_frame(summary, metric="p_sofa_3plus")

    assert heatmap.shape[0] == (
        len(request.obs_freq_minutes_values)
        * len(request.noise_sd_values)
        * len(request.room_air_threshold_values)
    )
    assert sorted(heatmap["obs_freq_minutes"].unique().tolist()) == list(
        request.obs_freq_minutes_values
    )
    assert sorted(heatmap["noise_sd"].unique().tolist()) == list(request.noise_sd_values)


def test_build_sweep_heatmap_frame_has_room_air_facets():
    request = _build_request()
    summary, _ = run_sweep_scenario(request, return_replicates=False)
    heatmap = build_sweep_heatmap_frame(summary, metric="p_sofa_3plus")

    assert sorted(heatmap["room_air_threshold"].unique().tolist()) == list(
        request.room_air_threshold_values
    )



def test_build_sweep_heatmap_frame_metric_selection():
    request = _build_request()
    summary, _ = run_sweep_scenario(request, return_replicates=False)

    heatmap_3plus = build_sweep_heatmap_frame(summary, metric="p_sofa_3plus")
    heatmap_4 = build_sweep_heatmap_frame(summary, metric="p_sofa_4")
    heatmap_count = build_sweep_heatmap_frame(summary, metric="mean_count_pf_ratio_acute")

    assert "metric_value" in heatmap_3plus.columns
    assert "metric_value" in heatmap_4.columns
    assert "metric_value" in heatmap_count.columns
    assert not heatmap_3plus["metric_value"].equals(heatmap_count["metric_value"])
