import json

import pytest

from sofa_resp_sim.core.experiment_config import ScenarioConfig, ScoringProfile
from sofa_resp_sim.core.experiment_scoring import score_documented_events
from sofa_resp_sim.core.observation import document_patient
from sofa_resp_sim.core.paired_simulation import generate_patient

ADMIT = "2024-01-01T12:37:00Z"


def oxygenation(minute, *, event_id="ox", spo2=96, measured=None, label="ROOM_AIR", available=None):
    return {
        "event_id": event_id,
        "patient_id": 0,
        "event_type": "oxygenation",
        "measurement_minute": minute,
        "available_minute": minute if available is None else available,
        "support_type": label,
        "spo2_obs": spo2,
        "pao2_meas": measured,
    }


def denominator(minute, *, event_id="fio2", label="ROOM_AIR", fio2=0.5, flow=None, available=None):
    return {
        "event_id": event_id,
        "patient_id": 0,
        "event_type": "fio2",
        "measurement_minute": minute,
        "available_minute": minute if available is None else available,
        "support_type": label,
        "is_room_air": label == "ROOM_AIR",
        "fio2_set_fraction": fio2 if label not in {"ROOM_AIR", "LOW_FLOW"} else None,
        "flow_lpm": flow,
    }


def fixture(times=(0, 15), *, spo2=96, measured=None, label="ROOM_AIR", fio2=0.5, flow=None):
    events = []
    for i, minute in enumerate(times):
        events.extend(
            [
                oxygenation(minute, event_id=f"ox{i}", spo2=spo2, measured=measured, label=label),
                denominator(minute, event_id=f"fio2{i}", label=label, fio2=fio2, flow=flow),
            ]
        )
    return events


def score(events, **settings):
    return score_documented_events(events, ADMIT, ScoringProfile(**settings))


def test_threshold_factor_preserves_conversion():
    a, b = score(fixture()), score(fixture(), threshold_factor=0.85)
    assert a["acute"]["algorithm_score"] == 1
    assert b["acute"]["algorithm_score"] == 0
    for output in [a, b]:
        assert [e["pao2_calc_mmhg"] for e in output["events"]] == [81.9, 81.9]
        assert [e["pf_ratio_mmhg"] for e in output["events"]] == [390, 390]
    json.dumps(a, allow_nan=False)


def test_identical_fio2_source_label_preserves_numerical_scores():
    set_events = fixture(label="IMV", spo2=90, fio2=0.5)
    measured_events = [dict(event) for event in set_events]
    for event in measured_events:
        if event["event_type"] == "fio2":
            event["fio2_meas_fraction"] = event.pop("fio2_set_fraction")
    left, right = score(set_events), score(measured_events)
    assert left["acute"] == right["acute"]
    for a, b in zip(left["events"], right["events"], strict=True):
        assert a["fio2_inference_method"] != b["fio2_inference_method"]
        for key in (
            "fio2_fraction",
            "pf_ratio_mmhg",
            "raw_rubric",
            "detail_support_score",
            "support_adjusted_score",
            "reported_score",
        ):
            assert a[key] == b[key]


def test_measured_pao2_priority_and_strict_cutpoints():
    result = score(fixture(measured=84))
    assert result["acute"]["algorithm_score"] == 0
    assert [e["pao2_used_mmhg"] for e in result["events"]] == [84, 84]
    assert [e["pf_ratio_mmhg"] for e in result["events"]] == [400, 400]
    for pf, expected in [(100, 3), (200, 2), (300, 1), (400, 0)]:
        result = score(fixture(measured=pf, label="IMV", fio2=1))
        assert result["acute"]["algorithm_score"] == expected
        result = score(fixture(measured=pf - 0.01, label="IMV", fio2=1))
        assert result["acute"]["algorithm_score"] == expected + 1


