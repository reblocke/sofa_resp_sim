const state = {
  worker: null,
  nextId: 1,
  pending: new Map(),
  config: null,
  scenario: null,
  sweep: null,
};

const inputHelp = {
  "scenario-preset": {
    label: "Scenario preset",
    description: "Loads a saved set of scenario values. You can edit any value after selecting a preset.",
  },
  "scenario-n-reps": {
    label: "Replicates",
    description: "Number of simulated encounters for this scenario. Higher values are more stable but slower.",
  },
  "scenario-seed": {
    label: "Scenario seed",
    description: "Random seed. Use the same seed to reproduce the same simulated run.",
  },
  "scenario-obs-freq": {
    label: "Scenario observation minutes",
    description: "Minutes between SpO2 observations in the simulated record.",
  },
  "scenario-room-air": {
    label: "Scenario room-air threshold",
    description: "Observed SpO2 at or above this value is treated as room air for support assignment.",
  },
  "scenario-spo2-mean": {
    label: "SpO2 mean",
    description: "Baseline average true SpO2 used to generate each simulated encounter.",
  },
  "scenario-spo2-sd": {
    label: "SpO2 SD",
    description: "Within-encounter variability around the true SpO2 process.",
  },
  "scenario-ar1": {
    label: "AR(1)",
    description: "Autocorrelation from one observation to the next. Higher values make SpO2 more persistent.",
  },
  "scenario-measurement-sd": {
    label: "Measurement SD",
    description: "Random measurement noise added to true SpO2 before rounding and support assignment.",
  },
  "scenario-rounding": {
    label: "SpO2 rounding",
    description: "How observed SpO2 values are rounded before scoring and support logic run.",
  },
  "scenario-desat-prob": {
    label: "Desat probability",
    description: "Probability that a desaturation episode starts at an observation.",
  },
  "scenario-desat-depth": {
    label: "Desat depth",
    description: "SpO2 drop applied during a modeled desaturation episode.",
  },
  "scenario-desat-duration": {
    label: "Desat duration",
    description: "Approximate duration of a modeled desaturation episode in minutes.",
  },
  "scenario-fio2-prob": {
    label: "FiO2 measured probability",
    description: "Probability that FiO2 is charted as measured rather than inferred from set or ordered support.",
  },
  "scenario-altitude": {
    label: "Altitude factor",
    description: "Adjustment factor used by the SpO2-to-PaO2 conversion for altitude.",
  },
  "scenario-flow-min": {
    label: "O2 flow minimum",
    description: "Minimum low-flow oxygen rate sampled when low-flow support is assigned.",
  },
  "scenario-flow-max": {
    label: "O2 flow maximum",
    description: "Maximum low-flow oxygen rate sampled when low-flow support is assigned.",
  },
  "scenario-support-observed": {
    label: "Support follows observed SpO2",
    description:
      "When enabled, support category is assigned from noisy observed SpO2; otherwise it uses underlying true SpO2.",
  },
  "scenario-acute-start": {
    label: "Acute start hours",
    description: "Start of the acute scoring window relative to admission time; negative values begin before admission.",
  },
  "scenario-acute-end": {
    label: "Acute end hours",
    description: "End of the acute scoring window relative to admission time.",
  },
  "scenario-include-baseline": {
    label: "Include baseline window",
    description: "Adds a pre-admission baseline window and computes baseline respiratory SOFA for delta outputs.",
  },
  "scenario-baseline-days": {
    label: "Baseline days before",
    description: "How many days before admission the baseline window starts.",
  },
  "scenario-baseline-hours": {
    label: "Baseline hours",
    description: "Length of the baseline window.",
  },
  "scenario-bootstrap": {
    label: "Bootstrap samples",
    description: "Number of bootstrap resamples used to estimate uncertainty intervals. Higher values are slower.",
  },
  "scenario-ci-level": {
    label: "CI level",
    description: "Width of the uncertainty interval, such as 0.95 for a 95% interval.",
  },
  "sweep-preset": {
    label: "Sweep preset",
    description: "Loads a saved sweep grid. You can edit the grid values after selecting a preset.",
  },
  "sweep-n-reps": {
    label: "Base replicates",
    description: "Replicates run for each sweep grid cell.",
  },
  "sweep-seed": {
    label: "Base seed",
    description: "Seed used to make the sweep reproducible.",
  },
  "sweep-obs-values": {
    label: "Sweep observation minutes",
    description: "Comma-separated observation intervals to test, for example 15, 30, 60.",
  },
  "sweep-noise-values": {
    label: "Noise SD values",
    description: "Comma-separated measurement-noise levels to test.",
  },
  "sweep-room-values": {
    label: "Room-air thresholds",
    description: "Comma-separated room-air thresholds to test.",
  },
  "sweep-metric": {
    label: "Heatmap metric",
    description: "Summary metric used to color the sweep heatmap.",
  },
};

