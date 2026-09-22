"""Derived historical contract; no private SQL or clinical records are embedded.

Boundary: normalized timestamp values, supplied support flags and resolved
encounter partitions. Historical source mapping is not Oracle execution parity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import pandas as pd

from .experiment_config import ObservationConfig, ScenarioConfig, ScoringProfile, fingerprint

PROFILE = "trops_historical_e8b4de0_v1"
SOURCE_COMMIT = "e8b4de0b6e898e94d7ad091796a4aaea1df96231"
SOURCE_HASHES = {
    "SOFA Respiratory Detail.sql": (
        "5275b2c92423f1b35774265458115cd82383a7a452c3cc016869a67e09cb745d"
    ),
    "Trops Measures - SOFA.sql": "0a2bc680f5d902c7e461b93d3ee17e7ab3b851869b61a93a79d7025ab3d4f170",
    "Trops Measures - Delta SOFA.sql": (
        "9808aca5a40685b9a2b8c7aa3ad9ef77ebaf85466cfc8295b8a46ee2f1e00e65"
    ),
    "delta SOFA final.sql": "16012b237145a0e1223f948fcbe3ba6ad98456e6939ba12f88a19c38145831ab",
}
CONTRACT_HASH = fingerprint({"profile": PROFILE, "source": SOURCE_HASHES})
QUALIFICATION = "Historical source-mapped; not execution-validated"


def profile_provenance(profile):
    if profile.profile != PROFILE:
        return {"profile": profile.profile, "qualification": "Declared experimental profile"}
    default = ScoringProfile(profile=PROFILE).to_dict()
    deviations = {k: v for k, v in profile.to_dict().items() if v != default[k]}
    return {
        "profile": PROFILE,
        "source_commit": SOURCE_COMMIT,
        "source_files_sha256": dict(SOURCE_HASHES),
        "contract_sha256": CONTRACT_HASH,
        "qualification": QUALIFICATION
        if not deviations
        else "Modified historical-profile experiment; not execution-validated",
        "deviations": deviations,
        "input_boundary": "normalized values, support flags and resolved encounter partitions",
        "clock": profile.timezone,
        "deployment_timezone_known": False,
    }


@dataclass(frozen=True)
class ObservationV3(ObservationConfig):
    baseline_start_offset_minutes: int = 0

    def validate(self):
        super().validate()
        if self.baseline_start_offset_minutes < 0:
            raise ValueError("Baseline observation offset must be nonnegative")


@dataclass(frozen=True)
class ScenarioV3(ScenarioConfig):
    observation: ObservationV3 = ObservationV3()

    def validate(self):
        # Include the endpoint only when generation was specified to reach it.
        if (
            self.scoring.profile == PROFILE
            and self.horizon.end_minute == self.scoring.acute_end_minute
        ):
            object.__setattr__(
                self, "horizon", replace(self.horizon, end_minute=self.horizon.end_minute + 1)
            )
        super().validate()
        if (
            self.horizon.include_baseline
            and self.observation.baseline_start_offset_minutes
            + self.observation.baseline_exposure_minutes
            > self.horizon.baseline_generation_minutes
        ):
            raise ValueError("Baseline observation window exceeds generated history")

    @property
    def condition_id(self):
        data = self.to_dict()
        if self.scoring.profile == PROFILE:
            data = {**data, "historical_contract_sha256": CONTRACT_HASH}
        return fingerprint(data)


def historical_time(minute, admit, profile):
    """Oracle DATE arithmetic on the declared local wall clock, not elapsed DST days."""
    local_admit = admit.tz_localize(None)
    stamp = local_admit + pd.Timedelta(minutes=minute)
    relative = (stamp - local_admit).total_seconds() / 86400
    begin, end = profile.acute_begin_minute / 1440, profile.acute_end_minute / 1440
    day = 0 if begin <= relative <= end else math.trunc(relative) - (relative < begin)
    quarter = math.trunc(abs(relative - day) * 4) + 1
    return stamp, int(day), quarter, begin <= relative <= end


def historical_isoformat(stamp, timezone):
    """Label wall time without inventing an instant in a DST gap or repeated hour.

    The scoring clock is declared in resolved_windows.timezone. A unique local
    instant retains its offset (including +00:00 for unchanged UTC exports).
    Otherwise serialize the original local label without a UTC offset.
    """
    local = stamp.tz_localize(None)
    instant = local.tz_localize(timezone, ambiguous="NaT", nonexistent="NaT")
    return (local if pd.isna(instant) else instant).isoformat()


def validate_context(row):
    key = row.get("ce_admit_dts")
    if not isinstance(key, str):
        raise ValueError("Historical events require a resolved ce_admit_dts partition")
    timestamp = pd.Timestamp(key)
    if timestamp.tzinfo is None:
        raise ValueError("Resolved encounter partition requires an explicit timezone")
    row["ce_admit_dts"] = timestamp.tz_convert("UTC").isoformat()
    for field in ("invasive_ind", "support_ind"):
        if type(row.get(field)) is not bool:
            raise ValueError(f"Historical normalized context requires Boolean {field}")


def synthetic_context(events, admit_dts):
    """Adapt prescribed synthetic support; this does not infer clinical episodes."""
    result = []
    for event in events:
        row = dict(event)
        label = row["support_type"]
        row.update(
            {
                "ce_admit_dts": admit_dts,
                "invasive_ind": label in {"IMV", "SURG IMV"},
                "support_ind": label in {"HFNC", "NIPPV"},
                "support_context_origin": "prescribed_synthetic_context",
            }
        )
        result.append(row)
    return result
