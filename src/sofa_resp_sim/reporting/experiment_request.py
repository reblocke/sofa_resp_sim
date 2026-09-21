"""One normalized experiment request shared by CLI and browser callers."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.experiment_config import RNG_VERSION, SCHEMA_VERSION, ScenarioConfig, fingerprint

OUTCOMES = (
    "score_ge1",
    "score_ge2",
    "score_ge3",
    "score_eq4",
    "no_qualifying_data",
    "suppressed_only",
    "qualifying_pf_count",
    "delta_legacy_ge1",
    "delta_legacy_ge2",
)


@dataclass(frozen=True)
class Condition:
    label: str
    config: ScenarioConfig

    @property
    def condition_id(self) -> str:
        return self.config.condition_id


@dataclass(frozen=True)
class ExperimentRequest:
    experiment_id: str
    base: ScenarioConfig
    comparator: Condition
    conditions: tuple[Condition, ...]
    replicates: int
    seed: int
    primary_outcome: str

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "rng_version": RNG_VERSION,
            "experiment_id": self.experiment_id,
            "base": self.base.to_dict(),
            "comparator": {
                "label": self.comparator.label,
                "overrides": self.comparator.config.to_dict(),
            },
            "conditions": [
                {"label": c.label, "overrides": c.config.to_dict()} for c in self.conditions
            ],
            "replicates": self.replicates,
            "seed": self.seed,
            "primary_outcome": self.primary_outcome,
        }

    @property
    def run_id(self) -> str:
        return fingerprint(self.to_dict())


def normalize_experiment_request(payload: dict) -> ExperimentRequest:
    if not isinstance(payload, dict):
        raise ValueError("Experiment request must be an object")
    allowed = {
        "schema_version",
        "rng_version",
        "experiment_id",
        "base",
        "comparator",
        "conditions",
        "replicates",
        "seed",
        "primary_outcome",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"Unknown experiment keys: {sorted(unknown)}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema_version; expected {SCHEMA_VERSION}")
    if payload.get("rng_version", RNG_VERSION) != RNG_VERSION:
        raise ValueError(f"Unsupported rng_version; expected {RNG_VERSION}")
    experiment_id = payload.get("experiment_id", "custom")
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("experiment_id must be a nonempty string")
    base = ScenarioConfig.from_dict(payload.get("base", {}))

    def condition(raw):
        if not isinstance(raw, dict) or set(raw) - {"label", "overrides"}:
            raise ValueError("Condition requires label and scientific overrides")
        label = raw.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Condition label must be a nonempty string")
        return Condition(label=label, config=base.override(raw.get("overrides", {})))

    comparator = condition(payload.get("comparator", {"label": "Comparator"}))
    raw_conditions = payload.get("conditions", [])
    if not isinstance(raw_conditions, list):
        raise ValueError("conditions must be an array")
    conditions = tuple(condition(c) for c in raw_conditions)
    labels = [c.label for c in (comparator, *conditions)]
    if len(labels) != len(set(labels)):
        raise ValueError("Condition labels must be unique")
    outcome = payload.get("primary_outcome", "score_ge2")
    if outcome not in OUTCOMES:
        raise ValueError(f"Unsupported primary_outcome: {outcome}")
    return ExperimentRequest(
        experiment_id,
        base,
        comparator,
        conditions,
        _integer(payload.get("replicates", 200), "replicates", minimum=1),
        _integer(payload.get("seed", 0), "seed", minimum=0),
        outcome,
    )


def _integer(value, name, minimum):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value != int(value)
        or value < minimum
    ):
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)
