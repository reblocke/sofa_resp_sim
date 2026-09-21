"""Bounded, source-linked orchestration around the shared respiratory scoring rules.

Only documented events are accepted here. The v2 adapter never receives latent
arrays and never imputes denominator evidence from hidden patient state.
"""

from __future__ import annotations

import bisect
import math
from typing import get_args

import pandas as pd

from .experiment_config import ScoringProfile, SupportLabel
from .historical_trops import PROFILE, historical_time, profile_provenance, validate_context
from .resp_scoring import _apply_resp_detail_cap, _assign_fio2_priority, _assign_sofa_rubric
from .resp_utils import oracle_round, spo2_to_pao2

INVA = {"IMV", "SURG IMV"}
EXPANDED = {"HFNC", "NIPPV", "IMV", "SURG IMV"}
FINAL_LEGACY = {"IMV", "NIPPV"}
FIRST_EXCLUSION = (
    "oxygenation_missing",
    "conversion_disabled",
    "conversion_unavailable",
    "denominator_missing",
    "outside_analysis_windows",
    "fio2_not_recent",
)


def _finite(value, field, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number")
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f"{field} is outside its allowed range")
    return float(value)


def _validate_events(events, historical=False):
    records, ids, patients = [], set(), set()
    for original in events:
        row = dict(original)
        event_id = row.get("event_id")
        if not isinstance(event_id, str) or not event_id or event_id in ids:
            raise ValueError("Every documented event needs a unique nonempty event_id")
        ids.add(event_id)
        patient_id = row.get("patient_id")
        if isinstance(patient_id, bool) or not isinstance(patient_id, int) or patient_id < 0:
            raise ValueError("patient_id must be a nonnegative integer")
        patients.add(patient_id)
        if row.get("event_type") not in ("oxygenation", "fio2"):
            raise ValueError("Unknown documented event type")
        for field in ("measurement_minute", "available_minute"):
            row[field] = _finite(row.get(field), field)
        if row.get("support_type", "UNKNOWN") not in (
            *get_args(SupportLabel),
            *(("OSA",) if historical else ()),
        ):
            raise ValueError("Unknown support_type")
        row.setdefault("support_type", "UNKNOWN")
        for field, low, high in [
            ("spo2_obs", 0, 100),
            ("pao2_meas", 0, None),
            ("fio2_set_fraction", 0.21, 1),
            ("fio2_meas_fraction", 0.21, 1),
            ("fio2_abg_fraction", 0.21, 1),
            ("flow_lpm", 0, 15),
        ]:
            if row.get(field) is not None:
                row[field] = _finite(row[field], field, low, high)
                if field == "pao2_meas" and row[field] == 0:
                    raise ValueError("Measured PaO2 must be positive")
        if "is_room_air" in row and type(row["is_room_air"]) is not bool:
            raise ValueError("is_room_air must be boolean")
        if historical:
            validate_context(row)
        records.append(row)
    if len(patients) > 1:
        raise ValueError("Score one patient at a time; do not join patients' context streams")
    return sorted(records, key=lambda e: (e["measurement_minute"], e["event_id"]))


def _fio2_context(row, historical=False):
    """Explicit fraction-to-percent adapter to the shared legacy priority function."""
    compatible = {
        "is_room_air": row.get("is_room_air", False),
        "invasive_ind": row["invasive_ind"] if historical else row["support_type"] in INVA,
        "oxygen_flow_rate": row.get("flow_lpm"),
    }
    for source in ("set", "meas", "abg"):
        value = row.get(f"fio2_{source}_fraction")
        compatible[f"fio2_{source}"] = None if value is None else value * 100
    value, priority = _assign_fio2_priority(compatible)
    if pd.isna(value):
        return None
    if compatible["is_room_air"]:
        method = "documented_room_air"
    elif priority == 5:
        method = "low_flow_proxy"
    else:
        order = ("set", "meas", "abg") if compatible["invasive_ind"] else ("meas", "set", "abg")
        method = next(
            f"fio2_{source}" for source in order if compatible[f"fio2_{source}"] is not None
        )
    return {
        **row,
        "chosen_fio2_fraction": value / 100,
        "priority": int(priority),
        "inference_method": method,
        "invasive_ind": compatible["invasive_ind"],
    }


