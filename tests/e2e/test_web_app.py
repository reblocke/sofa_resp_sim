from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from sofa_resp_sim.browser_contract import (
    get_app_config_payload,
    run_scenario_payload,
    run_sweep_payload,
)

ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "web"


@pytest.fixture(scope="session")
def web_server() -> Iterator[str]:
    port = _free_port()
    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--directory", str(WEB_ROOT)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_server(base_url)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def test_static_app_runs_scenario_and_sweep(page: Page, web_server: str) -> None:
    browser_errors: list[str] = []
    page.on("pageerror", lambda exc: browser_errors.append(str(exc)))
    page.on(
        "console",
        lambda msg: browser_errors.append(msg.text) if msg.type == "error" else None,
    )

    page.goto(web_server, wait_until="domcontentloaded")
    expect(page.get_by_test_id("runtime-status")).to_contain_text("ready", timeout=120_000)

    page.locator("#scenario-n-reps").fill("5")
    page.locator("#scenario-bootstrap").fill("10")
    page.get_by_test_id("run-scenario").click()
    expect(page.get_by_test_id("runtime-status")).to_contain_text(
        "Scenario complete",
        timeout=120_000,
    )
    expect(page.locator("#scenario-chart .probability-row")).to_have_count(5)
    expect(page.locator("#uncertainty-table tbody tr")).to_have_count(5)
    with page.expect_download() as scenario_download:
        page.locator("#download-scenario-csv").click()
    assert scenario_download.value.suggested_filename == "sofa_resp_scenario_summary.csv"

    page.get_by_role("button", name="Sweep").click()
    page.locator("#sweep-n-reps").fill("2")
    page.locator("#sweep-obs-values").fill("15, 60")
    page.locator("#sweep-noise-values").fill("0.5")
    page.locator("#sweep-room-values").fill("92")
    page.get_by_test_id("run-sweep").click()
    expect(page.get_by_test_id("runtime-status")).to_contain_text(
        "Sweep complete",
        timeout=120_000,
    )
    expect(page.locator("#sweep-heatmap .heat-cell")).to_have_count(2)
    expect(page.locator("#sweep-table tbody tr")).to_have_count(2)
    with page.expect_download() as sweep_download:
        page.locator("#download-sweep-summary").click()
    assert sweep_download.value.suggested_filename == "sofa_resp_sweep_summary.csv"

    assert browser_errors == []


def test_input_help_tooltips_are_accessible(page: Page, web_server: str) -> None:
    page.goto(web_server, wait_until="domcontentloaded")

    expected_help_ids = [
        "scenario-preset",
        "scenario-n-reps",
        "scenario-seed",
        "scenario-obs-freq",
        "scenario-room-air",
        "scenario-spo2-mean",
        "scenario-spo2-sd",
        "scenario-ar1",
        "scenario-measurement-sd",
        "scenario-rounding",
        "scenario-desat-prob",
        "scenario-desat-depth",
        "scenario-desat-duration",
        "scenario-fio2-prob",
        "scenario-altitude",
        "scenario-flow-min",
        "scenario-flow-max",
        "scenario-support-observed",
        "scenario-acute-start",
        "scenario-acute-end",
        "scenario-include-baseline",
        "scenario-baseline-days",
        "scenario-baseline-hours",
        "scenario-bootstrap",
        "scenario-ci-level",
        "sweep-preset",
        "sweep-n-reps",
        "sweep-seed",
        "sweep-obs-values",
        "sweep-noise-values",
        "sweep-room-values",
        "sweep-metric",
    ]

    expect(page.get_by_text("What this app does")).to_be_visible()
    expect(page.locator(".help-button")).to_have_count(len(expected_help_ids))
    for help_id in expected_help_ids:
        assert page.get_by_test_id(f"help-{help_id}").count() == 1

    scenario_help = page.get_by_test_id("help-scenario-n-reps")
    scenario_tooltip = page.locator("#tooltip-scenario-n-reps")
    expect(scenario_help).to_be_visible()

    scenario_help.hover()
    expect(scenario_tooltip).to_be_visible()
    expect(scenario_tooltip).to_contain_text("Number of simulated encounters")

    page.keyboard.press("Escape")
    expect(scenario_tooltip).to_be_hidden()

    scenario_help.focus()
    expect(scenario_tooltip).to_be_visible()
    page.keyboard.press("Escape")
    expect(scenario_tooltip).to_be_hidden()

    page.get_by_role("button", name="Sweep").click()
    sweep_help = page.get_by_test_id("help-sweep-obs-values")
    sweep_tooltip = page.locator("#tooltip-sweep-obs-values")

    sweep_help.click()
    expect(sweep_tooltip).to_be_visible()
    expect(sweep_tooltip).to_contain_text("Comma-separated observation intervals")


