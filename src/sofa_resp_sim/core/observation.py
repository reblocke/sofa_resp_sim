"""Sample physiology and emit separate documented oxygenation/denominator events.

Latent arrays are diagnostic data. Scoring consumes only the returned event records.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .experiment_config import ScenarioConfig
from .paired_simulation import LatentBlock, LatentPatient, patient_rng
from .resp_utils import oracle_round


@dataclass(frozen=True)
class SupportTrajectory:
    labels: np.ndarray
    fio2_fraction: np.ndarray
    flow_lpm: np.ndarray


def _observed_path(patient, block, config):
    z = patient_rng(
        patient.seed, patient.patient_id, block.rng_block_id, "measurement_noise"
    ).standard_normal(len(block.minutes))
    return np.clip(block.saturation + config.bias_pct_points + config.noise_sd_pct * z, 0, 100)


def _round_observation(value, mode):
    if mode == "none":
        return float(value)
    return oracle_round(float(value), 0 if mode == "integer" else 1)


def support_trajectory(
    patient: LatentPatient,
    block: LatentBlock,
    config: ScenarioConfig,
) -> SupportTrajectory:
    support = config.support
    n = len(block.minutes)
    labels = np.full(n, support.label, dtype="U12")
    fio2 = np.full(n, np.nan if support.fio2_fraction is None else support.fio2_fraction)
    flow = np.full(n, np.nan if support.flow_lpm is None else support.flow_lpm)
    if support.mode == "fixed":
        # Segment coordinates follow the acute clock for replay controls.
        minutes = block.minutes
        if block.name == "baseline" and config.horizon.baseline_replay:
            minutes = minutes - minutes[0] + config.horizon.start_minute
        for segment in support.segments:
            mask = (minutes >= segment.start_minute) & (minutes < segment.end_minute)
            labels[mask] = segment.label
            fio2[mask] = np.nan if segment.fio2_fraction is None else segment.fio2_fraction
            flow[mask] = np.nan if segment.flow_lpm is None else segment.flow_lpm
    else:
        basis = (
            _observed_path(patient, block, config.observation)
            if support.based_on_observed
            else block.saturation
        )
        if support.based_on_observed:
            basis = np.asarray([_round_observation(v, config.observation.rounding) for v in basis])
        thresholds = support.thresholds_pct
        categories = np.select(
            [basis >= threshold for threshold in thresholds],
            ["ROOM_AIR", "LOW_FLOW", "HFNC", "NIPPV"],
            default="IMV",
        )
        labels[:] = categories
        fio2[:] = np.nan
        flow[:] = np.nan
        flow_draws = patient_rng(
            patient.seed, patient.patient_id, block.rng_block_id, "support_assignment"
        ).uniform(2, 6, n)
        fio2_z = patient_rng(
            patient.seed, patient.patient_id, block.rng_block_id, "fio2_values"
        ).standard_normal(n)
        fio2[labels == "ROOM_AIR"] = 0.21
        flow[labels == "LOW_FLOW"] = flow_draws[labels == "LOW_FLOW"]
        for label, mean, sd in [("HFNC", 0.4, 0.05), ("NIPPV", 0.5, 0.05), ("IMV", 0.6, 0.08)]:
            mask = labels == label
            fio2[mask] = np.clip(mean + sd * fio2_z[mask], 0.21, 1)
    return SupportTrajectory(labels, fio2, flow)


def _number(value):
    return None if np.isnan(value) else float(value)


def document_patient(patient: LatentPatient, config: ScenarioConfig) -> list[dict]:
    events = []
    observation, documentation = config.observation, config.documentation
    for block in patient.blocks:
        n = len(block.minutes)
        observed = _observed_path(patient, block, observation)
        support = support_trajectory(patient, block, config)
        spo2_missing = patient_rng(
            patient.seed, patient.patient_id, block.rng_block_id, "spo2_missingness"
        ).random(n)
        fio2_missing = patient_rng(
            patient.seed, patient.patient_id, block.rng_block_id, "fio2_missingness"
        ).random(n)
        source_labels = patient_rng(
            patient.seed, patient.patient_id, block.rng_block_id, "source_label"
        ).random(n)
        if block.name == "baseline":
            origin = int(block.minutes[0]) + getattr(
                observation, "baseline_start_offset_minutes", 0
            )
            interval = observation.baseline_interval_minutes
            stop = origin + observation.baseline_exposure_minutes
        else:
            origin = observation.start_minute
            interval = observation.interval_minutes
            stop = int(block.minutes[-1]) + 1
        for i, minute in enumerate(block.minutes):
            minute = int(minute)
            label = str(support.labels[i])
            if (
                origin + observation.phase_minutes <= minute < stop
                and (minute - origin - observation.phase_minutes) % interval == 0
            ):
                missing = spo2_missing[i] < observation.missing_probability
                events.append(
                    {
                        "event_id": f"p{patient.patient_id}:{block.name}:ox:{minute}",
                        "patient_id": patient.patient_id,
                        "block": block.name,
                        "event_type": "oxygenation",
                        "measurement_minute": float(minute),
                        "available_minute": float(minute),
                        "support_type": label,
                        "spo2_obs": None
                        if missing
                        else _round_observation(observed[i], observation.rounding),
                        "pao2_meas": None if missing else observation.measured_pao2_mmhg,
                        "documentation_missing": bool(missing),
                        **(
                            {
                                "synthetic_delivered_fio2_fraction": _number(
                                    support.fio2_fraction[i]
                                )
                                if label != "LOW_FLOW"
                                else None
                            }
                            if hasattr(observation, "baseline_start_offset_minutes")
                            else {}
                        ),
                        "units": "SpO2 percent; PaO2 mmHg",
                    }
                )
            doc_origin = int(block.minutes[0]) + documentation.phase_minutes
            if minute < doc_origin or (minute - doc_origin) % documentation.interval_minutes:
                continue
            missing = fio2_missing[i] < documentation.missing_probability
            source_i = max(0, i - documentation.stale_minutes)
            fio2_value = _number(support.fio2_fraction[source_i])
            fio2_set = fio2_meas = None
            if not missing and fio2_value is not None and label != "ROOM_AIR":
                if documentation.disagreement_fraction:
                    fio2_set = fio2_value
                    fio2_meas = float(
                        np.clip(fio2_value + documentation.disagreement_fraction, 0.21, 1)
                    )
                elif source_labels[i] < documentation.measured_source_probability:
                    fio2_meas = fio2_value
                else:
                    fio2_set = fio2_value
            events.append(
                {
                    "event_id": f"p{patient.patient_id}:{block.name}:fio2:{minute}",
                    "patient_id": patient.patient_id,
                    "block": block.name,
                    "event_type": "fio2",
                    "measurement_minute": float(minute + documentation.timestamp_offset_minutes),
                    "available_minute": float(minute + documentation.recorded_delay_minutes),
                    "value_origin_minute": float(block.minutes[source_i]),
                    "support_type": label,
                    "fio2_set_fraction": fio2_set,
                    "fio2_meas_fraction": fio2_meas,
                    "fio2_abg_fraction": None,
                    "flow_lpm": None if missing else _number(support.flow_lpm[source_i]),
                    "is_room_air": bool(not missing and label == "ROOM_AIR"),
                    "documentation_missing": bool(missing),
                    "units": "FiO2 fraction; flow L/min",
                }
            )
    return sorted(events, key=lambda e: (e["measurement_minute"], e["event_id"]))
