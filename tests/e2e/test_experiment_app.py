from __future__ import annotations

import csv
import functools
import http.server
import io
import json
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def investigation_server():
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT / "web"),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


def test_saved_example_precedes_python_and_new_run_trace_and_bundle(
    page: Page, investigation_server
):
    page.set_viewport_size({"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(investigation_server, wait_until="domcontentloaded")
    expect(page.locator("#result-status")).to_contain_text("Saved synthetic example", timeout=15000)
    expect(page.locator("#outcome-plots figure")).to_have_count(2)
    path = ROOT / "artifacts/local/acceptance/screenshots"
    path.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path / "investigation_desktop.png"), full_page=True)
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    page.locator("#replicates").fill("3")
    page.locator("#replicates").press("Tab")
    expect(page.locator("#result-status")).to_contain_text("Stale")
    page.locator("#run").click()
    expect(page.locator("#result-status")).to_contain_text(
        "Completed preview; 3 paired patients", timeout=120000
    )
    expect(page.locator("#progress-note")).to_contain_text("3 completed / 3 attempted")
    page.locator("#transitions button:not([disabled])").first.click()
    expect(page.locator("#trace-summary")).to_contain_text("Saved score", timeout=120000)
    expect(page.locator("#trace-plots figure")).to_have_count(4)
    assert page.locator("#trace-plots .determining-point").count() >= 1
    expect(page.locator("#trace-sources")).to_contain_text("fio2:")
    expect(page.locator("#trace-events")).to_contain_text("Final support cap")
    ticks = page.locator("#trace-plots svg").evaluate_all(
        "nodes=>nodes.map(n=>[...n.querySelectorAll('.time-tick')].map(t=>t.getAttribute('x')))"
    )
    assert all(axis == ticks[0] for axis in ticks)
    page.screenshot(path=str(path / "investigation_trace.png"), full_page=True)
    page.locator("#trace-plots").screenshot(path=str(path / "investigation_trace_panels.png"))
    page.get_by_role("button", name="Methods and export", exact=True).click()
    with page.expect_download() as download:
        page.locator("#download-bundle").click()
    archive = path / "browser_result.zip"
    download.value.save_as(archive)
    page.locator("#import-bundle").set_input_files(archive)
    expect(page.locator("#result-status")).to_contain_text(
        "Imported synthetic bundle", timeout=120000
    )
    page.get_by_role("button", name="Experiment", exact=True).click()
    assert not errors


def test_saved_example_is_available_without_starting_python(page: Page, investigation_server):
    page.route(
        "**/pyodide_worker.js",
        lambda route: route.fulfill(
            body="self.onmessage=()=>{};", content_type="application/javascript"
        ),
    )
    page.goto(investigation_server)
    expect(page.locator("#result-status")).to_contain_text("Saved synthetic example")
    expect(page.locator("#outcome-plots figure")).to_have_count(2)
    expect(page.locator("#run")).to_be_disabled()
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(
        path=str(ROOT / "artifacts/local/acceptance/screenshots/investigation_mobile.png"),
        full_page=True,
    )


