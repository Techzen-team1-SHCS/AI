from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from ai_service.evaluation.errors import ErrorConfig, compute_forecast_actual_error


@dataclass(frozen=True)
class ComparisonConfig:
    ds_col: str = "ds"
    actual_col: str = "y"
    forecast_col: str = "yhat"
    save_csv_path: Optional[Path] = None


def compare_forecast_with_actual_over_time(
    *,
    forecast_df: pd.DataFrame,
    actual_df: pd.DataFrame,
    error_config: ErrorConfig,
    config: ComparisonConfig,
) -> pd.DataFrame:
    """
    Compare forecast vs actual by time index (ds) and compute error per point.

    Outputs a merged table including:
    - ds
    - actual (config.actual_col)
    - forecast (config.forecast_col)
    - error fields produced by compute_forecast_actual_error
    """

    ds_col = config.ds_col
    required_forecast = {ds_col, config.forecast_col}
    required_actual = {ds_col, config.actual_col}
    missing_forecast = required_forecast - set(forecast_df.columns)
    missing_actual = required_actual - set(actual_df.columns)
    if missing_forecast:
        raise ValueError(f"forecast_df missing columns: {sorted(missing_forecast)}")
    if missing_actual:
        raise ValueError(f"actual_df missing columns: {sorted(missing_actual)}")

    f = forecast_df[[ds_col, config.forecast_col]].copy()
    a = actual_df[[ds_col, config.actual_col]].copy()
    f[ds_col] = pd.to_datetime(f[ds_col])
    a[ds_col] = pd.to_datetime(a[ds_col])

    merged = a.merge(f, on=ds_col, how="inner", validate="one_to_one")

    # Let compute_forecast_actual_error handle absolute/percentage selection.
    # Its column names are configurable via error_config.
    error_config = ErrorConfig(
        error_type=error_config.error_type,
        forecast_col=config.forecast_col,
        actual_col=config.actual_col,
    )
    out = compute_forecast_actual_error(merged, config=error_config, keep_input_cols=True)
    out = out.sort_values(ds_col).reset_index(drop=True)

    if config.save_csv_path is not None:
        config.save_csv_path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(config.save_csv_path, index=False, encoding="utf-8")

    return out

