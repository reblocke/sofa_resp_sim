from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .app_services import (
    DEFAULT_BOOTSTRAP_SAMPLES,
    DEFAULT_CI_LEVEL,
    DEFAULT_SWEEP_GUARDRAIL_RUNS,
    build_cache_key,
    build_sweep_cache_key,
    build_sweep_heatmap_frame,
    build_uncertainty_table,
    compute_divergence_metrics,
    format_sweep_replicates_for_export,
    format_sweep_summary_for_export,
    parse_request_payload,
    parse_sweep_payload,
    run_single_scenario,
    run_sweep_scenario,
    serialize_request_payload,
    serialize_sweep_payload,
)
from .reference import REQUIRED_PROBABILITY_COLUMNS, load_builtin_reference
from .view_model import (
    SPO2_ROUNDING_OPTIONS,
    SWEEP_HEATMAP_METRICS,
    AppletRunRequest,
    AppletSweepRequest,
    default_run_request,
    default_sweep_request,
    estimate_total_sweep_runs,
    normalize_request,
    normalize_sweep_request,
)

SWEEP_PRESETS = {
    "Quick": {
        "obs_freq_minutes_values": "15,30,60",
        "noise_sd_values": "0.5,1.0,1.5",
        "room_air_threshold_values": "92,94,96",
    },
    "Broad": {
        "obs_freq_minutes_values": "5,15,30,60",
        "noise_sd_values": "0.5,1.0,1.5,2.0",
        "room_air_threshold_values": "90,92,94",
    },
    "Custom": None,
}


def main() -> None:
    import plotly.graph_objects as go
    import streamlit as st

    st.set_page_config(page_title="Respiratory SOFA Applet", layout="wide")
    st.title("Respiratory SOFA Simulation Applet")
    st.caption(
        "Milestone 3: single scenario plus parameter sweep with heatmaps and CSV exports."
    )

    defaults = default_run_request()
    run_clicked, run_mode, request, sweep_request_raw = _render_sidebar(st, defaults)

    if not run_clicked:
        st.info("Configure parameters in the sidebar and click Run simulation.")
        return

    if run_mode == "Single scenario":
        _run_single_scenario_flow(st, go, request)
        return

    _run_sweep_flow(st, go, sweep_request_raw)


def _run_single_scenario_flow(st, go, request: AppletRunRequest) -> None:
    try:
        request = normalize_request(request)
    except ValueError as exc:
        st.error(f"Invalid request: {exc}")
        return

    cache_key = build_cache_key(request)
    payload = serialize_request_payload(request)

    @st.cache_data(show_spinner=False)
    def _run_cached(serialized_payload: str, deterministic_key: str):
        _ = deterministic_key
        parsed_request = parse_request_payload(serialized_payload)
        return run_single_scenario(parsed_request)

    with st.spinner("Running simulation..."):
        summary_df, replicates_df = _run_cached(payload, cache_key)

    reference_path = _default_reference_path()
    try:
        reference_df = load_builtin_reference(reference_path)
    except (OSError, ValueError) as exc:
        st.error(f"Failed to load built-in reference ({reference_path}): {exc}")
        return

    scenario_probs = summary_df.loc[0, REQUIRED_PROBABILITY_COLUMNS]
    reference_probs = reference_df.loc[0, REQUIRED_PROBABILITY_COLUMNS]
    comparison_df = pd.DataFrame(
        {
            "score": [str(score) for score in range(5)],
            "scenario": scenario_probs.values,
            "reference": reference_probs.values,
        }
    )
    comparison_df["delta"] = comparison_df["scenario"] - comparison_df["reference"]

    tabs = st.tabs(["Distribution", "Uncertainty"])

    with tabs[0]:
        _render_distribution_tab(st, go, summary_df, replicates_df, comparison_df)

    with tabs[1]:
        _render_uncertainty_tab(
            st=st,
            go=go,
            request=request,
            replicates_df=replicates_df,
            scenario_probs=scenario_probs,
            reference_probs=reference_probs,
        )


