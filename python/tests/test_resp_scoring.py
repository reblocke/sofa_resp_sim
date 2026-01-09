import numpy as np
import pandas as pd

from tcco2_accuracy.resp_scoring import RespScoringConfig, score_respiratory
from tcco2_accuracy.resp_utils import oracle_round, spo2_to_pao2


def test_oracle_round_half_up():
    assert oracle_round(1.25, 1) == 1.3
    assert oracle_round(2.5, 0) == 3.0
    assert oracle_round(-1.5, 0) == -2.0


def test_spo2_to_pao2_reference_points():
    assert np.isnan(spo2_to_pao2(45))
    assert spo2_to_pao2(80) == 44.3
    assert spo2_to_pao2(90) == 58.7
    assert spo2_to_pao2(95) == 75.7


def test_fio2_lookback_windows():
    admit_dts = pd.Timestamp("2024-01-01 00:00")
    times = pd.to_datetime(
        [
            "2024-01-01 00:00",
            "2024-01-01 00:10",
            "2024-01-01 00:20",
            "2024-01-01 00:26",
        ]
    )
    df = pd.DataFrame(
        {
            "etime_ts": times,
            "spo2_obs": [90, 90, 90, 90],
            "fio2_meas": [30.0, np.nan, 40.0, np.nan],
            "is_room_air": [False, False, False, False],
            "support_type": [None, None, None, None],
        }
    )
    scored = score_respiratory(df, admit_dts)
    event_df = scored.event_level

    assert event_df.loc[1, "fio2_minute_lookback"] == 30.0
    assert np.isnan(event_df.loc[2, "fio2_minute_lookback"])
    assert event_df.loc[2, "fio2_minute_look_fw"] == 40.0
    assert event_df.loc[3, "fio2_minute_lookback"] == 40.0
    assert event_df.loc[3, "fio2_day_lookback"] == 40.0


def test_pf_ratio_rubric_altitude_boundary():
    admit_dts = pd.Timestamp("2024-01-01 00:00")
    df = pd.DataFrame(
        {
            "etime_ts": ["2024-01-01 01:00"],
            "spo2_obs": [90],
            "pao2_meas": [85.0],
            "fio2_meas": [50.0],
            "support_type": ["IMV"],
            "is_room_air": [False],
        }
    )
    config = RespScoringConfig(altitude_factor=0.85)
    scored = score_respiratory(df, admit_dts, config)
    event_df = scored.event_level

    assert event_df.loc[0, "pf_ratio_temp"] == 170.0
    assert event_df.loc[0, "sofa_resp_rubric"] == 2.0


def test_single_pf_suppression_rule():
    admit_dts = pd.Timestamp("2024-01-01 00:00")
    df = pd.DataFrame(
        {
            "etime_ts": ["2024-01-01 02:00"],
            "spo2_obs": [90],
            "pao2_meas": [80.0],
            "fio2_meas": [40.0],
            "support_type": [None],
            "is_room_air": [False],
        }
    )
    scored = score_respiratory(df, admit_dts)
    assert scored.count_pf_ratio_acute == 1
    assert scored.sofa_pulm == 0
    assert scored.single_pf_suppressed is True


def test_measures_cap_for_hfnc():
    admit_dts = pd.Timestamp("2024-01-01 00:00")
    df = pd.DataFrame(
        {
            "etime_ts": ["2024-01-01 03:00"],
            "spo2_obs": [88],
            "pao2_meas": [75.0],
            "fio2_set": [50.0],
            "support_type": ["HFNC"],
            "is_room_air": [False],
        }
    )
    scored = score_respiratory(df, admit_dts)
    event_df = scored.event_level

    assert event_df.loc[0, "sofa_resp_temp"] == 3.0
    assert event_df.loc[0, "sofa_temp"] == 2.0
