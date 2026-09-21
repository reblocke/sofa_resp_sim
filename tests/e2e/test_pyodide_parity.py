"""Execute staged scientific Python in an actual browser worker, not a mock contract."""

from __future__ import annotations

import base64
import functools
import hashlib
import http.server
import json
import platform
import threading
from pathlib import Path

import numpy as np
import pytest
from playwright.sync_api import Page

from sofa_resp_sim.browser_contract import run_experiment_payload

ROOT = Path(__file__).resolve().parents[2]
PYTHON_PROBE = r"""
import json
import numpy as np
import pandas as pd
import scipy
import tzdata
from scipy.stats import binomtest
from sofa_resp_sim.core.experiment_config import SCHEMA_VERSION
from sofa_resp_sim.reporting.experiment_request import normalize_experiment_request
from sofa_resp_sim.core.paired_simulation import generate_patient
from sofa_resp_sim.core.observation import document_patient
from sofa_resp_sim.core.experiment_scoring import score_documented_events
from sofa_resp_sim.reporting.experiment_service import _support_checksum

request = normalize_experiment_request({
    "schema_version": SCHEMA_VERSION,
    "base": {"horizon": {"start_minute": 0, "end_minute": 120},
             "observation": {"start_minute": 0}},
    "conditions": [{"label": "Hourly", "overrides": {
        "observation": {"interval_minutes": 60}}}],
    "replicates": 2,
})
patients = []
for patient_id in range(request.replicates):
    latent = generate_patient(request.base.generator, request.base.horizon,
                              request.seed, patient_id)
    patients.append({"patient_id": patient_id,
        "latent_id": latent.identity, "runtime_content_sha256": latent.content_sha256,
        "runtime_support_sha256": _support_checksum(latent, request.base),
        "minutes": latent.blocks[0].minutes.tolist(),
        "latent": latent.blocks[0].saturation.tolist(),
        "comparator_events": document_patient(latent, request.comparator.config),
        "variant_events": document_patient(latent, request.conditions[0].config),
        "comparator_score": score_documented_events(document_patient(latent, request.base),
                                                     request.base.horizon.admit_dts),
        "variant_score": score_documented_events(
            document_patient(latent, request.conditions[0].config),
            request.base.horizon.admit_dts)})
wilson = binomtest(0, 200).proportion_ci(confidence_level=.95, method="wilson")
paired = []
for plus, minus in [(30,10),(0,0)]:
    a = binomtest(plus, 100).proportion_ci(confidence_level=.975, method="exact")
    b = binomtest(minus, 100).proportion_ci(confidence_level=.975, method="exact")
    paired.append([max(-1., a.low-b.high),min(1.,a.high-b.low)])
result = {"request": request.to_dict(), "patients": patients,
          "wilson": [float(wilson.low),float(wilson.high)], "paired_intervals": paired,
          "versions": {"numpy": np.__version__, "pandas": pd.__version__,
                       "scipy": scipy.__version__, "tzdata": tzdata.__version__}}
"""

WORKER_RUN = r"""async ({base, python}) => {
  const code = `self.onmessage = async ({data}) => {
    try {
      importScripts('https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.js');
      const py = await loadPyodide({indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.29.0/full/'});
      await py.loadPackage(['numpy', 'pandas', 'scipy', 'tzdata']);
      const manifest = await (await fetch(data.base + '/assets/py/manifest.json')).json();
      for (const entry of manifest.python_files) {
        const content = await (await fetch(data.base + '/' + entry.path)).text();
        const path = '/home/pyodide/src/' + entry.path.replace('assets/py/', '');
        py.FS.mkdirTree(path.slice(0,path.lastIndexOf('/')));
        py.FS.writeFile(path,content);
      }
      await py.runPythonAsync("import sys; sys.path.insert(0, '/home/pyodide/src')");
      await py.runPythonAsync(data.python);
      const encoded = await py.runPythonAsync('json.dumps(result, allow_nan=False)');
      self.postMessage({ok:true, result:JSON.parse(encoded)});
    } catch(error) { self.postMessage({ok:false,error:String(error)}); }
  };`;
  const url = URL.createObjectURL(new Blob([code],{type:'application/javascript'}));
  const worker = new Worker(url);
  try {
    return await new Promise((resolve,reject) => {
      const timer = setTimeout(() => reject(new Error('Pyodide probe timed out')),240000);
      worker.onmessage = ({data}) => {clearTimeout(timer); resolve(data);};
      worker.onerror = event => {clearTimeout(timer); reject(new Error(event.message));};
      worker.postMessage({base,python});
    });
  } finally { worker.terminate(); URL.revokeObjectURL(url); }
}"""


def _compare(expected, actual):
    if isinstance(expected, dict):
        assert expected.keys() == actual.keys()
        for key in expected:
            _compare(expected[key], actual[key])
    elif isinstance(expected, list):
        assert len(expected) == len(actual)
        for a, b in zip(expected, actual, strict=True):
            _compare(a, b)
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=1e-10, abs=1e-10)
    else:
        assert type(expected) is type(actual)
        assert expected == actual