const scenarioFields = {
  admit_dts: null,
  acute_start_hours: "scenario-acute-start",
  acute_end_hours: "scenario-acute-end",
  include_baseline: "scenario-include-baseline",
  baseline_days_before: "scenario-baseline-days",
  baseline_duration_hours: "scenario-baseline-hours",
  obs_freq_minutes: "scenario-obs-freq",
  spo2_mean: "scenario-spo2-mean",
  spo2_sd: "scenario-spo2-sd",
  ar1: "scenario-ar1",
  desat_prob: "scenario-desat-prob",
  desat_depth: "scenario-desat-depth",
  desat_duration_minutes: "scenario-desat-duration",
  measurement_sd: "scenario-measurement-sd",
  spo2_rounding: "scenario-rounding",
  room_air_threshold: "scenario-room-air",
  support_based_on_observed: "scenario-support-observed",
  fio2_meas_prob: "scenario-fio2-prob",
  oxygen_flow_min: "scenario-flow-min",
  oxygen_flow_max: "scenario-flow-max",
  altitude_factor: "scenario-altitude",
  n_reps: "scenario-n-reps",
  seed: "scenario-seed",
};

const numericScenarioFields = new Set([
  "acute_start_hours",
  "acute_end_hours",
  "baseline_days_before",
  "baseline_duration_hours",
  "obs_freq_minutes",
  "spo2_mean",
  "spo2_sd",
  "ar1",
  "desat_prob",
  "desat_depth",
  "desat_duration_minutes",
  "measurement_sd",
  "room_air_threshold",
  "fio2_meas_prob",
  "oxygen_flow_min",
  "oxygen_flow_max",
  "altitude_factor",
  "n_reps",
  "seed",
]);

const integerScenarioFields = new Set([
  "baseline_days_before",
  "obs_freq_minutes",
  "desat_duration_minutes",
  "n_reps",
  "seed",
]);

const booleanScenarioFields = new Set(["include_baseline", "support_based_on_observed"]);

document.addEventListener("DOMContentLoaded", () => {
  initializeHelpTooltips();
  bindTabs();
  bindControls();
  resetWorker();
  initializeApp();
});

function initializeHelpTooltips() {
  for (const [controlId, help] of Object.entries(inputHelp)) {
    const field = document.querySelector(`[data-help-for="${controlId}"]`);
    const labelRow = field?.querySelector(".label-row");
    if (!labelRow) continue;

    const tooltipId = `tooltip-${controlId}`;
    const button = document.createElement("button");
    button.id = `help-button-${controlId}`;
    button.className = "help-button";
    button.type = "button";
    button.textContent = "i";
    button.setAttribute("aria-label", `${help.label} explanation`);
    button.setAttribute("aria-describedby", tooltipId);
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("data-testid", `help-${controlId}`);

    const tooltip = document.createElement("span");
    tooltip.id = tooltipId;
    tooltip.className = "help-tooltip";
    tooltip.setAttribute("role", "tooltip");
    tooltip.hidden = true;
    tooltip.textContent = help.description;

    button.addEventListener("mouseenter", () => openHelpTooltip(button));
    button.addEventListener("focus", () => openHelpTooltip(button));
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openHelpTooltip(button);
    });
    button.addEventListener("blur", () => closeHelpTooltip(button));
    labelRow.addEventListener("mouseleave", () => closeHelpTooltip(button));

    labelRow.append(button, tooltip);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAllHelpTooltips();
    }
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".label-row")) {
      closeAllHelpTooltips();
    }
  });
}

