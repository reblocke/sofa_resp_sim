from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from sofa_resp_sim.reporting.app_services import run_single_scenario
from sofa_resp_sim.reporting.view_model import default_run_request


def benchmark_single_scenario(
    n_reps: int,
    repeats: int,
    seed: int,
    target_seconds: float,
) -> dict[str, float | int | bool]:
    request = replace(default_run_request(), n_reps=n_reps, seed=seed)

    elapsed: list[float] = []
    for _ in range(repeats):
        start = perf_counter()
        run_single_scenario(request)
        elapsed.append(perf_counter() - start)

    result: dict[str, float | int | bool] = {
        "n_reps": n_reps,
        "repeats": repeats,
        "seed": seed,
        "mean_seconds": float(mean(elapsed)),
        "median_seconds": float(median(elapsed)),
        "min_seconds": float(min(elapsed)),
        "max_seconds": float(max(elapsed)),
        "target_seconds": target_seconds,
        "meets_target": bool(median(elapsed) < target_seconds),
    }
    return result


def write_csv(path: Path, row: dict[str, float | int | bool]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "n_reps",
        "repeats",
        "seed",
        "mean_seconds",
        "median_seconds",
        "min_seconds",
        "max_seconds",
        "target_seconds",
        "meets_target",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile browser-contract single-scenario service runtime."
    )
    parser.add_argument("--n-reps", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--target-seconds", type=float, default=2.0)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional output CSV path for benchmark summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = benchmark_single_scenario(
        n_reps=args.n_reps,
        repeats=args.repeats,
        seed=args.seed,
        target_seconds=args.target_seconds,
    )

    print("Browser contract performance benchmark (single scenario)")
    for key in (
        "n_reps",
        "repeats",
        "seed",
        "mean_seconds",
        "median_seconds",
        "min_seconds",
        "max_seconds",
        "target_seconds",
        "meets_target",
    ):
        print(f"{key}: {result[key]}")

    if args.output_csv is not None:
        write_csv(args.output_csv, result)
        print(f"wrote_csv: {args.output_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
