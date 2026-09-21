"""Reproduce a small synthetic bundle in a fresh locked wheel installation."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from sofa_resp_sim.reporting.experiment_catalogue import catalogue_request

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts/local/acceptance"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    commands = []
    with tempfile.TemporaryDirectory(prefix="sofa-clean-install-") as directory:
        work = Path(directory)
        log = OUTPUT / "clean_experiment_install.log"
        log.write_text("")

        def run(args, cwd=work):
            response = subprocess.run(list(map(str, args)), cwd=cwd, text=True, capture_output=True)
            with log.open("a") as stream:
                stream.write(
                    json.dumps(
                        {
                            "command": list(map(str, args)),
                            "cwd": str(cwd),
                            "exit_code": response.returncode,
                        }
                    )
                    + "\n"
                )
                stream.write(response.stdout + response.stderr + "\n")
            commands.append({"command": list(map(str, args)), "exit_code": response.returncode})
            if response.returncode:
                raise RuntimeError(f"Clean install check failed; see {log}")
            return response.stdout

        lock = run(
            [
                "uv",
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements-txt",
            ],
            ROOT,
        )
        (work / "requirements.txt").write_text(lock)
        run(["uv", "venv", "--python", sys.executable, work / "venv"])
        python = work / "venv/bin/python"
        wheel = ROOT / "dist/sofa_resp_sim-0.1.0-py3-none-any.whl"
        run(["uv", "pip", "install", "--python", python, "-r", work / "requirements.txt", wheel])
        imported = run(
            [python, "-c", "import sofa_resp_sim; print(sofa_resp_sim.__file__)"]
        ).strip()
        assert str(work / "venv") in imported
        cli = work / "venv/bin/resp-sofa-experiment"
        run([cli, "--help"])
        checks = []
        for entry in ("E1_density", "H_missing_historical"):
            request = catalogue_request(entry, "hfnc", replicates=3)
            request_path = work / f"{entry}.json"
            request_path.write_text(json.dumps(request.to_dict()))
            original = work / entry
            reproduced = work / f"{entry}.zip"
            run(
                [
                    sys.executable,
                    "-m",
                    "sofa_resp_sim.workflows.experiment_cli",
                    "run",
                    "--request",
                    request_path,
                    "--output",
                    original,
                ]
            )
            run([cli, "reproduce", original, "--output", reproduced])
            checks.append(json.loads(run([cli, "verify-bundle", reproduced])))
        receipt = {"status": "verified", "checks": checks}
        receipt.update(
            {
                "scope": "Fresh locked wheel outside checkout; exact scientific reproduction",
                "imported_package": imported,
                "commands": commands,
                "log_path": str(log),
                "temporary_environment_removed_after_check": True,
            }
        )
        (OUTPUT / "clean_experiment_install.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "status": receipt["status"],
                    "receipt": str(OUTPUT / "clean_experiment_install.json"),
                }
            )
        )


if __name__ == "__main__":
    main()