def test_pyodide_foundation_and_interval_components(page: Page):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT / "web")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        # An inert same-origin page avoids launching the application's second worker.
        page.route(
            "**/parity-host",
            lambda route: route.fulfill(body="<html></html>", content_type="text/html"),
        )
        page.goto(base + "/parity-host")
        response = page.evaluate(WORKER_RUN, {"base": base, "python": PYTHON_PROBE})
        assert response["ok"], response.get("error")
        production = page.evaluate(
            r"""async ({base, request}) => {
              const worker = new Worker(base + '/pyodide_worker.js');
              try {
                async function requestWorker(id, type, payload) {
                  return await new Promise((resolve, reject) => {
                  const timer = setTimeout(() => reject(new Error('Worker timeout')), 240000);
                  worker.onmessage = ({data}) => {
                    if (data.id !== id || data.type === 'progress') return;
                    clearTimeout(timer); resolve(data.payload);
                  };
                  worker.onerror = event => {
                    clearTimeout(timer); reject(new Error(event.message));
                  };
                  worker.postMessage({id, type, payload});
                });
                }
                const experiment = await requestWorker(1, 'experiment', {request});
                const exported = await requestWorker(4, 'export_bundle', {result: experiment});
                const imported = exported.ok
                  ? await requestWorker(5, 'import_bundle', {
                      archive_base64: exported.archive_base64
                    })
                  : exported;
                return {
                  experiment,
                  exported,
                  imported,
                  catalogue: await requestWorker(2, 'catalogue', {}),
                  explorer: await requestWorker(3, 'rule_explorer', {}),
                };
              } finally {worker.terminate();}
            }""",
            {"base": base, "request": response["result"]["request"]},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    from sofa_resp_sim.browser_contract import (
        get_experiment_catalogue_payload,
        run_rule_explorer_payload,
    )

    _compare(get_experiment_catalogue_payload({}), production["catalogue"])
    _compare(run_rule_explorer_payload({}), production["explorer"])
    assert production["exported"]["ok"], production["exported"]
    assert production["imported"]["ok"], production["imported"]
    _compare(production["experiment"]["scores"], production["imported"]["scores"])
    _compare(
        production["experiment"]["paired_contrasts"], production["imported"]["paired_contrasts"]
    )
    from sofa_resp_sim.browser_contract import import_experiment_bundle_payload

    native_import = import_experiment_bundle_payload(
        {"archive_base64": production["exported"]["archive_base64"]}
    )
    assert native_import["ok"], native_import
    _compare(production["experiment"]["scores"], native_import["scores"])
    bundle_path = ROOT / "artifacts/local/acceptance/pyodide_bundle.zip"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_bytes(base64.b64decode(production["exported"]["archive_base64"]))
    production = production["experiment"]
    assert response["ok"], response.get("error")
    native = {}
    exec(PYTHON_PROBE, native)
    expected = json.loads(json.dumps(native["result"], allow_nan=False))
    actual = response["result"]
    native_versions = expected.pop("versions")
    browser_versions = actual.pop("versions")
    native_production = run_experiment_payload({"request": expected["request"]})
    output_dir = ROOT / "artifacts/local/acceptance"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "native_pyodide_cases.json").write_text(
        json.dumps(
            {
                "native": expected,
                "pyodide": actual,
                "native_contract": native_production,
                "pyodide_contract": production,
            },
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    assert native_production["ok"] and production["ok"]
    for contract, probe in [(native_production, expected), (production, actual)]:
        provenance = contract.pop("runtime_provenance")
        assert provenance["hash_scheme"] == "raw_float64_le_v1"
        assert len(provenance["latent_content"]) == len(probe["patients"])
        assert len(provenance["support_content"]) == len(probe["patients"])
        for patient in probe["patients"]:
            record = next(
                r for r in provenance["latent_content"] if r["patient_id"] == patient["patient_id"]
            )
            assert record["latent_id"] == patient["latent_id"]
            assert record["content_sha256"] == patient.pop("runtime_content_sha256")
            support = next(
                r for r in provenance["support_content"] if r["patient_id"] == patient["patient_id"]
            )
            assert support["content_sha256"] == patient.pop("runtime_support_sha256")
    _compare(expected, actual)
    _compare(native_production, production)
    assert actual["wilson"] == pytest.approx([0, 0.018845326377266575], abs=1e-10)
    assert actual["paired_intervals"][0] == pytest.approx(
        [0.013763053206362341, 0.3700078964050354], abs=1e-10
    )
    assert actual["paired_intervals"][1] == pytest.approx(
        [-0.042874030238438485, 0.042874030238438485], abs=1e-10
    )
    manifest = ROOT / "web/assets/py/manifest.json"
    receipt = {
        "scope": "v2 paired API, generation, documentation, scoring and interval components",
        "status": "passed",
        "pyodide": "0.29.0",
        "python": platform.python_version(),
        "native_versions": native_versions,
        "browser_versions": browser_versions,
        "staging_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "atol": 1e-10,
        "rtol": 1e-10,
        "max_absolute_latent_difference": max(
            float(np.max(np.abs(np.asarray(a["latent"]) - np.asarray(b["latent"]))))
            for a, b in zip(expected["patients"], actual["patients"], strict=True)
        ),
    }
    output = ROOT / "artifacts/local/acceptance/runtime_probe.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n")
