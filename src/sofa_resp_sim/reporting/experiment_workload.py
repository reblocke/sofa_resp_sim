"""Allocation-free workload accounting and bounded browser previews."""

from __future__ import annotations

from ..core.experiment_config import fingerprint
from .experiment_request import ExperimentRequest

PREVIEW_LIMITS = {
    "patients": 200,
    "scoring_evaluations": 1600,
    "latent_minutes": 720000,
    "documented_events": 400000,
    "peak_latent_minutes_per_patient": 10000,
}


def _samples(start, stop, origin, phase, interval):
    first = origin + phase
    if first < start:
        first += ((start - first + interval - 1) // interval) * interval
    return max(0, (stop - 1 - first) // interval + 1)


def estimate_workload(request: ExperimentRequest) -> dict:
    conditions = {c.condition_id: c for c in (request.comparator, *request.conditions)}
    generators, observations = {}, {}
    for condition in conditions.values():
        c = condition.config
        latent_key = fingerprint(
            {"generator": c.generator.to_dict(), "horizon": c.horizon.to_dict()}
        )
        minutes = c.horizon.end_minute - c.horizon.start_minute
        if c.horizon.include_baseline:
            minutes += c.horizon.baseline_generation_minutes
        generators[latent_key] = minutes
        observed = c.to_dict()
        observed.pop("scoring")
        key = fingerprint(observed)
        events = _samples(
            c.horizon.start_minute,
            c.horizon.end_minute,
            c.observation.start_minute,
            c.observation.phase_minutes,
            c.observation.interval_minutes,
        )
        events += _samples(
            0,
            c.horizon.end_minute - c.horizon.start_minute,
            0,
            c.documentation.phase_minutes,
            c.documentation.interval_minutes,
        )
        if c.horizon.include_baseline:
            events += _samples(
                0,
                c.observation.baseline_exposure_minutes,
                0,
                c.observation.phase_minutes,
                c.observation.baseline_interval_minutes,
            )
            events += _samples(
                0,
                c.horizon.baseline_generation_minutes,
                0,
                c.documentation.phase_minutes,
                c.documentation.interval_minutes,
            )
        observations[key] = events
    workload = {
        "patients": request.replicates,
        "scoring_evaluations": request.replicates * len(conditions),
        "latent_minutes": request.replicates * sum(generators.values()),
        "documented_events": request.replicates * sum(observations.values()),
        "peak_latent_minutes_per_patient": sum(generators.values()),
        "unique_conditions": len(conditions),
        "unique_generators": len(generators),
        "unique_documentation_streams": len(observations),
    }
    exceeded = [key for key, limit in PREVIEW_LIMITS.items() if workload[key] > limit]
    return {
        **workload,
        "preview_limits": dict(PREVIEW_LIMITS),
        "preview_allowed": not exceeded,
        "exceeded_limits": exceeded,
        "scope": "Generated minutes/records with shared caches; not a RAM prediction",
        "cli_alternative": "resp-sofa-experiment run --request request.json --output output-bundle",
    }


def require_preview_budget(request: ExperimentRequest) -> dict:
    workload = estimate_workload(request)
    if not workload["preview_allowed"]:
        raise ValueError(
            f"Preview exceeds {', '.join(workload['exceeded_limits'])}. "
            f"Export request.json and use: {workload['cli_alternative']}"
        )
    return workload
