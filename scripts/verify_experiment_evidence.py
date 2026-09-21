"""Check completeness and freshness of the compact, reviewed evidence collection."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from sofa_resp_sim.reporting.experiment_catalogue import CATALOGUE, REFERENCE_N, STRATA


def check_hash(root, name, expected):
    path = root / name
    path.resolve().relative_to(root.resolve())
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Stale artifact: {path}")


def reviewed_figures(root, manifest):
    for figure in manifest["figures"]:
        if {Path(o["path"]).suffix for o in figure["outputs"]} != {".png", ".svg"}:
            raise ValueError("Each figure requires both PNG and SVG outputs")
        pngs = []
        for output in figure["outputs"]:
            check_hash(root, output["path"], output["sha256"])
            if output["path"].endswith(".png"):
                pngs.append(output["sha256"])
        review = figure.get("visual_review", {})
        if len(pngs) != 1 or review.get("reviewed_png_sha256") != pngs[0]:
            raise ValueError("Each figure needs a visual review bound to its current PNG")
        if figure.get("visual_review_status") != "reviewed_png":
            raise ValueError("Visual review is incomplete")


def verify(root):
    provenance = json.loads((root / "table_provenance.json").read_text())
    expected = {(entry, stratum) for entry in CATALOGUE for stratum in STRATA}
    sources = provenance["sources"]
    if len(sources) != len(expected) or {(r["entry"], r["stratum"]) for r in sources} != expected:
        raise ValueError("Reference source catalogue is incomplete or duplicated")
    for source in sources:
        minimum = 1 if CATALOGUE[source["entry"]]["deterministic"] else REFERENCE_N
        if source["completed_patients"] < minimum:
            raise ValueError("Reference N is below the declared minimum")
    tables = {}
    for name, digest in provenance["table_sha256"].items():
        check_hash(root, name, digest)
        with (root / name).open(newline="") as stream:
            tables[name] = list(csv.DictReader(stream))
    if set(tables) != {"condition_summary.csv", "paired_contrasts.csv"}:
        raise ValueError("Required reference tables are missing")
    for name, digest in provenance["selected_trace_sha256"].items():
        check_hash(root, name, digest)
    trace_examples = {
        ("E1_episode", "room_air"),
        ("E2_bias", "low_flow"),
        ("E3_timing", "hfnc"),
        ("E4_measured", "imv"),
        ("E5_replay", "room_air"),
        ("E6_singleton", "low_flow"),
    }
    expected_traces = {
        f"traces/{entry}__{stratum}__{name}.csv"
        for entry, stratum in trace_examples
        for name in ("selected_events", "episodes")
    }
    if set(provenance["selected_trace_sha256"]) != expected_traces:
        raise ValueError("The fixed six event/episode trace pairs are incomplete")
    if (
        provenance["trace_selection"]["patient_id"] != 0
        or {tuple(pair) for pair in provenance["trace_selection"]["examples"]} != trace_examples
    ):
        raise ValueError("The declared patient-0 selection differs")
    figures = json.loads((root / "figure_data_manifest.json").read_text())
    check_hash(root, "table_provenance.json", figures["table_provenance_sha256"])
    pairs = {(f["entry"], f["kind"]) for f in figures["figures"]}
    if len(figures["figures"]) != 36 or pairs != {
        (e, k) for e in CATALOGUE for k in ("absolute", "paired")
    }:
        raise ValueError("Primary-outcome figures are incomplete or duplicated")
    for figure in figures["figures"]:
        if figure["primary_outcome"] != CATALOGUE[figure["entry"]]["primary_outcome"]:
            raise ValueError("Figure does not show the prespecified primary outcome")
        table = figure["source_table"]
        if figure["source_table_sha256"] != provenance["table_sha256"][table]:
            raise ValueError("Figure uses a different source table")
        selected = [
            r
            for r in tables[table]
            if r["entry"] == figure["entry"] and r["metric"] == figure["primary_outcome"]
        ]
        if not selected or len(selected) != figure["selected_rows"]:
            raise ValueError("Figure row selection differs")
    reviewed_figures(root, figures)
    rules = root / "rule_explorer"
    rule_manifest = json.loads((rules / "manifest.json").read_text())
    if rule_manifest["monte_carlo"] or rule_manifest["cases"] != 8 or rule_manifest["cells"] != 476:
        raise ValueError("Deterministic evidence catalogue differs")
    for name, digest in rule_manifest["file_sha256"].items():
        check_hash(rules, name, digest)
    rule_figures = json.loads((rules / "figure_data_manifest.json").read_text())
    if len(rule_figures["figures"]) != 8:
        raise ValueError("Deterministic figures are incomplete")
    if {f["source"] for f in rule_figures["figures"]} != {
        name for name in rule_manifest["file_sha256"] if name.endswith(".json")
    }:
        raise ValueError("Deterministic figure sources are missing or duplicated")
    for figure in rule_figures["figures"]:
        check_hash(rules, figure["source"], figure["source_sha256"])
    reviewed_figures(rules, rule_figures)
    findings = (root / "FINDINGS.md").read_text()
    if not all(f"## {entry}:" in findings for entry in CATALOGUE):
        raise ValueError("Findings do not cover the complete catalogue")
    return {
        "status": "verified_artifact_completeness",
        "sources": len(sources),
        "primary_figures": 36,
        "rule_figures": 8,
        "scope": "Artifact completeness and hashes; scientific acceptance is separate",
    }


def verify_historical(root):
    from sofa_resp_sim.core.historical_trops import SOURCE_HASHES
    from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request
    from sofa_resp_sim.reporting.historical_catalogue import MECHANISMS, REFERENCE_ENTRIES

    repo = Path(__file__).resolve().parents[1]
    frozen_path = repo / "experiments/trops_v1/manifest.json"
    frozen = json.loads(frozen_path.read_text())
    manifest = json.loads((root / "table_provenance.json").read_text())
    check_hash(repo, "experiments/trops_v1/manifest.json", manifest["catalogue_manifest_sha256"])
    check_hash(
        repo,
        "experiments/trops_v1/deterministic_manifest.json",
        manifest["deterministic_manifest_sha256"],
    )
    if manifest["source_files_sha256"] != SOURCE_HASHES:
        raise ValueError("Historical source hash mismatch")
    expected = {
        f"experiments/trops_v1/{entry}__{stratum}.json"
        for entry in REFERENCE_ENTRIES
        for stratum in STRATA
    }
    if len(frozen["requests"]) != 48 or {r["path"] for r in frozen["requests"]} != expected:
        raise ValueError("Frozen historical inventory is incomplete")
    sources = manifest["sources"]
    if len(sources) != 48 or {r["path"] for r in sources} != expected:
        raise ValueError("Historical reference inventory is incomplete")
    for item in sources:
        check_hash(repo, item["path"], item["sha256"])
        request = normalize_experiment_request(json.loads((repo / item["path"]).read_text()))
        if request.run_id != item["run_id"] or item["completed_patients"] != 2000:
            raise ValueError("Historical reference identity or N differs")
    for name, digest in manifest["file_sha256"].items():
        check_hash(root, name, digest)
    if manifest["deterministic"] != {
        "pf_cells": 336,
        "conversion_cells": 16,
        "eligibility_cells": 75,
        "monte_carlo": False,
    }:
        raise ValueError("Historical deterministic grids differ")
    traces = json.loads((root / "trace_index.json").read_text())
    for item in traces:
        check_hash(root, item["path"], item["sha256"])
    if {(r["entry"], r["stratum"]) for r in traces if r["patient_id"] == 0} != {
        (e, s) for e in REFERENCE_ENTRIES for s in STRATA
    }:
        raise ValueError("Historical patient-zero trace inventory differs")
    with (root / "eligibility_transitions.csv").open() as stream:
        cells = list(csv.DictReader(stream))
    groups = {}
    for r in cells:
        key = (r["entry"], r["stratum"], r["table"])
        groups.setdefault(key, []).append(r)
    if len(groups) != 144:
        raise ValueError("Conditional transition groups are incomplete")
    for key, rows in groups.items():
        patients = [p for r in rows for p in json.loads(r["patient_ids"])]
        if (
            len(rows) != 9
            or sorted(patients) != list(range(2000))
            or any(
                int(r["count"]) != len(json.loads(r["patient_ids"]))
                or int(r["denominator"]) != 2000
                for r in rows
            )
        ):
            raise ValueError("Transition counts/patients do not reconcile")
        selected = {r["patient_id"] for r in traces if (r["entry"], r["stratum"]) == key[:2]}
        if not all(
            not json.loads(r["patient_ids"]) or min(json.loads(r["patient_ids"])) in selected
            for r in rows
        ):
            raise ValueError("Missing prespecified transition-member trace")
    figures = json.loads((root / "figure_data_manifest.json").read_text())
    check_hash(root, "table_provenance.json", figures["table_provenance_sha256"])
    if len(figures["figures"]) != 6 or {f["mechanism"] for f in figures["figures"]} != set(
        MECHANISMS
    ):
        raise ValueError("Historical mechanism figures incomplete")
    for f in figures["figures"]:
        check_hash(root, f["source_table"], f["source_table_sha256"])
        if f["primary_outcome"] != MECHANISMS[f["mechanism"]][2] or f["selected_rows"] != 8:
            raise ValueError("Historical figure selection differs")
    reviewed_figures(root, figures)
    return {
        "status": "verified_artifact_completeness",
        "sources": 48,
        "mechanism_figures": 6,
        "scope": "Historical synthetic source mapping, no SQL execution",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("artifacts/experiments_v2"))
    args = parser.parse_args()
    results = {"v2": verify(args.input)}
    if args.input == Path("artifacts/experiments_v2"):
        results["v3"] = verify_historical(Path("artifacts/trops_sensitivity_v1"))
    print(json.dumps(results))


if __name__ == "__main__":
    main()