function openHelpTooltip(button) {
  closeAllHelpTooltips(button);
  const tooltip = byId(button.getAttribute("aria-describedby"));
  if (!tooltip) return;
  tooltip.hidden = false;
  button.dataset.open = "true";
  button.setAttribute("aria-expanded", "true");
}

function closeHelpTooltip(button) {
  const tooltip = byId(button.getAttribute("aria-describedby"));
  if (!tooltip) return;
  tooltip.hidden = true;
  button.dataset.open = "false";
  button.setAttribute("aria-expanded", "false");
}

function closeAllHelpTooltips(exceptButton = null) {
  for (const button of document.querySelectorAll(".help-button")) {
    if (button !== exceptButton) {
      closeHelpTooltip(button);
    }
  }
}

function bindTabs() {
  for (const button of document.querySelectorAll(".tab-button")) {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab-button").forEach((item) => {
        item.classList.toggle("active", item === button);
      });
      document.querySelectorAll(".workspace").forEach((section) => {
        section.classList.toggle("active", section.id === `${button.dataset.tab}-tab`);
      });
    });
  }
}

function bindControls() {
  byId("run-scenario").addEventListener("click", runScenario);
  byId("cancel-scenario").addEventListener("click", cancelWork);
  byId("reset-scenario").addEventListener("click", () => applyScenarioDefaults());
  byId("scenario-preset").addEventListener("change", applyScenarioPreset);
  byId("run-sweep").addEventListener("click", runSweep);
  byId("cancel-sweep").addEventListener("click", cancelWork);
  byId("reset-sweep").addEventListener("click", () => applySweepDefaults());
  byId("sweep-preset").addEventListener("change", applySweepPreset);
  ["sweep-n-reps", "sweep-obs-values", "sweep-noise-values", "sweep-room-values"].forEach((id) => {
    byId(id).addEventListener("input", updateSweepWorkload);
  });
}

async function initializeApp() {
  setRuntimeStatus("loading", "Starting Pyodide");
  setBusy(true);
  try {
    const config = await requestWorker("init");
    if (!config.ok) {
      throw new Error(config.error?.message || "Configuration failed.");
    }
    state.config = config;
    hydrateControls(config);
    applyScenarioDefaults();
    applySweepDefaults();
    renderReference(config.reference_distribution);
    renderGuardrails(config.browser_guardrails);
    setRuntimeStatus("ready", "Pyodide ready");
  } catch (error) {
    setRuntimeStatus("error", error.message);
    toast(error.message);
  } finally {
    setBusy(false);
  }
}

function resetWorker() {
  if (state.worker) {
    state.worker.terminate();
  }
  rejectPendingRequests(new Error("Worker reset."));
  state.worker = new Worker("pyodide_worker.js");
  state.worker.onmessage = handleWorkerMessage;
  state.worker.onerror = (event) => {
    const message = event.message || "Worker error";
    rejectPendingRequests(new Error(message));
    setRuntimeStatus("error", message);
    toast(message);
  };
}

function rejectPendingRequests(error) {
  state.pending.forEach(({ reject }) => reject(error));
  state.pending.clear();
}

function cancelWork() {
  resetWorker();
  setRuntimeStatus("loading", "Worker reset");
  setBusy(false);
  initializeApp();
}

function handleWorkerMessage(event) {
  const { id, type, payload } = event.data || {};
  if (type === "status") {
    setRuntimeStatus("loading", payload.message);
    return;
  }
  const pending = state.pending.get(id);
  if (!pending) {
    return;
  }
  state.pending.delete(id);
  pending.resolve(payload);
}

function requestWorker(type, payload = {}) {
  const id = state.nextId++;
  return new Promise((resolve, reject) => {
    state.pending.set(id, { resolve, reject });
    state.worker.postMessage({ id, type, payload });
  });
}

