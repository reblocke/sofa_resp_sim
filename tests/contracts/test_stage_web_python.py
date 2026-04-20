from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_stage_web_python_stages_allowlisted_files_only() -> None:
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

    staged_python = {entry["path"] for entry in manifest["python_files"]}
    staged_data = {entry["path"] for entry in manifest["data_files"]}

    assert "assets/py/sofa_resp_sim/browser_contract.py" in staged_python
    assert "assets/py/sofa_resp_sim/core/resp_scoring.py" in staged_python
    assert "assets/py/sofa_resp_sim/reporting/app_services.py" in staged_python
    assert "assets/data/resp_sofa_sim_summary.csv" in staged_data
    assert not any("__pycache__" in path for path in staged_python)
    assert not any("workflows/cli.py" in path for path in staged_python)
    assert not any("tests/" in path for path in staged_python)
    assert (ROOT / "web" / ".nojekyll").exists()
