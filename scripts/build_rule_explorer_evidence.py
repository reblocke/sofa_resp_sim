"""Generate deterministic edge/cutpoint evidence independently of cohort sampling."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from sofa_resp_sim.reporting.experiment_bundle import encode_table
from sofa_resp_sim.reporting.experiment_catalogue import STRATA
from sofa_resp_sim.reporting.rule_explorer import explore_rules
from sofa_resp_sim.workflows.experiment_cli import native_environment


def cases():
    supports = list(STRATA.values()) + [
        {"label": "NIPPV", "fio2_fraction": 0.5},
        {"label": "SURG IMV", "fio2_fraction": 0.5},
        {"label": "UNKNOWN", "fio2_fraction": None},
    ]
    for source, values in (
        ("spo2", [49, 50, 90, 96, 97]),
        (
            "measured_pao2",
            [49.99, 50, 50.01, 99.99, 100, 100.01, 149.99, 150, 150.01, 199.99, 200, 200.01],
        ),
    ):
        for records in (1, 2):
            for factor in (1.0, 0.85):
                yield (
                    f"{source}_{records}record_factor{factor}",
                    {
                        "source": source,
                        "values": values,
                        "supports": supports,
                        "records": records,
                        "scoring": {"threshold_factor": factor},
                    },
                )


def build(output):
    if output.exists():
        raise ValueError("Output exists; use a new directory to preserve previous evidence")
    generated, rows = {}, []
    for name, request in cases():
        result = explore_rules(request)
        generated[f"{name}.json"] = json.dumps(result, indent=2, allow_nan=False) + "\n"
        for cell in result["cells"]:
            event, encounter = cell["event_trace"], cell["encounter"]
            rows.append(
                {
                    "case": name,
                    "source": request["source"],
                    "records": request["records"],
                    "threshold_factor": request["scoring"]["threshold_factor"],
                    "input_value": cell["input_value"],
                    "input_unit": result["input_unit"],
                    "support_label": cell["support"]["label"],
                    "fio2_fraction": event["fio2_fraction"],
                    "pao2_calc_mmhg": cell["pao2_calc_mmhg"],
                    "pf_ratio_mmhg": cell["pf_ratio_mmhg"],
                    "raw_rubric": cell["raw_rubric"],
                    "support_adjusted_score": event["support_adjusted_score"],
                    "algorithm_score": encounter["algorithm_score"],
                    "score_status": encounter["score_status"],
                    "conversion_unavailable": cell["conversion_unavailable"],
                    "singleton_suppressed": event["singleton_suppressed"],
                    "qualifying_pf_count": encounter["qualifying_pf_count"],
                    "source_event_id": event["fio2_source_event_id"],
                }
            )
    csv, schema = encode_table(rows)
    generated["cells.csv"] = csv
    output.mkdir(parents=True)
    for name, text in generated.items():
        (output / name).write_text(text)
    manifest = {
        "schema_version": "deterministic_rule_evidence_v1",
        "monte_carlo": False,
        "environment": native_environment(),
        "cells": len(rows),
        "cases": len(generated) - 1,
        "table_schema": schema,
        "file_sha256": {
            name: hashlib.sha256(text.encode()).hexdigest() for name, text in generated.items()
        },
        "scope": "Synthetic deterministic conversion edges and cutpoints; no clinical validation",
        "figure_status": "pending",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts/local/rule_explorer_v2"))
    build(parser.parse_args().output)


if __name__ == "__main__":
    main()