function hydrateControls(config) {
  fillSelect(
    byId("scenario-preset"),
    config.run_presets.map((preset) => preset.name),
  );
  fillSelect(
    byId("sweep-preset"),
    config.sweep_presets.map((preset) => preset.name),
  );
  fillSelect(byId("scenario-rounding"), config.spo2_rounding_options);
  fillSelect(byId("sweep-metric"), config.supported_sweep_metrics);
  byId("scenario-bootstrap").value = config.guardrails.default_bootstrap_samples;
  byId("scenario-ci-level").value = config.guardrails.default_ci_level;
}

function applyScenarioDefaults() {
  if (!state.config) return;
  byId("scenario-preset").value = "Default";
  applyScenarioRequest(state.config.defaults);
}

function applyScenarioPreset() {
  const name = byId("scenario-preset").value;
  const preset = state.config.run_presets.find((item) => item.name === name);
  if (preset) {
    applyScenarioRequest(preset.request);
  }
}

function applyScenarioRequest(request) {
  for (const [key, id] of Object.entries(scenarioFields)) {
    if (id === null) continue;
    const element = byId(id);
    if (booleanScenarioFields.has(key)) {
      element.checked = Boolean(request[key]);
    } else {
      element.value = request[key];
    }
  }
}

function collectScenarioRequest() {
  const request = { admit_dts: state.config.defaults.admit_dts };
  for (const [key, id] of Object.entries(scenarioFields)) {
    if (id === null) continue;
    const element = byId(id);
    if (booleanScenarioFields.has(key)) {
      request[key] = element.checked;
    } else if (numericScenarioFields.has(key)) {
      const value = Number(element.value);
      request[key] = integerScenarioFields.has(key) ? Math.trunc(value) : value;
    } else {
      request[key] = element.value;
    }
  }
  return request;
}

async function runScenario() {
  if (!state.config) return;
  setBusy(true);
  setRuntimeStatus("loading", "Running scenario");
  try {
    const payload = await requestWorker("scenario", {
      request: collectScenarioRequest(),
      n_bootstrap: Number(byId("scenario-bootstrap").value),
      ci_level: Number(byId("scenario-ci-level").value),
      uncertainty_seed: Number(byId("scenario-seed").value),
    });
    if (!payload.ok) {
      throw new Error(payload.error?.message || "Scenario failed.");
    }
    state.scenario = payload;
    renderScenario(payload);
    setRuntimeStatus("ready", "Scenario complete");
  } catch (error) {
    setRuntimeStatus("error", error.message);
    toast(error.message);
  } finally {
    setBusy(false);
  }
}

function renderScenario(payload) {
  const summary = payload.summary_rows[0];
  byId("scenario-summary-note").textContent =
    `${summary.n_reps} replicates at ${summary.obs_freq_minutes} minute observations.`;
  renderMetrics(byId("scenario-metrics"), [
    ["P(SOFA 3+)", formatPercent((summary.p_sofa_3 || 0) + (summary.p_sofa_4 || 0))],
    ["P(SOFA 4)", formatPercent(summary.p_sofa_4)],
    ["Mean qualifying P/F count", formatNumber(summary.mean_count_pf_ratio_acute, 2)],
    ["Jensen-Shannon", formatNumber(payload.divergence_metrics.jensen_shannon_distance, 3)],
  ]);
  renderProbabilityChart(payload.reference_comparison);
  renderTable(byId("uncertainty-table"), payload.uncertainty_rows, [
    "score",
    "p_scenario",
    "ci_lower",
    "ci_upper",
    "p_reference",
    "delta_vs_reference",
  ]);
  bindDownload("download-scenario-csv", "sofa_resp_scenario_summary.csv", payload.summary_csv);
  bindDownload("download-scenario-reps", "sofa_resp_scenario_replicates.csv", payload.replicates_csv);
  bindDownload(
    "download-scenario-json",
    "sofa_resp_scenario_request.json",
    JSON.stringify(payload.request, null, 2),
    "application/json",
  );
}

function applySweepDefaults() {
  if (!state.config) return;
  byId("sweep-preset").value = "Quick";
  const sweep = state.config.sweep_defaults;
  byId("sweep-n-reps").value = sweep.base_request.n_reps;
  byId("sweep-seed").value = sweep.base_request.seed;
  byId("sweep-obs-values").value = sweep.obs_freq_minutes_values.join(", ");
  byId("sweep-noise-values").value = sweep.noise_sd_values.join(", ");
  byId("sweep-room-values").value = sweep.room_air_threshold_values.join(", ");
  byId("sweep-metric").value = sweep.heatmap_metric;
  updateSweepWorkload();
}

