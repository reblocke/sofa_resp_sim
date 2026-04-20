from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"
PY_STAGE_ROOT = WEB_ROOT / "assets" / "py"
DATA_STAGE_ROOT = WEB_ROOT / "assets" / "data"
PACKAGE_ROOT = ROOT / "src" / "sofa_resp_sim"
REFERENCE_ARTIFACT = ROOT / "artifacts" / "resp_sofa_sim_summary.csv"

BROWSER_PYTHON_FILES = (
    "__init__.py",
    "browser_contract.py",
    "resp_scoring.py",
    "resp_simulation.py",
    "resp_utils.py",
    "core/__init__.py",
    "core/resp_scoring.py",
    "core/resp_simulation.py",
    "core/resp_utils.py",
    "reporting/__init__.py",
    "reporting/app_services.py",
    "reporting/presets.py",
    "reporting/reference.py",
    "reporting/view_model.py",
)

STAGED_DATA_FILES = (REFERENCE_ARTIFACT,)


def main() -> None:
    if not PACKAGE_ROOT.exists():
        raise FileNotFoundError(f"Package root not found: {PACKAGE_ROOT}")

    _reset_generated_dir(PY_STAGE_ROOT)
    _reset_generated_dir(DATA_STAGE_ROOT)

    python_manifest = _stage_python_files()
    data_manifest = _stage_data_files()
    manifest = {
        "schema_version": 1,
        "package": "sofa_resp_sim",
        "python_files": python_manifest,
        "data_files": data_manifest,
    }
    manifest_path = PY_STAGE_ROOT / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (WEB_ROOT / ".nojekyll").write_text("", encoding="utf-8")
    print(
        "Staged "
        f"{len(python_manifest)} Python files and {len(data_manifest)} data files "
        f"under {WEB_ROOT}"
    )


def _reset_generated_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _stage_python_files() -> list[dict[str, str | int]]:
    staged: list[dict[str, str | int]] = []
    for relpath in BROWSER_PYTHON_FILES:
        source = PACKAGE_ROOT / relpath
        if not source.exists():
            raise FileNotFoundError(f"Allowlisted Python file not found: {source}")
        if "__pycache__" in source.parts:
            raise ValueError(f"Refusing to stage cache file: {source}")

        target = PY_STAGE_ROOT / "sofa_resp_sim" / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        staged.append(_manifest_entry(target, WEB_ROOT))
    return staged


def _stage_data_files() -> list[dict[str, str | int]]:
    staged: list[dict[str, str | int]] = []
    for source in STAGED_DATA_FILES:
        if not source.exists():
            raise FileNotFoundError(f"Required data artifact not found: {source}")
        target = DATA_STAGE_ROOT / source.name
        shutil.copy2(source, target)
        staged.append(_manifest_entry(target, WEB_ROOT))
    return staged


def _manifest_entry(path: Path, base: Path) -> dict[str, str | int]:
    data = path.read_bytes()
    relpath = path.relative_to(base).as_posix()
    return {
        "path": relpath,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


if __name__ == "__main__":
    main()
