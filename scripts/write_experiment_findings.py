"""Write descriptive primary-outcome findings with exact table provenance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from sofa_resp_sim.reporting.experiment_catalogue import CATALOGUE


def value(raw, unit):
    if raw == "":
        return "not evaluable"
    number = float(raw)
    if unit == "probability_difference":
        return f"{100 * number:+.3f} percentage points"
    if unit == "probability":
        return f"{100 * number:.3f}%"
    if unit in {"records", "records_difference"}:
        return f"{number:.3f} records"
    raise ValueError(f"Unsupported outcome unit: {unit}")


def write_findings(directory):
    provenance_path = directory / "table_provenance.json"
    provenance = json.loads(provenance_path.read_text())
    table = directory / "paired_contrasts.csv"
    if hashlib.sha256(table.read_bytes()).hexdigest() != provenance["table_sha256"][table.name]:
        raise ValueError("Paired table changed after source verification")
    with table.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    lines = [
        "# Paired synthetic experiment findings",
        "",
        "These are descriptive results conditional on the prespecified, uncalibrated model.",
        "Support strata are separate experiments with no population weights. They do not",
        "establish clinical accuracy, causal treatment effects, or external validation.",
        "Intervals quantify pointwise Monte Carlo uncertainty, not patient-level uncertainty.",
        "Each row below reports the first prespecified distinct comparison in that stratum.",
        "Contrasts follow preset order, not observed effect magnitude; intervals are pointwise.",
        "Full absolute and paired tables retain every metric and comparison, including nulls.",
        "",
        "All signs are variant minus comparator. An observed zero does not prove equivalence.",
        "Unavailable uncertainty at N < 2 is not a zero-width interval.",
        "",
    ]
    for entry, metadata in CATALOGUE.items():
        selected = [r for r in rows if r["entry"] == entry and r["metric"] == r["primary_outcome"]]
        if not selected:
            raise ValueError(f"No primary result for {entry}")
        lines.extend(
            [
                f"## {entry}: {metadata['title']}",
                "",
                f"Changed mechanism: {metadata['mechanism']}. {metadata['held_fixed']}",
                "",
                f"Primary outcome: `{selected[0]['metric']}`.",
                "",
                "| Stratum | First prespecified contrast | Pointwise 95% MC interval "
                "| Paired N | Observed zero comparisons |",
                "|---|---|---|---:|---:|",
            ]
        )
        for stratum in dict.fromkeys(r["stratum"] for r in selected):
            panel = [r for r in selected if r["stratum"] == stratum]
            variants = [r for r in panel if r["condition_id"] != r["comparator_id"]]
            candidates = [r for r in variants if r["estimate"] != ""]
            if candidates:
                contrast = min(candidates, key=lambda row: int(row["condition_order"]))
                description = (
                    f"{contrast['condition_label']}: "
                    f"{value(contrast['estimate'], contrast['unit'])}"
                )
            else:
                contrast = panel[0]
                description = (
                    "No distinct normalized variant"
                    if not variants
                    else "All variants not evaluable"
                )
            interval = (
                "not applicable: no distinct contrast"
                if not variants
                else "unavailable"
                if contrast["lower"] == "" or contrast["upper"] == ""
                else f"[{value(contrast['lower'], contrast['unit'])}, "
                f"{value(contrast['upper'], contrast['unit'])}]"
            )
            zeros = sum(float(r["estimate"]) == 0 for r in candidates)
            lines.append(
                f"| {stratum} | {description} | {interval} | {contrast['denominator']} "
                f"| {zeros}/{len(candidates)} |"
            )
        lines.extend(
            [
                "",
                metadata["limitations"].strip(),
                "",
                f"[Absolute figure](figures/{entry}_absolute.svg) · "
                f"[Paired figure](figures/{entry}_paired.svg)",
                "",
            ]
        )
    lines.extend(
        [
            "## Provenance",
            "",
            "Exact source tables, requests and bundles are identified in `table_provenance.json`.",
            "Figure-specific selections and image hashes are in `figure_data_manifest.json`.",
            f"Paired-table SHA256: `{provenance['table_sha256'][table.name]}`.",
            "",
            "This is an automatically generated descriptive readout. See `INTERPRETATION.md`",
            "for the reviewed interpretation of this reference collection and its limits.",
            "",
        ]
    )
    output = directory / "FINDINGS.md"
    with output.open("x") as stream:
        stream.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("artifacts/experiments_v2"))
    write_findings(parser.parse_args().input)


if __name__ == "__main__":
    main()
