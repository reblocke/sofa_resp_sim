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
from .presets import (
    APPLET_PRESET_VERSION,
    apply_run_preset,
    apply_sweep_preset,
    list_run_presets,
    list_sweep_presets,
)
from .reference import REQUIRED_PROBABILITY_COLUMNS, load_builtin_reference
from .view_model import (
    SPO2_ROUNDING_OPTIONS,
    SWEEP_HEATMAP_METRICS,
    AppletRunRequest,
    AppletSweepRequest,
    default_run_request,
    estimate_total_sweep_runs,
    normalize_request,
    normalize_sweep_request,
)

RUN_WIDGET_KEYS = {
    "admit_date": "run_admit_date",
    "admit_time": "run_admit_time",
    "acute_start_hours": "run_acute_start_hours",
    "acute_end_hours": "run_acute_end_hours",
    "include_baseline": "run_include_baseline",
    "baseline_days_before": "run_baseline_days_before",
    "baseline_duration_hours": "run_baseline_duration_hours",
    "obs_freq_minutes": "run_obs_freq_minutes",
    "spo2_mean": "run_spo2_mean",
    "spo2_sd": "run_spo2_sd",
    "ar1": "run_ar1",
    "desat_prob": "run_desat_prob",
    "desat_depth": "run_desat_depth",
    "desat_duration_minutes": "run_desat_duration_minutes",
    "measurement_sd": "run_measurement_sd",
    "spo2_rounding": "run_spo2_rounding",
    "room_air_threshold": "run_room_air_threshold",
    "support_based_on_observed": "run_support_based_on_observed",
    "fio2_meas_prob": "run_fio2_meas_prob",
    "oxygen_flow_min": "run_oxygen_flow_min",
    "oxygen_flow_max": "run_oxygen_flow_max",
    "altitude_factor": "run_altitude_factor",
    "n_reps": "run_n_reps",
    "seed": "run_seed",
}

SWEEP_WIDGET_KEYS = {
    "obs_values": "sweep_obs_values",
    "noise_values": "sweep_noise_values",
    "room_values": "sweep_room_values",
    "heatmap_metric": "sweep_heatmap_metric",
}


