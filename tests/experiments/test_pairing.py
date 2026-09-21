import copy
import json
from unittest.mock import patch

from sofa_resp_sim.browser_contract import explain_experiment_payload, run_experiment_payload
from sofa_resp_sim.core.experiment_config import SCHEMA_VERSION
from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request
from sofa_resp_sim.reporting.experiment_service import explain_patient, run_experiment


def payload(n=5):
    return {
        "schema_version": SCHEMA_VERSION,
        "replicates": n,
        "base": {
            "horizon": {"start_minute": 0, "end_minute": 60},
            "observation": {"start_minute": 0},
        },
        "conditions": [
            {"label": "Hourly", "overrides": {"observation": {"interval_minutes": 60}}},
            {"label": "Threshold", "overrides": {"scoring": {"threshold_factor": 0.85}}},
        ],
    }


def scientific_rows(result):
    return {
        (row["patient_id"], row["condition_id"]): {
            key: value
            for key, value in row.items()
            if key not in {"experiment_run_id", "condition_label"}
        }
        for row in result["scores"]
    }


def test_condition_order_and_isolation():
    source = payload()
    base = run_experiment(normalize_experiment_request(source))
    reordered = copy.deepcopy(source)
    reordered["conditions"].reverse()
    reordered["conditions"][0]["label"] = "A new display label"
    assert scientific_rows(base) == scientific_rows(
        run_experiment(normalize_experiment_request(reordered))
    )
    request = normalize_experiment_request(source)
    isolated = {
        "schema_version": SCHEMA_VERSION,
        "replicates": request.replicates,
        "base": request.conditions[0].config.to_dict(),
    }
    alone = scientific_rows(run_experiment(normalize_experiment_request(isolated)))
    assert alone == {key: row for key, row in scientific_rows(base).items() if key in alone}
    extended = copy.deepcopy(source)
    extended["conditions"].append(
        {"label": "Missing", "overrides": {"documentation": {"missing_probability": 0.5}}}
    )
    extended_rows = scientific_rows(run_experiment(normalize_experiment_request(extended)))
    assert scientific_rows(base) == {key: extended_rows[key] for key in scientific_rows(base)}


def test_chunk_and_append_invariance():
    source = payload(200)
    source["base"]["horizon"]["end_minute"] = 2
    source["conditions"] = source["conditions"][:1]
    request = normalize_experiment_request(source)
    first = scientific_rows(run_experiment(request, chunk_size=1))
    for chunk in [7, 64]:
        assert scientific_rows(run_experiment(request, chunk_size=chunk)) == first
    extended = run_experiment(normalize_experiment_request({**source, "replicates": 1000}))
    assert first == {key: row for key, row in scientific_rows(extended).items() if key[0] < 200}


def test_physiology_is_generated_once_and_progress_is_real():
    from sofa_resp_sim.reporting import experiment_service

    request = normalize_experiment_request(payload())
    reports = []
    with patch.object(
        experiment_service, "generate_patient", wraps=experiment_service.generate_patient
    ) as generate:
        result = run_experiment(request, chunk_size=2, on_progress=reports.append)
    assert generate.call_count == request.replicates
    assert [r["completed_patients"] for r in reports if r["stage"] == "completed_chunk"] == [
        2,
        4,
        5,
    ]
    attempts = [r for r in reports if r["stage"] == "scoring"]
    assert [r["attempted_patients"] for r in attempts] == [1, 2, 3, 4, 5]
    assert [r["completed_patients"] for r in attempts] == [0, 1, 2, 3, 4]
    assert reports[-1]["completed_scoring_evaluations"] == len(result["scores"])
    for patient_id in range(request.replicates):
        rows = [r for r in result["scores"] if r["patient_id"] == patient_id]
        assert len({r["latent_id"] for r in rows}) == 1
        assert len({r["support_id"] for r in rows}) == 1


def test_single_patient_reconstruction():
    from sofa_resp_sim.reporting import experiment_service

    request = normalize_experiment_request(payload())
    saved = run_experiment(request)["scores"][4]
    with patch.object(
        experiment_service, "generate_patient", wraps=experiment_service.generate_patient
    ) as generate:
        explanation = explain_patient(
            request, saved["patient_id"], saved["condition_id"], expected_score=saved
        )
    assert generate.call_count == 1
    assert explanation["score"] == saved
    json.dumps(explanation, allow_nan=False)


def test_browser_contract_roundtrip_and_structured_errors():
    request = payload(2)
    result = run_experiment_payload({"request": request})
    assert result["ok"]
    json.dumps(result, allow_nan=False)
    saved = result["scores"][0]
    explained = explain_experiment_payload(
        {
            "request": result["request"],
            "patient_id": saved["patient_id"],
            "condition_id": saved["condition_id"],
            "expected_score": saved,
        }
    )
    assert explained["ok"]
    assert explained["score"] == saved
    invalid = run_experiment_payload({"request": {**request, "schema_version": "v99"}})
    assert not invalid["ok"]
    assert invalid["error"]["type"] == "ValueError"
    assert not explain_experiment_payload(
        {"request": request, "patient_id": 1.5, "condition_id": saved["condition_id"]}
    )["ok"]
