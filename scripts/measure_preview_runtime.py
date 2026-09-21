"""Measure representative 200-patient previews in the real production worker."""

from __future__ import annotations

import functools
import hashlib
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

from sofa_resp_sim.reporting.experiment_catalogue import catalogue_request
from sofa_resp_sim.reporting.experiment_workload import PREVIEW_LIMITS

ROOT = Path(__file__).resolve().parents[1]


def main():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT / "web")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    requests = [
        catalogue_request(name, "hfnc").to_dict() for name in ["E1_density", "E5_opportunity"]
    ]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.route(
                "**/measure-host",
                lambda route: route.fulfill(body="<html></html>", content_type="text/html"),
            )
            page.goto(base + "/measure-host")
            receipt = page.evaluate(
                r"""async ({base,requests}) => {
              const worker=new Worker(base+'/pyodide_worker.js');
              let id=0;
              async function call(type,payload) {
                const requestId=++id, progress=[], started=performance.now();
                return await new Promise((resolve,reject)=>{
                  const timer=setTimeout(()=>reject(new Error('Preview exceeded 240s')),240000);
                  worker.onerror=e=>{clearTimeout(timer);reject(new Error(e.message));};
                  worker.onmessage=({data})=>{
                    if(data.id!==requestId)return;
                    if(data.type==='progress'){progress.push(data.payload);return;}
                    clearTimeout(timer);
                    if(!data.payload.ok){
                      reject(new Error(JSON.stringify(data.payload.error)));return;
                    }
                    resolve({result:data.payload,progress,elapsed_ms:performance.now()-started});
                  };
                  worker.postMessage({id:requestId,type,payload});
                });
              }
              try {
                const cold=await call('init',{}), cases=[];
                for(const request of requests){
                  const run=await call('experiment',{request});
                  cases.push({experiment_id:request.experiment_id,request,
                    elapsed_ms:run.elapsed_ms,workload:run.result.workload,
                    completed_patients:run.result.completed_patients,
                    scoring_evaluations:run.result.scores.length,
                    progress:run.progress,
                    window_js_heap_after_bytes:performance.memory?.usedJSHeapSize ?? null});
                }
                return {cold_initialization_ms:cold.elapsed_ms,cases,
                  user_agent:navigator.userAgent,hardware_concurrency:navigator.hardwareConcurrency,
                  device_memory_gb:navigator.deviceMemory ?? null};
              } finally{worker.terminate();}
            }""",
                {"base": base, "requests": requests},
            )
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    for case in receipt["cases"]:
        assert case["completed_patients"] == 200
        assert case["progress"][0]["attempted_patients"] == 1
        assert case["progress"][0]["completed_patients"] == 0
        assert case["progress"][-1]["completed_patients"] == 200
        assert case["scoring_evaluations"] == case["workload"]["scoring_evaluations"]
    receipt.update(
        {
            "status": "measured",
            "pyodide": "0.29.0",
            "preview_limits": PREVIEW_LIMITS,
            "staging_manifest_sha256": hashlib.sha256(
                (ROOT / "web/assets/py/manifest.json").read_bytes()
            ).hexdigest(),
            "memory_note": "Window JS heap only, not worker/Wasm peak; browser-reported hardware.",
            "scope": "Density/baseline previews measured on this browser; not a latency guarantee",
        }
    )
    path = ROOT / "artifacts/local/acceptance/preview_runtime.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {
                "receipt": str(path),
                "cold_ms": receipt["cold_initialization_ms"],
                "cases": [
                    {k: c[k] for k in ["experiment_id", "elapsed_ms", "completed_patients"]}
                    for c in receipt["cases"]
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