def main() -> None:
    import plotly.graph_objects as go
    import streamlit as st

    st.set_page_config(page_title="Respiratory SOFA Applet", layout="wide")
    st.title("Respiratory SOFA Simulation Applet")
    st.caption(
        "Milestone 4: hardened presets, sweep/export flow, uncertainty views, "
        "and handoff-ready runbook."
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
    _ = defaults

    st.sidebar.header("Scenario Controls")
    run_mode = st.sidebar.radio("Run mode", ["Single scenario", "Parameter sweep"])

    st.sidebar.subheader("Presets")
    run_preset_name = st.sidebar.selectbox(
        "Scenario preset",
        options=list_run_presets(),
        key="run_preset_name",
    )
    sweep_preset_name = st.sidebar.selectbox(
        "Sweep preset",
        options=list_sweep_presets(),
        key="sweep_preset_name",
    )
    st.sidebar.caption(f"Preset version: {APPLET_PRESET_VERSION}")

    run_preset_request = apply_run_preset(run_preset_name)
    sweep_preset_request = apply_sweep_preset(
        sweep_preset_name,
        base_request=run_preset_request,
    )

    _set_run_widget_state(st.session_state, run_preset_request, overwrite=False)
    _set_sweep_widget_state(st.session_state, sweep_preset_request, overwrite=False)

    if st.sidebar.button("Reset controls to selected preset"):
        _set_run_widget_state(st.session_state, run_preset_request, overwrite=True)
        _set_sweep_widget_state(st.session_state, sweep_preset_request, overwrite=True)
        st.rerun()

    request = _render_base_controls(st)
    sweep_request_raw: dict | None = None

    if run_mode == "Parameter sweep":
        st.sidebar.subheader("Sweep Controls")
        obs_values_raw = st.sidebar.text_input(
            "obs_freq_minutes sweep values",
            key=SWEEP_WIDGET_KEYS["obs_values"],
        )
        noise_values_raw = st.sidebar.text_input(
            "noise_sd sweep values",
            key=SWEEP_WIDGET_KEYS["noise_values"],
        )
        room_air_values_raw = st.sidebar.text_input(
            "room_air_threshold sweep values",
            key=SWEEP_WIDGET_KEYS["room_values"],
        )
        heatmap_metric = st.sidebar.selectbox(
            "Heatmap metric",
            options=list(SWEEP_HEATMAP_METRICS),
            key=SWEEP_WIDGET_KEYS["heatmap_metric"],
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


def _render_base_controls(st) -> AppletRunRequest:
    st.sidebar.subheader("Timeline")
    admit_date = st.sidebar.date_input("admit_dts (date)", key=RUN_WIDGET_KEYS["admit_date"])
    admit_time = st.sidebar.time_input("admit_dts (time)", key=RUN_WIDGET_KEYS["admit_time"])
    admit_dts = pd.Timestamp(datetime.combine(admit_date, admit_time))

    acute_start_hours = st.sidebar.number_input(
        "acute_start_hours",
        step=1.0,
        format="%.2f",
        key=RUN_WIDGET_KEYS["acute_start_hours"],
    )
    acute_end_hours = st.sidebar.number_input(
        "acute_end_hours",
        step=1.0,
        format="%.2f",
        key=RUN_WIDGET_KEYS["acute_end_hours"],
    )
    include_baseline = st.sidebar.checkbox(
        "include_baseline",
        key=RUN_WIDGET_KEYS["include_baseline"],
    )
    baseline_days_before = st.sidebar.number_input(
        "baseline_days_before",
        min_value=1,
        step=1,
        key=RUN_WIDGET_KEYS["baseline_days_before"],
    )
    baseline_duration_hours = st.sidebar.number_input(
        "baseline_duration_hours",
        min_value=0.5,
        step=0.5,
        key=RUN_WIDGET_KEYS["baseline_duration_hours"],
    )

    st.sidebar.subheader("Process")
    obs_freq_minutes = st.sidebar.number_input(
        "obs_freq_minutes",
        min_value=1,
        step=1,
        key=RUN_WIDGET_KEYS["obs_freq_minutes"],
    )
    spo2_mean = st.sidebar.number_input(
        "spo2_mean",
        min_value=0.0,
        max_value=100.0,
        step=0.5,
        key=RUN_WIDGET_KEYS["spo2_mean"],
    )
    spo2_sd = st.sidebar.number_input(
        "spo2_sd",
        min_value=0.01,
        step=0.1,
        key=RUN_WIDGET_KEYS["spo2_sd"],
    )
    ar1 = st.sidebar.number_input(
        "ar1",
        min_value=-0.99,
        max_value=0.99,
        step=0.05,
        key=RUN_WIDGET_KEYS["ar1"],
    )
    desat_prob = st.sidebar.number_input(
        "desat_prob",
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        key=RUN_WIDGET_KEYS["desat_prob"],
    )
    desat_depth = st.sidebar.number_input(
        "desat_depth",
        min_value=0.0,
        step=0.5,
        key=RUN_WIDGET_KEYS["desat_depth"],
    )
    desat_duration_minutes = st.sidebar.number_input(
        "desat_duration_minutes",
        min_value=1,
        step=1,
        key=RUN_WIDGET_KEYS["desat_duration_minutes"],
    )

    st.sidebar.subheader("Measurement and Support")
    measurement_sd = st.sidebar.number_input(
        "measurement_sd",
        min_value=0.0,
        step=0.1,
        key=RUN_WIDGET_KEYS["measurement_sd"],
    )
    spo2_rounding = st.sidebar.selectbox(
        "spo2_rounding",
        options=list(SPO2_ROUNDING_OPTIONS),
        key=RUN_WIDGET_KEYS["spo2_rounding"],
    )
    room_air_threshold = st.sidebar.number_input(
        "room_air_threshold",
        step=1.0,
        key=RUN_WIDGET_KEYS["room_air_threshold"],
    )
    support_based_on_observed = st.sidebar.checkbox(
        "support_based_on_observed",
        key=RUN_WIDGET_KEYS["support_based_on_observed"],
    )
    fio2_meas_prob = st.sidebar.number_input(
        "fio2_meas_prob",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        key=RUN_WIDGET_KEYS["fio2_meas_prob"],
    )
    oxygen_flow_min = st.sidebar.number_input(
        "oxygen_flow_min",
        step=0.5,
        key=RUN_WIDGET_KEYS["oxygen_flow_min"],
    )
    oxygen_flow_max = st.sidebar.number_input(
        "oxygen_flow_max",
        step=0.5,
        key=RUN_WIDGET_KEYS["oxygen_flow_max"],
    )
    altitude_factor = st.sidebar.number_input(
        "altitude_factor",
        step=0.05,
        key=RUN_WIDGET_KEYS["altitude_factor"],
    )

    st.sidebar.subheader("Simulation")
    n_reps = st.sidebar.number_input(
        "n_reps",
        min_value=1,
        step=100,
        key=RUN_WIDGET_KEYS["n_reps"],
    )
    seed = st.sidebar.number_input(
        "seed",
        min_value=0,
        step=1,
        key=RUN_WIDGET_KEYS["seed"],
    )

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


def _set_state_value(state, key: str, value, overwrite: bool) -> None:
    if overwrite or key not in state:
        state[key] = value


def _set_run_widget_state(state, request: AppletRunRequest, *, overwrite: bool) -> None:
    dt = request.admit_dts.to_pydatetime()
    _set_state_value(state, RUN_WIDGET_KEYS["admit_date"], dt.date(), overwrite)
    _set_state_value(state, RUN_WIDGET_KEYS["admit_time"], dt.time(), overwrite)
    _set_state_value(
        state,
        RUN_WIDGET_KEYS["acute_start_hours"],
        request.acute_start_hours,
        overwrite,
    )
    _set_state_value(
        state,
        RUN_WIDGET_KEYS["acute_end_hours"],
        request.acute_end_hours,
        overwrite,
    )
    _set_state_value(
        state,
        RUN_WIDGET_KEYS["include_baseline"],
        request.include_baseline,
        overwrite,
    )
    _set_state_value(
        state,
        RUN_WIDGET_KEYS["baseline_days_before"],
        request.baseline_days_before,
        overwrite,
    )
    _set_state_value(
        state,
        RUN_WIDGET_KEYS["baseline_duration_hours"],
        request.baseline_duration_hours,
        overwrite,
    )
    _set_state_value(
        state,
        RUN_WIDGET_KEYS["obs_freq_minutes"],
        request.obs_freq_minutes,
        overwrite,
    )
    _set_state_value(state, RUN_WIDGET_KEYS["spo2_mean"], request.spo2_mean, overwrite)
    _set_state_value(state, RUN_WIDGET_KEYS["spo2_sd"], request.spo2_sd, overwrite)
    _set_state_value(state, RUN_WIDGET_KEYS["ar1"], request.ar1, overwrite)
    _set_state_value(state, RUN_WIDGET_KEYS["desat_prob"], request.desat_prob, overwrite)
    _set_state_value(state, RUN_WIDGET_KEYS["desat_depth"], request.desat_depth, overwrite)
    _set_state_value(
        state,
        RUN_WIDGET_KEYS["desat_duration_minutes"],
        request.desat_duration_minutes,
        overwrite,
    )
    _set_state_value(state, RUN_WIDGET_KEYS["measurement_sd"], request.measurement_sd, overwrite)
    _set_state_value(state, RUN_WIDGET_KEYS["spo2_rounding"], request.spo2_rounding, overwrite)
    _set_state_value(
        state,
        RUN_WIDGET_KEYS["room_air_threshold"],
        request.room_air_threshold,
        overwrite,
    )
    _set_state_value(
        state,
        RUN_WIDGET_KEYS["support_based_on_observed"],
        request.support_based_on_observed,
        overwrite,
    )
    _set_state_value(state, RUN_WIDGET_KEYS["fio2_meas_prob"], request.fio2_meas_prob, overwrite)
    _set_state_value(state, RUN_WIDGET_KEYS["oxygen_flow_min"], request.oxygen_flow_min, overwrite)
    _set_state_value(state, RUN_WIDGET_KEYS["oxygen_flow_max"], request.oxygen_flow_max, overwrite)
    _set_state_value(state, RUN_WIDGET_KEYS["altitude_factor"], request.altitude_factor, overwrite)
    _set_state_value(state, RUN_WIDGET_KEYS["n_reps"], request.n_reps, overwrite)
    _set_state_value(state, RUN_WIDGET_KEYS["seed"], request.seed, overwrite)


def _set_sweep_widget_state(state, request: AppletSweepRequest, *, overwrite: bool) -> None:
    _set_state_value(
        state,
        SWEEP_WIDGET_KEYS["obs_values"],
        ",".join(str(value) for value in request.obs_freq_minutes_values),
        overwrite,
    )
    _set_state_value(
        state,
        SWEEP_WIDGET_KEYS["noise_values"],
        ",".join(str(value) for value in request.noise_sd_values),
        overwrite,
    )
    _set_state_value(
        state,
        SWEEP_WIDGET_KEYS["room_values"],
        ",".join(str(value) for value in request.room_air_threshold_values),
        overwrite,
    )
    _set_state_value(
        state,
        SWEEP_WIDGET_KEYS["heatmap_metric"],
        request.heatmap_metric,
        overwrite,
    )


def _default_reference_path() -> Path:
    return Path(__file__).resolve().parents[4] / "artifacts" / "resp_sofa_sim_summary.csv"


if __name__ == "__main__":
    main()
