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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("artifacts/experiments_v2"))
    print(json.dumps(verify(parser.parse_args().input)))


if __name__ == "__main__":
    main()
