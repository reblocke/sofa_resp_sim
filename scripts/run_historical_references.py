"""Execute the prespecified synthetic v3 catalogue; preserve complete hashed bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from sofa_resp_sim.reporting.experiment_bundle import build_bundle, verify_bundle
from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request
from sofa_resp_sim.reporting.experiment_service import run_experiment
from sofa_resp_sim.workflows.experiment_cli import native_environment, read_files, write_files

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments/trops_v1/manifest.json"


def execute(item, output):
    source = ROOT / item["path"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != item["sha256"]:
        raise ValueError(f"Frozen request changed: {source}")
    request = normalize_experiment_request(json.loads(source.read_text()))
    if request.run_id != item["run_id"] or request.replicates != 2000:
        raise ValueError("Reference identity or patient allocation changed")
    target = Path(output) / (source.stem + ".zip")
    environment = native_environment()
    if target.exists():
        bundle = verify_bundle(read_files(target))
        if (
            bundle["request"] != request.to_dict()
            or bundle["manifest"]["environment"]["source_sha256"] != environment["source_sha256"]
        ):
            raise ValueError("Existing reference has a different request or package source")
    else:
        result = run_experiment(request)
        files = build_bundle(result, environment=environment)
        verify_bundle(files)
        write_files(files, target)
        bundle = verify_bundle(read_files(target))
    return {
        **item,
        "bundle": str(target.relative_to(ROOT)),
        "bundle_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "scientific_data_sha256": bundle["manifest"]["scientific_data_sha256"],
        "source_sha256": environment["source_sha256"],
        "completed_patients": request.replicates,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/local/historical_references"
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text())
    completed = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        pending = [pool.submit(execute, item, args.output) for item in manifest["requests"]]
        for future in as_completed(pending):
            completed.append(future.result())
            index = {
                "status": "complete" if len(completed) == 48 else "in_progress",
                "recorded_at_utc": datetime.now(UTC).isoformat(),
                "catalogue_manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                "completed": sorted(completed, key=lambda r: r["path"]),
            }
            (args.output / "index.json").write_text(json.dumps(index, indent=2) + "\n")
            print(f"{len(completed)}/48 verified: {completed[-1]['path']}", flush=True)


if __name__ == "__main__":
    main()
