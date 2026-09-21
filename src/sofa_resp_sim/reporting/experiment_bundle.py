"""Versioned synthetic bundles, usable without filesystem access in Pyodide."""

from __future__ import annotations

import base64
import csv
import hashlib
import importlib.metadata
import io
import json
import math
import platform
import zipfile
from datetime import UTC, datetime

from ..core.experiment_config import GENERATOR_VERSION, RNG_VERSION, fingerprint
from ..core.historical_trops import profile_provenance
from .experiment_catalogue import CATALOGUE_VERSION
from .experiment_request import V3, normalize_experiment_request
from .experiment_service import explain_patient, result_schema, summarize_request

BUNDLE_VERSION = "experiment_bundle_v2"
MAX_BUNDLE_BYTES = 64 * 1024 * 1024
TABLES = ("condition_summary", "paired_contrasts", "transitions", "scores", "reclassification")
REQUIRED = {
    "request.json",
    "manifest.json",
    "condition_summary.csv",
    "paired_contrasts.csv",
    "transitions.csv",
    "scores.csv",
    "selected_events.csv",
    "episodes.csv",
    "metric_dictionary.json",
    "README.md",
    "SHA256SUMS",
    "reclassification.csv",
}


def _json(value):
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compare_scientific_values(expected, actual, *, tolerance=1e-10, path="root"):
    """Only unrounded float values receive tolerance; IDs/counts/statuses stay exact."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        if set(expected) != set(actual):
            raise ValueError(f"Scientific keys differ at {path}")
        for key in expected:
            compare_scientific_values(
                expected[key], actual[key], tolerance=tolerance, path=f"{path}.{key}"
            )
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            raise ValueError(f"Scientific lengths differ at {path}")
        for i, (left, right) in enumerate(zip(expected, actual, strict=True)):
            compare_scientific_values(left, right, tolerance=tolerance, path=f"{path}[{i}]")
    elif isinstance(expected, float) and isinstance(actual, float):
        if not math.isclose(expected, actual, rel_tol=tolerance, abs_tol=tolerance):
            raise ValueError(f"Scientific float differs at {path}: {expected} != {actual}")
    elif type(expected) in (int, float) and type(actual) in (int, float) and expected == actual:
        # JSON has one number type; JS serializes an integral float such as 1.0 as 1.
        return
    elif type(expected) is not type(actual) or expected != actual:
        raise ValueError(f"Scientific discrete value differs at {path}: {expected} != {actual}")


def _kind(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (dict, list)):
        return "json"
    raise ValueError(f"Unsupported CSV value type: {type(value).__name__}")


def encode_table(rows, empty_columns=()):
    columns = sorted({key for row in rows for key in row} or set(empty_columns))
    schema = {}
    for column in columns:
        kinds = {_kind(row.get(column)) for row in rows} - {None}
        schema[column] = "json" if len(kinds) > 1 else (next(iter(kinds)) if kinds else "null")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        encoded = {}
        for column in columns:
            value = row.get(column)
            if value is None:
                encoded[column] = ""
            elif isinstance(value, str) and schema[column] != "json":
                encoded[column] = (
                    "\\e" if value == "" else ("\\" + value if value.startswith("\\") else value)
                )
            else:
                encoded[column] = json.dumps(
                    value, sort_keys=True, separators=(",", ":"), allow_nan=False
                )
        writer.writerow(encoded)
    return stream.getvalue(), schema


def decode_table(text, schema):
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != sorted(schema):
        raise ValueError("CSV columns do not match the declared schema")
    rows = []
    for raw in reader:
        if set(raw) != set(schema) or any(v is None for v in raw.values()):
            raise ValueError("Malformed CSV row")
        row = {}
        for key, kind in schema.items():
            value = raw[key]
            if value == "":
                row[key] = None
            elif kind == "string":
                row[key] = (
                    "" if value == "\\e" else (value[1:] if value.startswith("\\\\") else value)
                )
            else:
                row[key] = json.loads(
                    value,
                    parse_constant=lambda v: (_ for _ in ()).throw(
                        ValueError(f"Nonfinite CSV value: {v}")
                    ),
                )
                if kind != "json" and _kind(row[key]) != kind:
                    raise ValueError(f"CSV type mismatch in {key}")
        rows.append(row)
    return rows


def runtime_environment():
    versions = {}
    for name in ("sofa-resp-sim", "numpy", "pandas", "scipy", "tzdata"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "unavailable"
    return {
        "python": platform.python_version(),
        "dependencies": versions,
        "git_commit": None,
        "dirty_tree": None,
        "source_provenance_note": "Execution surface must supply Git provenance when available",
    }


def _validate_scores(request, scores):
    conditions = {c.condition_id for c in (request.comparator, *request.conditions)}
    expected = {(p, c) for p in range(request.replicates) for c in conditions}
    actual = {(r["patient_id"], r["condition_id"]) for r in scores}
    if len(scores) != len(expected) or actual != expected:
        raise ValueError(
            "Incomplete or duplicate patient-condition rows; cannot export a completed bundle"
        )
    if any(r["experiment_run_id"] != request.run_id for r in scores):
        raise ValueError("Score run identity does not match immutable request")


def build_bundle(result: dict, *, environment=None, selected_patient=0) -> dict[str, str]:
    request = normalize_experiment_request(result["request"])
    if (
        result.get("schema_version") != result_schema(request)
        or result.get("experiment_run_id") != request.run_id
    ):
        raise ValueError("Unsupported result version or mismatched run identity")
    if (
        result.get("completed_patients") != request.replicates
        or result.get("attempted_patients") != request.replicates
    ):
        raise ValueError("Incomplete runs cannot be exported as completed bundles")
    scores = result["scores"]
    _validate_scores(request, scores)
    recalculated = summarize_request(request, scores)
    for key in (*TABLES[:-2], "reclassification", "metric_dictionary"):
        compare_scientific_values(recalculated[key], result[key], path=key)
    result = {**result, **recalculated}
    selected = [r for r in scores if r["patient_id"] == selected_patient]
    if isinstance(selected_patient, bool) or not isinstance(selected_patient, int) or not selected:
        raise ValueError("Selected patient must be an executed integer patient ID")
    events, episodes = [], []
    for row in selected:
        trace = explain_patient(request, selected_patient, row["condition_id"], expected_score=row)
        identity = {"experiment_run_id": request.run_id, "condition_id": row["condition_id"]}
        events.extend(
            {**event, **identity}
            for event in [*trace["scoring"]["events"], *trace["scoring"]["context_events"]]
        )
        episodes.extend({**episode, **identity} for episode in trace["episodes"])
    files = {
        "request.json": _json(request.to_dict()),
        "metric_dictionary.json": _json(result["metric_dictionary"]),
    }
    schemas = {}
    for name, rows in [(key, result[key]) for key in TABLES] + [
        ("selected_events", events),
        ("episodes", episodes),
    ]:
        files[name + ".csv"], schemas[name + ".csv"] = encode_table(
            rows,
            ["experiment_run_id", "condition_id", "patient_id", "event_id"]
            if name == "selected_events"
            else [
                "episode_id",
                "patient_id",
                "condition_id",
                "block",
                "start_minute",
                "end_minute",
                "depth_pct_points",
            ],
        )
    scientific_hashes = {name: _sha(text) for name, text in files.items()}
    files["README.md"] = (
        f"# Synthetic experiment {request.experiment_id}\n\n"
        f"Completed paired patients: {request.replicates}. Comparator: {request.comparator.label}. "
        f"Primary outcome: {request.primary_outcome}. "
        f"Selected trace: patient {selected_patient}.\n\n"
        "Uncalibrated illustrative simulation; "
        "no clinical calibration or independent SQL equivalence. "
        "Intervals are pointwise Monte Carlo uncertainty conditional on the model, "
        "not clinical CIs. "
        "Algorithm zeros include missing evidence and suppression; "
        "inspect statuses and denominators. "
        "No population weights or additive rule attribution are implied.\n\n"
        "Reproduce from this directory in the recorded locked runtime:\n\n"
        "```bash\nresp-sofa-experiment reproduce . --output ../reproduced-bundle\n```\n\n"
        "CSV blank cells are null. Empty strings use \\e; literal leading backslashes are escaped "
        "with another backslash. Nested objects/arrays use JSON. Types are in manifest.json.\n"
    )
    files["manifest.json"] = _json(
        {
            "bundle_version": "experiment_bundle_v3"
            if request.schema_version == V3
            else BUNDLE_VERSION,
            "request_schema": request.schema_version,
            "algorithm_version": "profiled_analysis_v3"
            if request.schema_version == V3
            else "bounded_analysis_v2",
            "generator_version": GENERATOR_VERSION,
            "rng_version": RNG_VERSION,
            "catalogue_version": "trops_sensitivity_v1"
            if request.schema_version == V3
            else CATALOGUE_VERSION,
            "reference_version": "none_uncalibrated",
            "status": "complete",
            "experiment_run_id": request.run_id,
            "completed_patients": request.replicates,
            "seed": request.seed,
            "selected_patient": selected_patient,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "environment": {**runtime_environment(), **(environment or {})},
            "runtime_provenance": result["runtime_provenance"],
            "append_parent_run_id": result.get("append_parent_run_id"),
            "reproduction": result.get("reproduction"),
            "warnings": result["warnings"],
            "uncertainty_scope": result["uncertainty_scope"],
            "interval_methods": ["wilson", "paired_exact_discordance_bonferroni"],
            "table_schemas": schemas,
            "scientific_hashes": scientific_hashes,
            "scientific_data_sha256": fingerprint(scientific_hashes),
            **(
                {
                    "profile_provenance": {
                        c.condition_id: profile_provenance(c.config.scoring)
                        for c in (request.comparator, *request.conditions)
                    }
                }
                if request.schema_version == V3
                else {}
            ),
            "generation_and_target_windows": {
                c.condition_id: {
                    "horizon": c.config.horizon.to_dict(),
                    "scoring": c.config.scoring.to_dict(),
                }
                for c in (request.comparator, *request.conditions)
            },
        }
    )
    files["SHA256SUMS"] = "".join(f"{_sha(files[name])}  {name}\n" for name in sorted(files))
    return files


def verify_bundle(files: dict[str, str]) -> dict:
    if set(files) != REQUIRED or any(not isinstance(value, str) for value in files.values()):
        raise ValueError(f"Bundle must contain exactly the supported files: {sorted(REQUIRED)}")
    expected_sums = "".join(
        f"{_sha(files[name])}  {name}\n" for name in sorted(files) if name != "SHA256SUMS"
    )
    if files["SHA256SUMS"] != expected_sums:
        raise ValueError("Bundle content hash mismatch; obtain the intact original bundle")
    manifest = json.loads(files["manifest.json"])
    request = normalize_experiment_request(json.loads(files["request.json"]))
    if request.schema_version == V3:
        expected_profiles = {
            c.condition_id: profile_provenance(c.config.scoring)
            for c in (request.comparator, *request.conditions)
        }
        if manifest.get("profile_provenance") != expected_profiles:
            raise ValueError("Profile source or qualification identity mismatch")
    versions = {
        "bundle_version": "experiment_bundle_v3"
        if request.schema_version == V3
        else BUNDLE_VERSION,
        "request_schema": request.schema_version,
        "algorithm_version": "profiled_analysis_v3"
        if request.schema_version == V3
        else "bounded_analysis_v2",
        "generator_version": GENERATOR_VERSION,
        "rng_version": RNG_VERSION,
        "catalogue_version": "trops_sensitivity_v1"
        if request.schema_version == V3
        else CATALOGUE_VERSION,
        "reference_version": "none_uncalibrated",
    }
    for key, expected in versions.items():
        if manifest.get(key) != expected:
            raise ValueError(
                f"Unsupported {key}: expected {expected}; use the matching software version"
            )
    request = normalize_experiment_request(json.loads(files["request.json"]))
    if json.loads(files["request.json"]) != request.to_dict():
        raise ValueError("Bundle request is not fully normalized")
    if (
        manifest.get("status") != "complete"
        or manifest.get("completed_patients") != request.replicates
        or manifest.get("experiment_run_id") != request.run_id
    ):
        raise ValueError("Bundle completion or run identity mismatch")
    hashes = {
        name: _sha(files[name]) for name in REQUIRED - {"manifest.json", "README.md", "SHA256SUMS"}
    }
    if manifest.get("scientific_hashes") != hashes or manifest.get(
        "scientific_data_sha256"
    ) != fingerprint(hashes):
        raise ValueError("Bundle scientific identity mismatch")
    tables = {
        name[:-4]: decode_table(files[name], schema)
        for name, schema in manifest["table_schemas"].items()
    }
    if set(tables) != {*TABLES, "selected_events", "episodes"}:
        raise ValueError("Unsupported bundle table set")
    _validate_scores(request, tables["scores"])
    calculated = summarize_request(request, tables["scores"])
    for key in (*TABLES[:-2], "reclassification"):
        encoded, schema = encode_table(calculated[key])
        compare_scientific_values(decode_table(encoded, schema), tables[key], path=key)
        # Preserve original floating values while restoring field presence from the schema.
        tables[key] = [
            {field: row[field] for field in expected}
            for row, expected in zip(tables[key], calculated[key], strict=True)
        ]
    if json.loads(files["metric_dictionary.json"]) != calculated["metric_dictionary"]:
        raise ValueError("Bundle metric definitions do not match this version")
    return {
        "request": request.to_dict(),
        "manifest": manifest,
        **tables,
        "metric_dictionary": calculated["metric_dictionary"],
        "algorithm_zero_convention": calculated["algorithm_zero_convention"],
        "uncertainty_scope": manifest["uncertainty_scope"],
        "warnings": manifest["warnings"],
        "schema_version": result_schema(request),
        **(
            {"profile_provenance": manifest["profile_provenance"]}
            if request.schema_version == V3
            else {}
        ),
        "experiment_run_id": request.run_id,
        "completed_patients": request.replicates,
        "attempted_patients": request.replicates,
        "runtime_provenance": manifest["runtime_provenance"],
        "append_parent_run_id": manifest.get("append_parent_run_id"),
        "reproduction": manifest.get("reproduction"),
    }


def encode_bundle_archive(files: dict[str, str]) -> str:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for name, text in sorted(files.items()):
            output.writestr(name, text)
    return base64.b64encode(archive.getvalue()).decode("ascii")


def decode_bundle_archive(encoded: str) -> dict[str, str]:
    if not isinstance(encoded, str) or len(encoded) > MAX_BUNDLE_BYTES * 4 // 3 + 4:
        raise ValueError("Bundle archive exceeds the 64 MiB import limit")
    try:
        raw = base64.b64decode(encoded, validate=True)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if set(archive.namelist()) != REQUIRED or len(archive.namelist()) != len(REQUIRED):
                raise ValueError("ZIP has missing, duplicate or unexpected bundle members")
            if sum(info.file_size for info in archive.infolist()) > MAX_BUNDLE_BYTES:
                raise ValueError("Expanded bundle exceeds the 64 MiB import limit")
            return {name: archive.read(name).decode("utf-8") for name in REQUIRED}
    except (zipfile.BadZipFile, UnicodeError) as error:
        raise ValueError("Invalid UTF-8 bundle ZIP archive") from error
