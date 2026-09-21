"""Write/check the fully resolved, prespecified illustrative catalogue (no simulations)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sofa_resp_sim.reporting.experiment_catalogue import (
    CATALOGUE,
    REFERENCE_N,
    STRATA,
    catalogue_metadata,
    catalogue_request,
)


def freeze(destination: Path, check=False):
    destination.mkdir(parents=True, exist_ok=True)
    outputs = {"catalogue.json": catalogue_metadata()}
    for experiment in ("E1", "E2", "E3", "E4", "E5", "E6"):
        outputs[f"{experiment}.json"] = {
            "experiment": experiment,
            "requests": [
                catalogue_request(key, stratum, replicates=REFERENCE_N).to_dict()
                for key, entry in CATALOGUE.items()
                if entry["experiment"] == experiment
                for stratum in STRATA
            ],
        }
    for name, payload in outputs.items():
        text = json.dumps(payload, indent=2, allow_nan=False) + "\n"
        path = destination / name
        if check:
            if not path.exists() or path.read_text() != text:
                raise ValueError(
                    f"Stale catalogue: {path}; run scripts/freeze_experiment_catalogue.py"
                )
        else:
            path.write_text(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    freeze(Path(__file__).resolve().parents[1] / "experiments", args.check)