class EvidenceIndex:
    def __init__(self, records, historical=False):
        self.historical = historical
        self.groups = {False: [], True: []} if not historical else {}
        for row in records:
            if row["event_type"] == "fio2":
                context = _fio2_context(row, historical)
                if context is not None:
                    key = (
                        (context["ce_admit_dts"], context["invasive_ind"])
                        if historical
                        else context["invasive_ind"]
                    )
                    self.groups.setdefault(key, []).append(context)
        self.times = {
            key: [r["measurement_minute"] for r in rows] for key, rows in self.groups.items()
        }

    def lookup(self, event, profile):
        key = (
            (event["ce_admit_dts"], event["invasive_ind"])
            if self.historical
            else event["support_type"] in INVA
        )
        rows, times = self.groups.get(key, []), self.times.get(key, [])
        minute = event["measurement_minute"]

        def window(low, high, reverse=False):
            start, end = bisect.bisect_left(times, low), bisect.bisect_right(times, high)
            indices = range(end - 1, start - 1, -1) if reverse else range(start, end)
            for i in indices:
                row = rows[i]
                if (
                    profile.availability == "retrospective"
                    or row["available_minute"] <= event["available_minute"]
                ):
                    return row
            return None

        current = window(minute, minute)
        backward = window(minute - 14, minute - 1, reverse=True)
        forward = window(minute, minute + 5)
        day = window(minute - 1440, minute, reverse=True)
        recent = backward or forward
        # Explicit contemporaneous room-air documentation retains the legacy override.
        if current and current.get("is_room_air") and event["support_type"] == "ROOM_AIR":
            selected = current
        elif profile.lookup == "contemporaneous_first":
            selected = current or backward or forward or day
        else:
            selected = backward or forward or day
        return (
            selected,
            recent,
            {"current": current, "backward": backward, "forward": forward, "day": day},
        )


def _period_record(events, kind, profile):
    qualifying = [e for e in events if e[f"qualifies_{kind}"]]
    if not qualifying:
        return {
            "algorithm_score": 0,
            "pre_suppression_score": None,
            "score_status": "no_qualifying_data",
            "qualifying_pf_count": 0,
            "selected_event_id": None,
            "tied_event_ids": [],
            "suppressed": False,
        }
    pre_score = max(e["support_adjusted_score"] for e in qualifying)
    suppressed = False
    if kind == "acute" and profile.single_record_suppression and len(qualifying) == 1:
        event = qualifying[0]
        if not event["final_support_eligible"] and event["support_adjusted_score"] > 0:
            event["reported_score"] = 0
            event["singleton_suppressed"] = True
            suppressed = True

    def ordering(e):
        if kind == "acute":
            return (
                -e["reported_score"],
                -int(e["final_support_eligible"]),
                e["measurement_minute"],
                e["event_id"],
            )
        if profile.baseline_selection == "latest_day":
            return (
                -e["bin_epoch"],
                -e["reported_score"],
                -e["measurement_minute"],
                e["event_id"],
            )
        return (
            -e["reported_score"],
            -e["bin_epoch"],
            -e["measurement_minute"],
            e["event_id"],
        )

    winner = min(qualifying, key=ordering)
    score = int(winner["reported_score"])
    tied = [
        e["event_id"]
        for e in qualifying
        if e["reported_score"] == score
        and (
            kind == "acute"
            or profile.baseline_selection != "latest_day"
            or e["bin_epoch"] == winner["bin_epoch"]
        )
    ]
    winner[f"selected_{kind}"] = True
    return {
        "algorithm_score": score,
        "pre_suppression_score": int(pre_score),
        "score_status": "suppressed_only" if suppressed else "observed_scored",
        "qualifying_pf_count": len(qualifying),
        "selected_event_id": winner["event_id"],
        "tied_event_ids": sorted(tied),
        "suppressed": suppressed,
    }


