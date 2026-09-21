"""Strict aggregate-only reference interchange; validation is not calibration."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date

from ..core.experiment_config import ScoringProfile

SCHEMA = "aggregate_reference_v2"
COLUMNS = ("stratum", "score_status", "algorithm_score", "count", "denominator")
CELLS = {(s, "observed_scored") for s in range(5)} | {
    (0, "suppressed_only"),
    (0, "no_qualifying_data"),
}
METADATA_KEYS = {
    "schema_version",
    "source",
    "extraction_date",
    "cohort_definition",
    "scoring_profile",
    "units",
    "access_class",
    "denominator_definition",
}


def validate_aggregate_reference(csv_text: str, metadata: dict) -> dict:
    if not isinstance(metadata, dict) or set(metadata) != METADATA_KEYS:
        raise ValueError(f"Reference metadata requires exactly {sorted(METADATA_KEYS)}")
    if metadata["schema_version"] != SCHEMA:
        raise ValueError(f"Unsupported reference schema; expected {SCHEMA}")
    for key in ("source", "cohort_definition", "denominator_definition"):
        if not isinstance(metadata[key], str) or not metadata[key].strip():
            raise ValueError(f"Reference {key} must be nonempty")
    if metadata["units"] != "patient_counts":
        raise ValueError("Reference units must be patient_counts")
    if metadata["access_class"] not in {"synthetic", "public_aggregate", "restricted_aggregate"}:
        raise ValueError("Reference access_class is unsupported")
    try:
        extracted = date.fromisoformat(metadata["extraction_date"])
    except (TypeError, ValueError) as error:
        raise ValueError("Reference extraction_date must be YYYY-MM-DD") from error
    if extracted.isoformat() != metadata["extraction_date"]:
        raise ValueError("Reference extraction_date must be YYYY-MM-DD")
    if not isinstance(metadata["scoring_profile"], dict) or not metadata["scoring_profile"]:
        raise ValueError("Reference scoring_profile must declare a profile")
    profile = ScoringProfile.from_dict(metadata["scoring_profile"])
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames != list(COLUMNS):
        raise ValueError(f"Reference CSV columns must be {','.join(COLUMNS)}")
    groups = defaultdict(dict)
    for line, raw in enumerate(reader, 2):
        if set(raw) != set(COLUMNS) or any(v is None for v in raw.values()):
            raise ValueError(f"Malformed reference row {line}")
        stratum = raw["stratum"].strip()
        if not stratum:
            raise ValueError(f"Empty stratum at row {line}")
        integers = {}
        for key in ("algorithm_score", "count", "denominator"):
            if not raw[key].isascii() or not raw[key].isdigit():
                raise ValueError(f"Reference {key} must be a nonnegative integer at row {line}")
            integers[key] = int(raw[key])
        cell = integers["algorithm_score"], raw["score_status"]
        if cell not in CELLS:
            raise ValueError(f"Invalid score/status combination at row {line}")
        if cell in groups[stratum]:
            raise ValueError(f"Duplicate score/status cell in stratum {stratum}")
        if integers["count"] > integers["denominator"]:
            raise ValueError(f"Count exceeds denominator at row {line}")
        groups[stratum][cell] = {"stratum": stratum, "score_status": cell[1], **integers}
    if not groups:
        raise ValueError("Reference CSV is empty")
    rows = []
    for stratum, cells in sorted(groups.items()):
        if set(cells) != CELLS:
            raise ValueError(
                f"Stratum {stratum} requires all seven score/status cells, including zeros"
            )
        denominators = {row["denominator"] for row in cells.values()}
        if len(denominators) != 1 or next(iter(denominators)) <= 0:
            raise ValueError(f"Stratum {stratum} needs one positive denominator")
        if sum(row["count"] for row in cells.values()) != next(iter(denominators)):
            raise ValueError(f"Stratum {stratum} counts do not reconcile to denominator")
        rows.extend(cells[cell] for cell in sorted(cells))
    return {
        "metadata": {**metadata, "scoring_profile": profile.to_dict()},
        "rows": rows,
        "validation_scope": "aggregate schema and arithmetic only; not clinical calibration",
        "public_export_allowed": metadata["access_class"] != "restricted_aggregate",
    }
