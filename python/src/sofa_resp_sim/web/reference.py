from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_PROBABILITY_COLUMNS = [f"p_sofa_{score}" for score in range(5)]


def load_builtin_reference(path: str | Path) -> pd.DataFrame:
    reference_path = Path(path)
    if not reference_path.exists():
        raise FileNotFoundError(f"Reference file not found: {reference_path}")

    frame = pd.read_csv(reference_path)
    missing = [column for column in REQUIRED_PROBABILITY_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            "Reference CSV is missing required probability columns: "
            + ", ".join(sorted(missing))
        )
    if frame.empty:
        raise ValueError("Reference CSV is empty.")

    row = frame.loc[0, REQUIRED_PROBABILITY_COLUMNS].astype(float)
    total = float(row.sum())
    if total <= 0:
        raise ValueError("Reference probabilities must sum to a positive value.")

    normalized = (row / total).to_frame().T
    normalized.columns = REQUIRED_PROBABILITY_COLUMNS
    return normalized.reset_index(drop=True)
