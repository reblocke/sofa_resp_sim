"""Compare all frozen UTC scenarios with pre-DST-fix Python in an isolated snapshot.

One paired patient per request checks exact output/trace compatibility, not Monte
Carlo precision. The archived 2,000-patient references are never overwritten.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from sofa_resp_sim.workflows.experiment_cli import native_environment

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "2a100aadf707abb29cf1d52761c307255bd74809"
PROBE = """
import hashlib, json, sys
from pathlib import Path
from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request
from sofa_resp_sim.reporting.experiment_service import run_experiment, explain_patient
root = Path(sys.argv[1])
manifest = json.loads((root / 'experiments/trops_v1/manifest.json').read_text())
digests = {}
for item in manifest['requests']:
    raw = json.loads((root / item['path']).read_text())
    raw['replicates'] = 1
    request = normalize_experiment_request(raw)
    conditions = (request.comparator, *request.conditions)
    assert all(c.config.scoring.timezone == 'UTC' for c in conditions)
    result = {'output': run_experiment(request), 'traces': [
        explain_patient(request, 0, c.condition_id) for c in conditions]}
    encoded = json.dumps(result, sort_keys=True, allow_nan=False).encode()
    digests[item['path']] = hashlib.sha256(encoded).hexdigest()
print(json.dumps(digests, sort_keys=True))
"""


def main():
    with tempfile.TemporaryDirectory(prefix="sofa-dst-compatibility-") as temporary:
        snapshot = Path(temporary)
        archive = subprocess.check_output(
            ["git", "archive", BASELINE, "src/sofa_resp_sim"], cwd=ROOT
        )
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(snapshot, filter="data")
        comparisons = []
        for package_root in (snapshot, ROOT):
            environment = {**os.environ, "PYTHONPATH": str(package_root / "src")}
            output = subprocess.check_output(
                [sys.executable, "-c", PROBE, str(ROOT)],
                cwd=snapshot,
                env=environment,
                text=True,
            )
            comparisons.append(json.loads(output))
        before, after = comparisons
        if len(before) != 48 or before != after:
            changed = [name for name in before if before[name] != after.get(name)]
            raise RuntimeError(f"UTC output/trace compatibility failed: {changed}")
        receipt = {
            "status": "passed",
            "baseline_revision": BASELINE,
            "tested_environment": native_environment(),
            "scope": "48 frozen UTC requests, one paired patient each; exact results and traces",
            "request_output_sha256": after,
            "verification_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
        destination = ROOT / "artifacts/local/dst/utc_compatibility.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"48/48 UTC requests match {BASELINE}; receipt: {destination}")


if __name__ == "__main__":
    main()
