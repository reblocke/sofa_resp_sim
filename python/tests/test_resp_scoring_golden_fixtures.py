import numpy as np
import pandas as pd
import pytest

from tcco2_accuracy.resp_scoring import RespScoringConfig, score_respiratory
from tcco2_accuracy.resp_utils import spo2_to_pao2


ADMIT_DTS = pd.Timestamp("2026-01-01 00:00:00")
CANONICAL_COLUMNS = {
    "etime_ts",
    "spo2_obs",
    "support_type",
    "is_room_air",
    "oxygen_flow_rate",
    "fio2_set",
    "fio2_meas",
    "fio2_abg",
    "altitude_factor",
    "admit_dts",
}


def score_rows(rows, altitude_factor=1.0):
    df = pd.DataFrame(rows)
    extra = set(df.columns) - CANONICAL_COLUMNS
    assert not extra, f"Unexpected columns in fixture rows: {sorted(extra)}"
    missing = CANONICAL_COLUMNS - set(df.columns)
    assert not missing, f"Missing canonical columns in fixture rows: {sorted(missing)}"

    admit_values = df["admit_dts"].dropna().unique()
    if len(admit_values) == 0:
        admit_dts = ADMIT_DTS
    else:
        assert len(admit_values) == 1
        admit_dts = pd.Timestamp(admit_values[0])

    df = df.drop(columns=["admit_dts"])
    if "altitude_factor" in df.columns:
        df["altitude_factor"] = pd.to_numeric(df["altitude_factor"], errors="coerce")
        df["altitude_factor"] = df["altitude_factor"].fillna(altitude_factor)
    else:
        df["altitude_factor"] = altitude_factor
    config = RespScoringConfig(altitude_factor=altitude_factor)
    return score_respiratory(df, admit_dts, config)


def make_row(time, **fields):
    admit_dts = fields.pop("admit_dts", ADMIT_DTS)
    row = {
        "etime_ts": pd.Timestamp(time),
        "spo2_obs": None,
        "support_type": None,
        "is_room_air": False,
        "oxygen_flow_rate": None,
        "fio2_set": None,
        "fio2_meas": None,
        "fio2_abg": None,
        "altitude_factor": None,
        "admit_dts": pd.Timestamp(admit_dts),
    }
    row.update(fields)
    return row


def get_row(event_df, timestamp):
    ts = pd.Timestamp(timestamp)
    row = event_df.loc[event_df["etime_ts"] == ts]
    assert not row.empty
    return row.iloc[0]


def test_fixture_0_spo2_to_pao2_reference_points():
    spo2_values = [50, 70, 80, 85, 90, 96]
    expected = [26.9, 36.6, 44.3, 50.0, 58.7, 81.9]
    results = spo2_to_pao2(spo2_values)

    for value, expected_value in zip(results, expected, strict=True):
        assert value == pytest.approx(expected_value, abs=1e-3)

    assert np.isnan(spo2_to_pao2(49))
    assert np.isnan(spo2_to_pao2(97))


def test_fixture_1_spo2_above_96_no_pf_ratio():
    scored = score_rows(
        [make_row(ADMIT_DTS + pd.Timedelta(hours=1), spo2_obs=99, is_room_air=True)],
        altitude_factor=1.0,
    )
    event = scored.event_level.iloc[0]

    assert np.isnan(event["pao2_calc"])
    assert np.isnan(event["pf_ratio_temp"])
    assert scored.sofa_pulm == 0
    assert scored.count_pf_ratio_acute == 0


