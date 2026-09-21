const $ = (id) => document.getElementById(id);
const clone = (value) => structuredClone(value);
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const state = {
  worker: null,
  generation: 0,
  nextId: 1,
  pending: new Map(),
  ready: false,
  busy: false,
  request: null,
  result: null,
  catalogue: null,
  entry: "E1_density",
  stratum: "room_air",
  version: 0,
  resultVersion: 0,
  resultKind: "Saved synthetic example",
  needsExpansion: false,
  allConditions: [],
  allowed: false,
  trace: null,
  imported: false,
};
const names = {
  score_ge1: "Score ≥1",
  score_ge2: "Score ≥2",
  score_ge3: "Score ≥3",
  score_eq4: "Score =4",
  no_qualifying_data: "No qualifying data",
  suppressed_only: "Suppressed only",
  qualifying_pf_count: "Qualifying P/F count",
  delta_legacy_ge1: "Legacy delta ≥1",
  delta_legacy_ge2: "Legacy delta ≥2",
};
const fields = [
  ["generator.mean_pct", "Background SpO2 mean (%)", 0.1],
  ["generator.marginal_sd_pct", "Marginal SD (%)", 0.1],
  ["generator.tau_minutes", "Correlation time (minutes)", 1],
  ["generator.episode_rate_per_hour", "Episode initiation rate (/hour)", 0.01],
  [
    "generator.episode_depth_pct_points",
    "Episode depth (percentage points)",
    0.1,
  ],
  ["generator.episode_duration_minutes", "Episode duration (minutes)", 1],
  ["observation.interval_minutes", "Observation interval (minutes)", 1],
  ["observation.noise_sd_pct", "Measurement noise SD (%)", 0.1],
  ["observation.bias_pct_points", "Measurement bias (percentage points)", 0.1],
  ["observation.missing_probability", "Missing oxygenation probability", 0.05],
  [
    "documentation.interval_minutes",
    "FiO2 documentation interval (minutes)",
    1,
  ],
  [
    "documentation.missing_probability",
    "Missing FiO2 bundle probability",
    0.05,
  ],
  ["scoring.threshold_factor", "Threshold factor", 0.05],
];
export function formatMetric(value, unit) {
  if (value === null || value === undefined) return "U / not evaluable";
  const n = Number(value);
  if (!Number.isFinite(n)) return "Unavailable";
  if (unit === "probability")
    return `${(n * 100).toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
  if (unit === "probability_difference")
    return `${(n * 100).toLocaleString(undefined, { maximumFractionDigits: 2 })} percentage points`;
  if (unit === "records")
    return `${n.toLocaleString(undefined, { maximumFractionDigits: 2 })} records`;
  if (unit === "mmHg") return `${n.toFixed(2)} mmHg`;
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}
const metric = formatMetric;
function showError(error) {
  if (error?.cancelled) return;
  $("error").hidden = false;
  $("error").textContent = error.message || String(error);
}
function clearError() {
  $("error").hidden = true;
  $("error").textContent = "";
}
function meta() {
  return state.catalogue?.entries.find((e) => e.id === state.entry);
}
function conditions(result = state.result) {
  return [
    ...new Map(
      (result?.scores || []).map((r) => [
        r.condition_id,
        { id: r.condition_id, label: r.condition_label },
      ]),
    ).values(),
  ];
}
function changed() {
  state.version++;
  clearError();
  renderStatus();
}
function buttons() {
  const locked = !state.ready || state.busy;
  for (const id of [
    "entry",
    "stratum",
    "replicates",
    "expand",
    "reset",
    "outcome",
    "rule-run",
    "explain-run",
    "import-bundle",
  ])
    $(id).disabled = locked;
  for (const input of $("advanced-fields").querySelectorAll("input"))
    input.disabled =
      locked || input.dataset.controlled === "true" || state.imported;
  for (const input of $("conditions").querySelectorAll("input"))
    input.disabled = locked;
  $("run").disabled =
    locked || !state.allowed || state.entry === "rule_explorer";
  $("cancel").disabled = !state.busy;
  $("restart").disabled = state.busy;
  $("download-bundle").disabled = locked || !state.result;
  $("expand").disabled = locked || state.imported;
  $("reset").disabled = locked || state.entry === "rule_explorer";
}
function renderStatus() {
  if (!state.result) return;
  const stale = state.version !== state.resultVersion;
  const r = state.result;
  $("result-status").className = `result-status${stale ? " stale" : ""}`;
  $("result-status").textContent =
    `${stale ? "Stale — " : ""}${state.resultKind}; ${r.completed_patients} paired patients. Original results: ${r.request.experiment_id}. Comparator: ${r.request.comparator.label}.`;
  $("export-status").textContent = stale
    ? "Results are stale. The bundle retains the original immutable result request."
    : "The result bundle retains its immutable normalized request.";
  $("download-bundle").textContent = stale
    ? "Download original stale result bundle"
    : "Download result bundle";
  $("download-table").textContent = stale
    ? "Download original stale result CSV"
    : "Download original result CSV";
  $("result-request").textContent = JSON.stringify(r.request, null, 2);
}
function describe() {
  const m = meta();
  $("question").textContent = m?.title || "Imported custom experiment";
  $("mechanism").textContent =
    `Comparator: ${state.request?.comparator.label || ""}. Changed mechanism: ${m?.mechanism || "see immutable request"}.`;
  $("held-fixed").textContent =
    m?.held_fixed || "Imported conditions retain their recorded settings.";
  $("methods-description").textContent =
    m?.limitations ||
    "Uncalibrated synthetic experiment. Inspect the recorded request and evidence statuses.";
}
function renderAdvanced() {
  if (!state.request) return;
  const controlled = new Set();
  const m = meta();
  for (const c of [m?.comparator, ...(m?.conditions || [])])
    for (const [group, values] of Object.entries(c?.overrides || {}))
      for (const key of Object.keys(values)) controlled.add(`${group}.${key}`);
  $("advanced-fields").innerHTML =
    fields
      .map(([path, label, step]) => {
        const [group, key] = path.split(".");
        return `<label>${esc(label)}${controlled.has(path) ? " · varied by comparison" : ""}<input type="number" step="${step}" data-path="${path}" data-controlled="${controlled.has(path)}" value="${esc(state.request.base[group][key])}"></label>`;
      })
      .join("") +
    `<label>Seed<input type="number" min="0" step="1" data-seed value="${state.request.seed}"></label>`;
  $("replicates").value = state.request.replicates;
  $("outcome").value = state.request.primary_outcome;
  const chosen = new Set(state.request.conditions.map((c) => c.label));
  $("conditions").innerHTML = state.allConditions
    .map(
      (c, i) =>
        `<label><input type="checkbox" data-condition-index="${i}" ${chosen.has(c.label) ? "checked" : ""}>${esc(c.label)}</label>`,
    )
    .join("");
  buttons();
}
function view(name) {
  for (const section of ["experiment", "explain", "methods"])
    $(section + "-view").hidden = section !== name;
  for (const b of document.querySelectorAll("[data-view]"))
    b.setAttribute("aria-selected", String(b.dataset.view === name));
}
function call(type, payload = {}) {
  return new Promise((resolve, reject) => {
    const id = state.nextId++;
    state.pending.set(id, { resolve, reject, type });
    state.worker.postMessage({ id, type, payload: clone(payload) });
  });
}
async function startWorker() {
  state.generation++;
  const generation = state.generation;
  state.worker?.terminate();
  for (const p of state.pending.values())
    p.reject(
      Object.assign(new Error("Worker restarted; edited request preserved"), {
        cancelled: true,
      }),
    );
  state.pending.clear();
  state.ready = false;
  state.busy = false;
  buttons();
  $("runtime").textContent = "Starting Python; saved results remain available";
  state.worker = new Worker("pyodide_worker.js");
  state.worker.onmessage = ({ data }) => {
    if (generation !== state.generation) return;
    if (data.type === "status") {
      $("runtime").textContent = data.payload.message;
      return;
    }
    const pending = state.pending.get(data.id);
    if (!pending) return;
    if (data.type === "progress") {
      $("progress").hidden = false;
      $("progress").max = data.payload.requested_patients;
      $("progress").value = data.payload.completed_patients;
      $("progress-note").textContent =
        `${data.payload.completed_patients} completed / ${data.payload.attempted_patients} attempted patients; ${data.payload.completed_scoring_evaluations} scoring evaluations completed.`;
      return;
    }
    state.pending.delete(data.id);
    data.payload.ok
      ? pending.resolve(data.payload)
      : pending.reject(
          new Error(data.payload.error?.message || "Worker operation failed"),
        );
  };
  state.worker.onerror = (e) => {
    if (generation !== state.generation) return;
    state.ready = false;
    state.busy = false;
    for (const p of state.pending.values())
      p.reject(new Error(e.message || "Worker failed"));
    state.pending.clear();
    $("runtime").textContent =
      "Worker failed; restart preserves your edited request";
    showError(e);
    buttons();
  };
  try {
    await call("init");
    if (generation !== state.generation) return;
    state.ready = true;
    $("runtime").textContent = "Python ready";
    await updateWorkload();
    buttons();
  } catch (e) {
    showError(e);
  }
}
async function operation(fn) {
  if (state.busy) return;
  state.busy = true;
  buttons();
  clearError();
  const generation = state.generation;
  try {
    await fn();
  } catch (e) {
    showError(e);
  } finally {
    if (generation === state.generation) {
      state.busy = false;
      buttons();
    }
  }
}
async function expandBase(all = false) {
  const revision = state.version,
    selected = new Set(state.request.conditions.map((c) => c.label)),
    outcome = state.request.primary_outcome;
  const response = await call("catalogue", {
    entry_id: state.entry,
    stratum: state.stratum,
    replicates: state.request.replicates,
    seed: state.request.seed,
    base: state.request.base,
  });
  if (revision !== state.version) return;
  state.allConditions = clone(response.request.conditions);
  state.request = response.request;
  state.request.primary_outcome = outcome;
  if (!all)
    state.request.conditions = state.request.conditions.filter((c) =>
      selected.has(c.label),
    );
  state.needsExpansion = false;
  renderAdvanced();
  describe();
}
async function updateWorkload() {
  if (!state.ready || !state.request || state.entry === "rule_explorer") return;
  try {
    if (state.needsExpansion && !state.imported) await expandBase();
    const revision = state.version;
    const work = await call("workload", { request: state.request });
    if (revision !== state.version) return;
    state.allowed = work.preview_allowed;
    $("workload").textContent =
      `Workload: ${work.patients} patients · ${work.scoring_evaluations} scoring evaluations · ${work.latent_minutes.toLocaleString()} generated minutes · ${work.documented_events.toLocaleString()} documented records.${work.preview_allowed ? "" : " Preview limit exceeded; download the request and use the CLI."}`;
    buttons();
  } catch (e) {
    state.allowed = false;
    buttons();
    showError(e);
  }
}
async function loadPreset() {
  changed();
  state.entry = $("entry").value;
  state.stratum = $("stratum").value;
  const rule = state.entry === "rule_explorer";
  $("stochastic-results").hidden = rule;
  $("rule-panel").hidden = !rule;
  if (rule) {
    $("question").textContent = "Deterministic rule explorer";
    $("mechanism").textContent =
      "Evaluate specified oxygenation and support evidence without Monte Carlo sampling.";
    $("held-fixed").textContent =
      "Event-level rules are separate from encounter-level suppression.";
    $("workload").textContent =
      "Deterministic cells; no synthetic cohort is generated.";
    buttons();
    return;
  }
  await operation(async () => {
    const response = await call("catalogue", {
      entry_id: state.entry,
      stratum: state.stratum,
      replicates: 200,
    });
    state.request = response.request;
    state.allConditions = clone(state.request.conditions);
    state.imported = false;
    state.needsExpansion = false;
    renderAdvanced();
    describe();
    await updateWorkload();
  });
}
function table(headers, rows) {
  return `<table><thead><tr>${headers.map((h) => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}
function dotPlot(rows, title, unit, difference = false) {
  const bounds = rows
    .flatMap((r) => [r.estimate, r.lower, r.upper])
    .filter((v) => v !== null && v !== undefined);
  const extent = difference
    ? Math.max(0.01, ...bounds.map(Math.abs))
    : unit === "probability"
      ? 1
      : Math.max(1, ...bounds);
  const min = difference ? -extent : 0,
    max = extent,
    x = (v) => 190 + ((v - min) / (max - min)) * 210,
    height = rows.length * 38 + 45;
  const tick = (v) =>
    unit.startsWith("probability")
      ? `${(v * 100).toFixed(0)}${difference ? "" : "%"}`
      : v.toFixed(1);
  let svg = `<svg viewBox="0 0 530 ${height}" role="img" aria-label="${esc(title)}"><line x1="190" x2="400" y1="${height - 30}" y2="${height - 30}" stroke="#8499a2"/>`;
  if (difference)
    svg += `<line x1="${x(0)}" x2="${x(0)}" y1="8" y2="${height - 30}" stroke="#8499a2" stroke-dasharray="3 3"/>`;
  for (let i = 0; i <= 4; i++) {
    const v = min + ((max - min) * i) / 4;
    svg += `<text x="${x(v)}" y="${height - 10}" text-anchor="middle">${tick(v)}</text>`;
  }
  rows.forEach((r, i) => {
    const y = 22 + i * 38;
    svg += `<text x="2" y="${y + 4}">${esc(r.label)}</text>`;
    if (r.estimate !== null) {
      if (r.lower !== null && r.upper !== null)
        svg += `<line x1="${x(r.lower)}" x2="${x(r.upper)}" y1="${y}" y2="${y}" stroke="#286b7e" stroke-width="2"/>`;
      svg += `<circle cx="${x(r.estimate)}" cy="${y}" r="4" fill="#195f70"/><text x="414" y="${y + 4}">${esc(unit === "probability_difference" ? `${(r.estimate * 100).toFixed(1)} pp` : metric(r.estimate, unit))}</text>`;
    } else svg += `<text x="200" y="${y + 4}">U / not evaluable</text>`;
  });
  return `<figure><figcaption>${esc(title)}</figcaption>${svg}</svg></figure>`;
}
function matrixPlot(rows, title, unit, difference = false) {
  const bound = unit.startsWith("probability")
    ? 1
    : Math.max(1, ...rows.map((row) => Math.abs(row.estimate ?? 0)));
  const grid = new Map();
  for (const r of rows) {
    const config = r.config;
    grid.set(
      `${config.observation.baseline_exposure_minutes / 60}:${config.observation.baseline_interval_minutes}`,
      r,
    );
  }
  return `<figure><figcaption>${esc(title)}</figcaption><table><thead><tr><th>Baseline hours / interval</th><th>15 minutes</th><th>60 minutes</th></tr></thead><tbody>${[
    1, 6, 24,
  ]
    .map(
      (h) =>
        `<tr><th>${h} hours</th>${[15, 60]
          .map((m) => {
            const r = grid.get(`${h}:${m}`),
              v = r?.estimate;
            const endpoint =
              difference && v < 0 ? [163, 93, 36] : [25, 95, 112];
            const strength = Math.min(1, Math.abs(v ?? 0) / bound);
            const color =
              v === undefined || v === null
                ? "#eee"
                : `rgb(${endpoint.map((channel) => Math.round(255 + strength * (channel - 255))).join(",")})`;
            return `<td style="background:${color}">${esc(metric(v, unit))}</td>`;
          })
          .join("")}</tr>`,
    )
    .join(
      "",
    )}</tbody></table><p class="hint">Color scale: ${esc(metric(difference ? -bound : 0, unit))} to ${esc(metric(bound, unit))}. Zero is white; unavailable cells are gray and marked U. Exact estimates and intervals are in the table below.</p></figure>`;
}
function renderResults() {
  const r = state.result;
  if (!r) return;
  renderStatus();
  const metricName = r.request.primary_outcome,
    cs = conditions(r);
  const summaries = cs.map((c) => ({
    ...r.condition_summary.find(
      (x) => x.condition_id === c.id && x.metric === metricName,
    ),
    label: c.label,
    config: (c.label === r.request.comparator.label
      ? r.request.comparator
      : r.request.conditions.find((x) => x.label === c.label)
    )?.overrides,
  }));
  const paired = cs.map((c) => ({
    ...r.paired_contrasts.find(
      (x) => x.condition_id === c.id && x.metric === metricName,
    ),
    label: c.label,
    config: summaries.find((x) => x.label === c.label)?.config,
  }));
  const first =
    paired.find((x) => x.condition_id !== x.comparator_id) || paired[0];
  $("interval-note").textContent =
    summaries[0].unit === "records"
      ? "Mean/count estimates report empirical MCSE in the table; no confidence interval is asserted."
      : "95% pointwise Monte Carlo intervals are conditional on the model. Empty evidence is not normal oxygenation; inspect the U state below.";
  $("primary-result").textContent =
    `${names[metricName] || metricName}: ${first.label} changes by ${metric(first.estimate, first.unit)} versus ${r.request.comparator.label} (paired N=${first.denominator}).`;
  const plot = r.request.experiment_id.startsWith("E5_opportunity:")
    ? matrixPlot
    : dotPlot;
  $("outcome-plots").innerHTML =
    plot(
      summaries,
      `${names[metricName] || metricName} — absolute estimate`,
      summaries[0].unit,
    ) +
    plot(
      paired,
      paired[0].unit === "probability_difference"
        ? "Variant minus comparator — percentage points (pp)"
        : "Variant minus comparator — records",
      paired[0].unit,
      true,
    );
  const prior = $("transition-condition").value;
  $("transition-condition").innerHTML = cs
    .map((c) => `<option value="${esc(c.id)}">${esc(c.label)}</option>`)
    .join("");
  $("transition-condition").value = cs.some((c) => c.id === prior)
    ? prior
    : (cs.find((c) => c.id !== r.paired_contrasts[0].comparator_id) || cs[0])
        .id;
  renderTransitions();
  $("summary-table").innerHTML = table(
    [
      "Condition",
      "Metric",
      "Absolute estimate",
      "Paired difference",
      "Paired N",
      "MCSE",
      "Pointwise bounds",
    ],
    r.condition_summary.map((s) => {
      const p = r.paired_contrasts.find(
        (c) => c.condition_id === s.condition_id && c.metric === s.metric,
      );
      return [
        cs.find((c) => c.id === s.condition_id)?.label,
        s.metric,
        metric(s.estimate, s.unit),
        metric(p.estimate, p.unit),
        p.denominator,
        p.mcse ?? "Unavailable",
        `${metric(p.lower, p.unit)} to ${metric(p.upper, p.unit)}`,
      ];
    }),
  );
}
function renderTransitions() {
  if (!state.result) return;
  const id = $("transition-condition").value,
    kind = $("transition-table").value,
    cells = state.result.transitions.filter(
      (c) => c.condition_id === id && c.table === kind,
    ),
    states = [...new Set(cells.map((c) => c.comparator_state))];
  $("transitions").innerHTML =
    `<table><thead><tr><th>Comparator / variant</th>${states.map((s) => `<th>${esc(s)}</th>`).join("")}</tr></thead><tbody>${states
      .map(
        (a) =>
          `<tr><th>${esc(a)}</th>${states
            .map((b) => {
              const c = cells.find(
                (c) => c.comparator_state === a && c.variant_state === b,
              );
              return `<td><button ${c?.count ? "" : "disabled"} data-patient="${c?.patient_ids[0] ?? ""}" data-trace-condition="${id}" aria-label="${esc(a)} to ${esc(b)}: ${c?.count || 0} of ${c?.denominator || 0}">${c?.count || 0} / ${c?.denominator || 0}</button></td>`;
            })
            .join("")}</tr>`,
      )
      .join("")}</tbody></table>`;
}
function linePlot(series, title, min, max, xmin, xmax) {
  const x = (v) => 110 + ((v - xmin) / (xmax - xmin || 1)) * 720,
    y = (v) => 160 - ((v - min) / (max - min || 1)) * 130;
  let body = "";
  for (const [i, s] of series.entries()) {
    const points = s.points.filter(
      (p) => p[1] !== null && Number.isFinite(p[1]),
    );
    if (s.dots)
      body += points
        .map((p) => {
          const detail = p[2] || {},
            cx = x(p[0]),
            cy = y(p[1]);
          const title = `<title>${esc(s.name)}: ${p[1]} at minute ${p[0]}. ${esc(detail.reason || "")}</title>`;
          const marker = detail.excluded
            ? `<path class="excluded-point" d="M${cx - 4},${cy - 4}L${cx + 4},${cy + 4}M${cx - 4},${cy + 4}L${cx + 4},${cy - 4}" stroke="${s.color}">${title}</path>`
            : `<circle cx="${cx}" cy="${cy}" r="2.5" fill="${s.color}">${title}</circle>`;
          return (
            marker +
            (detail.selected
              ? `<circle class="determining-point" cx="${cx}" cy="${cy}" r="6" fill="none" stroke="#111">${title}</circle>`
              : "")
          );
        })
        .join("");
    else {
      const segments = [[]];
      for (const point of s.points) {
        if (point[1] === null || !Number.isFinite(point[1])) segments.push([]);
        else segments.at(-1).push(point);
      }
      for (const segment of segments.filter((p) => p.length))
        body += `<polyline points="${segment.map((p) => `${x(p[0])},${y(p[1])}`).join(" ")}" fill="none" stroke="${s.color}" stroke-width="1.5" ${i ? 'stroke-dasharray="4 2"' : ""}/>`;
    }
    body += `<text x="${60 + i * 260}" y="16">${esc(s.name)}</text>`;
  }
  for (let i = 0; i <= 4; i++) {
    const v = min + ((max - min) * i) / 4;
    body += `<text x="100" y="${y(v) + 4}" text-anchor="end">${v.toFixed(1)}</text>`;
  }
  for (let i = 0; i <= 4; i++) {
    const v = xmin + ((xmax - xmin) * i) / 4;
    body += `<text class="time-tick" x="${x(v)}" y="185" text-anchor="middle">${(v / 60).toFixed(1)}h</text>`;
  }
  return `<figure><figcaption>${esc(title)}</figcaption><svg viewBox="0 0 900 220" role="img" aria-label="${esc(title)}">${body}<text x="470" y="210" text-anchor="middle">Hours relative to admission</text></svg></figure>`;
}
function supportPlot(latent, xmin, xmax) {
  const labels = [
    "ROOM_AIR",
    "LOW_FLOW",
    "HFNC",
    "NIPPV",
    "IMV",
    "SURG IMV",
    "UNKNOWN",
  ];
  const x = (v) => 110 + ((v - xmin) / (xmax - xmin || 1)) * 720;
  let body = labels
    .map(
      (label, i) =>
        `<text x="100" y="${30 + i * 20}" text-anchor="end">${label}</text>`,
    )
    .join("");
  body += `<polyline points="${latent.map((p) => `${x(p.minute)},${26 + labels.indexOf(p.support_type) * 20}`).join(" ")}" fill="none" stroke="#195f70" stroke-width="2"/>`;
  for (let i = 0; i <= 4; i++) {
    const minute = xmin + ((xmax - xmin) * i) / 4;
    body += `<text class="time-tick" x="${x(minute)}" y="185" text-anchor="middle">${(minute / 60).toFixed(1)}h</text>`;
  }
  return `<figure><figcaption>Generated support trajectory — categorical, not a modeled treatment response</figcaption><svg viewBox="0 0 900 220" role="img" aria-label="Generated support trajectory">${body}<text x="470" y="210" text-anchor="middle">Hours relative to admission</text></svg></figure>`;
}
function renderTrace() {
  const t = state.trace;
  if (!t) return;
  const block = $("trace-block").value,
    latent = t.latent.filter((p) => p.block === block),
    events = t.scoring.events.filter((e) => e.block === block);
  const determining = new Set(t.scoring[block].tied_event_ids);
  $("trace-summary").textContent =
    `Saved score ${t.score.algorithm_score}; ${t.score.score_status}. Qualifying P/F count ${t.score.qualifying_pf_count}. Selected event ${t.score.selected_event_id ?? "none"}. Tied determining events: ${t.scoring.acute.tied_event_ids.length}.`;
  if (latent.length) {
    const lo = latent[0].minute,
      hi = latent.at(-1).minute;
    $("trace-plots").innerHTML =
      linePlot(
        [
          {
            name: "Latent SpO2 (%)",
            points: latent.map((p) => [p.minute, p.latent_spo2_pct]),
            color: "#195f70",
          },
          {
            name: "Observed SpO2 (%) · points",
            points: events.map((e) => [
              e.measurement_minute,
              e.spo2_obs,
              {
                excluded: Boolean(e.first_exclusion),
                selected: determining.has(e.event_id),
                reason:
                  e.exclusion_reasons.join(", ") ||
                  (determining.has(e.event_id)
                    ? "Determining event"
                    : "Eligible event"),
              },
            ]),
            dots: true,
            color: "#a35d24",
          },
        ],
        "Oxygenation (%): crosses mark excluded points; rings mark determining events, including ties",
        40,
        100,
        lo,
        hi,
      ) +
      linePlot(
        [
          {
            name: "Delivered FiO2 fraction",
            points: latent.map((p) => [p.minute, p.fio2_fraction]),
            color: "#195f70",
          },
          {
            name: "Documented / inferred fraction",
            points: events.map((e) => [e.measurement_minute, e.fio2_fraction]),
            dots: true,
            color: "#a35d24",
          },
        ],
        "FiO2 evidence (fraction); low-flow values are proxies",
        0.2,
        1,
        lo,
        hi,
      ) +
      linePlot(
        [
          {
            name: "Raw rubric",
            points: events.map((e) => [e.measurement_minute, e.raw_rubric]),
            color: "#a35d24",
          },
          {
            name: "Support-adjusted event score",
            points: events.map((e) => [
              e.measurement_minute,
              e.support_adjusted_score,
            ]),
            color: "#195f70",
          },
        ],
        "Scoring stages before encounter suppression",
        0,
        4,
        lo,
        hi,
      );
    $("trace-plots").innerHTML += supportPlot(latent, lo, hi);
    if (latent.some((p) => p.flow_lpm !== null)) {
      $("trace-plots").innerHTML += linePlot(
        [
          {
            name: "Generated flow (L/min)",
            points: latent.map((p) => [p.minute, p.flow_lpm]),
            color: "#195f70",
          },
        ],
        "Oxygen flow (L/min); inferred FiO2 remains a proxy",
        0,
        15,
        lo,
        hi,
      );
    }
  } else $("trace-plots").textContent = "No generated block available.";
  $("trace-events").innerHTML = table(
    [
      "Event",
      "Minute",
      "Support",
      "SpO2 (%)",
      "P/F (mmHg)",
      "Rubric",
      "Support-adjusted",
      "Detail cap",
      "Final support cap",
      "Exclusion / selection",
      "FiO2 source",
      "Source age (min)",
      "Suppressed",
    ],
    events.map((e) => [
      e.event_id,
      e.measurement_minute,
      e.support_type,
      e.spo2_obs ?? "U",
      e.pf_ratio_mmhg ?? "U",
      e.raw_rubric ?? "U",
      e.support_adjusted_score ?? "U",
      e.detail_support_capped,
      e.final_support_capped,
      e.first_exclusion ||
        (e.selected_acute
          ? "Selected acute"
          : e.selected_baseline
            ? "Selected baseline"
            : "Eligible / unselected"),
      e.fio2_source_event_id ?? "none",
      e.fio2_source_age_minutes ?? "U",
      e.singleton_suppressed,
    ]),
  );
  const sources = t.scoring.context_events.filter((e) => e.block === block);
  $("trace-sources").innerHTML = table(
    [
      "Source ID",
      "Measured minute",
      "Available minute",
      "Support",
      "Set FiO2 fraction",
      "Measured FiO2 fraction",
      "Flow (L/min)",
    ],
    sources.map((e) => [
      e.event_id,
      e.measurement_minute,
      e.available_minute,
      e.support_type,
      e.fio2_set_fraction ?? "U",
      e.fio2_meas_fraction ?? "U",
      e.flow_lpm ?? "U",
    ]),
  );
}
async function explain() {
  if (!state.result) return;
  await operation(async () => {
    await requireTraceBudget();
    const id = $("transition-condition").value,
      patient = Number($("patient").value),
      row = state.result.scores.find(
        (r) => r.patient_id === patient && r.condition_id === id,
      );
    if (!row)
      throw new Error("Select a patient and condition present in this result.");
    state.trace = await call("explain", {
      request: state.result.request,
      patient_id: patient,
      condition_id: id,
      expected_score: row,
    });
    $("trace-context").textContent =
      `Synthetic patient ${patient}; ${row.condition_label}. Reconstructed from the immutable ${state.resultKind.toLowerCase()} request.`;
    renderTrace();
    view("explain");
  });
}
async function requireTraceBudget() {
  const workload = await call("workload", {
    request: { ...clone(state.result.request), replicates: 1 },
  });
  if (!workload.preview_allowed)
    throw new Error(
      "This result needs a larger trace than the browser budget allows. Use the CLI to explain or export it.",
    );
}
function download(content, name, type = "application/json") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
for (const b of document.querySelectorAll("[data-view]"))
  b.onclick = () => view(b.dataset.view);
$("entry").onchange = loadPreset;
$("stratum").onchange = loadPreset;
$("reset").onclick = loadPreset;
$("replicates").oninput = () => {
  if (!state.request) return;
  state.request.replicates = Number($("replicates").value);
  changed();
};
$("replicates").onchange = updateWorkload;
$("outcome").onchange = () => {
  state.request.primary_outcome = $("outcome").value;
  changed();
};
$("advanced-fields").oninput = (e) => {
  if (!e.target.matches("input")) return;
  const value = Number(e.target.value);
  if (e.target.hasAttribute("data-seed")) state.request.seed = value;
  else {
    const [group, key] = e.target.dataset.path.split(".");
    state.request.base[group][key] = value;
    state.needsExpansion = true;
  }
  changed();
};
$("advanced-fields").onchange = updateWorkload;
$("conditions").onchange = () => {
  const selected = [...$("conditions").querySelectorAll("input:checked")].map(
    (e) => Number(e.dataset.conditionIndex),
  );
  state.request.conditions = selected.map((i) => clone(state.allConditions[i]));
  changed();
  updateWorkload();
};
$("expand").onclick = () =>
  operation(async () => {
    changed();
    await expandBase(true);
    await updateWorkload();
  });
$("run").onclick = () =>
  operation(async () => {
    if (state.needsExpansion) await expandBase();
    const request = clone(state.request),
      revision = state.version;
    $("progress").value = 0;
    $("progress").hidden = false;
    $("runtime").textContent = "Running paired preview";
    const result = await call("experiment", { request }).catch((error) => {
      if (state.ready && !error.cancelled)
        $("runtime").textContent = "Preview failed; prior result retained";
      throw error;
    });
    state.result = clone(result);
    state.resultVersion = revision;
    state.resultKind = "Completed preview";
    $("runtime").textContent = "Preview complete";
    renderResults();
  });
$("cancel").onclick = () => {
  $("progress-note").textContent +=
    " Cancelled; no completed result published.";
  startWorker();
};
$("restart").onclick = startWorker;
$("transition-condition").onchange = renderTransitions;
$("transition-table").onchange = renderTransitions;
$("transitions").onclick = (e) => {
  const b = e.target.closest("[data-patient]");
  if (!b || b.disabled) return;
  $("patient").value = b.dataset.patient;
  $("transition-condition").value = b.dataset.traceCondition;
  explain();
};
$("explain-run").onclick = explain;
$("trace-block").onchange = renderTrace;
$("download-request").onclick = () =>
  download(JSON.stringify(state.request, null, 2), "request.json");
$("download-table").onclick = () => {
  if (!state.result) return;
  const name = $("raw-table").value;
  const rows = state.result[name];
  const headers = [...new Set(rows.flatMap(Object.keys))];
  const cell = (value) => {
    const text =
      value === null || value === undefined
        ? ""
        : typeof value === "object"
          ? JSON.stringify(value)
          : String(value);
    return `"${text.replaceAll('"', '""')}"`;
  };
  const csv =
    [headers, ...rows.map((row) => headers.map((key) => row[key]))]
      .map((row) => row.map(cell).join(","))
      .join("\r\n") + "\r\n";
  download(
    csv,
    `${state.version === state.resultVersion ? "" : "stale-original-"}${name}.csv`,
    "text/csv",
  );
};
$("download-bundle").onclick = () =>
  operation(async () => {
    await requireTraceBudget();
    const exported = await call("export_bundle", { result: state.result });
    download(
      Uint8Array.from(atob(exported.archive_base64), (c) => c.charCodeAt(0)),
      state.version === state.resultVersion
        ? "synthetic-result.zip"
        : "stale-original-result.zip",
      "application/zip",
    );
  });
$("import-bundle").onchange = () =>
  operation(async () => {
    const file = $("import-bundle").files[0];
    if (!file) return;
    if (file.size > 64 * 1024 * 1024)
      throw new Error(
        "Bundle exceeds the 64 MiB browser import limit. Use the CLI to inspect it.",
      );
    const bytes = new Uint8Array(await file.arrayBuffer());
    let binary = "";
    for (let i = 0; i < bytes.length; i += 32768)
      binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
    const imported = await call("import_bundle", {
      archive_base64: btoa(binary),
    });
    state.request = clone(imported.request);
    state.result = clone(imported);
    state.allConditions = clone(state.request.conditions);
    state.version++;
    state.resultVersion = state.version;
    state.resultKind = "Imported synthetic bundle";
    state.imported = true;
    state.needsExpansion = false;
    [state.entry, state.stratum] = state.request.experiment_id.split(":");
    if (!meta()) {
      state.entry = "custom";
      if (!$("entry").querySelector("[value=custom]"))
        $("entry").add(new Option("Imported custom request", "custom"));
    }
    $("entry").value = state.entry;
    $("stratum").value = state.stratum || "room_air";
    $("stochastic-results").hidden = false;
    $("rule-panel").hidden = true;
    renderAdvanced();
    describe();
    renderResults();
    await updateWorkload();
  });
function ruleSupport() {
  const label = $("rule-support").value;
  return {
    label,
    fio2_fraction: ["ROOM_AIR", "LOW_FLOW", "UNKNOWN"].includes(label)
      ? null
      : Number($("rule-fio2").value),
    flow_lpm: label === "LOW_FLOW" ? Number($("rule-flow").value) : null,
  };
}
$("rule-support").onchange = () => {
  $("rule-fio2").disabled = ["ROOM_AIR", "LOW_FLOW", "UNKNOWN"].includes(
    $("rule-support").value,
  );
  $("rule-flow").disabled = $("rule-support").value !== "LOW_FLOW";
};
$("rule-support").onchange();
$("rule-source").onchange = () => {
  $("rule-values").value =
    $("rule-source").value === "spo2" ? "49,50,90,96,97" : "100,200,300,400";
};
$("rule-run").onclick = () =>
  operation(async () => {
    if (!$("rule-values").value.trim())
      throw new Error("Enter at least one oxygenation value.");
    const result = await call("rule_explorer", {
      source: $("rule-source").value,
      values: $("rule-values")
        .value.split(",")
        .map((v) => Number(v.trim())),
      supports: [ruleSupport()],
      scoring: { threshold_factor: Number($("rule-factor").value) },
      records: Number($("rule-records").value),
    });
    $("rule-caption").textContent = result.caption;
    $("rule-output").innerHTML = table(
      [
        `Input (${result.input_unit})`,
        "Estimated PaO2 (mmHg)",
        "P/F (mmHg)",
        "Raw rubric",
        "Support-adjusted",
        "Encounter score",
        "Status",
      ],
      result.cells.map((c) => [
        c.input_value,
        c.pao2_calc_mmhg ??
          (c.conversion_unavailable
            ? "Conversion unavailable"
            : "Not used: measured source"),
        c.pf_ratio_mmhg ?? "U",
        c.raw_rubric ?? "U",
        c.event_trace.support_adjusted_score ?? "U",
        c.encounter.algorithm_score,
        c.encounter.score_status,
      ]),
    );
  });
async function boot() {
  try {
    const response = await fetch("assets/data/saved_experiment_v2.json");
    if (!response.ok) throw new Error("Saved example could not be loaded");
    const saved = await response.json();
    state.catalogue = saved.catalogue;
    state.result = saved.result;
    state.request = clone(saved.result.request);
    state.allConditions = clone(state.request.conditions);
    $("entry").innerHTML =
      state.catalogue.entries
        .map((e) => `<option value="${e.id}">${esc(e.title)}</option>`)
        .join("") +
      '<option value="rule_explorer">Deterministic rule explorer</option>';
    $("entry").value = state.entry;
    renderAdvanced();
    describe();
    renderResults();
    await startWorker();
  } catch (e) {
    showError(e);
    $("runtime").textContent = "Startup failed; see diagnostics";
  }
}
boot();