def test_run_buttons_show_in_place_busy_state(page: Page, web_server: str) -> None:
    config_payload = get_app_config_payload()
    scenario_payload = run_scenario_payload(
        {
            "request": {
                **config_payload["defaults"],
                "n_reps": 5,
                "seed": 0,
            },
            "n_bootstrap": 10,
            "ci_level": 0.9,
            "uncertainty_seed": 0,
        }
    )
    sweep_payload = run_sweep_payload(
        {
            "base_request": {
                **config_payload["defaults"],
                "n_reps": 2,
                "seed": 0,
            },
            "obs_freq_minutes_values": [15, 60],
            "noise_sd_values": [0.5],
            "room_air_threshold_values": [92.0],
            "heatmap_metric": "p_sofa_3plus",
        }
    )

    worker_script = f"""
const configPayload = {json.dumps(config_payload)};
const scenarioPayload = {json.dumps(scenario_payload)};
const sweepPayload = {json.dumps(sweep_payload)};
self.onmessage = (event) => {{
  const {{ id, type }} = event.data || {{}};
  if (type === "init") {{
    self.postMessage({{ id, type, payload: configPayload }});
    return;
  }}
  if (type === "scenario") {{
    setTimeout(() => {{
      self.postMessage({{ id, type, payload: scenarioPayload }});
    }}, 250);
    return;
  }}
  if (type === "sweep") {{
    setTimeout(() => {{
      self.postMessage({{ id, type, payload: sweepPayload }});
    }}, 250);
  }}
}};
"""

    page.route(
        "**/pyodide_worker.js",
        lambda route: route.fulfill(
            status=200,
            content_type="application/javascript",
            body=worker_script,
        ),
    )

    page.goto(web_server, wait_until="domcontentloaded")
    expect(page.get_by_test_id("runtime-status")).to_contain_text("ready", timeout=10_000)

    run_scenario = page.get_by_test_id("run-scenario")
    run_sweep = page.get_by_test_id("run-sweep")
    scenario_note = page.get_by_test_id("scenario-run-status")
    sweep_note = page.get_by_test_id("sweep-run-status")

    run_scenario.click()
    expect(run_scenario).to_have_text("Running scenario...")
    expect(run_scenario).to_have_attribute("aria-busy", "true")
    expect(run_sweep).to_have_text("Scenario running...")
    expect(run_sweep).to_be_disabled()
    expect(scenario_note).to_contain_text("Scenario simulation in progress")

    page.get_by_role("button", name="Sweep").click()
    expect(sweep_note).to_contain_text("Scenario simulation is running in the other pane")
    expect(page.get_by_test_id("runtime-status")).to_contain_text(
        "Scenario complete",
        timeout=10_000,
    )
    expect(run_scenario).to_have_text("Run scenario")
    expect(run_scenario).to_be_enabled()
    expect(run_sweep).to_have_text("Run sweep")
    expect(scenario_note).to_be_hidden()
    expect(sweep_note).to_be_hidden()

    run_sweep.click()
    expect(run_sweep).to_have_text("Running sweep...")
    expect(run_sweep).to_have_attribute("aria-busy", "true")
    expect(run_scenario).to_have_text("Sweep running...")

    page.get_by_role("button", name="Scenario").click()
    expect(scenario_note).to_contain_text("Sweep simulation is running in the other pane")
    expect(page.get_by_test_id("runtime-status")).to_contain_text(
        "Sweep complete",
        timeout=10_000,
    )
    expect(run_scenario).to_have_text("Run scenario")
    expect(run_sweep).to_have_text("Run sweep")
    expect(scenario_note).to_be_hidden()
    expect(sweep_note).to_be_hidden()


