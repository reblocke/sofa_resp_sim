from __future__ import annotations

import subprocess
import sys


def test_module_cli_help_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "sofa_resp_sim.workflows.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Run respiratory SOFA simulation sweeps." in result.stdout
    assert "--replicates" in result.stdout
