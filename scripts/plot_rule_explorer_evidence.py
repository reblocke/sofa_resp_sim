"""Render deterministic rubric, support-cap and encounter panels with unavailable cells."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def render(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    output = directory / "figures"
    output.mkdir(exist_ok=False)
    figures = []
    plt.rcParams.update({"font.size": 10, "svg.fonttype": "none", "svg.hashsalt": "rules-v2"})
    for name, expected in manifest["file_sha256"].items():
        path = directory / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Changed deterministic source: {name}")
        if not name.endswith(".json"):
            continue
        result = json.loads(path.read_text())
        request = result["request"]
        nrows, ncols = len(request["values"]), len(request["supports"])
        fig, axes = plt.subplots(1, 3, figsize=(16, max(5, nrows * 0.45 + 2)), layout="constrained")
        for axis, stage in zip(
            axes, ("Raw rubric", "Support-adjusted", "Reported encounter"), strict=True
        ):
            values = np.full((nrows, ncols), np.nan)
            labels = {}
            for cell in result["cells"]:
                i, j = cell["value_index"], cell["support_index"]
                if stage == "Raw rubric":
                    score = cell["raw_rubric"]
                elif stage == "Support-adjusted":
                    score = cell["event_trace"]["support_adjusted_score"]
                else:
                    score = (
                        None
                        if cell["encounter"]["score_status"] == "no_qualifying_data"
                        else cell["encounter"]["algorithm_score"]
                    )
                values[i, j] = np.nan if score is None else score
                labels[i, j] = "U" if score is None else str(score)
                if stage == "Reported encounter" and cell["encounter"]["suppressed"]:
                    labels[i, j] += "*"
            cmap = plt.get_cmap("Greys").copy()
            cmap.set_bad("#d8d8d8")
            axis.imshow(values, vmin=0, vmax=4, cmap=cmap, aspect="auto")
            for (i, j), label in labels.items():
                axis.text(
                    j,
                    i,
                    label,
                    ha="center",
                    va="center",
                    color="white" if np.isfinite(values[i, j]) and values[i, j] >= 3 else "black",
                )
            axis.set_xticks(
                range(ncols), [s["label"] for s in request["supports"]], rotation=45, ha="right"
            )
            axis.set_yticks(range(nrows), [str(v) for v in request["values"]])
            axis.set_ylabel(f"Input oxygenation ({result['input_unit']})")
            axis.set_title(stage, fontweight="bold")
        caption = (
            f"Deterministic {request['source']} evidence: {request['records']} record(s), "
            f"threshold factor {request['scoring']['threshold_factor']}\n"
            "Stages separate support caps from encounter suppression; no Monte Carlo sampling.\n"
            "Numbers: score 0–4; gray U: unavailable evidence; 0*: singleton suppression. "
            "Unknown support supplies no FiO2.\n"
            "FiO2: room air 0.21, HFNC 0.40, IMV/NIPPV/SURG IMV 0.50; "
            "low flow 4 L/min uses an inferred fraction.\n"
            "HFNC: high-flow nasal cannula; NIPPV: noninvasive positive-pressure ventilation; "
            "IMV: invasive mechanical ventilation; SURG: surgical."
        )
        fig.suptitle(caption, fontsize=11, ha="left", x=0.01)
        images = []
        for extension in ("svg", "png"):
            target = output / f"{path.stem}.{extension}"
            fig.savefig(target, dpi=160, metadata={"Date": None} if extension == "svg" else None)
            images.append(
                {
                    "path": str(target.relative_to(directory)),
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                }
            )
        plt.close(fig)
        figures.append(
            {
                "source": name,
                "source_sha256": expected,
                "caption": caption,
                "outputs": images,
                "visual_review_status": "pending",
            }
        )
    (directory / "figure_data_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "rule_figure_manifest_v1",
                "figures": figures,
                "matplotlib_version": matplotlib.__version__,
                "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("artifacts/local/rule_explorer_v2"))
    render(parser.parse_args().input)


if __name__ == "__main__":
    main()