def test_fixture_2_day_lookback_pf_not_acute():
    scored = score_rows(
        [
            make_row(
                ADMIT_DTS + pd.Timedelta(hours=-1),
                oxygen_flow_rate=2,
                is_room_air=False,
            ),
            make_row(ADMIT_DTS, spo2_obs=90, is_room_air=False),
        ],
        altitude_factor=1.0,
    )
    event = get_row(scored.event_level, ADMIT_DTS)

    assert event["pao2_calc"] == pytest.approx(58.7, abs=1e-2)
    assert event["pao2"] == pytest.approx(58.7, abs=1e-2)
    assert event["pao2_priority"] == 2
    assert event["fio2_day_lookback"] == pytest.approx(27.0, abs=1e-6)
    assert np.isnan(event["fio2_minute_lookback"])
    assert np.isnan(event["fio2_minute_look_fw"])
    assert event["fio2_lookback"] == pytest.approx(27.0, abs=1e-6)
    assert event["pf_ratio_temp"] == pytest.approx(217.41, abs=1e-2)
    assert bool(event["qualifies_acute"]) is False
    assert scored.count_pf_ratio_acute == 0
    assert scored.sofa_pulm == 0


def test_fixture_3_hfnc_resp_detail_vs_measures():
    scored = score_rows(
        [
            make_row(
                ADMIT_DTS,
                spo2_obs=90,
                fio2_meas=50,
                support_type="HFNC",
                oxygen_flow_rate=40,
                is_room_air=False,
            ),
            make_row(
                ADMIT_DTS + pd.Timedelta(minutes=30),
                spo2_obs=85,
                fio2_meas=50,
                support_type="HFNC",
                oxygen_flow_rate=40,
                is_room_air=False,
            ),
        ],
        altitude_factor=1.0,
    )
    event_df = scored.event_level
    row0 = get_row(event_df, ADMIT_DTS)
    row1 = get_row(event_df, ADMIT_DTS + pd.Timedelta(minutes=30))

    assert row0["pf_ratio_temp"] == pytest.approx(117.4, abs=1e-2)
    assert row1["pf_ratio_temp"] == pytest.approx(100.0, abs=1e-2)
    assert row0["sofa_resp_temp"] == 3.0
    assert row1["sofa_resp_temp"] == 3.0
    assert row0["sofa_temp"] == 2.0
    assert row1["sofa_temp"] == 2.0
    assert scored.count_pf_ratio_acute == 2
    assert scored.single_pf_suppressed is False
    assert scored.sofa_pulm == 2


def test_fixture_4_imv_single_pf_no_suppression():
    scored = score_rows(
        [
            make_row(
                ADMIT_DTS,
                spo2_obs=85,
                fio2_set=80,
                support_type="IMV",
                is_room_air=False,
            )
        ],
        altitude_factor=1.0,
    )
    event = scored.event_level.iloc[0]

    assert event["pf_ratio_temp"] == pytest.approx(62.5, abs=1e-2)
    assert scored.count_pf_ratio_acute == 1
    assert scored.single_pf_suppressed is False
    assert scored.sofa_pulm == 4


def test_fixture_5_nippv_single_pf_no_suppression():
    scored = score_rows(
        [
            make_row(
                ADMIT_DTS,
                spo2_obs=90,
                fio2_meas=50,
                support_type="NIPPV",
                is_room_air=False,
            )
        ],
        altitude_factor=1.0,
    )
    event = scored.event_level.iloc[0]

    assert event["pf_ratio_temp"] == pytest.approx(117.4, abs=1e-2)
    assert scored.count_pf_ratio_acute == 1
    assert scored.single_pf_suppressed is False
    assert scored.sofa_pulm == 3


def test_fixture_6_single_pf_suppression_non_support():
    scored = score_rows(
        [
            make_row(
                ADMIT_DTS,
                spo2_obs=90,
                oxygen_flow_rate=4,
                is_room_air=False,
            )
        ],
        altitude_factor=1.0,
    )
    event = scored.event_level.iloc[0]

    assert event["fio2_prioritized"] == pytest.approx(33.0, abs=1e-6)
    assert event["fio2_minute_look_fw"] == pytest.approx(33.0, abs=1e-6)
    assert event["pf_ratio_temp"] == pytest.approx(177.88, abs=1e-2)
    assert event["sofa_resp_temp"] == 2.0
    assert event["sofa_temp2"] == 0
    assert scored.count_pf_ratio_acute == 1
    assert scored.single_pf_suppressed is True
    assert scored.sofa_pulm == 0


