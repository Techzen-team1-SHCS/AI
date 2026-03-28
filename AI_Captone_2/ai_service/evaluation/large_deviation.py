from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class LargeDeviationConfig:
    """
    Cấu hình phát hiện sai lệch lớn (so với một ngưỡng cố định).

    - Dùng cột `error_col` đã được tính trước (thường là `error` từ
      `compute_forecast_actual_error`, tương ứng absolute hoặc percentage).
    - Một dòng được coi là vượt ngưỡng khi: error > threshold.
    - Nếu error là NaN (ví dụ percentage khi actual=0): không đánh dấu vượt ngưỡng.
    """

    threshold: float
    error_col: str = "error"
    flag_col: str = "large_deviation"


def mark_large_deviations(df: pd.DataFrame, *, config: LargeDeviationConfig) -> pd.DataFrame:
    """
    Thêm cột boolean đánh dấu từng mốc thời gian có sai lệch vượt ngưỡng.

    Yêu cầu: DataFrame đã có cột `config.error_col`.
    """
    if config.error_col not in df.columns:
        raise ValueError(f"Thiếu cột error: {config.error_col}")

    out = df.copy()
    err = out[config.error_col].astype("float64")
    exceeds = err > config.threshold
    out[config.flag_col] = exceeds.fillna(False).astype(bool)
    return out


def count_large_deviations(df: pd.DataFrame, *, flag_col: str = "large_deviation") -> int:
    """Đếm số điểm được đánh dấu large_deviation == True."""
    if flag_col not in df.columns:
        raise ValueError(f"Thiếu cột cờ: {flag_col}")
    return int(df[flag_col].sum())
