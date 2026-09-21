"""Patient-level estimands and pointwise Monte Carlo uncertainty for paired runs."""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
from scipy.stats import binomtest

CONFIDENCE = 0.95
STATUSES = ("observed_scored", "suppressed_only", "no_qualifying_data")
UNCERTAINTY_SCOPE = "pointwise Monte Carlo uncertainty conditional on the illustrative model"


def _count(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def wilson_probability(k: int, n: int) -> dict:
    _count(k, "k")
    _count(n, "n")
    if k > n:
        raise ValueError("k cannot exceed n")
    bounds = binomtest(k, n).proportion_ci(CONFIDENCE, method="wilson") if n >= 2 else None
    return {
        "numerator": k,
        "denominator": n,
        "estimate": k / n if n else None,
        "mcse": math.sqrt((k / n) * (1 - k / n) / (n - 1)) if n >= 2 else None,
        "lower": float(bounds.low) if bounds else None,
        "upper": float(bounds.high) if bounds else None,
        "interval_method": "wilson" if bounds else None,
        "confidence_level": CONFIDENCE if bounds else None,
        "uncertainty_unavailable_reason": "fewer_than_two_patients" if n < 2 else None,
    }


def paired_binary(n_plus: int, n_minus: int, n: int) -> dict:
    for value, name in [(n_plus, "n_plus"), (n_minus, "n_minus"), (n, "n")]:
        _count(value, name)
    if n_plus + n_minus > n:
        raise ValueError("Discordances cannot exceed paired N")
    estimate = (n_plus - n_minus) / n if n else None
    lower = upper = mcse = None
    if n >= 2:
        mcse = math.sqrt(max(0, (n_plus + n_minus - n * estimate**2) / ((n - 1) * n)))
        component_confidence = 1 - (1 - CONFIDENCE) / 2
        plus = binomtest(n_plus, n).proportion_ci(component_confidence, method="exact")
        minus = binomtest(n_minus, n).proportion_ci(component_confidence, method="exact")
        lower, upper = max(-1.0, plus.low - minus.high), min(1.0, plus.high - minus.low)
    return {
        "n_plus": n_plus,
        "n_minus": n_minus,
        "denominator": n,
        "estimate": estimate,
        "percentage_point_difference": 100 * estimate if estimate is not None else None,
        "mcse": mcse,
        "lower": float(lower) if lower is not None else None,
        "upper": float(upper) if upper is not None else None,
        "interval_method": "paired_exact_discordance_bonferroni" if n >= 2 else None,
        "confidence_level": CONFIDENCE if n >= 2 else None,
        "uncertainty_unavailable_reason": "fewer_than_two_patients" if n < 2 else None,
        "structural_identity": False,
    }


def empirical_mean(values: list[float]) -> dict:
    n = len(values)
    return {
        "denominator": n,
        "estimate": float(np.mean(values)) if n else None,
        "mcse": float(np.std(values, ddof=1) / np.sqrt(n)) if n >= 2 else None,
        "lower": None,
        "upper": None,
        "interval_method": None,
        "confidence_level": None,
        "uncertainty_unavailable_reason": "fewer_than_two_patients" if n < 2 else None,
    }


def _metrics():
    result = {}
    for threshold in (1, 2, 3):
        result[f"score_ge{threshold}"] = (
            "probability",
            lambda row, t=threshold: row["algorithm_score"] >= t,
            "all_patients",
        )
    for score in range(5):
        result[f"score_eq{score}"] = (
            "probability",
            lambda row, s=score: row["algorithm_score"] == s,
            "all_patients",
        )
    for status in STATUSES[1:]:
        result[status] = (
            "probability",
            lambda row, s=status: row["score_status"] == s,
            "all_patients",
        )
    result["qualifying_pf_count"] = (
        "records",
        lambda row: row["qualifying_pf_count"],
        "all_patients",
    )
    result["missing_baseline"] = (
        "probability",
        lambda row: row["baseline_score_status"] == "no_qualifying_data",
        "all_patients",
    )
    for threshold in (1, 2):
        result[f"delta_legacy_ge{threshold}"] = (
            "probability",
            lambda row, t=threshold: row["delta_legacy"] >= t,
            "all_patients",
        )
        result[f"delta_evaluable_ge{threshold}"] = (
            "probability",
            lambda row, t=threshold: row["delta_evaluable"] >= t,
            "acute_and_baseline_evaluable",
        )
    for delta in range(-4, 5):
        result[f"delta_signed_eq{delta}"] = (
            "probability",
            lambda row, d=delta: row["delta_signed"] == d,
            "all_patients",
        )
        result[f"delta_evaluable_eq{delta}"] = (
            "probability",
            lambda row, d=delta: row["delta_evaluable"] == d,
            "acute_and_baseline_evaluable",
        )
    return result


METRICS = _metrics()


def _eligible(row, population):
    return population == "all_patients" or row["delta_evaluable"] is not None


def summarize_paired_scores(scores: list[dict], comparator_id: str) -> dict:
    """Reject incomplete/duplicate pairs; never replace computation failures with zeros."""
    grouped = defaultdict(dict)
    run_ids = set()
    for row in scores:
        patient, condition = row["patient_id"], row["condition_id"]
        if patient in grouped[condition]:
            raise ValueError("Duplicate patient-condition score row")
        if row["score_status"] not in STATUSES or row["algorithm_score"] not in range(5):
            raise ValueError("Invalid score or evidence status")
        grouped[condition][patient] = row
        run_ids.add(row["experiment_run_id"])
    if len(run_ids) != 1 or comparator_id not in grouped:
        raise ValueError("One nonempty run with a comparator is required")
    comparator = grouped[comparator_id]
    if any(set(rows) != set(comparator) for rows in grouped.values()):
        raise ValueError("Incomplete paired cohort; patient IDs must match in every condition")
    run_id = next(iter(run_ids))
    summary, contrasts, transitions, reclassification = [], [], [], []
    for condition_id, rows in sorted(grouped.items()):
        common = {"experiment_run_id": run_id, "condition_id": condition_id}
        for metric, (unit, value, population) in METRICS.items():
            eligible = [r for r in rows.values() if _eligible(r, population)]
            values = [value(r) for r in eligible]
            estimate = (
                wilson_probability(sum(values), len(values))
                if unit == "probability"
                else empirical_mean(values)
            )
            summary.append(
                {**common, "metric": metric, "unit": unit, "population": population, **estimate}
            )
            pairs = [
                (comparator[p], rows[p])
                for p in sorted(rows)
                if _eligible(comparator[p], population) and _eligible(rows[p], population)
            ]
            differences = [
                int(value(v)) - int(value(c)) if unit == "probability" else value(v) - value(c)
                for c, v in pairs
            ]
            estimate = (
                paired_binary(differences.count(1), differences.count(-1), len(pairs))
                if unit == "probability"
                else empirical_mean(differences)
            )
            # Only identical normalized configurations prove structural identity.
            if unit == "probability":
                estimate["structural_identity"] = condition_id == comparator_id
            contrasts.append(
                {
                    **common,
                    "comparator_id": comparator_id,
                    "metric": metric,
                    "unit": "probability_difference" if unit == "probability" else "records",
                    "population": population,
                    "direction": "variant_minus_comparator",
                    **estimate,
                }
            )
        for table, states in [
            ("algorithm", list(range(5))),
            ("evidence", [*range(5), "U"]),
            ("status", list(STATUSES)),
        ]:
            cells = defaultdict(list)

            def state(row, table=table):
                if table == "status":
                    return row["score_status"]
                if table == "evidence" and row["score_status"] == "no_qualifying_data":
                    return "U"
                return row["algorithm_score"]

            for patient in sorted(rows):
                cells[state(comparator[patient]), state(rows[patient])].append(patient)
            for before in states:
                for after in states:
                    patients = cells[before, after]
                    transitions.append(
                        {
                            **common,
                            "comparator_id": comparator_id,
                            "table": table,
                            "comparator_state": before,
                            "variant_state": after,
                            "count": len(patients),
                            "denominator": len(rows),
                            "patient_ids": patients,
                        }
                    )
        for population in ("all_patients", "both_conditions_evaluable"):
            patients = [
                p
                for p in rows
                if population == "all_patients"
                or all(r["score_status"] != "no_qualifying_data" for r in (rows[p], comparator[p]))
            ]
            differences = [
                rows[p]["algorithm_score"] - comparator[p]["algorithm_score"] for p in patients
            ]
            for name, count in [
                ("upward", sum(d > 0 for d in differences)),
                ("downward", sum(d < 0 for d in differences)),
                ("unchanged", differences.count(0)),
            ]:
                reclassification.append(
                    {
                        **common,
                        "comparator_id": comparator_id,
                        "population": population,
                        "direction": name,
                        **wilson_probability(count, len(patients)),
                    }
                )
    return {
        "condition_summary": summary,
        "paired_contrasts": contrasts,
        "transitions": transitions,
        "reclassification": reclassification,
        "uncertainty_scope": UNCERTAINTY_SCOPE,
        "algorithm_zero_convention": (
            "No qualifying data and suppressed singletons retain algorithm zero; "
            "inspect evidence status."
        ),
        "metric_dictionary": {
            name: {"unit": unit, "population": population}
            for name, (unit, _, population) in METRICS.items()
        },
    }