def test_fixture_7_baseline_uses_recent_day():
    scored = score_rows(
        [
            make_row(
                "2025-12-12 00:00:00",
                spo2_obs=90,
                fio2_meas=50,
                support_type="NIPPV",
                is_room_air=False,
            ),
            make_row(
                "2025-12-22 00:00:00",
                spo2_obs=96,
                is_room_air=True,
            ),
        ],
        altitude_factor=1.0,
    )
    event_recent = get_row(scored.event_level, "2025-12-22 00:00:00")
    event_prior = get_row(scored.event_level, "2025-12-12 00:00:00")

    assert event_recent["sofa_eval_period"] == "baseline"
    assert event_recent["sofa_ts"] == pd.Timestamp("2025-12-22 00:00:00")
    assert event_recent["sofa_temp2"] == 1.0
    assert event_prior["sofa_temp2"] == 3.0
    assert scored.sofa_pulm_bl == 1


def test_fixture_8_quartile_suppresses_room_air_pf():
    scored = score_rows(
        [
            make_row(ADMIT_DTS + pd.Timedelta(hours=1), spo2_obs=90, is_room_air=False),
            make_row(
                ADMIT_DTS + pd.Timedelta(hours=2),
                fio2_meas=50,
                is_room_air=False,
            ),
        ],
        altitude_factor=1.0,
    )
    event_df = scored.event_level
    row1 = get_row(event_df, ADMIT_DTS + pd.Timedelta(hours=1))
    row2 = get_row(event_df, ADMIT_DTS + pd.Timedelta(hours=2))

    assert np.isnan(row1["fio2_lookback"])
    assert bool(row1["has_fio2_in_block"]) is True
    assert row1["quartile"] == row2["quartile"]
    assert np.isnan(row1["pf_ratio_temp"])
    assert scored.count_pf_ratio_acute == 0
    assert scored.sofa_pulm == 0


def test_sofa_ts_and_quartile_binning():
    scored = score_rows(
        [
            make_row(ADMIT_DTS + pd.Timedelta(hours=1)),
            make_row(ADMIT_DTS + pd.Timedelta(hours=7)),
            make_row(ADMIT_DTS + pd.Timedelta(hours=13)),
            make_row(ADMIT_DTS + pd.Timedelta(hours=19)),
            make_row(ADMIT_DTS - pd.Timedelta(hours=1)),
        ],
        altitude_factor=1.0,
    )
    event_df = scored.event_level
    admit_day = ADMIT_DTS.normalize()

    row_01 = get_row(event_df, ADMIT_DTS + pd.Timedelta(hours=1))
    row_07 = get_row(event_df, ADMIT_DTS + pd.Timedelta(hours=7))
    row_13 = get_row(event_df, ADMIT_DTS + pd.Timedelta(hours=13))
    row_19 = get_row(event_df, ADMIT_DTS + pd.Timedelta(hours=19))
    row_preadmit = get_row(event_df, ADMIT_DTS - pd.Timedelta(hours=1))

    assert row_01["sofa_ts"] == admit_day
    assert row_01["quartile"] == 1
    assert row_07["sofa_ts"] == admit_day
    assert row_07["quartile"] == 2
    assert row_13["sofa_ts"] == admit_day
    assert row_13["quartile"] == 3
    assert row_19["sofa_ts"] == admit_day
    assert row_19["quartile"] == 4
    assert row_preadmit["sofa_ts"] == admit_day
    assert row_preadmit["quartile"] == 1


@pytest.mark.parametrize(
    "altitude_factor, expected_score, expected_rubric",
    [(1.0, 4, 4.0), (0.85, 3, 3.0)],
)
def test_fixture_9_altitude_factor_thresholds(
    altitude_factor, expected_score, expected_rubric
):
    scored = score_rows(
        [
            make_row(
                ADMIT_DTS,
                spo2_obs=80,
                fio2_set=50,
                support_type="IMV",
                is_room_air=False,
            )
        ],
        altitude_factor=altitude_factor,
    )
    event = scored.event_level.iloc[0]

    assert event["pf_ratio_temp"] == pytest.approx(88.6, abs=1e-2)
    assert event["sofa_resp_rubric"] == expected_rubric
    assert scored.sofa_pulm == expected_score
