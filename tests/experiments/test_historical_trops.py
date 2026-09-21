"""Wholly synthetic expectations reconstructed from pinned historical statements.

These tests do not execute Oracle or assert current-production equivalence.
"""

import copy
import itertools

import pandas as pd
import pytest

from sofa_resp_sim.core.experiment_config import ScoringProfile
from sofa_resp_sim.core.experiment_scoring import score_documented_events
from sofa_resp_sim.core.historical_trops import PROFILE, historical_time, profile_provenance
from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request
from sofa_resp_sim.reporting.experiment_service import run_experiment
from sofa_resp_sim.reporting.historical_results import eligibility, summarize_v3

ADMIT = "2026-01-31T12:00:00Z"


def ox(minute, *, key="a", label="ROOM_AIR", pao2=52.5, spo2=None, partition=ADMIT):
    return {
        "event_id": key,
        "patient_id": 0,
        "event_type": "oxygenation",
        "measurement_minute": minute,
        "available_minute": minute,
        "support_type": label,
        "invasive_ind": label in ("IMV", "SURG IMV"),
        "support_ind": label in ("HFNC", "NIPPV"),
        "ce_admit_dts": partition,
        "pao2_meas": pao2,
        "spo2_obs": spo2,
    }


def fio(minute, *, key="f", value=0.21, label="ROOM_AIR", partition=ADMIT):
    row = ox(minute, key=key, label=label, partition=partition)
    row.update(event_type="fio2", fio2_set_fraction=value, is_room_air=label == "ROOM_AIR")
    return row


def score(events, historical=True, **changes):
    profile = ScoringProfile(profile=PROFILE if historical else "bounded_analysis_v2", **changes)
    return score_documented_events(events, ADMIT, profile)


def minute(timestamp):
    return (pd.Timestamp(timestamp) - pd.Timestamp(ADMIT)).total_seconds() / 60


def test_january_ranking_and_component_delta():
    morning, evening = minute("2026-01-20T08:00Z"), minute("2026-01-20T18:00Z")
    events = [
        ox(morning),
        fio(morning),
        ox(evening, key="b", pao2=105),
        fio(evening, key="g"),
        ox(0, key="c"),
        fio(0, key="h"),
        ox(15, key="d"),
        fio(15, key="i"),
    ]
    historical, bounded = score(events), score(events, False)
    assert historical["baseline"]["algorithm_score"] == 0
    assert bounded["baseline"]["algorithm_score"] == 2
    assert historical["delta_legacy"] == 2 and bounded["delta_legacy"] == 0
    assert [e["historical_day_index"] for e in historical["events"][:2]] == [-12, -11]


@pytest.mark.parametrize(
    "offset,expected", [(-0.001, True), (0, True), (0.001, False), (720, False)]
)
def test_actual_baseline_cutoff(offset, expected):
    t = minute("2026-01-24T00:00Z") + offset
    result = score([ox(t), fio(t)])
    assert result["events"][0]["qualifies_baseline"] is expected


@pytest.mark.parametrize(
    "t,expected",
    [(-360.001, False), (-360, True), (1439.999, True), (1440, True), (1440.001, False)],
)
def test_inclusive_acute_endpoints(t, expected):
    assert score([ox(t), fio(t)])["events"][0]["qualifies_acute"] is expected


def test_exact_negative_integer_day_and_quarter():
    profile = ScoringProfile(profile=PROFILE)
    _, day, quarter, _ = historical_time(-11 * 1440, pd.Timestamp(ADMIT), profile)
    assert (day, quarter) == (-12, 5)
    _, day, quarter, _ = historical_time(-11 * 1440 + 0.001, pd.Timestamp(ADMIT), profile)
    assert (day, quarter) == (-11, 1)


def test_room_air_fallback_requires_estimate_and_empty_partition_quarter():
    t = -30 * 1440
    event = ox(t, pao2=None, spo2=90)
    result = score([event])
    assert result["events"][0]["historical_room_air_fallback"]
    assert result["events"][0]["fio2_source_event_id"] is None
    assert score([ox(t)])["baseline"]["score_status"] == "no_qualifying_data"
    # The quarter at this exact day boundary is 5; a following same-day fraction
    # has a different day/quarter key. A denominator at the same time blocks fallback.
    context = fio(t, label="IMV", value=0.5)
    assert not score([event, context])["events"][0]["historical_room_air_fallback"]
    context["ce_admit_dts"] = "2025-01-01T00:00:00Z"
    assert score([event, context])["events"][0]["historical_room_air_fallback"]