def test_edited_base_stale_export_and_rule_explorer(page: Page, investigation_server):
    page.goto(investigation_server)
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    page.get_by_text("Advanced scenario and comparison settings", exact=True).click()
    page.locator('[data-path="generator.mean_pct"]').fill("87")
    page.locator("#expand").click()
    expect(page.locator('[data-path="generator.mean_pct"]')).to_have_value("87")
    page.get_by_role("button", name="Methods and export", exact=True).click()
    with page.expect_download() as download:
        page.locator("#download-request").click()
    current = json.loads(Path(download.value.path()).read_text())
    assert current["base"]["generator"]["mean_pct"] == 87
    assert current["comparator"]["overrides"]["generator"]["mean_pct"] == 87
    assert all(c["overrides"]["generator"]["mean_pct"] == 87 for c in current["conditions"])
    # The stale original result remains bound to the original saved request.
    page.get_by_text("Immutable result request", exact=True).click()
    assert (
        json.loads(page.locator("#result-request").inner_text())["base"]["generator"]["mean_pct"]
        == 94
    )
    expect(page.locator("#download-bundle")).to_have_text("Download original stale result bundle")
    with page.expect_download() as raw_download:
        page.locator("#download-table").click()
    assert raw_download.value.suggested_filename == "stale-original-condition_summary.csv"
    raw = list(csv.DictReader(io.StringIO(Path(raw_download.value.path()).read_text())))
    saved = json.loads((ROOT / "artifacts/saved_experiment_v2.json").read_text())["result"]
    assert {row["experiment_run_id"] for row in raw} == {saved["experiment_run_id"]}
    assert len(raw) == len(saved["condition_summary"])
    for actual, expected in zip(raw, saved["condition_summary"], strict=True):
        assert actual["metric"] == expected["metric"]
        assert (float(actual["estimate"]) if actual["estimate"] else None) == expected["estimate"]
    page.get_by_role("button", name="Experiment", exact=True).click()
    page.locator("#entry").select_option("rule_explorer")
    page.locator("#rule-run").click()
    expect(page.locator("#rule-output")).to_contain_text("Conversion unavailable", timeout=120000)
    expect(page.locator("#rule-output")).to_contain_text("390")
    page.locator("#rule-source").select_option("measured_pao2")
    page.locator("#rule-support").select_option("IMV")
    page.locator("#rule-fio2").fill("1")
    page.locator("#rule-run").click()
    expect(page.locator("#rule-output")).to_contain_text(
        "Not used: measured source", timeout=120000
    )


def test_cancel_preserves_edited_request_and_reinitializes(page: Page, investigation_server):
    page.goto(investigation_server)
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    page.get_by_text("Advanced scenario and comparison settings", exact=True).click()
    page.locator('[data-path="generator.mean_pct"]').fill("88")
    page.locator("#expand").click()
    expect(page.locator("#run")).to_be_enabled()
    page.locator("#run").click()
    expect(page.locator("#progress-note")).to_contain_text("attempted", timeout=120000)
    page.locator("#cancel").click()
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    expect(page.locator('[data-path="generator.mean_pct"]')).to_have_value("88")
    expect(page.locator("#result-status")).to_contain_text("Stale")
    expect(page.locator("#result-status")).to_contain_text("Saved synthetic example")


def test_metric_units_are_declared_not_guessed(page: Page, investigation_server):
    page.route(
        "**/pyodide_worker.js",
        lambda route: route.fulfill(
            body="self.onmessage=()=>{};", content_type="application/javascript"
        ),
    )
    page.goto(investigation_server)
    values = page.evaluate(
        """async()=>{
          const {formatMetric}=await import('/assets/js/investigation.js');
          return [formatMetric(.5,'probability'),formatMetric(.5,'records'),
            formatMetric(-.02,'probability_difference'),formatMetric(null,'probability')];
        }"""
    )
    assert values == ["50%", "0.5 records", "-2 percentage points", "U / not evaluable"]


def test_low_flow_trace_keeps_flow_and_fraction_separate(page: Page, investigation_server):
    page.goto(investigation_server)
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    page.locator("#entry").select_option("E1_episode")
    page.locator("#stratum").select_option("low_flow")
    expect(page.locator("#replicates")).to_have_value("1")
    page.locator("#run").click()
    expect(page.locator("#result-status")).to_contain_text(
        "Completed preview; 1 paired patients", timeout=120000
    )
    page.locator("#transitions button:not([disabled])").first.click()
    expect(page.locator("#trace-summary")).to_contain_text("Saved score", timeout=120000)
    expect(page.locator("#trace-plots figure")).to_have_count(5)
    expect(page.locator("#trace-plots")).to_contain_text("Oxygen flow (L/min)")
    expect(page.locator("#trace-plots")).to_contain_text("FiO2 evidence (fraction)")
    expect(page.locator("#trace-sources")).to_contain_text("LOW_FLOW")
    ticks = page.locator("#trace-plots svg").evaluate_all(
        "nodes=>nodes.map(n=>[...n.querySelectorAll('.time-tick')].map(t=>t.getAttribute('x')))"
    )
    assert all(axis == ticks[0] for axis in ticks)