def score_documented_events(
    events: list[dict],
    admit_dts: str,
    profile: ScoringProfile | None = None,
) -> dict:
    profile = profile or ScoringProfile()
    admit = pd.Timestamp(admit_dts)
    if admit.tzinfo is None:
        raise ValueError("Admission must have an explicit timezone")
    admit = admit.tz_convert(profile.timezone)
    baseline_begin = admit.normalize() - pd.DateOffset(months=profile.baseline_months)
    baseline_end = admit.normalize() - pd.DateOffset(days=profile.baseline_end_days)
    historical = profile.profile == PROFILE
    records = _validate_events(events, historical)
    index = EvidenceIndex(records, historical)
    quarter_evidence = set()
    if historical:
        for row in records:
            if row["event_type"] == "fio2" and _fio2_context(row, True) is not None:
                _, day, quarter, _ = historical_time(row["measurement_minute"], admit, profile)
                quarter_evidence.add((row["ce_admit_dts"], day, quarter))
    trace = []
    for original in records:
        if original["event_type"] != "oxygenation":
            continue
        event = dict(original)
        minute = event["measurement_minute"]
        timestamp = admit + pd.Timedelta(minutes=minute)
        adjusted = admit if profile.acute_begin_minute <= minute < 0 else timestamp
        if profile.binning == "calendar":
            bin_start = adjusted.normalize()
        else:
            days = math.floor((adjusted - admit).total_seconds() / 86400)
            bin_start = admit + pd.Timedelta(days=days)
        in_acute = profile.acute_begin_minute <= minute < profile.acute_end_minute
        in_baseline = (
            minute < profile.acute_begin_minute and baseline_begin <= bin_start <= baseline_end
        )
        if historical:
            timestamp, day, quarter, in_acute = historical_time(minute, admit, profile)
            if profile.binning == "admission":
                day = math.floor(
                    (timestamp.tz_localize(None) - admit.tz_localize(None)).total_seconds() / 86400
                )
            bin_start = admit + pd.DateOffset(days=day)
            in_baseline = baseline_begin <= timestamp <= baseline_end and not in_acute
        selected, recent, candidates = index.lookup(event, profile)
        measured, saturation = event.get("pao2_meas"), event.get("spo2_obs")
        converted = None
        if saturation is not None and profile.conversion == "spo2_or_measured":
            value = spo2_to_pao2(saturation)
            converted = None if pd.isna(value) else float(value)
        pao2 = measured if measured is not None else converted
        pao2_source = (
            "measured" if measured is not None else "estimated" if converted is not None else None
        )
        fio2 = selected["chosen_fio2_fraction"] if selected else None
        inferred_room_air = bool(
            historical
            and fio2 is None
            and pao2_source == "estimated"
            and (event["ce_admit_dts"], day, quarter) not in quarter_evidence
        )
        if inferred_room_air:
            fio2 = 0.21
        pf = None if pao2 is None or fio2 is None else oracle_round(pao2 / fio2, 2)
        rubric = (
            None
            if pf is None
            else int(
                _assign_sofa_rubric(
                    {"pf_ratio_temp": pf, "altitude_factor": profile.threshold_factor}
                )
            )
        )
        label = event["support_type"]
        detail = (
            None
            if rubric is None
            else int(
                _apply_resp_detail_cap(
                    {
                        "sofa_resp_rubric": rubric,
                        "invasive_ind": event["invasive_ind"] if historical else label in INVA,
                        "support_ind": event["support_ind"]
                        if historical
                        else label in {"HFNC", "NIPPV"},
                    }
                )
            )
        )
        final_eligible = label in (
            EXPANDED if profile.support_eligibility == "expanded" else FINAL_LEGACY
        )
        capped = None if detail is None else min(detail, 4 if final_eligible else 2)
        reasons = []
        if measured is None and saturation is None:
            reasons.append("oxygenation_missing")
        elif pao2 is None:
            reasons.append(
                "conversion_disabled"
                if profile.conversion == "measured_only"
                else "conversion_unavailable"
            )
        if fio2 is None:
            reasons.append("denominator_missing")
        if not in_acute and not in_baseline:
            reasons.append("outside_analysis_windows")
        if in_acute and pf is not None and recent is None:
            reasons.append("fio2_not_recent")
        source_age = minute - selected["measurement_minute"] if selected else None
        event.update(
            {
                "measurement_time": timestamp.isoformat(),
                "available_time": (
                    admit + pd.Timedelta(minutes=event["available_minute"])
                ).isoformat(),
                "bin_start": bin_start.isoformat(),
                "bin_epoch": bin_start.timestamp(),
                "pao2_calc_mmhg": converted,
                "pao2_used_mmhg": pao2,
                "pao2_source": pao2_source,
                "fio2_fraction": fio2,
                "fio2_source_event_id": selected["event_id"] if selected else None,
                "fio2_source_age_minutes": source_age,
                "fio2_time_direction": None
                if source_age is None
                else "backward"
                if source_age > 0
                else "forward"
                if source_age < 0
                else "current",
                "fio2_inference_method": selected["inference_method"]
                if selected
                else "historical_quarter_room_air_fallback"
                if inferred_room_air
                else None,
                "fio2_lookup_candidates": {
                    key: value["event_id"] if value else None for key, value in candidates.items()
                },
                "pf_ratio_mmhg": pf,
                "threshold_factor": profile.threshold_factor,
                "raw_rubric": rubric,
                "detail_support_score": detail,
                "support_adjusted_score": capped,
                "reported_score": capped,
                "detail_support_capped": rubric is not None and detail != rubric,
                "final_support_capped": detail is not None and capped != detail,
                "final_support_eligible": final_eligible,
                "singleton_suppressed": False,
                "in_acute_target": bool(in_acute),
                "in_baseline_window": bool(in_baseline),
                "qualifies_acute": bool(in_acute and pf is not None and recent is not None),
                "qualifies_baseline": bool(in_baseline and pf is not None),
                "exclusion_reasons": reasons,
                "first_exclusion": reasons[0] if reasons else None,
                "selected_acute": False,
                "selected_baseline": False,
            }
        )
        if historical:
            event.update(
                {
                    "historical_day_index": day,
                    "historical_quarter": quarter,
                    "historical_room_air_fallback": inferred_room_air,
                }
            )
        trace.append(event)
    acute = _period_record(trace, "acute", profile)
    baseline = _period_record(trace, "baseline", profile)
    signed = acute["algorithm_score"] - baseline["algorithm_score"]
    evaluable = acute["qualifying_pf_count"] > 0 and baseline["qualifying_pf_count"] > 0
    return {
        **({"profile_provenance": profile_provenance(profile)} if historical else {}),
        "profile": profile.to_dict(),
        "acute": acute,
        "baseline": baseline,
        "delta_legacy": max(signed, 0),
        "delta_signed": signed,
        "delta_evaluable": signed if evaluable else None,
        "delta_nonnegative_evaluable": max(signed, 0) if evaluable else None,
        "events": trace,
        "context_events": [e for e in records if e["event_type"] == "fio2"],
        "first_exclusion_hierarchy": list(FIRST_EXCLUSION),
        "resolved_windows": {
            "timezone": profile.timezone,
            "binning": profile.binning,
            "acute_begin": (admit + pd.Timedelta(minutes=profile.acute_begin_minute)).isoformat(),
            ("acute_end_inclusive" if historical else "acute_end_exclusive"): (
                admit + pd.Timedelta(minutes=profile.acute_end_minute)
            ).isoformat(),
            "baseline_begin_inclusive": baseline_begin.isoformat(),
            "baseline_end_day_inclusive": baseline_end.isoformat(),
        },
    }
