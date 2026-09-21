"""Deterministic event rules and explicit one/two-record encounter scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..core.experiment_config import ScientificConfig, ScoringProfile, SupportConfig
from ..core.experiment_scoring import score_documented_events


@dataclass(frozen=True)
class RuleExplorerRequest(ScientificConfig):
    source: Literal["spo2", "measured_pao2"] = "spo2"
    values: tuple[float, ...] = (49, 50, 90, 96, 97)
    supports: tuple[SupportConfig, ...] = (SupportConfig(),)
    scoring: ScoringProfile = ScoringProfile()
    records: Literal[1, 2] = 2

    def validate(self):
        if not self.values or not self.supports or len(self.values) * len(self.supports) > 1000:
            raise ValueError("Rule explorer requires 1..1000 value/support cells")
        for value in self.values:
            if self.source == "spo2" and not 0 <= value <= 100:
                raise ValueError("SpO2 values must be percentages in [0,100]")
            if self.source == "measured_pao2" and value <= 0:
                raise ValueError("Measured PaO2 values must be positive mmHg")
        if any(s.mode != "fixed" or s.segments for s in self.supports):
            raise ValueError("Rule explorer support must be constant and fixed")
        if self.scoring.acute_begin_minute > 0 or self.scoring.acute_end_minute <= 15:
            raise ValueError("Rule explorer target must include minutes 0 and 15")


def explore_rules(payload: dict) -> dict:
    request = RuleExplorerRequest.from_dict(payload)
    cells = []
    for i, value in enumerate(request.values):
        for j, support in enumerate(request.supports):
            events = []
            for record in range(request.records):
                common = {
                    "patient_id": 0,
                    "measurement_minute": record * 15,
                    "available_minute": record * 15,
                    "support_type": support.label,
                }
                events.extend(
                    [
                        {
                            **common,
                            "event_id": f"cell{i}:{j}:ox{record}",
                            "event_type": "oxygenation",
                            "spo2_obs": value if request.source == "spo2" else None,
                            "pao2_meas": value if request.source == "measured_pao2" else None,
                        },
                        {
                            **common,
                            "event_id": f"cell{i}:{j}:fio2{record}",
                            "event_type": "fio2",
                            "is_room_air": support.label == "ROOM_AIR",
                            "flow_lpm": support.flow_lpm,
                            "fio2_set_fraction": support.fio2_fraction
                            if support.label not in {"ROOM_AIR", "LOW_FLOW"}
                            else None,
                        },
                    ]
                )
            result = score_documented_events(events, "2024-01-01T06:00:00Z", request.scoring)
            event = result["events"][0]
            cells.append(
                {
                    "value_index": i,
                    "support_index": j,
                    "input_value": value,
                    "support": support.to_dict(),
                    "pao2_calc_mmhg": event["pao2_calc_mmhg"],
                    "pf_ratio_mmhg": event["pf_ratio_mmhg"],
                    "raw_rubric": event["raw_rubric"],
                    "event_trace": event,
                    "encounter": result["acute"],
                    "conversion_unavailable": request.source == "spo2"
                    and event["pao2_calc_mmhg"] is None,
                }
            )
    return {
        "schema_version": "rule_explorer_v2",
        "request": request.to_dict(),
        "cells": cells,
        "input_unit": "percent" if request.source == "spo2" else "mmHg",
        "monte_carlo": False,
        "caption": (
            f"Deterministic rules with {request.records} record(s), 15 minutes apart when two. "
            "Event rubric and support caps precede encounter suppression; "
            "unavailable conversion is not normal score zero."
        ),
    }
