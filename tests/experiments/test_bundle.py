import copy
import hashlib
import json
from unittest.mock import patch

import pytest

from sofa_resp_sim.reporting.experiment_bundle import (
    REQUIRED,
    build_bundle,
    compare_scientific_values,
    decode_table,
    encode_table,
    verify_bundle,
)
from sofa_resp_sim.reporting.experiment_catalogue import catalogue_request
from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request
from sofa_resp_sim.reporting.experiment_service import run_experiment


@pytest.fixture
def result():
    return run_experiment(catalogue_request("E1_episode", "room_air"))


def rehash(files):
    files["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(files[name].encode()).hexdigest()}  {name}\n"
        for name in sorted(files)
        if name != "SHA256SUMS"
    )


def test_roundtrip_hashes_and_versions(result):
    files = build_bundle(result)
    assert set(files) == REQUIRED
    restored = verify_bundle(files)
    for key in [
        "request",
        "scores",
        "condition_summary",
        "paired_contrasts",
        "transitions",
        "reclassification",
    ]:
        assert restored[key] == result[key]
    again = build_bundle(result, environment={"test_environment": "different"})
    assert (
        json.loads(files["manifest.json"])["scientific_data_sha256"]
        == json.loads(again["manifest.json"])["scientific_data_sha256"]
    )
    assert files["SHA256SUMS"] != again["SHA256SUMS"]
    assert restored["selected_events"]
    assert {r["patient_id"] for r in restored["selected_events"]} == {0}
    source_ids = {(r["condition_id"], r["event_id"]) for r in restored["selected_events"]}
    for event in restored["selected_events"]:
        if event.get("fio2_source_event_id"):
            assert (event["condition_id"], event["fio2_source_event_id"]) in source_ids
    assert restored["algorithm_zero_convention"] == result["algorithm_zero_convention"]


def test_typed_csv_preserves_zero_null_empty_and_nested_values():
    rows = [
        {"cell": 0, "text": "", "value": None, "flag": False, "nested": {"ids": [1, 2]}},
        {"cell": "U", "text": r"\e", "value": 0.5, "flag": True, "nested": None},
    ]
    text, schema = encode_table(rows)
    assert decode_table(text, schema) == rows


def test_corruption_unknown_versions_and_incomplete_runs_fail(result):
    files = build_bundle(result)
    changed = dict(files)
    changed["scores.csv"] += "changed\n"
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_bundle(changed)
    manifest = json.loads(files["manifest.json"])
    manifest["bundle_version"] = "future"
    changed = dict(files)
    changed["manifest.json"] = json.dumps(manifest)
    rehash(changed)
    with pytest.raises(ValueError, match="Unsupported bundle_version"):
        verify_bundle(changed)
    invalid = copy.deepcopy(result)
    invalid["scores"].pop()
    with pytest.raises(ValueError, match="Incomplete"):
        build_bundle(invalid)
    invalid = copy.deepcopy(result)
    invalid["condition_summary"][0]["estimate"] = 99.0
    with pytest.raises(ValueError, match="Scientific"):
        build_bundle(invalid)


def test_float_tolerance_cannot_hide_changed_discrete_fields():
    compare_scientific_values({"float": 1.0}, {"float": 1.0 + 1e-12})
    compare_scientific_values({"score": 1}, {"score": 1.0})
    for a, b in [
        ({"score": 1}, {"score": 2}),
        ({"score": 1}, {"score": 1.000000000001}),
        ({"status": "observed_scored"}, {"status": "no_qualifying_data"}),
        ({"float": 1.0}, {"float": 1.01}),
    ]:
        with pytest.raises(ValueError):
            compare_scientific_values(a, b)


def test_append_only_generates_new_patients_and_preserves_prior_rows():
    from sofa_resp_sim.reporting import experiment_service

    request = catalogue_request("E1_density", "room_air", replicates=2)
    before = run_experiment(request)
    snapshot = copy.deepcopy(before)
    extended = normalize_experiment_request({**request.to_dict(), "replicates": 4})
    with patch.object(
        experiment_service, "generate_patient", wraps=experiment_service.generate_patient
    ) as generate:
        appended = run_experiment(extended, previous=before)
    assert generate.call_count == 2
    assert before == snapshot
    assert appended["scores"] == run_experiment(extended)["scores"]
    assert appended["append_parent_run_id"] == before["experiment_run_id"]
    for row in before["scores"]:
        updated = next(
            r
            for r in appended["scores"]
            if (r["patient_id"], r["condition_id"]) == (row["patient_id"], row["condition_id"])
        )
        assert updated == {**row, "experiment_run_id": extended.run_id}
    with pytest.raises(ValueError, match="increase N"):
        run_experiment(request, previous=before)
    changed = normalize_experiment_request({**extended.to_dict(), "seed": 1})
    with pytest.raises(ValueError, match="without changing"):
        run_experiment(changed, previous=before)
