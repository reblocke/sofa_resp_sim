"""Build compact historical evidence from all 48 verified, prespecified bundles."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
from pathlib import Path

from sofa_resp_sim.core.experiment_config import ScoringProfile
from sofa_resp_sim.core.experiment_scoring import score_documented_events
from sofa_resp_sim.core.historical_trops import SOURCE_HASHES
from sofa_resp_sim.reporting.experiment_bundle import verify_bundle
from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request
from sofa_resp_sim.reporting.experiment_service import explain_patient
from sofa_resp_sim.reporting.historical_catalogue import MECHANISMS, REFERENCE_ENTRIES
from sofa_resp_sim.reporting.historical_results import eligibility
from sofa_resp_sim.workflows.experiment_cli import read_files

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/trops_sensitivity_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            {k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in row.items()}
            for row in rows
        )


def event(minute, label, pao2=None, spo2=None, *, context=False):
    row = {
        "event_id": f"{'f' if context else 'o'}:{minute}",
        "patient_id": 0,
        "event_type": "fio2" if context else "oxygenation",
        "measurement_minute": minute,
        "available_minute": minute,
        "support_type": label,
        "invasive_ind": label in ("IMV", "SURG IMV"),
        "support_ind": label in ("HFNC", "NIPPV"),
        "ce_admit_dts": "2024-01-01T06:00:00Z",
    }
    if context:
        row["fio2_set_fraction"] = 1.0
    else:
        row.update(pao2_meas=pao2, spo2_obs=spo2)
    return row


def grids():
    pf_rows, conversion, algebra = [], [], []
    freeze = json.loads((ROOT / "experiments/trops_v1/deterministic_manifest.json").read_text())
    labels = freeze["support_labels"]
    pf_values = [v + d for v in freeze["pf_thresholds_mmhg"] for d in freeze["offsets_mmhg"]]
    for profile, label, pf, count in itertools.product(
        freeze["profiles"], labels, pf_values, freeze["record_counts"]
    ):
        events = [
            r
            for minute in range(count)
            for r in (event(minute, label, pao2=pf), event(minute, label, context=True))
        ]
        result = score_documented_events(
            events, "2024-01-01T06:00:00Z", ScoringProfile(profile=profile)
        )
        pf_rows.append(
            {
                "profile": profile,
                "support": label,
                "pf_mmhg": pf,
                "records": count,
                "raw_rubric": result["events"][0]["raw_rubric"],
                "score": result["acute"]["algorithm_score"],
                "status": result["acute"]["score_status"],
            }
        )
    for profile, spo2 in itertools.product(freeze["profiles"], freeze["spo2_pct"]):
        result = score_documented_events(
            [event(0, "IMV", spo2=spo2), event(0, "IMV", context=True)],
            "2024-01-01T06:00:00Z",
            ScoringProfile(profile=profile),
        )
        r = result["events"][0]
        conversion.append(
            {
                "profile": profile,
                "spo2_pct": spo2,
                "pao2_mmhg": r["pao2_used_mmhg"],
                "exclusion": r["first_exclusion"],
                "score": result["acute"]["algorithm_score"],
            }
        )
    for acute, baseline, c in itertools.product(
        freeze["acute_and_baseline_scores"], freeze["acute_and_baseline_scores"], freeze["C"]
    ):
        algorithm, state = eligibility(acute, baseline, True, c)
        algebra.append(
            {
                "acute": acute,
                "baseline": baseline,
                "C": c,
                "signed_delta": acute - baseline,
                "R": max(acute - baseline, 0),
                "algorithm_eligible": algorithm,
                "evidence_state": state,
                "missing_evidence_state": eligibility(acute, baseline, False, c)[1],
            }
        )
    for name, rows in (
        ("pf_grid.csv", pf_rows),
        ("conversion_grid.csv", conversion),
        ("eligibility_grid.csv", algebra),
    ):
        write_csv(OUT / name, rows)
    return {
        "pf_cells": len(pf_rows),
        "conversion_cells": len(conversion),
        "eligibility_cells": len(algebra),
        "monte_carlo": False,
    }


def compact_records(records):
    """Lossless columnar trace groups retain absent versus null and original order."""
    groups = {}
    for index, row in enumerate(records):
        columns = tuple(sorted(row))
        group = groups.setdefault(columns, {"columns": list(columns), "indices": [], "rows": []})
        group["indices"].append(index)
        group["rows"].append([row[key] for key in columns])
    return list(groups.values())


def write_trace(path, traces):
    for trace in traces:
        for field in ("events", "context_events"):
            trace["scoring"][field] = compact_records(trace["scoring"][field])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"encoding": "columnar_groups_v1", "traces": traces},
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )


def collect():
    frozen_path = ROOT / "experiments/trops_v1/manifest.json"
    frozen = json.loads(frozen_path.read_text())
    index = json.loads((ROOT / "artifacts/local/historical_references/index.json").read_text())
    expected = {r["path"]: r for r in frozen["requests"]}
    if (
        index["status"] != "complete"
        or len(index["completed"]) != 48
        or {r["path"] for r in index["completed"]} != set(expected)
    ):
        raise ValueError("Exactly 48 complete frozen references are required")
    summaries, contrasts, transitions, sources, trace_index = [], [], [], [], []
    for item in index["completed"]:
        path = ROOT / item["path"]
        if (
            sha(path) != expected[item["path"]]["sha256"]
            or sha(ROOT / item["bundle"]) != item["bundle_sha256"]
        ):
            raise ValueError("Request/bundle bytes differ from freeze/receipt")
        bundle = verify_bundle(read_files(ROOT / item["bundle"]))
        req = normalize_experiment_request(json.loads(path.read_text()))
        if bundle["request"] != req.to_dict() or bundle["completed_patients"] != 2000:
            raise ValueError("Bundle is not the frozen complete request")
        entry, stratum = path.stem.split("__")
        if entry not in REFERENCE_ENTRIES:
            raise ValueError("Undeclared entry")
        labels = {c.condition_id: c.label for c in (req.comparator, *req.conditions)}
        metadata = {"entry": entry, "stratum": stratum, "primary_outcome": req.primary_outcome}
        for key, target in (("condition_summary", summaries), ("paired_contrasts", contrasts)):
            target.extend(
                {**metadata, "condition_label": labels[r["condition_id"]], **r} for r in bundle[key]
            )
        chosen = {0}
        for row in bundle["transitions"]:
            if (
                row["table"].startswith("eligibility_")
                and row["condition_id"] != req.comparator.condition_id
            ):
                transitions.append({**metadata, **row})
                if row["patient_ids"]:
                    chosen.add(min(row["patient_ids"]))
        for patient in sorted(chosen):
            # Full normalized scoring explanation, omitting minute-resolution latent arrays.
            traces = []
            for condition in (req.comparator, *req.conditions):
                trace = explain_patient(
                    req,
                    patient,
                    condition.condition_id,
                    expected_score=next(
                        r
                        for r in bundle["scores"]
                        if r["patient_id"] == patient
                        and r["condition_id"] == condition.condition_id
                    ),
                )
                traces.append(
                    {
                        "condition_id": condition.condition_id,
                        "label": condition.label,
                        "score": trace["score"],
                        "scoring": trace["scoring"],
                    }
                )
            relative = f"traces/{path.stem}__patient{patient}.json"
            write_trace(OUT / relative, traces)
            trace_index.append(
                {
                    "entry": entry,
                    "stratum": stratum,
                    "patient_id": patient,
                    "path": relative,
                    "sha256": sha(OUT / relative),
                }
            )
        sources.append(
            {
                **item,
                "environment": bundle["manifest"]["environment"],
                "profile_provenance": bundle["manifest"]["profile_provenance"],
            }
        )
        print(f"Collected {entry}/{stratum}", flush=True)
    write_csv(OUT / "condition_summary.csv", summaries)
    write_csv(OUT / "paired_contrasts.csv", contrasts)
    write_csv(OUT / "eligibility_transitions.csv", transitions)
    write_json(OUT / "trace_index.json", trace_index)
    manifest = {
        "catalogue_manifest_sha256": sha(frozen_path),
        "source_files_sha256": SOURCE_HASHES,
        "deterministic_manifest_sha256": sha(
            ROOT / "experiments/trops_v1/deterministic_manifest.json"
        ),
        "sources": sources,
        ("trace_selection"): (
            "Patient 0 plus lowest patient ID in each nonempty paired eligibility "
            "cell across all C strata; both conditions reconstructed."
        ),
        "deterministic": grids(),
    }
    manifest["file_sha256"] = {
        p.name: sha(p)
        for p in OUT.iterdir()
        if p.is_file() and p.suffix in (".csv",) or p.name == "trace_index.json"
    }
    write_json(OUT / "table_provenance.json", manifest)
    return contrasts


def figures(contrasts):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {"font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11, "svg.hashsalt": "trops-v1"}
    )
    all_figures = []
    findings = [
        "# Historical sensitivity findings",
        "",
        (
            "Historical TROPS specification mapped to Python; synthetic "
            "verification complete; execution against the study SQL not performed."
        ),
        "",
        (
            "All 48 prespecified requests use 2,000 paired synthetic patients, seed"
            " 173203, stationary saturation (mean 96%, SD 0.5 percentage points, "
            "correlation time 30 minutes), no episodes or support drift. C strata "
            "have no population weights. Intervals quantify Monte Carlo "
            "uncertainty, not clinical uncertainty. Original v2 nulls and "
            "demonstrations remain in the separate v2 namespace."
        ),
        "",
        (
            "| Mechanism / profile / support | Common comparator → variant | Paired"
            " difference | Common N |"
        ),
        "|---|---:|---:|---:|",
    ]
    for mechanism, (title, _changed, metric) in MECHANISMS.items():
        selected = [
            r
            for r in contrasts
            if r["entry"].startswith(f"H_{mechanism}_")
            and r["metric"] == metric
            and r["condition_id"] != r["comparator_id"]
        ]
        if len(selected) != 8:
            raise ValueError("Each mechanism must have exactly eight primary contrasts")
        order = {k: i for i, k in enumerate(("room_air", "low_flow", "hfnc", "imv"))}
        selected.sort(key=lambda r: (order[r["stratum"]], r["entry"].endswith("experimental")))
        fig, (left, right) = plt.subplots(
            1, 2, figsize=(12, 6.8), sharey=True, gridspec_kw={"width_ratios": [1, 1.15]}
        )
        binary = selected[0]["unit"] == "probability_difference"
        scale = 100 if binary else 1
        labels = []
        for y, row in enumerate(selected):
            historical = row["entry"].endswith("historical")
            color = "#225F85" if historical else "#A24A16"
            marker = "o" if historical else "s"
            profile_label = "historical" if historical else "experimental"
            support_label = row["stratum"].replace("_", " ")
            if support_label in ("hfnc", "imv"):
                support_label = support_label.upper()
            label = f"{support_label} · {profile_label}"
            labels.append(label)
            a, b = row["common_pair_comparator_estimate"], row["common_pair_variant_estimate"]
            if a is not None and b is not None:
                left.plot([a * scale, b * scale], [y, y], color=color, lw=1)
                left.scatter(
                    [a * scale],
                    [y],
                    marker=marker,
                    s=48,
                    facecolors="white",
                    edgecolors=color,
                    zorder=3,
                )
                left.scatter([b * scale], [y], marker=marker, s=32, color=color, zorder=4)
                d = row["estimate"] * scale
                lo, hi = row.get("lower"), row.get("upper")
                if binary and lo is not None:
                    right.plot([lo * scale, hi * scale], [y, y], color=color, lw=2)
                elif row.get("mcse") is not None:
                    right.plot(
                        [d - row["mcse"] * scale, d + row["mcse"] * scale],
                        [y, y],
                        color=color,
                        lw=2,
                    )
                right.scatter([d], [y], color=color, marker=marker, s=32, zorder=4)
                right.annotate(
                    f"  N={row['denominator']}",
                    (d, y),
                    xytext=(4, 7),
                    textcoords="offset points",
                    fontsize=8,
                )
                val = f"{a * scale:.3g} → {b * scale:.3g}"
                diff = f"{d:.3g}"
            else:
                left.text(0.5, y, "Unavailable", ha="center", transform=left.get_yaxis_transform())
                val = diff = "Unavailable"
            findings.append(
                f"| {mechanism} / {profile_label} / {row['stratum']} | "
                f"{val} | {diff} | {row['denominator']} |"
            )
        left.set_yticks(range(8), labels)
        left.invert_yaxis()
        left.set_title("Common-pair values: open comparator, filled variant")
        right.set_title("Variant − comparator")
        left.set_xlabel(
            "Probability (%)" if binary else "Mean eligible / scheduled patient fraction"
        )
        right.set_xlabel(
            "Percentage points; 95% paired interval"
            if binary
            else "Fraction difference; ±1 patient-level MCSE"
        )
        right.axvline(0, color="#777777", lw=1, ls="--")
        for ax in (left, right):
            ax.grid(axis="x", alpha=0.2)
            ax.spines[["top", "right"]].set_visible(False)
            ax.margins(y=0.13, x=0.18)
        outcome_label = {
            "sofa_eligibility_C0": "SOFA eligibility criterion, C=0",
            "eligible_observation_fraction": "Scheduled-to-eligible observation retention",
            "delta_evaluable_ge1": "Evaluable respiratory delta ≥1",
        }[metric]
        left.set_xlim((-2, 102) if binary else (-0.02, 1.02))
        left.set_xticks([0, 25, 50, 75, 100] if binary else [0, 0.25, 0.5, 0.75, 1])
        fig.suptitle(f"{title}\n{outcome_label}", fontsize=14, y=0.99)
        fig.text(
            0.02,
            0.015,
            (
                "Stationary synthetic patients; no population weighting. Historical "
                "profile is source-mapped, not SQL execution-validated.\nHistorical "
                "circles / experimental squares. Pointwise Monte Carlo uncertainty; "
                "common pairs only. Nulls retained.\n"
                "HFNC: high-flow nasal cannula; IMV: invasive mechanical ventilation."
            ),
            fontsize=10,
        )
        fig.tight_layout(rect=(0, 0.08, 1, 0.92))
        outputs = []
        for extension in ("png", "svg"):
            p = OUT / f"{mechanism}.{extension}"
            fig.savefig(p, dpi=160)
            outputs.append({"path": p.name, "sha256": sha(p)})
        plt.close(fig)
        all_figures.append(
            {
                "mechanism": mechanism,
                "primary_outcome": metric,
                "selected_rows": 8,
                "source_table": "paired_contrasts.csv",
                "source_table_sha256": sha(OUT / "paired_contrasts.csv"),
                "outputs": outputs,
                "visual_review_status": "pending",
            }
        )
    findings += [
        "",
        (
            "Values for binary outcomes are percentages/percentage-point "
            "differences; retention uses fractions. Exact intervals, numerators, "
            "condition-specific marginals, all three C views and secondary outcomes"
            " are in the CSV tables. Empty common denominators are unavailable; N=1"
            " has no interval."
        ),
        "",
        (
            "Stable saturation near the conversion ceiling can exclude otherwise "
            "recorded observations. Retention therefore need not be 100% even with "
            "no missing documentation. A null eligibility contrast does not show "
            "that documentation is irrelevant: examine retention and evidence "
            "transitions. C≥2 is eligible in every condition by construction. E5 "
            "baseline opportunity counts are the actual selected-day counts in the "
            "patient explanations, rather than total-history counts. Acute scores "
            "are a negative control for baseline-only perturbations. Low-flow "
            "delivered FiO2 error is unavailable because the flow proxy does not "
            "identify true delivered FiO2."
        ),
    ]
    (OUT / "FINDINGS.md").write_text("\n".join(findings) + "\n")
    write_json(
        OUT / "figure_data_manifest.json",
        {"table_provenance_sha256": sha(OUT / "table_provenance.json"), "figures": all_figures},
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    figures(collect())


if __name__ == "__main__":
    main()