function applySweepPreset() {
  const name = byId("sweep-preset").value;
  const preset = state.config.sweep_presets.find((item) => item.name === name);
  if (!preset) return;
  byId("sweep-obs-values").value = preset.request.obs_freq_minutes_values.join(", ");
  byId("sweep-noise-values").value = preset.request.noise_sd_values.join(", ");
  byId("sweep-room-values").value = preset.request.room_air_threshold_values.join(", ");
  byId("sweep-metric").value = preset.request.heatmap_metric;
  updateSweepWorkload();
}

function collectSweepRequest() {
  const base = {
    ...state.config.defaults,
    n_reps: Number(byId("sweep-n-reps").value),
    seed: Number(byId("sweep-seed").value),
  };
  return {
    base_request: base,
    obs_freq_minutes_values: byId("sweep-obs-values").value,
    noise_sd_values: byId("sweep-noise-values").value,
    room_air_threshold_values: byId("sweep-room-values").value,
    heatmap_metric: byId("sweep-metric").value,
  };
}

function updateSweepWorkload() {
  if (!state.config) return;
  const obsCount = parseCsv(byId("sweep-obs-values").value).length;
  const noiseCount = parseCsv(byId("sweep-noise-values").value).length;
  const roomCount = parseCsv(byId("sweep-room-values").value).length;
  const nReps = Number(byId("sweep-n-reps").value) || 0;
  const combinations = obsCount * noiseCount * roomCount;
  const runs = combinations * nReps;
  byId("sweep-workload").textContent =
    `${combinations} combinations, ${runs.toLocaleString()} simulated encounters. Guardrail: ${state.config.guardrails.max_sweep_runs.toLocaleString()}.`;
}

async function runSweep() {
  if (!state.config) return;
  setBusy(true);
  setRuntimeStatus("loading", "Running sweep");
  try {
    const payload = await requestWorker("sweep", collectSweepRequest());
    if (!payload.ok) {
      throw new Error(payload.error?.message || "Sweep failed.");
    }
    state.sweep = payload;
    renderSweep(payload);
    setRuntimeStatus("ready", "Sweep complete");
  } catch (error) {
    setRuntimeStatus("error", error.message);
    toast(error.message);
  } finally {
    setBusy(false);
  }
}

function renderSweep(payload) {
  byId("sweep-summary-note").textContent =
    `${payload.workload_estimate.combinations} combinations, ${payload.workload_estimate.total_runs.toLocaleString()} simulated encounters.`;
  const summary = payload.summary_rows;
  const maxThreePlus = Math.max(...summary.map((row) => row.p_sofa_3plus));
  const maxSofa4 = Math.max(...summary.map((row) => row.p_sofa_4));
  renderMetrics(byId("sweep-metrics"), [
    ["Combinations", payload.workload_estimate.combinations.toLocaleString()],
    ["Total runs", payload.workload_estimate.total_runs.toLocaleString()],
    ["Max P(SOFA 3+)", formatPercent(maxThreePlus)],
    ["Max P(SOFA 4)", formatPercent(maxSofa4)],
  ]);
  renderHeatmap(payload.heatmap_rows);
  renderTable(byId("sweep-table"), summary.slice(0, 100), [
    "obs_freq_minutes",
    "noise_sd",
    "room_air_threshold",
    "n_reps",
    "p_sofa_3plus",
    "p_sofa_4",
    "mean_count_pf_ratio_acute",
  ]);
  bindDownload("download-sweep-summary", "sofa_resp_sweep_summary.csv", payload.summary_csv);
  bindDownload("download-sweep-reps", "sofa_resp_sweep_replicates.csv", payload.replicates_csv);
}

function renderMetrics(target, metrics) {
  target.replaceChildren(
    ...metrics.map(([label, value]) => {
      const card = document.createElement("div");
      card.className = "metric-card";
      card.innerHTML = `<span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong>`;
      return card;
    }),
  );
}

