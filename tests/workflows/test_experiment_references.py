import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/run_experiment_references.py"


def run(output, *extra):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output",
            str(output),
            "--entries",
            "E1_episode",
            "--strata",
            "room_air",
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def test_reference_runner_verifies_resumes_and_never_certifies_subset(tmp_path):
    first = run(tmp_path)
    assert first.returncode == 0, first.stderr
    index = json.loads((tmp_path / "run_index.json").read_text())
    assert index["status"] == "complete_partial_or_smoke"
    assert index["runs"][0]["completed_patients"] == 1
    archive = tmp_path / index["runs"][0]["bundle"]
    original = archive.read_bytes()
    second = run(tmp_path)
    assert second.returncode == 0, second.stderr
    assert archive.read_bytes() == original
    assert json.loads((tmp_path / "run_index.json").read_text())["runs"][0]["resumed"]
    # A corrupt saved result must fail, never be silently regenerated or accepted.
    archive.write_bytes(b"invalid archive")
    failed = run(tmp_path)
    assert failed.returncode != 0
    assert json.loads((tmp_path / "run_index.json").read_text())["status"] == "failed"
    assert archive.read_bytes() == b"invalid archive"


def test_reference_tables_reject_partial_and_check_source_hashes(tmp_path, monkeypatch):
    import runpy

    import pytest

    assert run(tmp_path).returncode == 0
    script = SCRIPT.with_name("summarize_experiment_references.py")
    collect = runpy.run_path(str(script))["collect"]
    index_path = tmp_path / "run_index.json"
    with pytest.raises(ValueError, match="Only a complete"):
        collect(index_path)
    # A one-entry registry isolates table extraction without running the full reference set.
    monkeypatch.setitem(collect.__globals__, "CATALOGUE", {"E1_episode": {}})
    monkeypatch.setitem(collect.__globals__, "STRATA", {"room_air": {}})
    index = json.loads(index_path.read_text())
    index["status"] = "complete_reference_bundles"
    index_path.write_text(json.dumps(index))
    tables, sources, traces = collect(index_path)
    assert tables["condition_summary.csv"]
    assert tables["paired_contrasts.csv"]
    assert {r["stratum"] for r in tables["paired_contrasts.csv"]} == {"room_air"}
    assert sources[0]["request_sha256"]
    assert "traces/E1_episode__room_air__selected_events.csv" in traces
    index["runs"][0]["bundle_sha256"] = "0" * 64
    index_path.write_text(json.dumps(index))
    with pytest.raises(ValueError, match="Archive digest differs"):
        collect(index_path)


def test_findings_use_declared_units_and_preserve_unavailable_uncertainty(tmp_path, monkeypatch):
    import csv
    import hashlib
    import runpy

    module = runpy.run_path(str(SCRIPT.with_name("write_experiment_findings.py")))
    assert module["value"]("0.5", "records") == "0.500 records"
    assert module["value"]("-0.02", "probability_difference") == "-2.000 percentage points"
    assert module["value"]("", "probability") == "not evaluable"
    write = module["write_findings"]
    monkeypatch.setitem(
        write.__globals__,
        "CATALOGUE",
        {
            "example": {
                "title": "Example",
                "mechanism": "Test",
                "held_fixed": "Fixed",
                "limitations": "Synthetic only",
            }
        },
    )
    row = dict(
        entry="example",
        stratum="room_air",
        metric="score_ge2",
        primary_outcome="score_ge2",
        condition_id="variant",
        comparator_id="base",
        condition_label="Variant",
        condition_order="1",
        estimate="-0.02",
        lower="",
        upper="",
        denominator="1",
        unit="probability_difference",
    )
    table = tmp_path / "paired_contrasts.csv"
    with table.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    (tmp_path / "table_provenance.json").write_text(
        json.dumps({"table_sha256": {table.name: hashlib.sha256(table.read_bytes()).hexdigest()}})
    )
    write(tmp_path)
    text = (tmp_path / "FINDINGS.md").read_text()
    assert "Variant: -2.000 percentage points | unavailable | 1 | 0/1" in text
    assert "preset order, not observed effect magnitude" in text


def test_deterministic_evidence_preserves_edges_and_singleton_anchor(tmp_path):
    import hashlib
    import runpy

    from sofa_resp_sim.reporting.experiment_bundle import decode_table

    build = runpy.run_path(str(SCRIPT.with_name("build_rule_explorer_evidence.py")))["build"]
    output = tmp_path / "rules"
    build(output)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["cases"] == 8 and manifest["cells"] == 476
    assert manifest["monte_carlo"] is False
    for name, digest in manifest["file_sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    rows = decode_table((output / "cells.csv").read_text(), manifest["table_schema"])
    for row in rows:
        if row["source"] == "spo2" and row["input_value"] in (49, 97):
            assert row["conversion_unavailable"] is True
        if (
            row["source"] == "spo2"
            and row["input_value"] == 90
            and row["support_label"] == "LOW_FLOW"
            and row["threshold_factor"] == 1
        ):
            assert row["pf_ratio_mmhg"] == 177.88
            assert row["algorithm_score"] == (0 if row["records"] == 1 else 2)


def test_artifact_verifier_requires_current_visual_review_hashes(tmp_path):
    import hashlib
    import runpy

    import pytest

    verify = runpy.run_path(str(SCRIPT.with_name("verify_experiment_evidence.py")))[
        "reviewed_figures"
    ]
    outputs = []
    for name in ("figure.png", "figure.svg"):
        path = tmp_path / name
        path.write_bytes(b"unit test content")
        outputs.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    figure = {"outputs": outputs}
    with pytest.raises(ValueError, match="visual review"):
        verify(tmp_path, {"figures": [figure]})
    figure.update(
        visual_review_status="reviewed_png",
        visual_review={"reviewed_png_sha256": outputs[0]["sha256"]},
    )
    verify(tmp_path, {"figures": [figure]})
    (tmp_path / "figure.png").write_bytes(b"changed after review")
    with pytest.raises(ValueError, match="Stale artifact"):
        verify(tmp_path, {"figures": [figure]})