def test_partition_and_invasive_flags_are_explicit():
    event = ox(0, label="IMV", pao2=80)
    same = fio(0, label="IMV", value=0.8)
    foreign = fio(-1, key="foreign", label="IMV", value=0.3, partition="2025-01-01T00:00Z")
    assert score([event, same, foreign])["events"][0]["fio2_source_event_id"] == "f"
    for field in ("ce_admit_dts", "invasive_ind", "support_ind"):
        invalid = dict(event)
        invalid.pop(field)
        with pytest.raises(ValueError):
            score([invalid, same])


@pytest.mark.parametrize(
    "label,expected", [("OSA", 0), ("NIPPV", 3), ("HFNC", 0), ("SURG IMV", 0), ("IMV", 3)]
)
def test_support_detail_final_cap_and_singleton(label, expected):
    result = score([ox(0, label=label, pao2=80), fio(0, label=label, value=0.8)])
    assert result["acute"]["algorithm_score"] == expected
    assert result["events"][0]["pf_ratio_mmhg"] == 100


@pytest.mark.parametrize(
    "acute,baseline,c", list(itertools.product(range(5), range(5), ("0", "1", "ge2")))
)
def test_all_75_component_criterion_cases(acute, baseline, c):
    algorithm, state = eligibility(acute, baseline, True, c)
    expected = (2 if c == "ge2" else int(c)) + max(acute - baseline, 0) >= 2
    assert algorithm is expected
    assert state == ("eligible" if expected else "ineligible")
    assert eligibility(acute, baseline, False, c)[1] == (
        "eligible" if c == "ge2" else "indeterminate"
    )


def test_component_truncation_and_invalid_c():
    changes = [1, -2, 1, 0, 0, 0]
    c = str(sum(max(x, 0) for x in changes[1:]))
    assert eligibility(1, 0, True, c) == (True, "eligible")
    assert sum(max(x, 0) for x in changes) == 2
    assert max(sum(changes), 0) == 0
    for c in (True, 0, 1.5, "-1", "unknown"):
        with pytest.raises(ValueError):
            eligibility(0, 0, True, c)


def request(n=2):
    return normalize_experiment_request(
        {
            "schema_version": "experiment_request_v3",
            "replicates": n,
            "seed": 173203,
            "base": {
                "horizon": {"start_minute": 0, "end_minute": 16},
                "observation": {"start_minute": 0},
                "scoring": {"profile": PROFILE},
            },
            "comparator": {"label": "base"},
            "conditions": [{"label": "variant", "overrides": {"observation": {"noise_sd_pct": 0}}}],
            "primary_outcome": "sofa_eligibility_C0",
        }
    )


def test_v3_pipeline_and_common_pair_probabilities():
    result = run_experiment(request())
    rows = copy.deepcopy(result["scores"])
    base = request().comparator.condition_id
    for row in rows:
        row["delta_evaluable"] = (
            (1 if row["patient_id"] == 0 else None)
            if row["condition_id"] == base
            else (1 if row["patient_id"] == 0 else 0)
        )
    summary = summarize_v3(rows, base)
    contrast = next(
        r
        for r in summary["paired_contrasts"]
        if r["condition_id"] != base and r["metric"] == "delta_evaluable_ge1"
    )
    assert (
        contrast["common_pair_comparator_estimate"] == contrast["common_pair_variant_estimate"] == 1
    )
    assert contrast["estimate"] == 0 and contrast["denominator"] == 1
    assert contrast["lower"] is None
    for c in ("0", "1", "ge2"):
        cells = [
            r
            for r in summary["transitions"]
            if r["condition_id"] == base and r["table"] == f"eligibility_C{c}"
        ]
        assert len(cells) == 9 and sum(r["count"] for r in cells) == 2


def test_endpoint_generation_and_profile_label():
    raw = request(1).to_dict()
    raw["base"]["horizon"]["end_minute"] = 1440
    raw["comparator"]["overrides"] = {}
    raw["conditions"] = []
    req = normalize_experiment_request(raw)
    assert req.comparator.config.horizon.end_minute == 1441
    assert (
        "Modified"
        in profile_provenance(ScoringProfile(profile=PROFILE, single_record_suppression=False))[
            "qualification"
        ]
    )


def test_generated_endpoint_is_documented_and_scored():
    from sofa_resp_sim.reporting.experiment_service import explain_patient

    raw = request(1).to_dict()
    raw["base"]["horizon"]["end_minute"] = 1440
    raw["comparator"]["overrides"] = {}
    raw["conditions"] = []
    req = normalize_experiment_request(raw)
    trace = explain_patient(req, 0, req.comparator.condition_id)
    endpoint = next(e for e in trace["scoring"]["events"] if e["measurement_minute"] == 1440)
    assert endpoint["in_acute_target"]


