const PYODIDE_VERSION = "0.29.0";
const PYODIDE_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const BASE_URL = new URL("./", self.location.href);

let pyodide = null;
let initPromise = null;
let messageQueue = Promise.resolve();

self.onmessage = (event) => {
  const { id, type, payload } = event.data || {};
  messageQueue = messageQueue.then(() => handleMessage(id, type, payload));
};

async function handleMessage(id, type, payload) {
  try {
    if (type === "init") {
      const config = await initializeRuntime();
      postResult(id, "init", config);
      return;
    }

    await initializeRuntime();
    if (type === "scenario") {
      postResult(id, type, await callContract("run_scenario_payload", payload || {}));
      return;
    }
    if (type === "sweep") {
      postResult(id, type, await callContract("run_sweep_payload", payload || {}));
      return;
    }
    if (type === "experiment") {
      postResult(id, type, await callContract("run_experiment_payload", payload || {}, (progress) => {
        self.postMessage({id, type: "progress", payload: progress});
      }));
      return;
    }
    if (type === "workload") {
      postResult(id, type, await callContract("get_experiment_workload_payload", payload || {}));
      return;
    }
    if (type === "explain") {
      postResult(id, type, await callContract("explain_experiment_payload", payload || {}));
      return;
    }
    if (type === "catalogue") {
      postResult(id, type, await callContract("get_experiment_catalogue_payload", payload || {}));
      return;
    }
    if (type === "rule_explorer") {
      postResult(id, type, await callContract("run_rule_explorer_payload", payload || {}));
      return;
    }
    if (type === "export_bundle") {
      postResult(id, type, await callContract("export_experiment_bundle_payload", payload || {}));
      return;
    }
    if (type === "import_bundle") {
      postResult(id, type, await callContract("import_experiment_bundle_payload", payload || {}));
      return;
    }

    throw new Error(`Unknown worker message type: ${type}`);
  } catch (error) {
    postResult(id, type || "unknown", {
      ok: false,
      error: {
        type: error?.name || "Error",
        message: error?.message || String(error),
      },
    });
  }
}

async function initializeRuntime() {
  if (!initPromise) {
    initPromise = bootRuntime();
  }
  return initPromise;
}

async function bootRuntime() {
  postStatus("Loading Pyodide");
  importScripts(new URL("pyodide.js", PYODIDE_INDEX_URL).toString());
  pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX_URL });

  postStatus("Loading Python packages");
  await pyodide.loadPackage(["numpy", "pandas", "scipy", "tzdata"]);

  postStatus("Staging Python source");
  await stageManifestFiles();

  postStatus("Importing browser contract");
  const config = await callContract("get_app_config_payload");
  if (!config.ok) {
    throw new Error(config.error?.message || "Browser contract configuration failed.");
  }
  postStatus("Ready");
  return config;
}

async function stageManifestFiles() {
  const manifest = await fetchJson("assets/py/manifest.json");
  pyodide.FS.mkdirTree("/home/pyodide/src");
  pyodide.FS.mkdirTree("/home/pyodide/assets/data");

  for (const entry of manifest.python_files || []) {
    const source = await fetchText(entry.path);
    const target = `/home/pyodide/src/${entry.path.replace(/^assets\/py\//, "")}`;
    writeFile(target, source);
  }

  for (const entry of manifest.data_files || []) {
    const source = await fetchText(entry.path);
    const target = `/home/pyodide/${entry.path}`;
    writeFile(target, source);
  }

  await pyodide.runPythonAsync(`
import sys
src_path = "/home/pyodide/src"
if src_path not in sys.path:
    sys.path.insert(0, src_path)
`);
}

async function callContract(functionName, payload = null, onProgress = null) {
  try {
    if (payload === null) {
      const encodedResult = await pyodide.runPythonAsync(`
import json
import sofa_resp_sim.browser_contract as browser_contract
json.dumps(browser_contract.${functionName}(), allow_nan=False)
`);
      return JSON.parse(encodedResult);
    }

    // JSON is the contract: normalize JS null to Python None, not a JsNull proxy.
    const encoded = JSON.stringify(payload, (_key, value) => {
      if (typeof value === "number" && !Number.isFinite(value)) {
        throw new Error("Scientific inputs must be finite numbers.");
      }
      return value;
    });
    pyodide.globals.set("browser_payload_json", encoded);
    if (onProgress) {
      pyodide.globals.set("browser_progress_json", (value) => onProgress(JSON.parse(value)));
    }
    const encodedResult = await pyodide.runPythonAsync(`
import json
import sofa_resp_sim.browser_contract as browser_contract
json.dumps(browser_contract.${functionName}(json.loads(browser_payload_json)${onProgress ? ", on_progress=lambda p: browser_progress_json(json.dumps(p, allow_nan=False))" : ""}), allow_nan=False)
`);
    return JSON.parse(encodedResult);
  } finally {
    if (payload !== null) {
      pyodide.globals.delete("browser_payload_json");
    }
    if (onProgress) pyodide.globals.delete("browser_progress_json");
  }
}

async function fetchJson(path) {
  const response = await fetch(new URL(path, BASE_URL), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to fetch ${path}: ${response.status}`);
  }
  return response.json();
}

async function fetchText(path) {
  const response = await fetch(new URL(path, BASE_URL), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to fetch ${path}: ${response.status}`);
  }
  return response.text();
}

function writeFile(path, contents) {
  const directory = path.slice(0, path.lastIndexOf("/"));
  pyodide.FS.mkdirTree(directory);
  pyodide.FS.writeFile(path, contents, { encoding: "utf8" });
}

function postStatus(message) {
  self.postMessage({
    type: "status",
    payload: { message },
  });
}

function postResult(id, type, payload) {
  self.postMessage({
    id,
    type,
    payload,
  });
}
