"""Paired patient orchestration with bounded trace retention and immutable requests."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Iterator

import numpy as np

from ..core.experiment_config import fingerprint
from ..core.experiment_scoring import score_documented_events
from ..core.historical_trops import profile_provenance, synthetic_context
from ..core.observation import document_patient, support_trajectory
from ..core.paired_simulation import generate_patient
from .experiment_request import V3, ExperimentRequest, normalize_experiment_request
from .experiment_results import summarize_paired_scores
from .historical_results import score_diagnostics, summarize_v3


def result_schema(request):
    return "experiment_result_v3" if request.schema_version == V3 else "experiment_result_v2"


def summarize_request(request, scores):
    return (summarize_v3 if request.schema_version == V3 else summarize_paired_scores)(
        scores, request.comparator.condition_id
    )


def _document(request, patient, config):
    events = document_patient(patient, config)
    return (
        synthetic_context(events, config.horizon.admit_dts)
        if request.schema_version == V3
        else events
    )


def _conditions(request):
    # Identical scientific configurations share rows, even if displayed under an alias.
    conditions = {}
    for condition in (request.comparator, *request.conditions):
        conditions.setdefault(condition.condition_id, condition)
    return conditions


def _support_identity(patient, config):
    return fingerprint(
        {
            "latent_id": patient.identity,
            "support": config.support.to_dict(),
            "observation": config.observation.to_dict()
            if config.support.mode == "assignment_stress_test"
            else None,
        }
    )


def _support_checksum(patient, config):
    digest = hashlib.sha256()
    for block in patient.blocks:
        support = support_trajectory(patient, block, config)
        digest.update(support.labels.astype("S12").tobytes())
        for values in (support.fio2_fraction, support.flow_lpm):
            digest.update(np.asarray(values, dtype="<f8").tobytes())
    return digest.hexdigest()


def _score_row(request, patient_id, condition, latent_id, support_id, result):
    acute, baseline = result["acute"], result["baseline"]
    return {
        "experiment_run_id": request.run_id,
        **(score_diagnostics(result) if request.schema_version == V3 else {}),
        "patient_id": patient_id,
        "condition_id": condition.condition_id,
        "condition_label": condition.label,
        "latent_id": latent_id,
        "support_id": support_id,
        "algorithm_score": acute["algorithm_score"],
        "score_status": acute["score_status"],
        "pre_suppression_score": acute["pre_suppression_score"],
        "qualifying_pf_count": acute["qualifying_pf_count"],
        "single_pf_suppressed": acute["suppressed"],
        "selected_event_id": acute["selected_event_id"],
        "baseline_algorithm_score": baseline["algorithm_score"],
        "baseline_score_status": baseline["score_status"],
        "baseline_qualifying_pf_count": baseline["qualifying_pf_count"],
        "baseline_selected_event_id": baseline["selected_event_id"],
        "delta_legacy": result["delta_legacy"],
        "delta_signed": result["delta_signed"],
        "delta_evaluable": result["delta_evaluable"],
        "delta_nonnegative_evaluable": result["delta_nonnegative_evaluable"],
    }


def _iter_patient_results(
    request: ExperimentRequest,
    patient_ids: Iterable[int],
    on_attempt: Callable[[int], None] | None = None,
) -> Iterator[tuple[list[dict], list[dict], list[dict]]]:
    conditions = _conditions(request)
    for patient_id in patient_ids:
        if on_attempt:
            on_attempt(patient_id)
        latent_cache, event_cache, support_cache = {}, {}, {}
        rows = []
        for condition in conditions.values():
            config = condition.config
            latent_key = fingerprint(
                {"generator": config.generator.to_dict(), "horizon": config.horizon.to_dict()}
            )
            if latent_key not in latent_cache:
                latent_cache[latent_key] = generate_patient(
                    config.generator, config.horizon, request.seed, patient_id
                )
            patient = latent_cache[latent_key]
            # Scoring-rule changes reuse the exact same documented records.
            observation_config = config.to_dict()
            observation_config.pop("scoring")
            event_key = fingerprint(observation_config)
            if event_key not in event_cache:
                event_cache[event_key] = _document(request, patient, config)
            support_key = fingerprint(
                {
                    "latent": latent_key,
                    "support": config.support.to_dict(),
                    "observation": config.observation.to_dict()
                    if config.support.mode == "assignment_stress_test"
                    else None,
                }
            )
            if support_key not in support_cache:
                support_cache[support_key] = (
                    _support_identity(patient, config),
                    _support_checksum(patient, config),
                )
            result = score_documented_events(
                event_cache[event_key], config.horizon.admit_dts, config.scoring
            )
            rows.append(
                _score_row(
                    request,
                    patient_id,
                    condition,
                    patient.identity,
                    support_cache[support_key][0],
                    result,
                )
            )
        latent_provenance = [
            {
                "patient_id": patient_id,
                "latent_id": patient.identity,
                "content_sha256": patient.content_sha256,
            }
            for patient in latent_cache.values()
        ]
        support_provenance = [
            {"patient_id": patient_id, "support_id": identity, "content_sha256": checksum}
            for identity, checksum in support_cache.values()
        ]
        yield rows, latent_provenance, support_provenance
        # Caches are per patient: minute-level frames are not retained for the whole cohort.


def run_experiment(
    request: ExperimentRequest,
    *,
    chunk_size: int = 32,
    on_progress: Callable[[dict], None] | None = None,
    previous: dict | None = None,
) -> dict:
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size < 1:
        raise ValueError("chunk_size must be a positive integer")
    scores, latent_provenance, support_provenance = [], [], []
    start = 0
    if previous is not None:
        old = normalize_experiment_request(previous["request"])
        extended = {**old.to_dict(), "replicates": request.replicates}
        if extended != request.to_dict() or request.replicates <= old.replicates:
            raise ValueError("Append must increase N without changing the original request")
        expected = {(p, c) for p in range(old.replicates) for c in _conditions(old)}
        if (
            previous.get("schema_version") != result_schema(request)
            or previous.get("completed_patients") != old.replicates
            or previous.get("attempted_patients") != old.replicates
            or previous.get("experiment_run_id") != old.run_id
            or len(previous["scores"]) != len(expected)
            or {(r["patient_id"], r["condition_id"]) for r in previous["scores"]} != expected
            or any(r["experiment_run_id"] != old.run_id for r in previous["scores"])
        ):
            raise ValueError("Append requires a complete original paired run")
        start = old.replicates
        scores = [{**row, "experiment_run_id": request.run_id} for row in previous["scores"]]
        latent_provenance = list(previous["runtime_provenance"]["latent_content"])
        support_provenance = list(previous["runtime_provenance"]["support_content"])

    def report_attempt(patient_id):
        if on_progress:
            on_progress(
                {
                    "stage": "scoring",
                    "completed_patients": patient_id,
                    "attempted_patients": patient_id + 1,
                    "requested_patients": request.replicates,
                    "completed_scoring_evaluations": len(scores),
                }
            )

    for completed, (rows, latent_hashes, support_hashes) in enumerate(
        _iter_patient_results(request, range(start, request.replicates), report_attempt), start + 1
    ):
        scores.extend(rows)
        latent_provenance.extend(latent_hashes)
        support_provenance.extend(support_hashes)
        if on_progress and (completed % chunk_size == 0 or completed == request.replicates):
            on_progress(
                {
                    "stage": "completed_chunk",
                    "completed_patients": completed,
                    "attempted_patients": completed,
                    "requested_patients": request.replicates,
                    "completed_scoring_evaluations": len(scores),
                }
            )
    warnings = ["uncalibrated illustrative simulation"]
    if any(
        c.config.support.mode == "assignment_stress_test" for c in _conditions(request).values()
    ):
        warnings.append("Support assignment stress test; not a physiological treatment response")
    return {
        "schema_version": result_schema(request),
        **(
            {
                "profile_provenance": {
                    c.condition_id: profile_provenance(c.config.scoring)
                    for c in _conditions(request).values()
                }
            }
            if request.schema_version == V3
            else {}
        ),
        "experiment_run_id": request.run_id,
        "request": request.to_dict(),
        "scores": scores,
        **summarize_request(request, scores),
        "completed_patients": request.replicates,
        "attempted_patients": request.replicates,
        "append_parent_run_id": previous["experiment_run_id"] if previous else None,
        "warnings": warnings,
        "runtime_provenance": {
            "hash_scheme": "raw_float64_le_v1",
            "latent_content": latent_provenance,
            "support_content": support_provenance,
        },
    }


def explain_patient(
    request: ExperimentRequest,
    patient_id: int,
    condition_id: str,
    *,
    expected_score: dict | None = None,
) -> dict:
    if (
        isinstance(patient_id, bool)
        or not isinstance(patient_id, int)
        or not 0 <= patient_id < request.replicates
    ):
        raise ValueError("patient_id must identify a patient in this run")
    conditions = _conditions(request)
    if condition_id not in conditions:
        raise ValueError("Unknown condition_id for this immutable request")
    condition = conditions[condition_id]
    config = condition.config
    patient = generate_patient(config.generator, config.horizon, request.seed, patient_id)
    result = score_documented_events(
        _document(request, patient, config), config.horizon.admit_dts, config.scoring
    )
    row = _score_row(
        request, patient_id, condition, patient.identity, _support_identity(patient, config), result
    )
    if expected_score is not None and row != expected_score:
        raise ValueError("Reconstructed patient does not match the saved score/request")
    latent, episodes = [], []
    for block in patient.blocks:
        support = support_trajectory(patient, block, config)
        for i, minute in enumerate(block.minutes):
            latent.append(
                {
                    "patient_id": patient_id,
                    "block": block.name,
                    "minute": int(minute),
                    "background_spo2_pct": float(block.background[i]),
                    "latent_spo2_pct": float(block.saturation[i]),
                    "support_type": str(support.labels[i]),
                    "fio2_fraction": None
                    if np.isnan(support.fio2_fraction[i])
                    else float(support.fio2_fraction[i]),
                    "flow_lpm": None
                    if np.isnan(support.flow_lpm[i])
                    else float(support.flow_lpm[i]),
                }
            )
        for i, episode in enumerate(block.episodes):
            episodes.append(
                {
                    "episode_id": f"p{patient_id}:{block.name}:episode:{i}",
                    "patient_id": patient_id,
                    "block": block.name,
                    **episode,
                }
            )
    return {
        "score": row,
        "scoring": result,
        "latent": latent,
        "episodes": episodes,
        "diagnostics": [block.diagnostics() for block in patient.blocks],
    }