def test_nine_transitions_are_exhaustive_disjoint_and_c_ge2_invariant():
    from sofa_resp_sim.reporting.historical_results import STATES

    req = request(9)
    rows = run_experiment(req)["scores"]
    for patient, (before, after) in enumerate(itertools.product(STATES, repeat=2)):
        for row in (r for r in rows if r["patient_id"] == patient):
            state = before if row["condition_id"] == req.comparator.condition_id else after
            row["algorithm_score"] = 2 if state == "eligible" else 0
            row["baseline_algorithm_score"] = 0
            row["delta_evaluable"] = None if state == "indeterminate" else row["algorithm_score"]
    result = summarize_v3(rows, req.comparator.condition_id)
    cells = [
        r
        for r in result["transitions"]
        if r["condition_id"] == req.conditions[0].condition_id and r["table"] == "eligibility_C0"
    ]
    assert [r["count"] for r in cells] == [1] * 9
    assert sorted(p for r in cells for p in r["patient_ids"]) == list(range(9))
    ge2 = [
        r
        for r in result["transitions"]
        if r["condition_id"] == req.conditions[0].condition_id
        and r["table"] == "eligibility_Cge2"
        and r["count"]
    ]
    assert len(ge2) == 1 and ge2[0]["count"] == 9
    assert ge2[0]["comparator_state"] == ge2[0]["variant_state"] == "eligible"


def test_c_changes_reuse_patient_and_scoring_identity():
    from sofa_resp_sim.reporting.experiment_bundle import build_bundle, verify_bundle

    req = request(2)
    first = run_experiment(req)
    raw = req.to_dict()
    raw["nonrespiratory_contribution"] = "ge2"
    second_request = normalize_experiment_request(raw)
    second = run_experiment(second_request)
    assert req.comparator.condition_id == second_request.comparator.condition_id

    def without_run(rows):
        return [{k: v for k, v in r.items() if k != "experiment_run_id"} for r in rows]

    assert without_run(first["scores"]) == without_run(second["scores"])
    files = build_bundle(first)
    assert verify_bundle(files)["scores"] == first["scores"]
    broken = dict(files)
    import json

    manifest = json.loads(broken["manifest.json"])
    manifest["profile_provenance"] = {}
    broken["manifest.json"] = json.dumps(manifest)
    import hashlib

    broken["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(broken[name].encode()).hexdigest()}  {name}\n"
        for name in sorted(broken)
        if name != "SHA256SUMS"
    )
    with pytest.raises(ValueError, match="[Pp]rofile"):
        verify_bundle(broken)


@pytest.mark.parametrize("profile", ["historical", "experimental"])
def test_e5_controlled_schedules_and_e6_negative_control(profile):
    from sofa_resp_sim.reporting.experiment_service import explain_patient
    from sofa_resp_sim.reporting.historical_catalogue import historical_request

    for mechanism in ("baseline_density", "history", "alignment"):
        req = historical_request(f"H_{mechanism}_{profile}", "imv", replicates=1)
        schedules = []
        for c in (req.comparator, *req.conditions):
            trace = explain_patient(req, 0, c.condition_id)
            events = [e for e in trace["scoring"]["events"] if e["block"] == "baseline"]
            schedules.append(events)
            assert trace["score"]["baseline_scheduled_count"] == len(events)
        a, b = schedules
        if mechanism == "baseline_density":
            assert (len(a), len(b)) == (24, 6)
            assert a[0]["measurement_minute"] == b[0]["measurement_minute"]
        elif mechanism == "history":
            assert (len(a), len(b)) == (24, 96)
            assert a[-1]["measurement_minute"] == b[-1]["measurement_minute"]
            latest = max(e["bin_epoch"] for e in b)
            assert sum(e["bin_epoch"] == latest for e in a) == sum(
                e["bin_epoch"] == latest for e in b
            )
        else:
            assert len(a) == len(b) == 24
            assert len({e["bin_epoch"] for e in a}) == 1
            assert len({e["bin_epoch"] for e in b}) == 2
    req = historical_request("H_rules_baseline_historical", "imv", replicates=2)
    result = run_experiment(req)
    for patient in range(2):
        assert (
            len({r["algorithm_score"] for r in result["scores"] if r["patient_id"] == patient}) == 1
        )


