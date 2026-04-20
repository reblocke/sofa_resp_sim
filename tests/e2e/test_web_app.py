from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

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
