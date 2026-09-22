"""Synthetic local-wall-clock regressions for PR #12's DST review finding."""

import json
import time

import pandas as pd
import pytest

from sofa_resp_sim.core.experiment_config import ScoringProfile
from sofa_resp_sim.core.experiment_scoring import score_documented_events
from sofa_resp_sim.core.historical_trops import PROFILE, historical_time
from sofa_resp_sim.reporting.experiment_bundle import build_bundle
from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request
from sofa_resp_sim.reporting.experiment_service import explain_patient, run_experiment

ZONE = "America/New_York"
ADMISSIONS = ("2024-03-10T00:00:00-05:00", "2024-11-03T00:00:00-04:00")


def events_at(minute, admit):
    common = {
        "patient_id": 0,
        "measurement_minute": minute,
        "available_minute": minute,
        "support_type": "IMV",
        "invasive_ind": True,
        "support_ind": False,
        "ce_admit_dts": admit,
    }
    return [
        {**common, "event_id": "ox", "event_type": "oxygenation", "pao2_meas": 80},
        {**common, "event_id": "fio", "event_type": "fio2", "fio2_set_fraction": 1.0},
    ]


@pytest.mark.parametrize(
    "admit", (*ADMISSIONS, "2024-03-10T06:00:00-04:00", "2024-11-03T06:00:00-05:00")
)
@pytest.mark.parametrize(
    "minute,included",
    [
        (-360.001, False),
        (-360, True),
        (-359.999, True),
        (1439.999, True),
        (1440, True),
        (1440.001, False),
    ],
)
def test_dst_acute_boundaries(admit, minute, included):
    profile = ScoringProfile(profile=PROFILE, timezone=ZONE)
    result = score_documented_events(events_at(minute, admit), admit, profile)
    event = result["events"][0]
    assert event["in_acute_target"] is included
    assert event["qualifies_acute"] is included
    assert result["acute"]["algorithm_score"] == (4 if included else 0)
    assert result["acute"]["score_status"] == (
        "observed_scored" if included else "no_qualifying_data"
    )
    if minute in (-360, 1440):
        key = "acute_begin" if minute == -360 else "acute_end_inclusive"
        assert event["measurement_time"] == result["resolved_windows"][key]
    if minute == 1440:
        assert (event["historical_day_index"], event["historical_quarter"]) == (0, 5)
        expected = (pd.Timestamp(admit).tz_localize(None) + pd.Timedelta(days=1)).tz_localize(ZONE)
        assert event["measurement_time"] == expected.isoformat()


@pytest.mark.parametrize("admit", ADMISSIONS)
def test_dst_negative_days_and_baseline_cutoff(admit):
    profile = ScoringProfile(profile=PROFILE, timezone=ZONE)
    admission = pd.Timestamp(admit).tz_convert(ZONE)
    # Admission one week after the transition: the baseline endpoint is the
    # transition day's midnight, on the other side of the UTC-offset change.
    later = (admission.tz_localize(None) + pd.Timedelta(days=7)).tz_localize(ZONE)
    for minute, expected in [(-15840, (-12, 5)), (-15839.999, (-11, 1))]:
        _, day, quarter, _ = historical_time(minute, later, profile)
        assert (day, quarter) == expected
    for offset, included in [(-0.001, True), (0, True), (0.001, False)]:
        minute = -7 * 1440 + offset
        result = score_documented_events(
            events_at(minute, later.isoformat()), later.isoformat(), profile
        )
        assert result["events"][0]["qualifies_baseline"] is included
        if offset == 0:
            assert (
                result["events"][0]["measurement_time"]
                == result["resolved_windows"]["baseline_end_day_inclusive"]
            )


@pytest.mark.parametrize("admit", ADMISSIONS)
def test_dst_quarter_fallback_uses_same_wall_clock_for_both_streams(admit):
    events = events_at(350, admit)  # 05:50 local, quarter 1
    events[0].update(pao2_meas=None, spo2_obs=90)
    events[1].update(measurement_minute=365, available_minute=365)  # 06:05, quarter 2
    result = score_documented_events(events, admit, ScoringProfile(profile=PROFILE, timezone=ZONE))
    event = result["events"][0]
    assert event["historical_quarter"] == 1
    assert event["historical_room_air_fallback"]
    assert event["fio2_fraction"] == 0.21


@pytest.mark.parametrize(
    "admit,minute,expected",
    [
        (ADMISSIONS[0], 150, "2024-03-10T02:30:00"),  # nonexistent local instant
        (ADMISSIONS[1], 90, "2024-11-03T01:30:00"),  # two possible local instants
    ],
)
def test_dst_gap_and_fold_are_local_labels_not_invented_instants(admit, minute, expected):
    events = events_at(minute, admit)
    events[0]["available_minute"] = minute + 10
    result = score_documented_events(events, admit, ScoringProfile(profile=PROFILE, timezone=ZONE))
    event = result["events"][0]
    assert event["measurement_time"] == expected
    assert (
        event["available_time"] == (pd.Timestamp(expected) + pd.Timedelta(minutes=10)).isoformat()
    )
    assert event["qualifies_acute"]
    assert result["resolved_windows"]["timezone"] == ZONE


@pytest.mark.parametrize("admit", ADMISSIONS)
def test_dst_generated_endpoint_is_documented_and_scored(admit):
    request = normalize_experiment_request(
        {
            "schema_version": "experiment_request_v3",
            "replicates": 1,
            "base": {
                "horizon": {"admit_dts": admit, "start_minute": 0, "end_minute": 1440},
                "observation": {"start_minute": 0},
                "scoring": {"profile": PROFILE, "timezone": ZONE},
            },
            "comparator": {"label": "DST"},
            "conditions": [],
        }
    )
    trace = explain_patient(request, 0, request.comparator.condition_id)
    endpoint = next(e for e in trace["scoring"]["events"] if e["measurement_minute"] == 1440)
    assert endpoint["in_acute_target"]
    assert endpoint["historical_quarter"] == 5


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="Host timezone switching requires tzset")
@pytest.mark.parametrize("admit", ADMISSIONS)
def test_historical_trace_and_bundle_ignore_host_timezone(admit, monkeypatch):
    request = normalize_experiment_request(
        {
            "schema_version": "experiment_request_v3",
            "replicates": 1,
            "base": {
                "horizon": {
                    "admit_dts": admit,
                    "start_minute": 0,
                    "end_minute": 1440,
                    "include_baseline": True,
                },
                "observation": {"start_minute": 0},
                "scoring": {"profile": PROFILE, "timezone": ZONE},
            },
            "comparator": {"label": "DST"},
            "conditions": [],
        }
    )
    results = []
    for zone in ("UTC", "America/Los_Angeles", "America/New_York"):
        try:
            with monkeypatch.context() as context:
                context.setenv("TZ", zone)
                time.tzset()
                trace = explain_patient(request, 0, request.comparator.condition_id)
                bundle = build_bundle(run_experiment(request))
                digest = json.loads(bundle["manifest.json"])["scientific_data_sha256"]
                results.append((trace, digest))
        finally:
            time.tzset()  # The context restored TZ, including on a failed assertion.
    assert results[0] == results[1] == results[2]