def test_e3_counts_reconcile_and_low_flow_truth_is_unavailable():
    from sofa_resp_sim.reporting.historical_catalogue import historical_request

    result = run_experiment(historical_request("H_missing_historical", "low_flow", replicates=3))
    for row in result["scores"]:
        assert (
            row["scheduled_oxygenation_count"]
            >= row["recorded_oxygenation_count"]
            >= row["convertible_oxygenation_count"]
            >= row["denominator_linked_count"]
            >= row["eligible_oxygenation_count"]
        )
        assert (
            sum(row["first_exclusion_counts"].values()) + row["eligible_oxygenation_count"]
            == row["scheduled_oxygenation_count"]
        )
        assert row["mean_synthetic_fio2_error_fraction"] is None


@pytest.mark.parametrize("invasive,expected", [(False, 0.5), (True, 0.8)])
def test_historical_source_priority(invasive, expected):
    event, context = ox(0, label="IMV"), fio(0, label="IMV", value=0.8)
    event["invasive_ind"] = context["invasive_ind"] = invasive
    context.update(fio2_meas_fraction=0.5, fio2_abg_fraction=0.3, flow_lpm=1)
    result = score([event, context])
    assert result["events"][0]["fio2_fraction"] == expected
    event["pao2_meas"], event["spo2_obs"] = 80, 90
    assert score([event, context])["events"][0]["pao2_used_mmhg"] == 80


@pytest.mark.parametrize(
    "t,recent",
    [
        (-14.001, False),
        (-14, True),
        (-1, True),
        (-0.999, False),
        (0, True),
        (5, True),
        (5.001, False),
    ],
)
def test_historical_lookup_edges(t, recent):
    result = score([ox(0, label="IMV"), fio(t, label="IMV")])
    assert result["events"][0]["qualifies_acute"] is recent


def test_flags_are_not_inferred_from_display_or_tracheostomy_context():
    events = [ox(0, label="NIPPV", pao2=70), fio(0, label="NIPPV", value=0.8)]
    for row in events:
        row["support_ind"] = False
        row["tracheostomy_context"] = "supplied_no_therapeutic_support"
    result = score(events)
    assert result["acute"]["algorithm_score"] == 2
    assert result["events"][0]["tracheostomy_context"] == "supplied_no_therapeutic_support"
    events[0]["support_ind"] = True
    assert score(events)["acute"]["algorithm_score"] == 4


def test_original_96_total_50_latest_date_and_exact_replay_are_preserved():
    from sofa_resp_sim.reporting.experiment_catalogue import catalogue_request
    from sofa_resp_sim.reporting.experiment_service import explain_patient

    req = catalogue_request("E5_opportunity", "room_air", replicates=1)
    trace = explain_patient(req, 0, req.comparator.condition_id)
    baseline = [e for e in trace["scoring"]["events"] if e["block"] == "baseline"]
    latest = max(e["bin_epoch"] for e in baseline)
    assert len(baseline) == 96
    assert sum(e["bin_epoch"] == latest for e in baseline) == 50
    replay = run_experiment(catalogue_request("E5_replay", "room_air", replicates=3))
    assert all(r["delta_legacy"] == 0 for r in replay["scores"])


def test_v3_empty_common_denominator_is_unavailable():
    result = run_experiment(request(1))
    contrast = next(r for r in result["paired_contrasts"] if r["metric"] == "delta_evaluable_ge1")
    assert contrast["denominator"] == contrast["common_pair_denominator"] == 0
    assert (
        contrast["estimate"]
        is contrast["common_pair_comparator_estimate"]
        is contrast["common_pair_variant_estimate"]
        is None
    )
    assert contrast["lower"] is contrast["upper"] is None


def test_v3_reorder_extension_and_rule_changes_preserve_pairing():
    from unittest.mock import patch

    from sofa_resp_sim.reporting import experiment_service

    raw = request(2).to_dict()
    raw["conditions"].append(
        {"label": "rule", "overrides": {"scoring": {"threshold_factor": 0.85}}}
    )
    req = normalize_experiment_request(raw)
    with patch.object(
        experiment_service, "generate_patient", wraps=experiment_service.generate_patient
    ) as generate:
        first = run_experiment(req, chunk_size=1)
    assert generate.call_count == 2
    raw["conditions"].reverse()
    raw["replicates"] = 4
    second = run_experiment(normalize_experiment_request(raw), chunk_size=3)

    def rows(result):
        return {
            (r["patient_id"], r["condition_id"]): {
                k: v for k, v in r.items() if k != "experiment_run_id"
            }
            for r in result["scores"]
        }

    a, b = rows(first), rows(second)
    assert a == {key: b[key] for key in a}