def test_oversized_preview_is_blocked_and_can_be_reduced(page: Page, investigation_server):
    page.goto(investigation_server)
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    page.locator("#replicates").fill("201")
    page.locator("#replicates").press("Tab")
    expect(page.locator("#workload")).to_contain_text("Preview limit exceeded")
    expect(page.locator("#run")).to_be_disabled()
    expect(page.locator("#result-status")).to_contain_text("Saved synthetic example")
    page.locator("#replicates").fill("3")
    page.locator("#replicates").press("Tab")
    expect(page.locator("#workload")).not_to_contain_text("Preview limit exceeded")
    expect(page.locator("#run")).to_be_enabled()


def test_worker_crash_preserves_request_and_prior_result(page: Page, investigation_server):
    delivered = 0

    def worker(route):
        nonlocal delivered
        response = route.fetch()
        body = response.text()
        if delivered == 0:
            body += """
            const originalHandler = self.onmessage;
            self.onmessage = event => {
              if (event.data.type === 'experiment') throw new Error('Injected worker crash');
              originalHandler(event);
            };
            """
        delivered += 1
        route.fulfill(response=response, body=body)

    page.route("**/pyodide_worker.js", worker)
    page.goto(investigation_server)
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    page.locator("#replicates").fill("3")
    page.locator("#replicates").press("Tab")
    page.locator("#run").click()
    expect(page.locator("#runtime")).to_contain_text("Worker failed", timeout=120000)
    expect(page.locator("#error")).to_contain_text("Injected worker crash")
    expect(page.locator("#result-status")).to_contain_text("Saved synthetic example")
    expect(page.locator("#result-status")).to_contain_text("Stale")
    page.locator("#restart").click()
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    expect(page.locator("#replicates")).to_have_value("3")
    page.locator("#run").click()
    expect(page.locator("#result-status")).to_contain_text(
        "Completed preview; 3 paired patients", timeout=120000
    )
    assert delivered == 2


def test_oversized_import_is_rejected_before_reading_file(page: Page, investigation_server):
    page.goto(investigation_server)
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    page.get_by_role("button", name="Methods and export", exact=True).click()
    page.evaluate("""() => {
      const file = new File(['x'], 'oversized.zip');
      Object.defineProperty(file, 'size', {value: 64 * 1024 * 1024 + 1});
      file.arrayBuffer = () => {throw new Error('File must not be read');};
      const transfer = new DataTransfer(); transfer.items.add(file);
      const input = document.querySelector('#import-bundle');
      input.files = transfer.files; input.dispatchEvent(new Event('change', {bubbles: true}));
    }""")
    expect(page.locator("#error")).to_contain_text("64 MiB browser import limit")
    expect(page.locator("#result-status")).to_contain_text("Saved synthetic example")


def test_structured_run_failure_is_not_left_labeled_running(page: Page, investigation_server):
    def worker(route):
        response = route.fetch()
        route.fulfill(
            response=response,
            body=response.text()
            + """
          const handler = self.onmessage;
          self.onmessage = event => {
            if (event.data.type === 'experiment') {
              self.postMessage({id: event.data.id, type: 'result', payload: {
                ok: false, error: {message: 'Injected structured failure'}}});
            } else handler(event);
          };
        """,
        )

    page.route("**/pyodide_worker.js", worker)
    page.goto(investigation_server)
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    page.locator("#run").click()
    expect(page.locator("#error")).to_contain_text("Injected structured failure")
    expect(page.locator("#runtime")).to_have_text("Preview failed; prior result retained")
    expect(page.locator("#result-status")).to_contain_text("Saved synthetic example")
    expect(page.locator("#run")).to_be_enabled()


