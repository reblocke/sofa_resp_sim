"""Run the frozen catalogue with verified, resumable per-stratum bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from sofa_resp_sim.reporting.experiment_bundle import verify_bundle
from sofa_resp_sim.reporting.experiment_catalogue import (
    CATALOGUE,
    CATALOGUE_VERSION,
    REFERENCE_N,
    REFERENCE_SEED,
    STRATA,
    catalogue_request,
)
from sofa_resp_sim.workflows.experiment_cli import native_environment, read_files


def save_index(path, index):
    temporary = path.with_suffix(".pending")
    temporary.write_text(json.dumps(index, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def validate_existing(path, request, environment):
    bundle = verify_bundle(read_files(path))
    if bundle["request"] != request.to_dict():
        raise ValueError(f"Saved request differs: {path}")
    recorded = bundle["manifest"]["environment"]
    for key in ("python", "dependencies", "source_sha256"):
        if recorded.get(key) != environment[key]:
            raise ValueError(f"Saved {key} differs: {path}; use a new output directory")
    if bundle["completed_patients"] != request.replicates:
        raise ValueError(f"Incomplete saved run: {path}")
    return bundle


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/local/references_v2"))
    parser.add_argument("--replicates", type=int, default=REFERENCE_N)
    parser.add_argument("--entries", nargs="+", choices=CATALOGUE, default=list(CATALOGUE))
    parser.add_argument("--strata", nargs="+", choices=STRATA, default=list(STRATA))
    args = parser.parse_args(argv)
    if args.replicates < 1:
        parser.error("replicates must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    environment = native_environment()
    full_catalogue = set(args.entries) == set(CATALOGUE) and set(args.strata) == set(STRATA)
    index = {
        "schema_version": "reference_run_index_v1",
        "catalogue_version": CATALOGUE_VERSION,
        "seed": REFERENCE_SEED,
        "requested_stochastic_patients": args.replicates,
        "full_catalogue": full_catalogue,
        "minimum_reference_n_met": args.replicates >= REFERENCE_N,
        "status": "running",
        "environment": environment,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "runs": [],
        "scope": "Uncalibrated synthetic demonstrations; no population weighting",
    }
    index_path = args.output / "run_index.json"
    save_index(index_path, index)
    try:
        for entry in dict.fromkeys(args.entries):
            for stratum in dict.fromkeys(args.strata):
                request = catalogue_request(entry, stratum, replicates=args.replicates)
                name = f"{entry}__{stratum}"
                output = args.output / f"{name}.zip"
                resumed = output.exists()
                if not resumed:
                    # Only a completely written and verified archive receives its final name.
                    with tempfile.TemporaryDirectory(prefix=f".{name}-", dir=args.output) as tmp:
                        pending = Path(tmp) / "bundle.zip"
                        command = [
                            sys.executable,
                            "-m",
                            "sofa_resp_sim.workflows.experiment_cli",
                            "run",
                            "--entry",
                            entry,
                            "--stratum",
                            stratum,
                            "--replicates",
                            str(args.replicates),
                            "--output",
                            str(pending),
                        ]
                        print(f"Running {name}: N={request.replicates}", flush=True)
                        with (args.output / f"{name}.log").open("w") as log:
                            subprocess.run(
                                command, stdout=log, stderr=subprocess.STDOUT, check=True
                            )
                        validate_existing(pending, request, environment)
                        pending.replace(output)
                bundle = validate_existing(output, request, environment)
                index["runs"].append(
                    {
                        "entry": entry,
                        "stratum": stratum,
                        "completed_patients": bundle["completed_patients"],
                        "bundle": output.name,
                        "bundle_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                        "scientific_data_sha256": bundle["manifest"]["scientific_data_sha256"],
                        "resumed": resumed,
                    }
                )
                save_index(index_path, index)
                print(f"Verified {name} ({len(index['runs'])} runs)", flush=True)
        index["status"] = (
            "complete_reference_bundles"
            if full_catalogue and args.replicates >= REFERENCE_N
            else "complete_partial_or_smoke"
        )
        index["finished_at_utc"] = datetime.now(UTC).isoformat()
        save_index(index_path, index)
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        index["status"] = "failed"
        index["error"] = str(error)
        save_index(index_path, index)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
