from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_PROBABILITY_COLUMNS = [f"p_sofa_{score}" for score in range(5)]
COUNT_REFERENCE_COLUMNS = ["sofa_pulm", "count"]


def load_builtin_reference(path: str | Path) -> pd.DataFrame:
    reference_path = Path(path)
    if not reference_path.exists():
        raise FileNotFoundError(f"Reference file not found: {reference_path}")

    frame = pd.read_csv(reference_path)
    return normalize_reference_distribution(frame)


def normalize_reference_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        raise ValueError("Reference table is empty.")

    has_probability_schema = all(column in frame.columns for column in REQUIRED_PROBABILITY_COLUMNS)
    has_count_schema = all(column in frame.columns for column in COUNT_REFERENCE_COLUMNS)

    # Deterministic precedence: if both schemas are present, use probability columns.
    if has_probability_schema:
        return _normalize_probability_frame(frame)
    if has_count_schema:
        return _normalize_count_frame(frame)
    raise ValueError(
        "Reference table must include either probability columns "
        f"{REQUIRED_PROBABILITY_COLUMNS} or count columns {COUNT_REFERENCE_COLUMNS}."
    )


def _normalize_probability_frame(frame: pd.DataFrame) -> pd.DataFrame:
    row = pd.to_numeric(
        frame.loc[0, REQUIRED_PROBABILITY_COLUMNS],
        errors="coerce",
    )
    if row.isna().any():
        raise ValueError("Reference probability values must be numeric.")
    if (row < 0).any():
        raise ValueError("Reference probability values must be non-negative.")
    total = float(row.sum())
    if total <= 0:
        raise ValueError("Reference probabilities must sum to a positive value.")

    normalized = (row / total).to_frame().T
    normalized.columns = REQUIRED_PROBABILITY_COLUMNS
    return normalized.reset_index(drop=True)


def _normalize_count_frame(frame: pd.DataFrame) -> pd.DataFrame:
    counts = frame.loc[:, COUNT_REFERENCE_COLUMNS].copy()
    counts["sofa_pulm"] = pd.to_numeric(counts["sofa_pulm"], errors="coerce")
    counts["count"] = pd.to_numeric(counts["count"], errors="coerce")

    if counts.isna().any().any():
        raise ValueError("Count-form reference values must be numeric.")

    sofa_values = counts["sofa_pulm"].to_numpy(dtype=float)
    if not np.all(np.equal(np.mod(sofa_values, 1), 0)):
        raise ValueError("sofa_pulm values in count-form reference must be integers 0..4.")

    counts["sofa_pulm"] = counts["sofa_pulm"].astype(int)
    if ((counts["sofa_pulm"] < 0) | (counts["sofa_pulm"] > 4)).any():
        raise ValueError("sofa_pulm values in count-form reference must be in [0, 4].")
    if (counts["count"] < 0).any():
        raise ValueError("Count-form reference values must be non-negative.")

    grouped = counts.groupby("sofa_pulm", as_index=True)["count"].sum()
    totals = np.zeros(5, dtype=float)
    for score in range(5):
        totals[score] = float(grouped.get(score, 0.0))

    total = float(totals.sum())
    if total <= 0:
        raise ValueError("Count-form reference values must sum to a positive value.")

    normalized = pd.DataFrame(
        [[value / total for value in totals]],
        columns=REQUIRED_PROBABILITY_COLUMNS,
    )
    return normalized.reset_index(drop=True)
