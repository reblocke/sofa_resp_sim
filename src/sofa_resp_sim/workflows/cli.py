from __future__ import annotations

import argparse
import math
from collections.abc import Sequence

import pandas as pd

from ..core.resp_simulation import SimulationConfig, run_parameter_sweep


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run respiratory SOFA simulation sweeps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Scoring parity notes:\n"
            "- Support types recognized by scoring: IMV, SURG IMV, NIPPV, HFNC, OSA, None.\n"
            "- Measures-stage gating allows scores 3–4 only for IMV/NIPPV; others cap at 2."
        ),
    )
    parser.add_argument("--replicates", type=int, default=1000)
    parser.add_argument("--obs-freq", type=str, default="15")
    parser.add_argument("--noise-sd", type=str, default="1.0")
    parser.add_argument("--room-air-threshold", type=str, default="94")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--admit-dts", type=str, default="2024-01-01")
    parser.add_argument("--include-baseline", action="store_true")
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args(argv)

    try:
        replicates = _validate_replicates(args.replicates)
        seed = _validate_seed(args.seed)
        admit_dts = _parse_timestamp(args.admit_dts, "admit_dts")
        obs_freq = _parse_csv_int_list(args.obs_freq, "obs_freq_minutes", minimum=1)
        noise_sd = _parse_csv_float_list(args.noise_sd, "noise_sd", minimum=0)
        room_air_thresholds = _parse_csv_float_list(
            args.room_air_threshold,
            "room_air_threshold",
        )
    except ValueError as exc:
        parser.error(str(exc))

    base_config = SimulationConfig(
        admit_dts=admit_dts,
        include_baseline=args.include_baseline,
    )

    summary, _ = run_parameter_sweep(
        base_config=base_config,
        obs_freq_minutes=obs_freq,
        noise_sd=noise_sd,
        room_air_thresholds=room_air_thresholds,
        n_reps=replicates,
        seed=seed,
    )

    if args.output:
        summary.to_csv(args.output, index=False)
    else:
        print(summary.to_string(index=False))


def _validate_replicates(value: int) -> int:
    if value < 1:
        raise ValueError("n_reps must be >= 1.")
    return value


def _validate_seed(value: int) -> int:
    if value < 0:
        raise ValueError("seed must be >= 0.")
    return value


def _parse_timestamp(raw: str, field_name: str) -> pd.Timestamp:
    try:
        value = pd.Timestamp(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid timestamp.") from exc
    if pd.isna(value):
        raise ValueError(f"{field_name} must be a valid timestamp.")
    return value


def _parse_csv_int_list(raw: str, field_name: str, minimum: int | None = None) -> list[int]:
    values = _parse_csv_list(raw, field_name)
    parsed = [_parse_int(value, field_name) for value in values]
    if minimum is not None:
        for value in parsed:
            if value < minimum:
                raise ValueError(f"{field_name} must be >= {minimum}.")
    return parsed


def _parse_csv_float_list(
    raw: str,
    field_name: str,
    minimum: float | None = None,
) -> list[float]:
    values = _parse_csv_list(raw, field_name)
    parsed = [_parse_float(value, field_name) for value in values]
    if minimum is not None:
        for value in parsed:
            if value < minimum:
                raise ValueError(f"{field_name} must be >= {minimum}.")
    return parsed


def _parse_csv_list(raw: str, field_name: str) -> list[str]:
    if not raw.strip():
        raise ValueError(f"{field_name} must not be empty.")

    values: list[str] = []
    for idx, token in enumerate(raw.split(","), start=1):
        value = token.strip()
        if not value:
            raise ValueError(f"{field_name} contains an empty value at position {idx}.")
        values.append(value)
    return values


def _parse_int(raw: str, field_name: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc


def _parse_float(raw: str, field_name: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a float.") from exc
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")
    return value


if __name__ == "__main__":
    main()