def test_cancel_keeps_buttons_disabled_during_worker_reinitialization(
    page: Page,
    web_server: str,
) -> None:
    config_payload = get_app_config_payload()
    scenario_payload = run_scenario_payload(
        {
            "request": {
                **config_payload["defaults"],
                "n_reps": 5,
                "seed": 0,
            },
            "n_bootstrap": 10,
            "ci_level": 0.9,
            "uncertainty_seed": 0,
        }
    )
    sweep_payload = run_sweep_payload(
        {
            "base_request": {
                **config_payload["defaults"],
                "n_reps": 2,
                "seed": 0,
            },
            "obs_freq_minutes_values": [15, 60],
            "noise_sd_values": [0.5],
            "room_air_threshold_values": [92.0],
            "heatmap_metric": "p_sofa_3plus",
        }
    )
    worker_script = f"""
const configPayload = {json.dumps(config_payload)};
const scenarioPayload = {json.dumps(scenario_payload)};
const sweepPayload = {json.dumps(sweep_payload)};
self.onmessage = (event) => {{
  const {{ id, type }} = event.data || {{}};
  if (type === "init") {{
    self.postMessage({{ type: "status", payload: {{ message: "Mock init pending" }} }});
    setTimeout(() => {{
      self.postMessage({{ id, type, payload: configPayload }});
    }}, 500);
    return;
  }}
  if (type === "scenario") {{
    setTimeout(() => {{
      self.postMessage({{ id, type, payload: scenarioPayload }});
    }}, 1000);
    return;
  }}
  if (type === "sweep") {{
    setTimeout(() => {{
      self.postMessage({{ id, type, payload: sweepPayload }});
    }}, 1000);
  }}
}};
"""

    page.route(
        "**/pyodide_worker.js",
        lambda route: route.fulfill(
            status=200,
            content_type="application/javascript",
            body=worker_script,
        ),
    )

    page.goto(web_server, wait_until="domcontentloaded")
    runtime_status = page.get_by_test_id("runtime-status")
    run_scenario = page.get_by_test_id("run-scenario")
    run_sweep = page.get_by_test_id("run-sweep")
    toast = page.locator("#toast")

    expect(runtime_status).to_contain_text("ready", timeout=10_000)

    run_scenario.click()
    expect(run_scenario).to_have_text("Running scenario...")
    page.locator("#cancel-scenario").click()
    expect(runtime_status).to_contain_text("Mock init pending")
    expect(run_scenario).to_be_disabled()
    expect(run_sweep).to_be_disabled()
    expect(runtime_status).not_to_contain_text("Worker reset")
    expect(toast).not_to_contain_text("Worker reset")
    expect(runtime_status).to_contain_text("ready", timeout=10_000)
    expect(run_scenario).to_be_enabled()
    expect(run_sweep).to_be_enabled()

    page.get_by_role("button", name="Sweep").click()
    run_sweep.click()
    expect(run_sweep).to_have_text("Running sweep...")
    page.locator("#cancel-sweep").click()
    expect(runtime_status).to_contain_text("Mock init pending")
    expect(run_scenario).to_be_disabled()
    expect(run_sweep).to_be_disabled()
    expect(runtime_status).not_to_contain_text("Worker reset")
    expect(toast).not_to_contain_text("Worker reset")
    expect(runtime_status).to_contain_text("ready", timeout=10_000)
    expect(run_scenario).to_be_enabled()
    expect(run_sweep).to_be_enabled()


def test_mode_guidance_and_tab_values_persist_in_session(page: Page, web_server: str) -> None:
    page.goto(web_server, wait_until="domcontentloaded")

    expect(page.get_by_text("Scenario vs Sweep")).to_be_visible()
    expect(page.get_by_text("Use Scenario to test one parameter set")).to_be_visible()
    expect(page.get_by_text("Switching panes keeps values in place")).to_be_visible()

    page.locator("#scenario-n-reps").fill("7")
    page.get_by_role("button", name="Sweep").click()

    expect(page.get_by_text("conclusions are robust to charting frequency")).to_be_visible()
    expect(page.get_by_text("not necessarily better or worse performance")).to_be_visible()
    page.locator("#sweep-n-reps").fill("3")
    page.locator("#sweep-obs-values").fill("10, 20")

    page.get_by_role("button", name="Scenario").click()
    expect(page.locator("#scenario-n-reps")).to_have_value("7")

    page.get_by_role("button", name="Sweep").click()
    expect(page.locator("#sweep-n-reps")).to_have_value("3")
    expect(page.locator("#sweep-obs-values")).to_have_value("10, 20")


def test_worker_error_rejects_pending_init_request(page: Page, web_server: str) -> None:
    page.route(
        "**/pyodide_worker.js",
        lambda route: route.fulfill(
            status=200,
            content_type="application/javascript",
            body=(
                "self.onmessage = () => { "
                "setTimeout(() => { throw new Error('forced worker crash'); }, 0); "
                "};"
            ),
        ),
    )

    page.goto(web_server, wait_until="domcontentloaded")

    expect(page.get_by_test_id("runtime-status")).to_contain_text(
        "forced worker crash",
        timeout=10_000,
    )
    expect(page.get_by_test_id("run-scenario")).to_be_enabled()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(base_url: str) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(base_url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Server did not start: {base_url}")
