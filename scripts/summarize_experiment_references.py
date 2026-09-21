"""Extract compact, source-linked tables only from a complete reference run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

from sofa_resp_sim.core.experiment_config import fingerprint
from sofa_resp_sim.reporting.experiment_bundle import verify_bundle
from sofa_resp_sim.reporting.experiment_catalogue import (
    CATALOGUE,
    CATALOGUE_VERSION,
    REFERENCE_N,
    STRATA,
    catalogue_request,
)
from sofa_resp_sim.workflows.experiment_cli import read_files

TRACE_EXAMPLES = {
    ("E1_episode", "room_air"),
    ("E2_bias", "low_flow"),
    ("E3_timing", "hfnc"),
    ("E4_measured", "imv"),
    ("E5_replay", "room_air"),
    ("E6_singleton", "low_flow"),
}


def collect(index_path):
    index = json.loads(index_path.read_text())
    expected = {(entry, stratum) for entry in CATALOGUE for stratum in STRATA}
    actual = [(run["entry"], run["stratum"]) for run in index["runs"]]
    if (
        index["status"] != "complete_reference_bundles"
        or index["catalogue_version"] != CATALOGUE_VERSION
        or len(actual) != len(expected)
        or set(actual) != expected
        or index["requested_stochastic_patients"] < REFERENCE_N
    ):
        raise ValueError(
            "Only a complete, current, minimum-N catalogue may become reference tables"
        )
    tables = {"condition_summary.csv": [], "paired_contrasts.csv": []}
    sources = []
    traces = {}
    for run in index["runs"]:
        path = index_path.parent / f"{run['entry']}__{run['stratum']}.zip"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != run["bundle_sha256"]:
            raise ValueError(f"Archive digest differs: {path}")
        files = read_files(path)
        bundle = verify_bundle(files)
        request = catalogue_request(
            run["entry"], run["stratum"], replicates=index["requested_stochastic_patients"]
        )
        if bundle["request"] != request.to_dict():
            raise ValueError(f"Frozen request differs: {path}")
        if bundle["completed_patients"] != request.replicates:
            raise ValueError(f"Incomplete run: {path}")
        if bundle["manifest"]["scientific_data_sha256"] != run["scientific_data_sha256"]:
            raise ValueError(f"Scientific identity differs: {path}")
        if (run["entry"], run["stratum"]) in TRACE_EXAMPLES:
            if bundle["manifest"]["selected_patient"] != 0:
                raise ValueError("Declared illustrative traces require synthetic patient 0")
            for name in ("selected_events.csv", "episodes.csv"):
                traces[f"traces/{run['entry']}__{run['stratum']}__{name}"] = files[name]
        labels = {request.comparator.condition_id: request.comparator.label}
        order = {request.comparator.condition_id: 0}
        for condition in request.conditions:
            labels.setdefault(condition.condition_id, condition.label)
            order.setdefault(condition.condition_id, len(order))
        for name in tables:
            for row in csv.DictReader(io.StringIO(files[name])):
                tables[name].append(
                    {
                        "entry": run["entry"],
                        "stratum": run["stratum"],
                        "condition_label": labels[row["condition_id"]],
                        "condition_order": order[row["condition_id"]],
                        "primary_outcome": request.primary_outcome,
                        **row,
                    }
                )
        sources.append(
            {
                **run,
                "request_sha256": fingerprint(request.to_dict()),
                "source_tables": {
                    name: bundle["manifest"]["scientific_hashes"][name] for name in tables
                },
            }
        )
    return tables, sources, traces


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index", type=Path, default=Path("artifacts/local/references_v2/run_index.json")
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/experiments_v2"))
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("Output already exists; choose a new directory to preserve earlier evidence")
    tables, sources, traces = collect(args.index)
    args.output.mkdir(parents=True)
    hashes = {}
    for name, rows in tables.items():
        path = args.output / name
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name, text in traces.items():
        path = args.output / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)
    manifest = {
        "schema_version": "reference_table_provenance_v1",
        "catalogue_version": CATALOGUE_VERSION,
        "index_sha256": hashlib.sha256(args.index.read_bytes()).hexdigest(),
        "table_sha256": hashes,
        "sources": sources,
        "selected_trace_sha256": {
            name: hashlib.sha256(text.encode()).hexdigest() for name, text in traces.items()
        },
        "trace_selection": {
            "patient_id": 0,
            "examples": sorted(TRACE_EXAMPLES),
            "rule": "Fixed patient 0; E1-E6 and four strata; no effect-size selection",
        },
        "scope": "Uncalibrated synthetic model; pointwise Monte Carlo uncertainty, not clinical CI",
        "figure_status": "Tables only; figure rendering and visual verification remain required",
    }
    (args.output / "table_provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
