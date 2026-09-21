import json
from pathlib import Path

import pytest

from sofa_resp_sim.reporting.aggregate_reference import validate_aggregate_reference

TEMPLATES = Path(__file__).resolve().parents[2] / "docs" / "templates"


def fixture():
    return (TEMPLATES / "aggregate_reference.csv").read_text(), json.loads(
        (TEMPLATES / "aggregate_reference.json").read_text()
    )


def test_aggregate_template_and_resolved_metadata_roundtrip():
    text, metadata = fixture()
    result = validate_aggregate_reference(text, metadata)
    assert sum(row["count"] for row in result["rows"]) == 100
    assert result["public_export_allowed"]
    assert validate_aggregate_reference(text, result["metadata"]) == result
    metadata["access_class"] = "restricted_aggregate"
    assert not validate_aggregate_reference(text, metadata)["public_export_allowed"]


@pytest.mark.parametrize(
    "edit",
    [
        lambda text: text.replace(",50,100", ",51,100"),
        lambda text: text.replace(",50,100", ",50.5,100"),
        lambda text: text.replace(",50,100", ",50,99"),
        lambda text: text.replace(",suppressed_only,0", ",suppressed_only,2"),
        lambda text: text + text.splitlines()[1] + "\n",
        lambda text: "\n".join(text.splitlines()[:-1]) + "\n",
        lambda text: text.replace(",50,100", ",50,100,extra"),
    ],
)
def test_invalid_counts_and_cells_fail(edit):
    text, metadata = fixture()
    with pytest.raises(ValueError):
        validate_aggregate_reference(edit(text), metadata)


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema_version", "future"),
        ("source", ""),
        ("extraction_date", "2024-02-30"),
        ("units", "percent"),
        ("access_class", "patient_data"),
        ("scoring_profile", {}),
        ("scoring_profile", {"profile": "unrecognized"}),
        ("extra", "unknown"),
    ],
)
def test_provenance_metadata_is_required_and_strict(key, value):
    text, metadata = fixture()
    metadata[key] = value
    with pytest.raises(ValueError):
        validate_aggregate_reference(text, metadata)
