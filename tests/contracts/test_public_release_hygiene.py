from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from sofa_resp_sim.browser_contract import (
    get_app_config_payload,
    run_scenario_payload,
    run_sweep_payload,
)
from sofa_resp_sim.reporting.view_model import default_run_request

ROOT = Path(__file__).resolve().parents[2]
DISALLOWED_TRACKED_SUFFIXES = {
    ".pdf",
    ".xlsx",
    ".xls",
    ".parquet",
    ".feather",
    ".dta",
    ".sav",
    ".sqlite",
    ".db",
    ".rds",
    ".pkl",
    ".joblib",
    ".pem",
    ".key",
    ".env",
}
DENYLISTED_FIELD_NAMES = {
    "patientid",
    "patientname",
    "mrn",
    "dob",
    "birthdate",
    "ssn",
    "email",
    "phone",
    "address",
    "encounterid",
    "accountnumber",
    "token",
    "secret",
    "password",
    "apikey",
    "privatekey",
}
EXPECTED_STAGED_DATA_FILES = {"assets/data/resp_sofa_sim_summary.csv"}


def test_no_disallowed_tracked_file_types_at_head() -> None:
    tracked_files = _tracked_relpaths()

    disallowed = [
        relpath
        for relpath in tracked_files
        if any(relpath.lower().endswith(suffix) for suffix in DISALLOWED_TRACKED_SUFFIXES)
    ]

    assert disallowed == [], f"Disallowed tracked files present at HEAD: {disallowed}"


def test_tracked_and_packaged_csv_headers_are_public_safe() -> None:
    tracked_csvs = [ROOT / relpath for relpath in _tracked_relpaths() if relpath.endswith(".csv")]

    for path in tracked_csvs:
        _assert_public_safe_headers(_csv_headers_from_path(path), str(path.relative_to(ROOT)))

    packaged_reference = ROOT / "src" / "sofa_resp_sim" / "data" / "resp_sofa_sim_summary.csv"
    _assert_public_safe_headers(
        _csv_headers_from_path(packaged_reference),
        "src/sofa_resp_sim/data/resp_sofa_sim_summary.csv",
    )


def test_browser_contract_keys_and_exports_are_public_safe() -> None:
    config_payload = get_app_config_payload()
    assert config_payload["ok"] is True
    _assert_public_safe_keys(_collect_keys(config_payload), "get_app_config_payload")

    scenario_payload = run_scenario_payload(
        {
            "request": default_run_request().to_json_dict(),
            "n_bootstrap": 10,
            "ci_level": 0.9,
            "uncertainty_seed": 1,
        }
    )
    assert scenario_payload["ok"] is True
    _assert_public_safe_keys(_collect_keys(scenario_payload), "run_scenario_payload")
    for field_name in ["summary_csv", "replicates_csv"]:
        _assert_public_safe_headers(
            _csv_headers_from_text(scenario_payload[field_name]),
            f"run_scenario_payload:{field_name}",
        )

    sweep_payload = run_sweep_payload(
        {
            "base_request": {
                **default_run_request().to_json_dict(),
                "n_reps": 3,
                "seed": 1,
            },
            "obs_freq_minutes_values": [15, 60],
            "noise_sd_values": [0.5],
            "room_air_threshold_values": [92.0],
            "heatmap_metric": "p_sofa_3plus",
        }
    )
    assert sweep_payload["ok"] is True
    _assert_public_safe_keys(_collect_keys(sweep_payload), "run_sweep_payload")
    for field_name in ["summary_csv", "replicates_csv"]:
        _assert_public_safe_headers(
            _csv_headers_from_text(sweep_payload[field_name]),
            f"run_sweep_payload:{field_name}",
        )


def test_stage_web_python_stages_only_allowlisted_public_safe_data() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/stage_web_python.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    manifest_path = ROOT / "web" / "assets" / "py" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    staged_data = {entry["path"] for entry in manifest["data_files"]}

    assert staged_data == EXPECTED_STAGED_DATA_FILES

    staged_reference = ROOT / "web" / "assets" / "data" / "resp_sofa_sim_summary.csv"
    _assert_public_safe_headers(
        _csv_headers_from_path(staged_reference),
        "web/assets/data/resp_sofa_sim_summary.csv",
    )


def _tracked_relpaths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return [line for line in result.stdout.splitlines() if line]


def _csv_headers_from_path(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def _csv_headers_from_text(text: str) -> list[str]:
    reader = csv.reader(io.StringIO(text))
    return next(reader, [])


def _collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(_collect_keys(nested))
    elif isinstance(value, list):
        for item in value:
            keys.update(_collect_keys(item))
    return keys


def _assert_public_safe_headers(headers: list[str], context: str) -> None:
    offending = sorted(
        {header for header in headers if _normalized_field_name(header) in DENYLISTED_FIELD_NAMES}
    )
    assert not offending, f"Potentially sensitive headers found in {context}: {offending}"


def _assert_public_safe_keys(keys: set[str], context: str) -> None:
    offending = sorted(
        {key for key in keys if _normalized_field_name(key) in DENYLISTED_FIELD_NAMES}
    )
    assert not offending, f"Potentially sensitive keys found in {context}: {offending}"


def _normalized_field_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())
