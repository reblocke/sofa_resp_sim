from __future__ import annotations

import argparse

import pandas as pd

from ..core.resp_simulation import SimulationConfig, run_parameter_sweep


def main() -> None:
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
    args = parser.parse_args()

    obs_freq = _parse_list(args.obs_freq, int)
    noise_sd = _parse_list(args.noise_sd, float)
    room_air_thresholds = _parse_list(args.room_air_threshold, float)

    base_config = SimulationConfig(
        admit_dts=pd.Timestamp(args.admit_dts),
        include_baseline=args.include_baseline,
    )

    summary, _ = run_parameter_sweep(
        base_config=base_config,
        obs_freq_minutes=obs_freq,
        noise_sd=noise_sd,
        room_air_thresholds=room_air_thresholds,
        n_reps=args.replicates,
        seed=args.seed,
    )

    if args.output:
        summary.to_csv(args.output, index=False)
    else:
        print(summary.to_string(index=False))


def _parse_list(raw: str, cast):
    return [cast(val.strip()) for val in raw.split(",") if val.strip()]


if __name__ == "__main__":
    main()