def _run_sweep_flow(st, go, sweep_request_raw) -> None:
    if sweep_request_raw is None:
        st.error("Sweep request is missing. Reconfigure sweep controls and retry.")
        return

    try:
        sweep_request = normalize_sweep_request(sweep_request_raw)
    except ValueError as exc:
        st.error(f"Invalid sweep request: {exc}")
        return

    total_runs = estimate_total_sweep_runs(sweep_request)
    combinations = (
        len(sweep_request.obs_freq_minutes_values)
        * len(sweep_request.noise_sd_values)
        * len(sweep_request.room_air_threshold_values)
    )
    if total_runs > DEFAULT_SWEEP_GUARDRAIL_RUNS:
        st.error(
            "Sweep workload exceeds guardrail. "
            f"Combinations={combinations}, n_reps={sweep_request.base_request.n_reps}, "
            f"total_runs={total_runs}, limit={DEFAULT_SWEEP_GUARDRAIL_RUNS}."
        )
        return

    cache_key = build_sweep_cache_key(sweep_request)
    payload = serialize_sweep_payload(sweep_request)

    @st.cache_data(show_spinner=False)
    def _run_sweep_cached(serialized_payload: str, deterministic_key: str):
        _ = deterministic_key
        parsed_request = parse_sweep_payload(serialized_payload)
        return run_sweep_scenario(parsed_request, return_replicates=True)

    with st.spinner("Running parameter sweep..."):
        try:
            summary_df, replicates_df = _run_sweep_cached(payload, cache_key)
        except ValueError as exc:
            st.error(f"Sweep run failed: {exc}")
            return

    _render_sweep_tab(
        st=st,
        go=go,
        sweep_request=sweep_request,
        summary_df=summary_df,
        replicates_df=replicates_df,
    )


