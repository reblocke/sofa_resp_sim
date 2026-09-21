"""Regenerate the explicitly labeled 200-patient startup example; not a reference run."""

from __future__ import annotations

import json
from pathlib import Path

from sofa_resp_sim.core.experiment_config import GENERATOR_VERSION, RNG_VERSION
from sofa_resp_sim.reporting.experiment_catalogue import catalogue_metadata, catalogue_request
from sofa_resp_sim.reporting.experiment_service import run_experiment

ROOT = Path(__file__).resolve().parents[1]


def main():
    request = catalogue_request("E1_density", "room_air", replicates=200)
    payload = {
        "schema_version": "saved_experiment_v2",
        "label": "Saved synthetic example (200 paired patients)",
        "purpose": "Precomputed startup preview; not a newly executed run or clinical reference",
        "generator_version": GENERATOR_VERSION,
        "rng_version": RNG_VERSION,
        "catalogue": catalogue_metadata(),
        "result": run_experiment(request),
    }
    path = ROOT / "artifacts/saved_experiment_v2.json"
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    )
    print(f"Wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
