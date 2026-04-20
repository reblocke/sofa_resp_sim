"""SQL-parity respiratory SOFA scoring and event-level diagnostics.

Defines 24h respiratory SOFA bins (``sofa_ts``) and 6h sub-bins (``quartile``,
values 1–4) anchored to ``admit_dts``. Events that fall in the acute lead-in
window (``admit_dts`` minus ``acute_begin_days``) are assigned to the admit-day
bin so that pre-admit acute records share the same bin as day 0.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .resp_utils import oracle_round, spo2_to_pao2


@dataclass(frozen=True)
class RespScoringConfig:
    altitude_factor: float = 0.85
    acute_begin_days: float = -0.25
    baseline_months: int = 36
    baseline_end_days: int = 7
    time_col: str = "etime_ts"
    encounter_id_col: str | None = None


@dataclass(frozen=True)
class RespiratoryScoreResult:
    event_level: pd.DataFrame
    sofa_pulm: int
    sofa_pulm_bl: int
    sofa_pulm_delta: int
    count_pf_ratio_acute: int
    n_qualifying_pf_records_acute: int
    n_qualifying_pf_records_baseline: int
    single_pf_suppressed: bool


def score_respiratory(
    observations: pd.DataFrame,
    admit_dts: pd.Timestamp,
    config: RespScoringConfig | None = None,
) -> RespiratoryScoreResult:
    """Score respiratory SOFA with SQL-parity intermediate fields.

    Parameters
    ----------
    observations:
        Event-level table with at minimum:
        - ``etime_ts`` (datetime64)
        - ``spo2_obs`` (float)
        - ``pao2_meas`` (float, optional)
        - ``support_type`` (str, optional: ``IMV``, ``SURG IMV``, ``NIPPV``, ``HFNC``, ``OSA``)
        - ``is_room_air`` (bool)
        - ``oxygen_flow_rate`` (float)
        - ``fio2_set`` / ``fio2_meas`` / ``fio2_abg`` (float)
        - ``altitude_factor`` (float, optional; per-row override)
    admit_dts:
        Encounter admit timestamp used to define acute/baseline windows and
        day-0 binning for ``sofa_ts``/``quartile``.
    config:
        Optional ``RespScoringConfig`` overrides for defaults and column names.

    Returns
    -------
    RespiratoryScoreResult
        ``event_level`` includes diagnostic columns such as ``pao2_calc``,
        ``pao2``, ``pao2_priority``, ``fio2_prioritized``, ``fio2_priority``,
        lookback fields (minute/day), ``pf_ratio_temp``, ``sofa_resp_temp``,
        ``sofa_temp``, ``sofa_temp2``, ``resp_support_ind``, ``sofa_ts`` (24h
        bin start anchored to ``admit_dts``), and ``quartile`` (1–4 for 6h
        sub-bins). Encounter-level outputs include ``sofa_pulm`` (acute),
        ``sofa_pulm_bl`` (baseline), ``sofa_pulm_delta``,
        ``count_pf_ratio_acute``, and qualifying record counts.
    """
    if config is None:
        config = RespScoringConfig()

    admit_dts = pd.to_datetime(admit_dts)

    df = observations.copy()
    time_col = config.time_col
    if time_col not in df.columns:
        raise ValueError(f"Missing required time column: {time_col}")

    df[time_col] = pd.to_datetime(df[time_col])
    df = df.sort_values(time_col).reset_index(drop=True)

    df = _ensure_columns(
        df,
        {
            "spo2_obs": np.nan,
            "pao2_meas": np.nan,
            "fio2_set": np.nan,
            "fio2_meas": np.nan,
            "fio2_abg": np.nan,
            "oxygen_flow_rate": np.nan,
            "is_room_air": False,
            "support_type": None,
            "altitude_factor": config.altitude_factor,
        },
    )

    df["is_room_air"] = df["is_room_air"].fillna(False).astype(bool)
    support_type = df["support_type"].fillna("None")
    df["invasive_ind"] = support_type.isin(["IMV", "SURG IMV"])
    df["support_ind"] = support_type.isin(["HFNC", "NIPPV"])
    df["resp_support_ind"] = support_type.isin(["IMV", "NIPPV"]).astype(int)

    df["pao2_calc"] = spo2_to_pao2(df["spo2_obs"])
    df["pao2"] = df["pao2_meas"].combine_first(df["pao2_calc"])
    df["pao2_priority"] = np.where(
        df["pao2_meas"].notna(),
        1,
        np.where(df["pao2_calc"].notna(), 2, np.nan),
    )

    df[["fio2_prioritized", "fio2_priority"]] = df.apply(
        _assign_fio2_priority,
        axis=1,
        result_type="expand",
    )

    df = _compute_fio2_lookbacks(df, config)
    df["fio2_lookback"] = np.where(
        df["is_room_air"],
        df["fio2_prioritized"],
        _coalesce(
            [
                df["fio2_minute_lookback"],
                df["fio2_minute_look_fw"],
                df["fio2_day_lookback"],
            ]
        ),
    )
    df["fio2_lookback_priority"] = np.where(
        df["is_room_air"],
        df["fio2_priority"],
        _coalesce(
            [
                df["fio2_minute_lookback_priority"],
                df["fio2_minute_look_fw_priority"],
                df["fio2_day_lookback_priority"],
            ]
        ),
    )

    acute_begin = admit_dts + pd.to_timedelta(config.acute_begin_days, unit="D")
    adjusted_time = df[time_col].where(
        ~((df[time_col] >= acute_begin) & (df[time_col] < admit_dts)),
        admit_dts,
    )
    df["sofa_ts"] = adjusted_time.dt.floor("D")
    df["quartile"] = ((adjusted_time - df["sofa_ts"]).dt.total_seconds() // (6 * 3600)).astype(
        int
    ) + 1
    df["has_fio2_in_block"] = (
        df.groupby(["sofa_ts", "quartile"], dropna=False)["fio2_prioritized"]
        .transform(lambda s: s.notna().any())
        .astype(bool)
    )

    df["pf_ratio_temp"] = df.apply(_assign_pf_ratio_temp, axis=1)
    df["sofa_resp_rubric"] = df.apply(_assign_sofa_rubric, axis=1)
    df["sofa_resp_temp"] = df.apply(_apply_resp_detail_cap, axis=1)

    results = _apply_measures_logic(df, admit_dts, config)
    return results


def _ensure_columns(df: pd.DataFrame, defaults: dict) -> pd.DataFrame:
    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default
    return df


def _assign_fio2_priority(row: pd.Series) -> tuple[float, float]:
    if bool(row["is_room_air"]):
        return 21.0, 1.0
    if bool(row["invasive_ind"]):
        for column, priority in (("fio2_set", 2), ("fio2_meas", 3), ("fio2_abg", 4)):
            value = row[column]
            if pd.notna(value):
                return float(value), float(priority)
        return np.nan, np.nan
    for column, priority in (("fio2_meas", 2), ("fio2_set", 3), ("fio2_abg", 4)):
        value = row[column]
        if pd.notna(value):
            return float(value), float(priority)
    flow = row["oxygen_flow_rate"]
    if pd.notna(flow) and 0 <= flow <= 15:
        return float(flow) * 3 + 21, 5.0
    return np.nan, np.nan


def _compute_fio2_lookbacks(df: pd.DataFrame, config: RespScoringConfig) -> pd.DataFrame:
    time_col = config.time_col
    group_cols: list[str] = ["invasive_ind"]
    if config.encounter_id_col and config.encounter_id_col in df.columns:
        group_cols.insert(0, config.encounter_id_col)

    df["fio2_day_lookback"] = np.nan
    df["fio2_day_lookback_priority"] = np.nan
    df["fio2_minute_lookback"] = np.nan
    df["fio2_minute_lookback_priority"] = np.nan
    df["fio2_minute_look_fw"] = np.nan
    df["fio2_minute_look_fw_priority"] = np.nan

    day_window = np.timedelta64(24, "h")
    minute_back_window = np.timedelta64(14, "m")
    minute_exclude = np.timedelta64(1, "m")
    minute_forward_window = np.timedelta64(5, "m")

    for _, group in df.groupby(group_cols, sort=False):
        idx = group.index.to_numpy()
        times = group[time_col].to_numpy()
        fio2_values = group["fio2_prioritized"].to_numpy()
        fio2_priorities = group["fio2_priority"].to_numpy()

        for local_i, row_idx in enumerate(idx):
            day_value, day_priority = _find_last_in_window(
                times,
                fio2_values,
                fio2_priorities,
                local_i,
                day_window,
                include_current=True,
            )
            back_value, back_priority = _find_last_in_minute_window(
                times,
                fio2_values,
                fio2_priorities,
                local_i,
                minute_back_window,
                minute_exclude,
            )
            forward_value, forward_priority = _find_first_in_forward_window(
                times,
                fio2_values,
                fio2_priorities,
                local_i,
                minute_forward_window,
            )

            df.at[row_idx, "fio2_day_lookback"] = day_value
            df.at[row_idx, "fio2_day_lookback_priority"] = day_priority
            df.at[row_idx, "fio2_minute_lookback"] = back_value
            df.at[row_idx, "fio2_minute_lookback_priority"] = back_priority
            df.at[row_idx, "fio2_minute_look_fw"] = forward_value
            df.at[row_idx, "fio2_minute_look_fw_priority"] = forward_priority

    return df


def _find_last_in_window(
    times: np.ndarray,
    values: np.ndarray,
    priorities: np.ndarray,
    current_idx: int,
    window: np.timedelta64,
    include_current: bool,
) -> tuple[float, float]:
    start = current_idx if include_current else current_idx - 1
    t = times[current_idx]
    for j in range(start, -1, -1):
        if pd.notna(values[j]) and t - times[j] <= window:
            return float(values[j]), float(priorities[j])
        if t - times[j] > window:
            break
    return np.nan, np.nan


def _find_last_in_minute_window(
    times: np.ndarray,
    values: np.ndarray,
    priorities: np.ndarray,
    current_idx: int,
    window: np.timedelta64,
    exclude_delta: np.timedelta64,
) -> tuple[float, float]:
    t = times[current_idx]
    for j in range(current_idx - 1, -1, -1):
        delta = t - times[j]
        if delta > window:
            break
        if delta >= exclude_delta and pd.notna(values[j]):
            return float(values[j]), float(priorities[j])
    return np.nan, np.nan


def _find_first_in_forward_window(
    times: np.ndarray,
    values: np.ndarray,
    priorities: np.ndarray,
    current_idx: int,
    window: np.timedelta64,
) -> tuple[float, float]:
    t = times[current_idx]
    for j in range(current_idx, len(times)):
        delta = times[j] - t
        if delta > window:
            break
        if pd.notna(values[j]):
            return float(values[j]), float(priorities[j])
    return np.nan, np.nan


def _coalesce(series_list: Iterable[pd.Series]) -> pd.Series:
    result = None
    for series in series_list:
        result = series if result is None else result.combine_first(series)
    return result


def _assign_pf_ratio_temp(row: pd.Series) -> float:
    pao2_priority = row["pao2_priority"]
    pao2_value = row["pao2"]
    if pd.isna(pao2_value) or pd.isna(pao2_priority):
        return np.nan
    fio2_lookback = row["fio2_lookback"]
    spo2_value = row["spo2_obs"]
    altitude_factor = row["altitude_factor"]
    if pao2_priority == 2 and spo2_value in (99, 100, 99.0, 100.0) and pd.notna(fio2_lookback):
        if pao2_value / fio2_lookback <= 4 * altitude_factor:
            return np.nan
    if pd.notna(fio2_lookback) and fio2_lookback != 0:
        return oracle_round(pao2_value / (fio2_lookback / 100), 2)
    if bool(row["has_fio2_in_block"]):
        return np.nan
    if pao2_priority == 2 and pd.isna(fio2_lookback):
        return oracle_round(pao2_value / 0.21, 2)
    return np.nan


def _assign_sofa_rubric(row: pd.Series) -> float:
    pf_ratio = row["pf_ratio_temp"]
    if pd.isna(pf_ratio):
        return np.nan
    altitude_factor = row["altitude_factor"]
    if pf_ratio < 100 * altitude_factor:
        return 4.0
    if pf_ratio < 200 * altitude_factor:
        return 3.0
    if pf_ratio < 300 * altitude_factor:
        return 2.0
    if pf_ratio < 400 * altitude_factor:
        return 1.0
    return 0.0


def _apply_resp_detail_cap(row: pd.Series) -> float:
    rubric = row["sofa_resp_rubric"]
    if pd.isna(rubric):
        return np.nan
    support_present = bool(row["invasive_ind"]) or bool(row["support_ind"])
    if not support_present and rubric in (3, 4):
        return 2.0
    return float(rubric)


def _apply_measures_logic(
    df: pd.DataFrame,
    admit_dts: pd.Timestamp,
    config: RespScoringConfig,
) -> RespiratoryScoreResult:
    df = df.copy()
    time_col = config.time_col

    admit_dts = pd.to_datetime(admit_dts)
    acute_begin = admit_dts + pd.to_timedelta(config.acute_begin_days, unit="D")

    df["sofa_temp"] = df["sofa_resp_temp"].fillna(0)
    cap_mask = ~df["support_type"].fillna("").isin(["IMV", "NIPPV"])
    cap_mask &= df["sofa_resp_temp"].fillna(-1) >= 3
    df.loc[cap_mask, "sofa_temp"] = 2

    df["fio2_recent"] = _coalesce([df["fio2_minute_lookback"], df["fio2_minute_look_fw"]])
    df["qualifies_acute"] = (
        df["pf_ratio_temp"].notna() & df["fio2_recent"].notna() & (df[time_col] >= acute_begin)
    )
    df["qualifies_baseline"] = df["pf_ratio_temp"].notna() & (df[time_col] < acute_begin)

    count_pf_ratio_acute = int(df.loc[df["qualifies_acute"], "pf_ratio_temp"].shape[0])
    n_qualifying_pf_records_acute = count_pf_ratio_acute

    df["sofa_temp2"] = df["sofa_temp"]
    single_pf_suppressed = False
    if count_pf_ratio_acute == 1:
        acute_row = df.loc[df["qualifies_acute"]].iloc[0]
        if acute_row["resp_support_ind"] == 0 and acute_row["sofa_temp"] > 0:
            df.loc[df["qualifies_acute"], "sofa_temp2"] = 0
            single_pf_suppressed = True

    acute_records = df.loc[df["qualifies_acute"]].copy()
    if not acute_records.empty:
        acute_records = acute_records.sort_values(
            ["sofa_temp2", "resp_support_ind", time_col],
            ascending=[False, False, True],
        )
        sofa_pulm = int(acute_records.iloc[0]["sofa_temp2"])
    else:
        sofa_pulm = 0

    admit_day = admit_dts.normalize()
    baseline_begin = admit_day - pd.DateOffset(months=config.baseline_months)
    baseline_end = admit_day - pd.Timedelta(days=config.baseline_end_days)

    baseline_records = df.loc[df["qualifies_baseline"]].copy()
    baseline_records = baseline_records.loc[
        (baseline_records["sofa_ts"] >= baseline_begin)
        & (baseline_records["sofa_ts"] <= baseline_end)
    ]
    n_qualifying_pf_records_baseline = int(baseline_records.shape[0])

    if not baseline_records.empty:
        baseline_records = baseline_records.sort_values(
            ["sofa_ts", "sofa_temp2", time_col],
            ascending=[False, False, False],
        )
        sofa_pulm_bl = int(baseline_records.iloc[0]["sofa_temp2"])
    else:
        sofa_pulm_bl = 0

    sofa_pulm_delta = max(sofa_pulm - sofa_pulm_bl, 0)

    df["sofa_eval_period"] = np.where(
        df[time_col] >= acute_begin,
        "acute",
        "baseline",
    )

    return RespiratoryScoreResult(
        event_level=df,
        sofa_pulm=sofa_pulm,
        sofa_pulm_bl=sofa_pulm_bl,
        sofa_pulm_delta=sofa_pulm_delta,
        count_pf_ratio_acute=count_pf_ratio_acute,
        n_qualifying_pf_records_acute=n_qualifying_pf_records_acute,
        n_qualifying_pf_records_baseline=n_qualifying_pf_records_baseline,
        single_pf_suppressed=single_pf_suppressed,
    )