def _render_sweep_tab(
    st,
    go,
    sweep_request: AppletSweepRequest,
    summary_df: pd.DataFrame,
    replicates_df: pd.DataFrame,
) -> None:
    st.subheader("Sweep Summary")

    summary_export = format_sweep_summary_for_export(summary_df)
    replicates_export = format_sweep_replicates_for_export(replicates_df)

    if summary_export.empty:
        st.error("Sweep returned no summary rows.")
        return

    st.dataframe(summary_export, use_container_width=True)

    st.subheader("Sweep Heatmaps")
    heatmap_frame = build_sweep_heatmap_frame(summary_export, sweep_request.heatmap_metric)
    thresholds = sorted(heatmap_frame["room_air_threshold"].unique())

    for threshold in thresholds:
        subset = heatmap_frame.loc[
            heatmap_frame["room_air_threshold"] == threshold,
            ["obs_freq_minutes", "noise_sd", "metric_value"],
        ]
        pivot = subset.pivot(
            index="obs_freq_minutes",
            columns="noise_sd",
            values="metric_value",
        )
        if pivot.isna().any().any():
            st.warning(
                "Missing sweep cells detected in heatmap grid "
                f"for room_air_threshold={threshold}."
            )

        fig = go.Figure(
            data=go.Heatmap(
                z=pivot.to_numpy(),
                x=[str(value) for value in pivot.columns.tolist()],
                y=[str(value) for value in pivot.index.tolist()],
                colorscale="Viridis",
                colorbar_title=sweep_request.heatmap_metric,
            )
        )
        fig.update_layout(
            title=(
                f"{sweep_request.heatmap_metric} "
                f"(room_air_threshold={threshold})"
            ),
            xaxis_title="noise_sd",
            yaxis_title="obs_freq_minutes",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Sweep Exports")
    summary_csv = summary_export.to_csv(index=False)
    replicates_csv = replicates_export.to_csv(index=False)

    export_col_1, export_col_2 = st.columns(2)
    export_col_1.download_button(
        label="Download sweep summary CSV",
        data=summary_csv,
        file_name="resp_applet_sweep_summary.csv",
        mime="text/csv",
    )
    export_col_2.download_button(
        label="Download sweep replicates CSV",
        data=replicates_csv,
        file_name="resp_applet_sweep_replicates.csv",
        mime="text/csv",
    )


def _render_distribution_tab(st, go, summary_df, replicates_df, comparison_df):
    dist_col, delta_col = st.columns(2)
    with dist_col:
        dist_fig = go.Figure()
        dist_fig.add_trace(
            go.Bar(
                x=comparison_df["score"],
                y=comparison_df["scenario"],
                name="Scenario",
                marker_color="#3b82f6",
            )
        )
        dist_fig.add_trace(
            go.Scatter(
                x=comparison_df["score"],
                y=comparison_df["reference"],
                name="Built-in reference",
                mode="lines+markers",
                marker_color="#ef4444",
            )
        )
        dist_fig.update_layout(
            title="SOFA Probability Distribution (0-4)",
            xaxis_title="SOFA respiratory score",
            yaxis_title="Probability",
            yaxis=dict(range=[0, 1]),
            barmode="group",
        )
        st.plotly_chart(dist_fig, use_container_width=True)

    with delta_col:
        delta_fig = go.Figure()
        delta_fig.add_trace(
            go.Bar(
                x=comparison_df["score"],
                y=comparison_df["delta"],
                marker_color="#10b981",
                name="Scenario - reference",
            )
        )
        delta_fig.update_layout(
            title="Delta vs Built-in Reference",
            xaxis_title="SOFA respiratory score",
            yaxis_title="Probability delta",
        )
        st.plotly_chart(delta_fig, use_container_width=True)

    st.subheader("Scenario Summary")
    st.dataframe(summary_df, use_container_width=True)

    st.subheader("Replicate Summary")
    replicate_summary = (
        replicates_df[
            [
                "sofa_pulm",
                "sofa_pulm_bl",
                "sofa_pulm_delta",
                "count_pf_ratio_acute",
                "n_qualifying_pf_records_acute",
                "n_qualifying_pf_records_baseline",
            ]
        ]
        .describe()
        .T
    )
    replicate_summary["single_pf_suppressed_rate"] = float(
        replicates_df["single_pf_suppressed"].mean()
    )
    st.dataframe(replicate_summary, use_container_width=True)


def _render_uncertainty_tab(
    st,
    go,
    request: AppletRunRequest,
    replicates_df: pd.DataFrame,
    scenario_probs: pd.Series,
    reference_probs: pd.Series,
):
    if request.n_reps < 100:
        st.warning(
            "n_reps is below 100; bootstrap confidence intervals may be unstable."
        )

    uncertainty_df = build_uncertainty_table(
        replicates=replicates_df,
        reference_probs=reference_probs,
        n_bootstrap=DEFAULT_BOOTSTRAP_SAMPLES,
        ci_level=DEFAULT_CI_LEVEL,
        seed=request.seed,
    )
    metrics = compute_divergence_metrics(scenario_probs, reference_probs)

    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
    metric_col_1.metric("L1 distance", f"{metrics['l1_distance']:.4f}")
    metric_col_2.metric(
        "Jensen-Shannon distance",
        f"{metrics['jensen_shannon_distance']:.4f}",
    )
    metric_col_3.metric(
        "Uncertainty method",
        f"{int(DEFAULT_CI_LEVEL * 100)}% bootstrap ({DEFAULT_BOOTSTRAP_SAMPLES})",
    )

    st.subheader("SOFA Probability Confidence Intervals")
    st.dataframe(uncertainty_df, use_container_width=True)

    ci_plot_col, count_plot_col = st.columns(2)

    with ci_plot_col:
        ci_fig = go.Figure()
        ci_fig.add_trace(
            go.Scatter(
                x=uncertainty_df["score"].astype(str),
                y=uncertainty_df["p_scenario"],
                mode="lines+markers",
                name="Scenario",
                line=dict(color="#2563eb"),
                error_y=dict(
                    type="data",
                    symmetric=False,
                    array=(
                        uncertainty_df["ci_upper"] - uncertainty_df["p_scenario"]
                    ),
                    arrayminus=(
                        uncertainty_df["p_scenario"] - uncertainty_df["ci_lower"]
                    ),
                ),
            )
        )
        ci_fig.add_trace(
            go.Scatter(
                x=uncertainty_df["score"].astype(str),
                y=uncertainty_df["p_reference"],
                mode="lines+markers",
                name="Built-in reference",
                line=dict(color="#dc2626"),
            )
        )
        ci_fig.update_layout(
            title="Scenario Probability with 95% Bootstrap CIs",
            xaxis_title="SOFA respiratory score",
            yaxis_title="Probability",
            yaxis=dict(range=[0, 1]),
        )
        st.plotly_chart(ci_fig, use_container_width=True)

    with count_plot_col:
        count_fig = go.Figure()
        count_fig.add_trace(
            go.Histogram(
                x=replicates_df["count_pf_ratio_acute"],
                marker_color="#0ea5e9",
                nbinsx=30,
                name="count_pf_ratio_acute",
            )
        )
        count_fig.update_layout(
            title="Distribution: count_pf_ratio_acute",
            xaxis_title="count_pf_ratio_acute",
            yaxis_title="Replicate frequency",
            bargap=0.05,
        )
        st.plotly_chart(count_fig, use_container_width=True)


def _render_sidebar(
    st,
    defaults: AppletRunRequest,
) -> tuple[bool, str, AppletRunRequest, dict | None]:
    st.sidebar.header("Scenario Controls")
    run_mode = st.sidebar.radio("Run mode", ["Single scenario", "Parameter sweep"])

    request = _render_base_controls(st, defaults)
    sweep_request_raw: dict | None = None

    if run_mode == "Parameter sweep":
        sweep_defaults = default_sweep_request()
        _render_sweep_control_defaults(st)

        obs_values_raw = st.sidebar.text_input(
            "obs_freq_minutes sweep values",
            key="sweep_obs_values",
        )
        noise_values_raw = st.sidebar.text_input(
            "noise_sd sweep values",
            key="sweep_noise_values",
        )
        room_air_values_raw = st.sidebar.text_input(
            "room_air_threshold sweep values",
            key="sweep_room_values",
        )
        heatmap_metric = st.sidebar.selectbox(
            "Heatmap metric",
            options=list(SWEEP_HEATMAP_METRICS),
            index=list(SWEEP_HEATMAP_METRICS).index(sweep_defaults.heatmap_metric),
        )

        sweep_request_raw = {
            "base_request": request,
            "obs_freq_minutes_values": obs_values_raw,
            "noise_sd_values": noise_values_raw,
            "room_air_threshold_values": room_air_values_raw,
            "heatmap_metric": heatmap_metric,
        }

        try:
            preview_request = normalize_sweep_request(sweep_request_raw)
            combinations = (
                len(preview_request.obs_freq_minutes_values)
                * len(preview_request.noise_sd_values)
                * len(preview_request.room_air_threshold_values)
            )
            total_runs = estimate_total_sweep_runs(preview_request)
            st.sidebar.caption(
                f"Sweep workload: combinations={combinations}, total_runs={total_runs}."
            )
            if total_runs > DEFAULT_SWEEP_GUARDRAIL_RUNS:
                st.sidebar.error(
                    "Sweep exceeds guardrail and will be blocked on run: "
                    f"{total_runs} > {DEFAULT_SWEEP_GUARDRAIL_RUNS}."
                )
        except ValueError as exc:
            st.sidebar.error(f"Sweep input error: {exc}")

    run_clicked = st.sidebar.button("Run simulation", type="primary")
    return run_clicked, run_mode, request, sweep_request_raw


def _render_base_controls(st, defaults: AppletRunRequest) -> AppletRunRequest:
    st.sidebar.subheader("Timeline")
    default_dt = defaults.admit_dts.to_pydatetime()
    admit_date = st.sidebar.date_input("admit_dts (date)", value=default_dt.date())
    admit_time = st.sidebar.time_input("admit_dts (time)", value=default_dt.time())
    admit_dts = pd.Timestamp(datetime.combine(admit_date, admit_time))

    acute_start_hours = st.sidebar.number_input(
        "acute_start_hours",
        value=defaults.acute_start_hours,
        step=1.0,
        format="%.2f",
    )
    acute_end_hours = st.sidebar.number_input(
        "acute_end_hours",
        value=defaults.acute_end_hours,
        step=1.0,
        format="%.2f",
    )
    include_baseline = st.sidebar.checkbox(
        "include_baseline",
        value=defaults.include_baseline,
    )
    baseline_days_before = st.sidebar.number_input(
        "baseline_days_before",
        min_value=1,
        value=defaults.baseline_days_before,
        step=1,
    )
    baseline_duration_hours = st.sidebar.number_input(
        "baseline_duration_hours",
        min_value=0.5,
        value=defaults.baseline_duration_hours,
        step=0.5,
    )

    st.sidebar.subheader("Process")
    obs_freq_minutes = st.sidebar.number_input(
        "obs_freq_minutes",
        min_value=1,
        value=defaults.obs_freq_minutes,
        step=1,
    )
    spo2_mean = st.sidebar.number_input(
        "spo2_mean",
        min_value=0.0,
        max_value=100.0,
        value=defaults.spo2_mean,
        step=0.5,
    )
    spo2_sd = st.sidebar.number_input(
        "spo2_sd",
        min_value=0.01,
        value=defaults.spo2_sd,
        step=0.1,
    )
    ar1 = st.sidebar.number_input(
        "ar1",
        min_value=-0.99,
        max_value=0.99,
        value=defaults.ar1,
        step=0.05,
    )
    desat_prob = st.sidebar.number_input(
        "desat_prob",
        min_value=0.0,
        max_value=1.0,
        value=defaults.desat_prob,
        step=0.01,
    )
    desat_depth = st.sidebar.number_input(
        "desat_depth",
        min_value=0.0,
        value=defaults.desat_depth,
        step=0.5,
    )
    desat_duration_minutes = st.sidebar.number_input(
        "desat_duration_minutes",
        min_value=1,
        value=defaults.desat_duration_minutes,
        step=1,
    )

    st.sidebar.subheader("Measurement and Support")
    measurement_sd = st.sidebar.number_input(
        "measurement_sd",
        min_value=0.0,
        value=defaults.measurement_sd,
        step=0.1,
    )
    spo2_rounding = st.sidebar.selectbox(
        "spo2_rounding",
        options=list(SPO2_ROUNDING_OPTIONS),
        index=SPO2_ROUNDING_OPTIONS.index(defaults.spo2_rounding),
    )
    room_air_threshold = st.sidebar.number_input(
        "room_air_threshold",
        value=defaults.room_air_threshold,
        step=1.0,
    )
    support_based_on_observed = st.sidebar.checkbox(
        "support_based_on_observed",
        value=defaults.support_based_on_observed,
    )
    fio2_meas_prob = st.sidebar.number_input(
        "fio2_meas_prob",
        min_value=0.0,
        max_value=1.0,
        value=defaults.fio2_meas_prob,
        step=0.05,
    )
    oxygen_flow_min = st.sidebar.number_input(
        "oxygen_flow_min",
        value=defaults.oxygen_flow_min,
        step=0.5,
    )
    oxygen_flow_max = st.sidebar.number_input(
        "oxygen_flow_max",
        value=defaults.oxygen_flow_max,
        step=0.5,
    )
    altitude_factor = st.sidebar.number_input(
        "altitude_factor",
        value=defaults.altitude_factor,
        step=0.05,
    )

    st.sidebar.subheader("Simulation")
    n_reps = st.sidebar.number_input(
        "n_reps",
        min_value=1,
        value=defaults.n_reps,
        step=100,
    )
    seed = st.sidebar.number_input("seed", min_value=0, value=defaults.seed, step=1)

    request = AppletRunRequest(
        admit_dts=admit_dts,
        acute_start_hours=float(acute_start_hours),
        acute_end_hours=float(acute_end_hours),
        include_baseline=bool(include_baseline),
        baseline_days_before=int(baseline_days_before),
        baseline_duration_hours=float(baseline_duration_hours),
        obs_freq_minutes=int(obs_freq_minutes),
        spo2_mean=float(spo2_mean),
        spo2_sd=float(spo2_sd),
        ar1=float(ar1),
        desat_prob=float(desat_prob),
        desat_depth=float(desat_depth),
        desat_duration_minutes=int(desat_duration_minutes),
        measurement_sd=float(measurement_sd),
        spo2_rounding=spo2_rounding,
        room_air_threshold=float(room_air_threshold),
        support_based_on_observed=bool(support_based_on_observed),
        fio2_meas_prob=float(fio2_meas_prob),
        oxygen_flow_min=float(oxygen_flow_min),
        oxygen_flow_max=float(oxygen_flow_max),
        altitude_factor=float(altitude_factor),
        n_reps=int(n_reps),
        seed=int(seed),
    )
    return request


def _render_sweep_control_defaults(st) -> None:
    st.sidebar.subheader("Sweep Controls")
    selected_preset = st.sidebar.selectbox("Sweep preset", options=list(SWEEP_PRESETS.keys()))

    applied_preset = st.session_state.get("sweep_applied_preset")
    if applied_preset != selected_preset:
        preset_values = SWEEP_PRESETS[selected_preset]
        if preset_values is not None:
            st.session_state["sweep_obs_values"] = preset_values["obs_freq_minutes_values"]
            st.session_state["sweep_noise_values"] = preset_values["noise_sd_values"]
            st.session_state["sweep_room_values"] = preset_values["room_air_threshold_values"]
        else:
            defaults = default_sweep_request()
            st.session_state.setdefault(
                "sweep_obs_values",
                ",".join(str(value) for value in defaults.obs_freq_minutes_values),
            )
            st.session_state.setdefault(
                "sweep_noise_values",
                ",".join(str(value) for value in defaults.noise_sd_values),
            )
            st.session_state.setdefault(
                "sweep_room_values",
                ",".join(str(value) for value in defaults.room_air_threshold_values),
            )
        st.session_state["sweep_applied_preset"] = selected_preset


def _default_reference_path() -> Path:
    return Path(__file__).resolve().parents[4] / "artifacts" / "resp_sofa_sim_summary.csv"


if __name__ == "__main__":
    main()
