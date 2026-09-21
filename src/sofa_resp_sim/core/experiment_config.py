"""Versioned, UI-independent scientific configuration for paired experiments.

Legacy SimulationConfig and no-profile scoring entry points are deliberately separate.
"""

from __future__ import annotations

import hashlib
import json
import math
import types
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Literal, Union, get_args, get_origin, get_type_hints
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCHEMA_VERSION = "experiment_request_v2"
GENERATOR_VERSION = "fixed_minute_ar1_v2"
RNG_VERSION = "seedsequence_pcg64_v2"
LEGACY_PROFILE = "legacy_py_v1"
EXPERIMENT_PROFILE = "bounded_analysis_v2"
SupportLabel = Literal["ROOM_AIR", "LOW_FLOW", "HFNC", "NIPPV", "IMV", "SURG IMV", "UNKNOWN"]


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


class ScientificConfig:
    """Small strict decoder shared by this finite set of scientific records."""

    def __post_init__(self) -> None:
        for name, annotation in get_type_hints(type(self)).items():
            value = _decode(getattr(self, name), annotation, name)
            object.__setattr__(self, name, value)
        self.validate()

    def validate(self) -> None:
        pass

    def to_dict(self) -> dict:
        return json.loads(canonical_json(asdict(self)))

    @classmethod
    def from_dict(cls, value: dict):
        if not isinstance(value, dict):
            raise ValueError(f"{cls.__name__} must be an object")
        unknown = set(value) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"Unknown {cls.__name__} keys: {sorted(unknown)}")
        try:
            return cls(**value)
        except TypeError as exc:
            raise ValueError(f"Invalid {cls.__name__}: {exc}") from exc


def _decode(value, annotation, name):
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        if value not in args or not isinstance(value, type(args[0])):
            raise ValueError(f"{name} must be one of {args}")
        return value
    if origin in (types.UnionType, Union):
        for option in args:
            try:
                return _decode(value, option, name)
            except ValueError:
                continue
        raise ValueError(f"{name} has invalid type or value")
    if annotation is type(None):
        if value is not None:
            raise ValueError(f"{name} must be null")
        return None
    if origin is tuple:
        if not isinstance(value, (tuple, list)):
            raise ValueError(f"{name} must be an array")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_decode(v, args[0], name) for v in value)
        if len(value) != len(args):
            raise ValueError(f"{name} requires {len(args)} values")
        return tuple(_decode(v, a, name) for v, a in zip(value, args, strict=True))
    if isinstance(annotation, type) and issubclass(annotation, ScientificConfig):
        if isinstance(value, annotation):
            return value
        return annotation.from_dict(value)
    if annotation in (int, float):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be numeric")
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        if annotation is int and value != int(value):
            raise ValueError(f"{name} must be an integer")
        return annotation(value)
    if annotation in (str, bool) and type(value) is annotation:
        return value
    raise ValueError(f"{name} has invalid type")


def _between(name: str, value: float, low: float, high: float) -> None:
    if not low <= value <= high:
        raise ValueError(f"{name} must be in [{low}, {high}]")


@dataclass(frozen=True)
class Episode(ScientificConfig):
    start_minute: int
    end_minute: int
    depth_pct_points: float

    def validate(self) -> None:
        if self.end_minute <= self.start_minute or self.depth_pct_points < 0:
            raise ValueError("Episode requires increasing times and nonnegative depth")


@dataclass(frozen=True)
class TrajectoryPoint(ScientificConfig):
    minute: int
    spo2_pct: float

    def validate(self) -> None:
        _between("spo2_pct", self.spo2_pct, 0, 100)


