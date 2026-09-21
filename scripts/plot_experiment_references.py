"""Render source-bound primary-outcome figures from verified reference tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from sofa_resp_sim.reporting.experiment_catalogue import catalogue_request

METRIC_LABELS = {
    "score_ge1": "Respiratory SOFA ≥1",
    "score_ge2": "Respiratory SOFA ≥2",
    "score_ge3": "Respiratory SOFA ≥3",
    "score_eq4": "Respiratory SOFA =4",
    "no_qualifying_data": "No qualifying oxygenation data",
    "suppressed_only": "Only singleton-suppressed evidence",
    "qualifying_pf_count": "Qualifying oxygenation records",
    "delta_legacy_ge1": "Acute minus baseline SOFA ≥1 (legacy zero convention)",
    "delta_legacy_ge2": "Acute minus baseline SOFA ≥2 (legacy zero convention)",
}
STRATUM_LABELS = {
    "room_air": "Room air",
    "low_flow": "Low-flow oxygen",
    "hfnc": "High-flow nasal cannula",
    "imv": "Invasive mechanical\nventilation",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(row, field):
    value = row[field]
    return None if value == "" else float(value)


def baseline_matrix(axis, panel, stratum, kind, factor, limits):
    request = catalogue_request("E5_opportunity", stratum)
    configs = {c.condition_id: c.config for c in (request.comparator, *request.conditions)}
    hours, intervals = [1, 6, 24], [15, 60]
    values = np.full((3, 2), np.nan)
    labels = {}
    for row in panel:
        observation = configs[row["condition_id"]].observation
        i = hours.index(observation.baseline_exposure_minutes / 60)
        j = intervals.index(observation.baseline_interval_minutes)
        estimate = number(row, "estimate")
        if estimate is None:
            labels[i, j] = "U"
            continue
        values[i, j] = factor * estimate
        low, high = number(row, "lower"), number(row, "upper")
        bounds = (
            "interval unavailable" if low is None else f"[{factor * low:.2f}, {factor * high:.2f}]"
        )
        labels[i, j] = f"{factor * estimate:.2f}\n{bounds}"
    cmap = plt.get_cmap("RdBu" if kind == "paired" else "Blues").copy()
    cmap.set_bad("#ddd")
    image = axis.imshow(values, vmin=limits[0], vmax=limits[1], cmap=cmap, aspect="auto")
    for (i, j), label in labels.items():
        axis.text(
            j,
            i,
            label,
            ha="center",
            va="center",
            fontsize=10,
            bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"},
        )
    axis.set_xticks(range(2), intervals)
    axis.set_yticks(range(3), hours)
    axis.set_xlabel("Baseline measurement interval (minutes)")
    axis.set_ylabel("Baseline exposure (hours)")
    axis.set_title(STRATUM_LABELS[stratum] + f" (N={panel[0]['denominator']})", loc="left")
    return image


def render(directory):
    provenance_path = directory / "table_provenance.json"
    provenance = json.loads(provenance_path.read_text())
    rows = {}
    for name, expected in provenance["table_sha256"].items():
        path = directory / name
        if digest(path) != expected:
            raise ValueError(f"Reference table changed: {name}")
        with path.open(newline="") as stream:
            rows[name] = list(csv.DictReader(stream))
    output = directory / "figures"
    output.mkdir(exist_ok=False)
    manifest = {
        "schema_version": "figure_data_manifest_v1",
        "table_provenance_sha256": digest(provenance_path),
        "renderer_sha256": digest(Path(__file__)),
        "matplotlib_version": matplotlib.__version__,
        "visual_review_status": "pending",
        "figures": [],
    }
    plt.rcParams.update({"font.size": 11, "svg.fonttype": "none", "svg.hashsalt": "sofa-v2"})
    entries = list(dict.fromkeys(r["entry"] for r in provenance["sources"]))
    strata = list(dict.fromkeys(r["stratum"] for r in provenance["sources"]))
    for entry in entries:
        for table, kind in (
            ("condition_summary.csv", "absolute"),
            ("paired_contrasts.csv", "paired"),
        ):
            selected = [
                r
                for r in rows[table]
                if r["entry"] == entry and r["metric"] == r["primary_outcome"]
            ]
            if not selected or len({r["unit"] for r in selected}) != 1:
                raise ValueError(f"Missing or mixed primary outcome units: {entry} {kind}")
            unit = selected[0]["unit"]
            probability = unit in {"probability", "probability_difference"}
            factor = 100 if probability else 1
            xlabel = (
                "Probability (%)"
                if unit == "probability"
                else "Variant minus comparator (percentage points)"
                if unit == "probability_difference"
                else "Variant minus comparator (records)"
                if kind == "paired"
                else "Mean records"
            )
            extent = [
                factor * number(r, key)
                for r in selected
                for key in ("estimate", "lower", "upper")
                if number(r, key) is not None
            ]
            if unit == "probability":
                limits = (-3, 103)
            elif kind == "paired":
                bound = max([abs(x) for x in extent] + [1]) * 1.15
                limits = (-bound, bound)
            else:
                limits = (0, max(extent + [1]) * 1.15)
            figure, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, layout="constrained")
            for axis, stratum in zip(axes.flat, strata, strict=True):
                panel = sorted(
                    [r for r in selected if r["stratum"] == stratum],
                    key=lambda row: int(row["condition_order"]),
                )
                if entry == "E5_opportunity":
                    matrix_limits = (0, 100) if unit == "probability" else limits
                    matrix_image = baseline_matrix(
                        axis, panel, stratum, kind, factor, matrix_limits
                    )
                    continue
                # Keep prespecified scientific order from the exact request's source tables.
                for y, row in enumerate(panel):
                    estimate = number(row, "estimate")
                    low, high = number(row, "lower"), number(row, "upper")
                    if estimate is None:
                        axis.text(0, y, "U / not evaluable", va="center", fontsize=10)
                        continue
                    axis.plot(factor * estimate, y, "o", color="#185b6c", markersize=6)
                    if low is not None and high is not None:
                        axis.hlines(y, factor * low, factor * high, color="#185b6c", linewidth=1.8)
                    axis.annotate(
                        f"{factor * estimate:.2f}",
                        (factor * estimate, y),
                        xytext=(0, 9),
                        textcoords="offset points",
                        ha="center",
                        fontsize=9,
                    )
                axis.set_yticks(range(len(panel)), [r["condition_label"] for r in panel])
                axis.set_ylim(len(panel) - 0.4, -0.65)
                axis.set_xlim(*limits)
                denominators = sorted({int(r["denominator"]) for r in panel})
                sample_size = (
                    str(denominators[0])
                    if len(denominators) == 1
                    else f"{min(denominators)}–{max(denominators)}"
                )
                axis.set_title(
                    STRATUM_LABELS[stratum] + f" (N={sample_size})",
                    loc="left",
                    fontweight="bold",
                )
                axis.set_xlabel(xlabel)
                axis.axvline(0, color=".55", linewidth=0.8, linestyle="--")
                axis.grid(axis="x", color=".9")
                axis.spines[["top", "right", "left"]].set_visible(False)
            if entry == "E5_opportunity":
                figure.colorbar(matrix_image, ax=axes.ravel().tolist(), label=xlabel, shrink=0.65)
            metric = selected[0]["metric"]
            caption = (
                f"{entry.replace('_', ' ')}: {METRIC_LABELS[metric]} — {kind} estimates\n"
                "Uncalibrated synthetic model; strata have no population weights.\n"
                "95% pointwise Monte Carlo intervals: bars/brackets; absent if undefined.\n"
                "Paired differences use the same patients; zero change does not prove identity."
            )
            figure.suptitle(caption, fontsize=12, ha="left", x=0.01)
            paths = []
            for extension in ("svg", "png"):
                path = output / f"{entry}_{kind}.{extension}"
                figure.savefig(
                    path, dpi=180, metadata={"Date": None} if extension == "svg" else None
                )
                paths.append({"path": str(path.relative_to(directory)), "sha256": digest(path)})
            plt.close(figure)
            manifest["figures"].append(
                {
                    "entry": entry,
                    "kind": kind,
                    "primary_outcome": metric,
                    "source_table": table,
                    "source_table_sha256": provenance["table_sha256"][table],
                    "selection": {"entry": entry, "metric": metric},
                    "selected_rows": len(selected),
                    "caption": caption,
                    "outputs": paths,
                    "sources": [s for s in provenance["sources"] if s["entry"] == entry],
                }
            )
    (directory / "figure_data_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("artifacts/experiments_v2"))
    args = parser.parse_args()
    render(args.input)


if __name__ == "__main__":
    main()
