from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

import numpy as np
import pandas as pd


def oracle_round(value: float | int | None, ndigits: int = 0) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    quantize_exp = Decimal("1").scaleb(-ndigits)
    decimal_value = Decimal(str(value)).quantize(quantize_exp, rounding=ROUND_HALF_UP)
    return float(decimal_value)


def spo2_to_pao2(spo2: float | pd.Series | Iterable[float]) -> float | pd.Series:
    if isinstance(spo2, pd.Series):
        return spo2.apply(_spo2_to_pao2_scalar)
    if isinstance(spo2, (list, tuple, np.ndarray)):
        series = pd.Series(spo2, dtype="float64")
        return series.apply(_spo2_to_pao2_scalar).to_numpy()
    return _spo2_to_pao2_scalar(spo2)


def _spo2_to_pao2_scalar(spo2_value: float | int | None) -> float:
    if spo2_value is None or (isinstance(spo2_value, float) and np.isnan(spo2_value)):
        return np.nan
    if spo2_value < 50 or spo2_value > 96:
        return np.nan
    s = spo2_value / 100
    if s <= 0 or s >= 1:
        return np.nan
    x = 11700 / ((1 / s) - 1)
    y = math.sqrt(50**3 + x**2)
    pao2_calc = (y + x) ** (1 / 3) - (y - x) ** (1 / 3)
    return oracle_round(pao2_calc, 1)
