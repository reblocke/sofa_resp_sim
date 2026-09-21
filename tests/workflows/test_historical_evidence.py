"""Historical evidence inventory, provenance and refusal of incomplete evidence."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_historical_inventory_and_tampered_completion(tmp_path):
    verifier = module("verify_experiment_evidence")
    source = ROOT / "artifacts/trops_sensitivity_v1"
    assert verifier.verify_historical(source)["sources"] == 48
    copy = tmp_path / "evidence"
    shutil.copytree(source, copy)
    path = copy / "table_provenance.json"
    manifest = json.loads(path.read_text())
    manifest["sources"].pop()
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="inventory"):
        verifier.verify_historical(copy)


def test_compact_trace_preserves_null_absent_values_types_and_order():
    compact = module("build_historical_evidence").compact_records
    original = [{"a": 1, "b": None}, {"b": False}, {"a": 2.5, "b": "x"}]
    groups = compact(original)
    restored = {}
    for group in groups:
        for index, values in zip(group["indices"], group["rows"], strict=True):
            restored[index] = dict(zip(group["columns"], values, strict=True))
    assert [restored[i] for i in range(len(original))] == original
