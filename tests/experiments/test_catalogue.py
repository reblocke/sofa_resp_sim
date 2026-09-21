import json
from pathlib import Path

import pytest

from sofa_resp_sim.core.experiment_config import ScenarioConfig
from sofa_resp_sim.core.observation import document_patient
from sofa_resp_sim.core.paired_simulation import generate_patient
from sofa_resp_sim.reporting.experiment_catalogue import CATALOGUE, STRATA, catalogue_request
from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request
from sofa_resp_sim.reporting.experiment_service import run_experiment


@pytest.mark.parametrize("entry", list(CATALOGUE))
@pytest.mark.parametrize("stratum", list(STRATA))
def test_finite_catalogue_executes_small_paired_runs(entry, stratum):
    request = catalogue_request(entry, stratum, replicates=2)
    result = run_experiment(request)
    assert result["completed_patients"] == request.replicates
    assert len(result["scores"]) == request.replicates * len(
        {c.condition_id for c in (request.comparator, *request.conditions)}
    )
    assert result["condition_summary"]
    json.dumps(result, allow_nan=False)
    if entry == "E5_replay":
        assert all(row["delta_signed"] == row["delta_legacy"] == 0 for row in result["scores"])
        assert all(row["qualifying_pf_count"] >= 2 for row in result["scores"])
    if entry == "E3_zero":
        assert request.comparator.condition_id == request.conditions[0].condition_id
        assert all(row["condition_label"] == request.comparator.label for row in result["scores"])


def test_expansion_preserves_the_edited_base():
    base = ScenarioConfig().override(
        {
            "generator": {"mean_pct": 87},
            "horizon": {"start_minute": -60},
            "observation": {"start_minute": -30, "noise_sd_pct": 0.25},
        }
    )
    request = catalogue_request("E1_density", "room_air", base=base.to_dict())
    assert request.base == base
    assert all(
        c.config.generator == base.generator for c in (request.comparator, *request.conditions)
    )
    assert all(c.config.observation.start_minute == -30 for c in request.conditions)
    assert all(c.config.observation.noise_sd_pct == 0.25 for c in request.conditions)


@pytest.mark.parametrize("entry", ["E4_estimated", "E4_measured", "E6_rules"])
def test_rule_contrasts_reuse_identical_records(entry):
    request = catalogue_request(entry, "hfnc", replicates=2)
    base = request.comparator.config
    patient = generate_patient(base.generator, base.horizon, request.seed, 0)
    records = document_patient(patient, base)
    assert all(document_patient(patient, c.config) == records for c in request.conditions)


def test_saved_configurations_match_prespecified_catalogue():
    root = Path(__file__).resolve().parents[2] / "experiments"
    found = set()
    for experiment in ["E1", "E2", "E3", "E4", "E5", "E6"]:
        saved = json.loads((root / f"{experiment}.json").read_text())
        for raw in saved["requests"]:
            entry, stratum = raw["experiment_id"].split(":")
            expected = catalogue_request(entry, stratum, replicates=2000)
            assert normalize_experiment_request(raw) == expected
            assert raw == expected.to_dict()
            found.add((entry, stratum))
    assert found == {(e, s) for e in CATALOGUE for s in STRATA}
