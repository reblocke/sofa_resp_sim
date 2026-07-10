from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "sofa_resp_sim.workflows.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_module_cli_help_runs() -> None:
    result = _run_cli("--help")

    assert result.returncode == 0
    assert "Run respiratory SOFA simulation sweeps." in result.stdout
    assert "--replicates" in result.stdout


def test_module_cli_happy_path_runs() -> None:
    result = _run_cli(
        "--replicates",
        "5",
        "--obs-freq",
        "15",
        "--noise-sd",
        "1.0",
        "--room-air-threshold",
        "94",
        "--seed",
        "0",
    )

    assert result.returncode == 0
    assert "obs_freq_minutes" in result.stdout
    assert "room_air_threshold" in result.stdout


def test_module_cli_rejects_zero_replicates() -> None:
    result = _run_cli("--replicates", "0")

    assert result.returncode != 0
    assert "n_reps must be >= 1." in result.stderr
    assert "Traceback" not in result.stderr


def test_module_cli_rejects_invalid_obs_freq_values() -> None:
    result = _run_cli("--obs-freq", "0")

    assert result.returncode != 0
    assert "obs_freq_minutes must be >= 1." in result.stderr
    assert "Traceback" not in result.stderr


def test_module_cli_writes_csv_output(tmp_path: Path) -> None:
    output_path = tmp_path / "sofa_resp_cli.csv"
    result = _run_cli(
        "--replicates",
        "3",
        "--obs-freq",
        "15,60",
        "--noise-sd",
        "0.5",
        "--room-air-threshold",
        "92",
        "--seed",
        "1",
        "--output",
        str(output_path),
    )

    assert result.returncode == 0
    assert output_path.exists()
    contents = output_path.read_text(encoding="utf-8")
    assert contents.startswith("obs_freq_minutes,noise_sd,room_air_threshold,n_reps")
    assert result.stdout == ""


def test_module_cli_rejects_empty_csv_tokens() -> None:
    result = _run_cli("--obs-freq", "15,,60")

    assert result.returncode != 0
    assert "obs_freq_minutes contains an empty value at position 2." in result.stderr
    assert "Traceback" not in result.stderr


def test_module_cli_rejects_invalid_timestamp() -> None:
    result = _run_cli("--admit-dts", "not-a-date")

    assert result.returncode != 0
    assert "admit_dts" in result.stderr
    assert "valid timestamp" in result.stderr
    assert "Traceback" not in result.stderr
