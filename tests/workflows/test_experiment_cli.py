import json
import subprocess
import sys
from pathlib import Path

from sofa_resp_sim.reporting.experiment_bundle import verify_bundle
from sofa_resp_sim.workflows.experiment_cli import read_files

CLI = Path(sys.executable).parent / "resp-sofa-experiment"


def call(tmp_path, *args, ok=True):
    response = subprocess.run(
        [str(CLI), *map(str, args)], cwd=tmp_path, text=True, capture_output=True
    )
    assert (response.returncode == 0) == ok, response.stderr
    return response


def test_installed_cli_directory_zip_reproduce_append_explain(tmp_path):
    listing = json.loads(call(tmp_path, "list").stdout)
    assert len(listing["entries"]) == 32
    assert any(e["id"] == "H_history_historical" for e in listing["entries"])
    original = tmp_path / "original"
    call(tmp_path, "run", "--entry", "E1_episode", "--output", original)
    call(tmp_path, "verify-bundle", original)
    restored = verify_bundle(read_files(original))
    row = restored["scores"][0]
    response = call(
        tmp_path, "explain", original, "--patient", 0, "--condition", row["condition_id"]
    )
    assert json.loads(response.stdout)["score"] == row
    zipped = tmp_path / "reproduced.zip"
    call(tmp_path, "reproduce", original, "--output", zipped)
    second = verify_bundle(read_files(zipped))
    assert (
        second["manifest"]["scientific_data_sha256"]
        == restored["manifest"]["scientific_data_sha256"]
    )
    call(tmp_path, "verify-bundle", zipped)
    extended = tmp_path / "appended"
    call(tmp_path, "append", zipped, "--replicates", 3, "--output", extended)
    assert verify_bundle(read_files(extended))["completed_patients"] == 3
    call(tmp_path, "run", "--entry", "E1_episode", "--output", original, ok=False)
    call(
        tmp_path, "append", original, "--replicates", 1, "--output", tmp_path / "invalid", ok=False
    )
