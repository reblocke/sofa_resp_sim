"""Generate each synthetic patient's minute-level physiology independently of charting."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
from scipy.signal import lfilter

from .experiment_config import (
    RNG_VERSION,
    GeneratorConfig,
    HorizonConfig,
    canonical_json,
    fingerprint,
)

# Append IDs when adding a stochastic mechanism; never renumber existing streams.
STREAM_IDS = {
    "physiology": 0,
    "episodes": 1,
    "measurement_noise": 2,
    "support_assignment": 3,
    "fio2_values": 4,
    "spo2_missingness": 5,
    "fio2_missingness": 6,
    "timestamp_perturbation": 7,
    "source_label": 8,
}


def patient_rng(seed: int, patient_id: int, block_id: int, stream: str) -> np.random.Generator:
    if any(
        isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (seed, patient_id, block_id)
    ):
        raise ValueError("Seed, patient ID and block ID must be nonnegative integers")
    sequence = np.random.SeedSequence([patient_id, block_id, STREAM_IDS[stream], seed])
    return np.random.Generator(np.random.PCG64(sequence))


@dataclass(frozen=True)
class LatentBlock:
    name: str
    rng_block_id: int
    minutes: np.ndarray
    background: np.ndarray
    saturation: np.ndarray
    episodes: tuple[dict, ...]

    def diagnostics(self) -> dict:
        clipped = np.clip(self.background, 0, 100)
        return {
            "block": self.name,
            "n_minutes": len(self.minutes),
            "background_mean_pct": float(self.background.mean()),
            "background_sd_pct": float(self.background.std()),
            "clipped_background_mean_pct": float(clipped.mean()),
            "clipped_background_sd_pct": float(clipped.std()),
            "background_clipping_fraction": float(np.mean(clipped != self.background)),
            "latent_mean_pct": float(self.saturation.mean()),
            "latent_sd_pct": float(self.saturation.std()),
            "episode_count": len(self.episodes),
            "achieved_episode_starts_per_hour": len(self.episodes) * 60 / len(self.minutes),
        }


@dataclass(frozen=True)
class LatentPatient:
    patient_id: int
    seed: int
    blocks: tuple[LatentBlock, ...]
    generation_id: str

    @property
    def identity(self) -> str:
        return fingerprint(
            {
                "rng_version": RNG_VERSION,
                "patient_id": self.patient_id,
                "seed": self.seed,
                "generation_id": self.generation_id,
            }
        )

    @property
    def content_sha256(self) -> str:
        """Runtime-specific raw checksum; not a cross-runtime patient identifier."""
        digest = hashlib.sha256(RNG_VERSION.encode())
        digest.update(f"{self.patient_id}:{self.seed}".encode())
        for block in self.blocks:
            digest.update(block.name.encode())
            digest.update(canonical_json(block.episodes).encode())
            for values in (block.minutes, block.background, block.saturation):
                digest.update(np.asarray(values, dtype="<f8").tobytes())
        return digest.hexdigest()


def stationary_background(
    n: int,
    config: GeneratorConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    """Stationary pre-clipping AR(1); sigma is marginal SD, tau is elapsed minutes."""
    if n < 1:
        raise ValueError("A latent block must contain at least one minute")
    z = rng.standard_normal(n)
    if config.marginal_sd_pct == 0:
        return np.full(n, config.mean_pct, dtype=float)
    if config.tau_minutes == 0:
        return config.mean_pct + config.marginal_sd_pct * z
    phi = np.exp(-1 / config.tau_minutes)
    deviation = np.empty(n)
    deviation[0] = config.marginal_sd_pct * z[0]
    # lfilter implements the specified scalar recurrence, with stationary x[0].
    if n > 1:
        deviation[1:], _ = lfilter(
            [config.marginal_sd_pct * np.sqrt(1 - phi**2)],
            [1, -phi],
            z[1:],
            zi=[phi * deviation[0]],
        )
    return config.mean_pct + deviation


def _block(name, block_id, start, end, config, seed, patient_id):
    minutes = np.arange(start, end, dtype=np.int64)
    n = len(minutes)
    background = stationary_background(
        n,
        config,
        patient_rng(seed, patient_id, block_id, "physiology"),
    )
    if config.prescribed_trajectory:
        background = np.interp(
            minutes,
            [p.minute for p in config.prescribed_trajectory],
            [p.spo2_pct for p in config.prescribed_trajectory],
        )
    episodes = []
    if config.prescribed_episodes:
        for episode in config.prescribed_episodes:
            if episode.start_minute < end and episode.end_minute > start:
                episodes.append(episode.to_dict())
    else:
        uniforms = patient_rng(seed, patient_id, block_id, "episodes").random(n)
        probability = -np.expm1(-config.episode_rate_per_hour / 60)
        idle_at = start
        for minute, uniform in zip(minutes, uniforms, strict=True):
            if minute >= idle_at and uniform < probability:
                idle_at = int(minute) + config.episode_duration_minutes
                episodes.append(
                    {
                        "start_minute": int(minute),
                        "end_minute": idle_at,
                        "depth_pct_points": config.episode_depth_pct_points,
                    }
                )
    saturation = background.copy()
    for episode in episodes:
        mask = (minutes >= episode["start_minute"]) & (minutes < episode["end_minute"])
        saturation[mask] -= episode["depth_pct_points"]
    saturation = np.clip(saturation, 0, 100)
    for values in (minutes, background, saturation):
        values.flags.writeable = False
    return LatentBlock(name, block_id, minutes, background, saturation, tuple(episodes))


def generate_patient(
    config: GeneratorConfig,
    horizon: HorizonConfig,
    seed: int,
    patient_id: int,
) -> LatentPatient:
    acute = _block("acute", 0, horizon.start_minute, horizon.end_minute, config, seed, patient_id)
    blocks = [acute]
    if horizon.include_baseline:
        start = -horizon.baseline_days_before * 1440
        end = start + horizon.baseline_generation_minutes
        if horizon.baseline_replay:
            n = horizon.baseline_generation_minutes
            if n > len(acute.minutes):
                raise ValueError("Replay exceeds the available acute trajectory")
            shift = start - horizon.start_minute
            episodes = tuple(
                {
                    **e,
                    "start_minute": e["start_minute"] + shift,
                    "end_minute": e["end_minute"] + shift,
                }
                for e in acute.episodes
                if e["start_minute"] < acute.minutes[n - 1] + 1
            )
            minutes = np.arange(start, end, dtype=np.int64)
            minutes.flags.writeable = False
            baseline = LatentBlock(
                "baseline", 0, minutes, acute.background[:n], acute.saturation[:n], episodes
            )
        else:
            baseline = _block("baseline", 1, start, end, config, seed, patient_id)
        blocks.insert(0, baseline)
    generation_id = fingerprint({"generator": config.to_dict(), "horizon": horizon.to_dict()})
    return LatentPatient(patient_id, seed, tuple(blocks), generation_id)
