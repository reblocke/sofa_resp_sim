import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sofa_resp_sim import score_respiratory
from sofa_resp_sim.core.resp_scoring import score_respiratory as core_score
from sofa_resp_sim.core.resp_simulation import (
    SimulationConfig,
    SupportPolicy,
    run_replicates,
    simulate_encounter,
)
from sofa_resp_sim.resp_scoring import score_respiratory as wrapped_score

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = json.loads((Path(__file__).parent / "fixtures/legacy_py_v1.json").read_text())


def test_legacy_entrypoints():
    assert score_respiratory is core_score is wrapped_score


@pytest.mark.parametrize("case", SNAPSHOT["cases"])
def test_seeded_legacy_snapshots(case):
    values = dict(case["config"])
    values["admit_dts"] = pd.Timestamp(values["admit_dts"])
    values["support_policy"] = SupportPolicy(**values["support_policy"])
    config = SimulationConfig(**values)
    assert (
        run_replicates(config, case["n_reps"], case["seed"]).to_dict("records")
        == case["replicates"]
    )
    observed = simulate_encounter(config, np.random.default_rng(case["seed"]))
    encoded = observed.to_json(orient="records", double_precision=15, date_format="epoch").encode()
    if hashlib.sha256(encoded).hexdigest() != case["observation_json_sha256"]:
        output = ROOT / "artifacts/local/acceptance"
        output.mkdir(parents=True, exist_ok=True)
        (output / f"legacy_observation_mismatch_seed_{case['seed']}.json").write_bytes(encoded)
    assert hashlib.sha256(encoded).hexdigest() == case["observation_json_sha256"]


def test_historical_artifacts_are_preserved():
    for path, digest in SNAPSHOT["historical_artifact_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