def test_every_advanced_control_reaches_the_resolved_request(page: Page, investigation_server):
    page.goto(investigation_server)
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    page.locator("#entry").select_option("E6_rules")
    page.get_by_text("Advanced scenario and comparison settings", exact=True).click()
    edits = {
        "generator.mean_pct": 92,
        "generator.marginal_sd_pct": 2,
        "generator.tau_minutes": 45,
        "generator.episode_rate_per_hour": 0.2,
        "generator.episode_depth_pct_points": 4,
        "generator.episode_duration_minutes": 25,
        "observation.interval_minutes": 10,
        "observation.noise_sd_pct": 0.3,
        "observation.bias_pct_points": 1,
        "observation.missing_probability": 0.1,
        "documentation.interval_minutes": 20,
        "documentation.missing_probability": 0.15,
        "scoring.threshold_factor": 0.9,
    }
    controls = page.locator("#advanced-fields [data-path]").evaluate_all(
        "nodes => nodes.map(n => n.dataset.path)"
    )
    assert set(controls) == set(edits)
    for path, value in edits.items():
        page.locator(f'[data-path="{path}"]').fill(str(value))
    page.locator("[data-seed]").fill("54321")
    page.locator("#expand").click()
    expect(page.locator("#expand")).to_be_enabled()
    page.get_by_role("button", name="Methods and export", exact=True).click()
    with page.expect_download() as download:
        page.locator("#download-request").click()
    request = json.loads(Path(download.value.path()).read_text())
    assert request["seed"] == 54321
    for config in [
        request["base"],
        request["comparator"]["overrides"],
        *(c["overrides"] for c in request["conditions"]),
    ]:
        for path, value in edits.items():
            group, key = path.split(".")
            assert config[group][key] == value, path


def test_baseline_matrix_uses_signed_scale_and_white_zero(page: Page, investigation_server):
    page.goto(investigation_server)
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    page.locator("#entry").select_option("E5_opportunity")
    page.locator("#replicates").fill("3")
    page.locator("#replicates").press("Tab")
    page.locator("#run").click()
    expect(page.locator("#result-status")).to_contain_text(
        "Completed preview; 3 paired patients", timeout=120000
    )
    matrix = page.locator("#outcome-plots figure").nth(1)
    expect(matrix.locator("tbody td")).to_have_count(6)
    expect(matrix).to_contain_text("-100 percentage points to 100 percentage points")
    zeros = matrix.locator("td").filter(has_text="0 percentage points")
    assert zeros.count() >= 1
    for cell in zeros.all():
        if cell.inner_text() == "0 percentage points":
            expect(cell).to_have_css("background-color", "rgb(255, 255, 255)")


def test_historical_criterion_c_view_trace_and_export(page: Page, investigation_server):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(investigation_server)
    expect(page.locator("#runtime")).to_have_text("Python ready", timeout=120000)
    page.locator("#entry").select_option("H_missing_historical")
    page.locator("#replicates").fill("3")
    page.locator("#replicates").press("Tab")
    page.locator("#run").click()
    expect(page.locator("#result-status")).to_contain_text(
        "Completed preview; 3 paired patients", timeout=120000
    )
    expect(page.locator("#profile-qualification")).to_contain_text("not execution-validated")
    expect(page.locator("#common-pair-table")).to_contain_text("Common")
    before = page.locator("#result-request").text_content()
    progress = page.locator("#progress-note").text_content()
    page.locator("#c-view").select_option("ge2")
    expect(page.locator("#eligibility-result")).to_contain_text("100% → 100%")
    assert page.locator("#result-request").text_content() == before
    assert page.locator("#progress-note").text_content() == progress
    expect(page.locator("#result-status")).not_to_contain_text("Stale")
    page.locator("#transitions button:not([disabled])").first.click()
    expect(page.locator("#trace-summary")).to_contain_text("Saved score", timeout=120000)
    expect(page.locator("#trace-events")).to_contain_text("Resolved partition")
    expect(page.locator("#trace-opportunity")).to_contain_text("Scheduled")
    path = ROOT / "artifacts/local/acceptance/screenshots"
    path.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path / "historical_desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(path / "historical_mobile.png"), full_page=True)
    page.get_by_role("button", name="Methods and export", exact=True).click()
    with page.expect_download() as download:
        page.locator("#download-bundle").click()
    archive = path / "historical_browser_result.zip"
    download.value.save_as(archive)
    page.locator("#import-bundle").set_input_files(archive)
    expect(page.locator("#result-status")).to_contain_text(
        "Imported synthetic bundle", timeout=120000
    )
    assert (
        json.loads(page.locator("#result-request").text_content())["schema_version"]
        == "experiment_request_v3"
    )
    assert not errors