@pytest.mark.parametrize("spo2,expected", [(49, None), (50, 26.9), (96, 81.9), (97, None)])
def test_conversion_edges(spo2, expected):
    result = score(fixture(spo2=spo2))
    assert result["events"][0]["pao2_calc_mmhg"] == expected
    if expected is None:
        assert result["acute"]["score_status"] == "no_qualifying_data"
        assert result["events"][0]["first_exclusion"] == "conversion_unavailable"


def test_low_flow_singleton_and_two_record_fixture():
    single = score(fixture(times=(0,), spo2=90, label="LOW_FLOW", flow=4))
    assert single["acute"]["algorithm_score"] == 0
    assert single["acute"]["pre_suppression_score"] == 2
    assert single["acute"]["score_status"] == "suppressed_only"
    assert single["events"][0]["fio2_fraction"] == 0.33
    assert single["events"][0]["pf_ratio_mmhg"] == 177.88
    assert single["events"][0]["singleton_suppressed"]
    double = score(fixture(spo2=90, label="LOW_FLOW", flow=4))
    assert double["acute"]["algorithm_score"] == 2
    assert not double["acute"]["suppressed"]


def test_normal_missing_and_suppressed_are_distinct():
    normal = score(fixture(measured=100))
    missing = score(fixture(spo2=None))
    suppressed = score(fixture(times=(0,), spo2=90))
    assert [r["acute"]["algorithm_score"] for r in [normal, missing, suppressed]] == [0, 0, 0]
    assert [r["acute"]["score_status"] for r in [normal, missing, suppressed]] == [
        "observed_scored",
        "no_qualifying_data",
        "suppressed_only",
    ]
    assert normal["baseline"]["score_status"] == "no_qualifying_data"
    assert normal["delta_evaluable"] is None
    assert score([])["acute"]["pre_suppression_score"] is None


def test_remove_entire_fio2_evidence_bundle():
    events = [oxygenation(t, event_id=f"ox{t}", spo2=90, label="LOW_FLOW") for t in (0, 15)]
    result = score(events)
    assert result["acute"]["score_status"] == "no_qualifying_data"
    assert result["acute"]["qualifying_pf_count"] == 0
    assert all(
        e["pf_ratio_mmhg"] is None and e["fio2_source_event_id"] is None for e in result["events"]
    )


@pytest.mark.parametrize("label", ["HFNC", "NIPPV", "IMV", "SURG IMV"])
def test_support_variant_changes_every_gate(label):
    events = fixture(times=(0,), measured=80, label=label, fio2=0.8)
    legacy = score(events)
    expanded = score(events, support_eligibility="expanded")
    assert expanded["acute"]["algorithm_score"] == 3
    assert expanded["events"][0]["final_support_eligible"]
    assert not expanded["acute"]["suppressed"]
    assert legacy["acute"]["algorithm_score"] == (3 if label in {"IMV", "NIPPV"} else 0)
    if label in {"HFNC", "SURG IMV"}:
        assert legacy["events"][0]["final_support_capped"]
        assert legacy["events"][0]["singleton_suppressed"]


@pytest.mark.parametrize(
    "minute,has_pf,qualifies",
    [
        (-1, True, True),
        (-0.999, True, False),
        (-14, True, True),
        (-14.001, True, False),
        (5, True, True),
        (5.001, False, False),
        (-1440, True, False),
        (-1440.001, False, False),
    ],
)
def test_fio2_lookup_boundaries(minute, has_pf, qualifies):
    result = score([oxygenation(0, measured=80, label="IMV"), denominator(minute, label="IMV")])
    event = result["events"][0]
    assert (event["pf_ratio_mmhg"] is not None) == has_pf
    assert event["qualifies_acute"] == qualifies
    assert event["fio2_source_event_id"] == ("fio2" if has_pf else None)