@dataclass(frozen=True)
class GeneratorConfig(ScientificConfig):
    version: Literal["fixed_minute_ar1_v2"] = GENERATOR_VERSION
    mean_pct: float = 94.0
    marginal_sd_pct: float = 1.5
    tau_minutes: float = 30.0
    episode_rate_per_hour: float = 0.1
    episode_depth_pct_points: float = 5.0
    episode_duration_minutes: int = 30
    prescribed_episodes: tuple[Episode, ...] = ()
    prescribed_trajectory: tuple[TrajectoryPoint, ...] = ()

    def validate(self) -> None:
        _between("mean_pct", self.mean_pct, 0, 100)
        for name in (
            "marginal_sd_pct",
            "tau_minutes",
            "episode_rate_per_hour",
            "episode_depth_pct_points",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be nonnegative")
        if self.episode_duration_minutes < 1:
            raise ValueError("episode_duration_minutes must be positive")
        points = [p.minute for p in self.prescribed_trajectory]
        if points != sorted(set(points)):
            raise ValueError("Prescribed trajectory minutes must be strictly increasing")
        if self.prescribed_trajectory and self.marginal_sd_pct != 0:
            raise ValueError("Prescribed trajectories require marginal_sd_pct=0")
        episodes = sorted(self.prescribed_episodes, key=lambda e: e.start_minute)
        if any(a.end_minute > b.start_minute for a, b in zip(episodes, episodes[1:], strict=False)):
            raise ValueError("Prescribed episodes must not overlap")
        if self.prescribed_episodes and self.episode_rate_per_hour != 0:
            raise ValueError("Prescribed episodes require episode_rate_per_hour=0")


@dataclass(frozen=True)
class HorizonConfig(ScientificConfig):
    admit_dts: str = "2024-01-01T12:37:00Z"
    start_minute: int = -360
    end_minute: int = 1440
    include_baseline: bool = False
    baseline_days_before: int = 30
    baseline_generation_minutes: int = 1440
    baseline_replay: bool = False

    def validate(self) -> None:
        try:
            timestamp = datetime.fromisoformat(self.admit_dts.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("admit_dts must be an ISO timestamp") from exc
        if timestamp.utcoffset() is None:
            raise ValueError("admit_dts must include an explicit UTC offset")
        if self.end_minute <= self.start_minute:
            raise ValueError("Generation horizon must have increasing endpoints")
        if self.baseline_days_before < 8 or self.baseline_generation_minutes < 1:
            raise ValueError("Baseline requires at least 8 days separation and positive duration")
        if self.baseline_generation_minutes >= self.baseline_days_before * 1440 + self.start_minute:
            raise ValueError("Baseline and acute generation blocks must not overlap")
        if self.baseline_replay and not self.include_baseline:
            raise ValueError("baseline_replay requires include_baseline")


@dataclass(frozen=True)
class ObservationConfig(ScientificConfig):
    interval_minutes: int = 15
    phase_minutes: int = 0
    start_minute: int = -360
    noise_sd_pct: float = 1.0
    bias_pct_points: float = 0.0
    rounding: Literal["integer", "one_decimal", "none"] = "integer"
    missing_probability: float = 0.0
    measured_pao2_mmhg: float | None = None
    baseline_interval_minutes: int = 15
    baseline_exposure_minutes: int = 1440

    def validate(self) -> None:
        if self.interval_minutes < 1 or self.baseline_interval_minutes < 1:
            raise ValueError("Observation intervals must be positive")
        if self.phase_minutes < 0 or self.baseline_exposure_minutes < 1:
            raise ValueError("Phase must be nonnegative and baseline exposure positive")
        if self.noise_sd_pct < 0:
            raise ValueError("noise_sd_pct must be nonnegative")
        _between("missing_probability", self.missing_probability, 0, 1)
        if self.measured_pao2_mmhg is not None and self.measured_pao2_mmhg <= 0:
            raise ValueError("measured_pao2_mmhg must be positive")


@dataclass(frozen=True)
class DocumentationConfig(ScientificConfig):
    interval_minutes: int = 15
    phase_minutes: int = 0
    missing_probability: float = 0.0
    measured_source_probability: float = 0.2
    disagreement_fraction: float = 0.0
    stale_minutes: int = 0
    recorded_delay_minutes: float = 0.0
    timestamp_offset_minutes: float = 0.0

    def validate(self) -> None:
        if self.interval_minutes < 1 or self.phase_minutes < 0 or self.stale_minutes < 0:
            raise ValueError("Documentation interval must be positive; phase/staleness nonnegative")
        for name in ("missing_probability", "measured_source_probability"):
            _between(name, getattr(self, name), 0, 1)
        _between("disagreement_fraction", self.disagreement_fraction, -0.79, 0.79)
        if self.recorded_delay_minutes < 0:
            raise ValueError("recorded_delay_minutes must be nonnegative")


@dataclass(frozen=True)
class SupportSegment(ScientificConfig):
    start_minute: int
    end_minute: int
    label: SupportLabel
    fio2_fraction: float | None = None
    flow_lpm: float | None = None

    def validate(self) -> None:
        if self.end_minute <= self.start_minute:
            raise ValueError("Support segment requires increasing endpoints")
        _validate_support(self.label, self.fio2_fraction, self.flow_lpm)


def _validate_support(label, fio2_fraction, flow_lpm):
    if fio2_fraction is not None:
        _between("fio2_fraction", fio2_fraction, 0.21, 1)
    if flow_lpm is not None:
        _between("flow_lpm", flow_lpm, 0, 15)
    if label == "ROOM_AIR" and fio2_fraction not in (None, 0.21):
        raise ValueError("Room-air FiO2 must be .21")
    if label == "ROOM_AIR" and flow_lpm not in (None, 0):
        raise ValueError("Room air cannot have oxygen flow")
    if label == "LOW_FLOW" and (flow_lpm is None or fio2_fraction is not None):
        raise ValueError("Low flow requires flow_lpm and no known delivered FiO2")
    if label in ("HFNC", "NIPPV", "IMV", "SURG IMV") and fio2_fraction is None:
        raise ValueError("Fixed supported modes require fio2_fraction")
    if label == "UNKNOWN" and (fio2_fraction is not None or flow_lpm is not None):
        raise ValueError("Unknown support cannot silently supply FiO2/flow")


@dataclass(frozen=True)
class SupportConfig(ScientificConfig):
    mode: Literal["fixed", "assignment_stress_test"] = "fixed"
    label: SupportLabel = "ROOM_AIR"
    fio2_fraction: float | None = 0.21
    flow_lpm: float | None = None
    thresholds_pct: tuple[float, float, float, float] = (94, 90, 86, 82)
    based_on_observed: bool = True
    segments: tuple[SupportSegment, ...] = ()

    def validate(self) -> None:
        _validate_support(self.label, self.fio2_fraction, self.flow_lpm)
        if not all(
            a > b for a, b in zip(self.thresholds_pct, self.thresholds_pct[1:], strict=False)
        ):
            raise ValueError("All four support thresholds must be strictly decreasing")
        for threshold in self.thresholds_pct:
            _between("support threshold", threshold, 0, 100)
        segments = sorted(self.segments, key=lambda s: s.start_minute)
        if any(a.end_minute > b.start_minute for a, b in zip(segments, segments[1:], strict=False)):
            raise ValueError("Support segments must not overlap")
        if self.mode != "fixed" and self.segments:
            raise ValueError("Assignment stress mode cannot use prescribed support segments")


@dataclass(frozen=True)
class ScoringProfile(ScientificConfig):
    profile: Literal["bounded_analysis_v2"] = EXPERIMENT_PROFILE
    threshold_factor: float = 1.0
    timezone: str = "UTC"
    binning: Literal["calendar", "admission"] = "calendar"
    availability: Literal["retrospective", "as_of"] = "retrospective"
    lookup: Literal["legacy", "contemporaneous_first"] = "legacy"
    conversion: Literal["spo2_or_measured", "measured_only"] = "spo2_or_measured"
    single_record_suppression: bool = True
    support_eligibility: Literal["legacy", "expanded"] = "legacy"
    baseline_selection: Literal["latest_day", "all_eligible_max"] = "latest_day"
    acute_begin_minute: int = -360
    acute_end_minute: int = 1440
    baseline_months: int = 36
    baseline_end_days: int = 7

    def validate(self) -> None:
        if self.threshold_factor <= 0:
            raise ValueError("threshold_factor must be positive")
        if self.acute_end_minute <= self.acute_begin_minute:
            raise ValueError("Acute target endpoints must increase")
        if self.baseline_months < 1 or self.baseline_end_days < 1:
            raise ValueError("Baseline date windows must be positive")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Unknown scoring timezone") from exc


@dataclass(frozen=True)
class ScenarioConfig(ScientificConfig):
    generator: GeneratorConfig = GeneratorConfig()
    horizon: HorizonConfig = HorizonConfig()
    observation: ObservationConfig = ObservationConfig()
    documentation: DocumentationConfig = DocumentationConfig()
    support: SupportConfig = SupportConfig()
    scoring: ScoringProfile = ScoringProfile()

    def validate(self) -> None:
        if self.observation.start_minute < self.horizon.start_minute:
            raise ValueError("Observation start precedes the generated horizon")
        if self.observation.start_minute >= self.horizon.end_minute:
            raise ValueError("Observation start is outside the generated horizon")
        if (
            self.horizon.include_baseline
            and self.observation.baseline_exposure_minutes
            > self.horizon.baseline_generation_minutes
        ):
            raise ValueError("Baseline exposure exceeds generated baseline")
        if self.horizon.baseline_replay:
            replay_end = self.horizon.start_minute + self.horizon.baseline_generation_minutes
            if replay_end > self.horizon.end_minute:
                raise ValueError("Baseline replay requires a complete generated acute segment")

    @property
    def condition_id(self) -> str:
        return fingerprint(self.to_dict())

    def override(self, changes: dict) -> ScenarioConfig:
        if not isinstance(changes, dict):
            raise ValueError("Condition overrides must be an object")
        data = self.to_dict()
        for group, values in changes.items():
            if group not in data or not isinstance(values, dict):
                raise ValueError(f"Unknown or invalid scientific override group: {group}")
            data[group].update(values)
        return ScenarioConfig.from_dict(data)
