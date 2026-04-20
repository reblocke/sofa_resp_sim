from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relpath: str) -> str:
    return (ROOT / relpath).read_text(encoding="utf-8")


def test_readme_uses_current_package_name():
    readme = _read("README.md")
    assert "sofa_resp_sim" in readme
    assert "tcco2_accuracy" not in readme


def test_pyproject_metadata_is_not_placeholder():
    pyproject = _read("pyproject.toml")
    assert 'project-title' not in pyproject
    assert 'One-line description.' not in pyproject


def test_agents_file_does_not_use_stale_continuity_ledger():
    agents = _read("AGENTS.md")
    assert "http://CONTINUITY.md" not in agents
    assert "http:/CONTINUITY.md" not in agents


def test_citation_file_is_not_placeholder():
    citation = _read("CITATION.cff")
    assert "your-org/your-repo" not in citation
    assert "placeholder-doi" not in citation