function renderProbabilityChart(rows) {
  const target = byId("scenario-chart");
  target.replaceChildren(
    ...rows.map((row) => {
      const line = document.createElement("div");
      line.className = "probability-row";
      const scenarioWidth = Math.max(0, Math.min(100, row.p_scenario * 100));
      const referenceLeft = Math.max(0, Math.min(100, row.p_reference * 100));
      line.innerHTML = `
        <span class="probability-label">SOFA ${row.score}</span>
        <span class="bar-track">
          <span class="bar-fill" style="width:${scenarioWidth}%"></span>
          <span class="bar-reference" style="left:${referenceLeft}%"></span>
        </span>
        <span class="probability-value">${formatPercent(row.p_scenario)}</span>
      `;
      return line;
    }),
  );
}

function renderHeatmap(rows) {
  const target = byId("sweep-heatmap");
  const values = rows.map((row) => row.metric_value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  target.replaceChildren(
    ...rows.map((row) => {
      const scaled = max === min ? 0.5 : (row.metric_value - min) / (max - min);
      const tint = 92 - scaled * 28;
      const cell = document.createElement("div");
      cell.className = "heat-cell";
      cell.style.background = `hsl(172 36% ${tint}%)`;
      cell.innerHTML = `
        <strong>${formatMaybePercent(row.metric_value)}</strong>
        <span>${row.obs_freq_minutes} min, noise ${formatNumber(row.noise_sd, 1)}</span>
        <span>Room-air ${formatNumber(row.room_air_threshold, 1)}</span>
      `;
      return cell;
    }),
  );
}

function renderTable(table, rows, columns) {
  if (!rows.length) {
    table.replaceChildren();
    return;
  }
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  for (const column of columns) {
    const th = document.createElement("th");
    th.textContent = column;
    headerRow.append(th);
  }
  thead.append(headerRow);

  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const column of columns) {
      const td = document.createElement("td");
      td.textContent = formatCell(row[column]);
      tr.append(td);
    }
    tbody.append(tr);
  }
  table.replaceChildren(thead, tbody);
}

function renderReference(rows) {
  const target = byId("reference-panel");
  const list = document.createElement("div");
  list.className = "probability-chart";
  for (const row of rows) {
    const line = document.createElement("div");
    line.className = "probability-row";
    const width = Math.max(0, Math.min(100, row.probability * 100));
    line.innerHTML = `
      <span class="probability-label">SOFA ${row.score}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${width}%"></span></span>
      <span class="probability-value">${formatPercent(row.probability)}</span>
    `;
    list.append(line);
  }
  target.replaceChildren(list);
}

function renderGuardrails(items) {
  const list = byId("guardrails-list");
  list.replaceChildren(
    ...items.map((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      return li;
    }),
  );
}

function bindDownload(id, filename, text, type = "text/csv") {
  const button = byId(id);
  button.disabled = false;
  button.onclick = () => {
    const blob = new Blob([text], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };
}

function setBusy(isBusy) {
  for (const id of ["run-scenario", "run-sweep"]) {
    byId(id).disabled = isBusy;
  }
}

function setRuntimeStatus(stateName, message) {
  const wrapper = document.querySelector(".runtime-status");
  wrapper.dataset.state = stateName;
  byId("runtime-status").textContent = message;
}

function toast(message) {
  const element = byId("toast");
  element.textContent = message;
  element.classList.add("visible");
  window.setTimeout(() => element.classList.remove("visible"), 4500);
}

function fillSelect(select, values) {
  select.replaceChildren(
    ...values.map((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      return option;
    }),
  );
}

function parseCsv(raw) {
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatCell(value) {
  if (typeof value === "number") {
    return Math.abs(value) <= 1 ? formatNumber(value, 3) : formatNumber(value, 2);
  }
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function formatMaybePercent(value) {
  return Math.abs(value) <= 1 ? formatPercent(value) : formatNumber(value, 2);
}

function formatPercent(value) {
  return `${formatNumber(value * 100, 1)}%`;
}

function formatNumber(value, digits) {
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value;
  return span.innerHTML;
}

function byId(id) {
  return document.getElementById(id);
}
