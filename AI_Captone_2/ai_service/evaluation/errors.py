from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd


class ErrorType(str, Enum):
    ABSOLUTE = "absolute"
    PERCENTAGE = "percentage"


@dataclass(frozen=True)
class ErrorConfig:
    """
    Error computation config.

    - absolute_error = |actual - forecast|
    - percentage_error = |actual - forecast| / |actual|

    For percentage error:
    - if actual == 0 => percentage_error = NaN (avoid division by zero)
    """

    error_type: ErrorType = ErrorType.ABSOLUTE
    forecast_col: str = "yhat"
    actual_col: str = "y"


def compute_forecast_actual_error(
    df: pd.DataFrame,
    *,
    config: ErrorConfig,
    keep_input_cols: bool = True,
) -> pd.DataFrame:
    """
    Compute error between forecast and actual values.

    Expected columns:
    - `ds` (time index)
    - `config.actual_col` (actual)
    - `config.forecast_col` (forecast)
    """

    required = {"ds", config.actual_col, config.forecast_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if keep_input_cols:
        out = df.copy()
    else:
        out = df[["ds", config.actual_col, config.forecast_col]].copy()

    actual = out[config.actual_col].astype("float64")
    forecast = out[config.forecast_col].astype("float64")

    out["absolute_error"] = (actual - forecast).abs()
    out["percentage_error"] = _compute_percentage_error(actual=actual, absolute_error=out["absolute_error"])

    out["error"] = (
        out["absolute_error"]
        if config.error_type == ErrorType.ABSOLUTE
        else out["percentage_error"]
    )
    return _reorder_ds_first(out)


def _compute_percentage_error(*, actual: pd.Series, absolute_error: pd.Series) -> pd.Series:
    denom = actual.abs()
    with np.errstate(divide="ignore", invalid="ignore"):
        pct_error = absolute_error / denom
    return pct_error.where(denom != 0, np.nan)


def _reorder_ds_first(df: pd.DataFrame) -> pd.DataFrame:
    cols = list(df.columns)
    if "ds" in cols:
        cols = ["ds"] + [c for c in cols if c != "ds"]
        return df[cols]
    return df

