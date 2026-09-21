"""Run, inspect and reproduce paired synthetic experiments from an installed package."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from ..core.experiment_config import fingerprint
from ..reporting.experiment_bundle import (
    REQUIRED,
    build_bundle,
    compare_scientific_values,
    decode_table,
    runtime_environment,
    verify_bundle,
)
from ..reporting.experiment_catalogue import STRATA, catalogue_metadata, catalogue_request
from ..reporting.experiment_request import normalize_experiment_request
from ..reporting.experiment_service import explain_patient, run_experiment


def read_files(path: Path) -> dict[str, str]:
    if path.is_dir():
        if {p.name for p in path.iterdir()} != REQUIRED:
            raise ValueError("Bundle directory contains missing or unexpected members")
        return {name: (path / name).read_text(encoding="utf-8") for name in REQUIRED}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if set(names) != REQUIRED or len(names) != len(REQUIRED):
            raise ValueError("ZIP has missing, duplicate or unexpected bundle members")
        if sum(info.file_size for info in archive.infolist()) > 512 * 1024 * 1024:
            raise ValueError("Bundle exceeds 512 MiB import limit")
        return {name: archive.read(name).decode("utf-8") for name in REQUIRED}


def write_files(files: dict[str, str], path: Path):
    if path.exists():
        raise ValueError(f"Output already exists: {path}; choose a new output path")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, text in sorted(files.items()):
                archive.writestr(name, text)
    else:
        path.mkdir()
        for name, text in files.items():
            (path / name).write_text(text, encoding="utf-8")


def native_environment():
    environment = runtime_environment()
    package_root = Path(__file__).resolve().parents[1]
    environment["source_sha256"] = fingerprint(
        {
            str(path.relative_to(package_root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(package_root.rglob("*"))
            if path.is_file() and path.suffix in {".py", ".csv", ".json"}
        }
    )
    source_root = Path(__file__).resolve().parents[3]
    if (source_root / "pyproject.toml").is_file():
        try:
            commit = subprocess.check_output(
                ["git", "-C", str(source_root), "rev-parse", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            status = subprocess.check_output(
                ["git", "-C", str(source_root), "status", "--porcelain"], text=True
            )
            environment.update(
                git_commit=commit,
                dirty_tree=bool(status),
                source_provenance_note="Git state of the source checkout",
            )
        except (OSError, subprocess.CalledProcessError):
            pass
    return environment


def _check_runtime(bundle):
    original = bundle["manifest"]["environment"]
    current = native_environment()
    if (
        original.get("python") != current["python"]
        or original.get("dependencies") != current["dependencies"]
    ):
        raise ValueError(
            "Runtime versions differ from the bundle. Install the recorded Python/dependency "
            "versions for exact reproduction/append, or use reproduce --allow-runtime-difference."
        )
    if original.get("source_sha256") and original["source_sha256"] != current["source_sha256"]:
        raise ValueError(
            "Package source differs from the bundle; "
            "exact append/reproduction needs the original source"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List prespecified demonstrations and support strata")
    run = commands.add_parser("run", help="Execute a normalized request or catalogue demonstration")
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument("--request", type=Path)
    source.add_argument("--entry")
    run.add_argument("--stratum", choices=STRATA, default="room_air")
    run.add_argument("--replicates", type=int, help="Override N; catalogue default is 200")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--patient", type=int, default=0)
    verify = commands.add_parser(
        "verify-bundle", help="Validate hashes, versions and table reconciliation"
    )
    verify.add_argument("bundle", type=Path)
    explain = commands.add_parser("explain", help="Regenerate one selected patient's trace")
    explain.add_argument("bundle", type=Path)
    explain.add_argument("--patient", type=int, required=True)
    explain.add_argument("--condition", required=True)
    explain.add_argument("--output", type=Path)
    reproduce = commands.add_parser(
        "reproduce", help="Rerun a bundle and compare exact scientific files"
    )
    reproduce.add_argument("bundle", type=Path)
    reproduce.add_argument("--output", required=True, type=Path)
    reproduce.add_argument(
        "--allow-runtime-difference",
        action="store_true",
        help="Compare exact discrete fields and floats at atol/rtol=1e-10",
    )
    append = commands.add_parser("append", help="Extend N while retaining earlier patient rows")
    append.add_argument("bundle", type=Path)
    append.add_argument(
        "--replicates", required=True, type=int, help="New total N, greater than original N"
    )
    append.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            print(json.dumps(catalogue_metadata(), indent=2))
            return 0
        if args.command == "run":
            if args.request:
                raw = json.loads(args.request.read_text(encoding="utf-8"))
                if args.replicates is not None:
                    raw["replicates"] = args.replicates
                request = normalize_experiment_request(raw)
            else:
                request = catalogue_request(
                    args.entry,
                    args.stratum,
                    replicates=args.replicates if args.replicates is not None else 200,
                )
            result = run_experiment(request)
            files = build_bundle(
                result, environment=native_environment(), selected_patient=args.patient
            )
            write_files(files, args.output)
        else:
            files = read_files(args.bundle)
            bundle = verify_bundle(files)
            request = normalize_experiment_request(bundle["request"])
            if args.command == "verify-bundle":
                print(
                    json.dumps(
                        {
                            "status": "verified",
                            "scientific_data_sha256": bundle["manifest"]["scientific_data_sha256"],
                        }
                    )
                )
                return 0
            if args.command == "explain":
                row = next(
                    (
                        r
                        for r in bundle["scores"]
                        if r["patient_id"] == args.patient and r["condition_id"] == args.condition
                    ),
                    None,
                )
                if row is None:
                    raise ValueError("Patient/condition is not present in this bundle")
                text = (
                    json.dumps(
                        explain_patient(request, args.patient, args.condition, expected_score=row),
                        indent=2,
                        allow_nan=False,
                    )
                    + "\n"
                )
                if args.output:
                    with args.output.open("x", encoding="utf-8") as stream:
                        stream.write(text)
                else:
                    print(text, end="")
                return 0
            cross_runtime = args.command == "reproduce" and args.allow_runtime_difference
            if not cross_runtime:
                _check_runtime(bundle)
            if args.command == "append":
                request = normalize_experiment_request(
                    {**request.to_dict(), "replicates": args.replicates}
                )
                result = run_experiment(request, previous=bundle)
            else:
                result = run_experiment(request)
                result["reproduction"] = {
                    "source_scientific_sha256": bundle["manifest"]["scientific_data_sha256"],
                    "comparison": "exact_discrete_float_1e-10" if cross_runtime else "exact_files",
                }
            regenerated = build_bundle(
                result,
                environment=native_environment(),
                selected_patient=bundle["manifest"]["selected_patient"],
            )
            if args.command == "reproduce":
                comparison = verify_bundle(regenerated)
                if cross_runtime:
                    if comparison["request"] != bundle["request"]:
                        raise ValueError("Reproduction changed the immutable request")
                    for name in bundle["manifest"]["scientific_hashes"]:
                        if name.endswith(".csv"):
                            compare_scientific_values(
                                decode_table(
                                    files[name], bundle["manifest"]["table_schemas"][name]
                                ),
                                decode_table(
                                    regenerated[name], comparison["manifest"]["table_schemas"][name]
                                ),
                                path=name,
                            )
                        elif json.loads(files[name]) != json.loads(regenerated[name]):
                            raise ValueError(f"Reproduction changed scientific metadata {name}")
                elif (
                    comparison["manifest"]["scientific_data_sha256"]
                    != bundle["manifest"]["scientific_data_sha256"]
                ):
                    changed = [
                        name
                        for name in bundle["manifest"]["scientific_hashes"]
                        if regenerated[name] != files[name]
                    ]
                    raise ValueError(
                        f"Scientific reproduction differs in {changed}; "
                        "no reproduced bundle written"
                    )
            files = regenerated
            write_files(files, args.output)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "experiment_run_id": request.run_id,
                    "completed_patients": request.replicates,
                    "request_sha256": fingerprint(request.to_dict()),
                }
            )
        )
        return 0
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        print(f"resp-sofa-experiment: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