def test_current_priority_and_asof_availability_are_explicit():
    events = [
        oxygenation(0, measured=80, label="IMV"),
        denominator(-2, event_id="old", label="IMV", fio2=0.4),
        denominator(0, event_id="current", label="IMV", fio2=0.8, available=2),
    ]
    assert score(events)["events"][0]["fio2_source_event_id"] == "old"
    assert (
        score(events, lookup="contemporaneous_first")["events"][0]["fio2_source_event_id"]
        == "current"
    )
    output = score(events, lookup="contemporaneous_first", availability="as_of")
    assert output["events"][0]["fio2_source_event_id"] == "old"
    only_future = [events[0], events[2]]
    assert score(only_future)["acute"]["qualifying_pf_count"] == 1
    assert score(only_future, availability="as_of")["acute"]["qualifying_pf_count"] == 0


def test_bounded_acute_endpoints_and_context_only_records():
    result = score(fixture(times=(-360.001, -360, 1439.999, 1440), measured=80, label="IMV"))
    assert [e["qualifies_acute"] for e in result["events"]] == [False, True, True, False]
    assert result["acute"]["qualifying_pf_count"] == 2
    assert len(result["context_events"]) == 4


def test_duplicate_and_coincident_events_preserve_counts():
    events = fixture(times=(0, 0), measured=80, label="IMV")
    result = score(list(reversed(events)))
    assert len(result["events"]) == 2
    assert result["acute"]["qualifying_pf_count"] == 2
    assert result["acute"]["selected_event_id"] == "ox0"
    assert result["acute"]["tied_event_ids"] == ["ox0", "ox1"]
    with pytest.raises(ValueError, match="unique"):
        score(events + [events[0]])


def test_calendar_admission_and_dst():
    events = fixture(times=(0, 30, 720), measured=80, label="IMV")
    calendar = score(events)
    anchored = score(events, binning="admission")
    assert calendar["events"][0]["bin_start"] != anchored["events"][0]["bin_start"]
    spring = score_documented_events(
        events, "2024-03-10T06:30:00Z", ScoringProfile(timezone="America/New_York")
    )
    assert "01:30:00-05:00" in spring["events"][0]["measurement_time"]
    assert "03:00:00-04:00" in spring["events"][1]["measurement_time"]
    fall = score_documented_events(
        fixture(times=(0, 60)), "2024-11-03T05:30:00Z", ScoringProfile(timezone="America/New_York")
    )
    assert "01:30:00-04:00" in fall["events"][0]["measurement_time"]
    assert "01:30:00-05:00" in fall["events"][1]["measurement_time"]


def test_exact_replay_zero_and_baseline_counts():
    config = ScenarioConfig.from_dict(
        {
            "horizon": {
                "start_minute": 0,
                "end_minute": 360,
                "include_baseline": True,
                "baseline_generation_minutes": 360,
                "baseline_replay": True,
            },
            "observation": {"start_minute": 0, "baseline_exposure_minutes": 360},
        }
    )
    patient = generate_patient(config.generator, config.horizon, 1, 0)
    result = score(document_patient(patient, config))
    assert result["delta_signed"] == result["delta_evaluable"] == 0
    assert result["baseline"]["qualifying_pf_count"] == result["acute"]["qualifying_pf_count"]


def test_named_suppression_conversion_and_baseline_variants():
    singleton = fixture(times=(0,), spo2=90, label="LOW_FLOW", flow=4)
    assert score(singleton, single_record_suppression=False)["acute"]["algorithm_score"] == 2
    assert (
        score(singleton, conversion="measured_only")["acute"]["score_status"]
        == "no_qualifying_data"
    )
    events = fixture(times=(-30 * 1440,), measured=50, label="IMV", fio2=0.8)
    more_recent = fixture(times=(-29 * 1440,), measured=400, label="IMV", fio2=1)
    for event in more_recent:
        event["event_id"] += "recent"
    events += more_recent
    assert score(events)["baseline"]["algorithm_score"] == 0
    assert score(events, baseline_selection="all_eligible_max")["baseline"]["algorithm_score"] == 4
    assert score(events)["baseline"]["qualifying_pf_count"] == 2
