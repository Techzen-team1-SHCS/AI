from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd


class DeviationLevel(str, Enum):
    """Mức độ sai lệch theo ba dải (dùng cho cảnh báo / drift)."""

    NORMAL = "normal"
    WARNING = "warning"
    DRIFT = "drift"


@dataclass(frozen=True)
class ThreeBandThresholds:
    """
    Hai ngưỡng trên cùng thang đo với cột `error` (absolute hoặc percentage).

    - error <= max_error_normal  → normal
    - max_error_normal < error <= max_error_warning → warning
    - error > max_error_warning → drift
    """

    max_error_normal: float
    max_error_warning: float

    def __post_init__(self) -> None:
        if self.max_error_normal >= self.max_error_warning:
            raise ValueError(
                "Cần max_error_normal < max_error_warning "
                f"(hiện tại: {self.max_error_normal}, {self.max_error_warning})"
            )


def classify_deviation_level(error: float, *, thresholds: ThreeBandThresholds) -> DeviationLevel:
    """
    Gán mức normal / warning / drift cho một giá trị error.

    - NaN: coi là normal (không đủ dữ liệu để phân loại).
    """
    if error is None or (isinstance(error, float) and np.isnan(error)):
        return DeviationLevel.NORMAL
    e = float(error)
    if e <= thresholds.max_error_normal:
        return DeviationLevel.NORMAL
    if e <= thresholds.max_error_warning:
        return DeviationLevel.WARNING
    return DeviationLevel.DRIFT


def infer_three_band_thresholds_from_errors(
    errors: pd.Series,
    *,
    normal_quantile: float = 0.75,
    warning_quantile: float = 0.95,
) -> ThreeBandThresholds:
    """
    Suy ra ngưỡng từ đặc điểm dataset: dùng phân vị của chuỗi sai lệch lịch sử.

    - normal_quantile: ví dụ 0.75 → ~75% quan sát coi là "bình thường" trở xuống
    - warning_quantile: ví dụ 0.95 → ranh giới warning vs drift

    Yêu cầu: 0 < normal_quantile < warning_quantile < 1
    """
    if not (0 < normal_quantile < warning_quantile < 1):
        raise ValueError("Cần 0 < normal_quantile < warning_quantile < 1")

    s = errors.dropna().astype("float64")
    if s.empty:
        raise ValueError("Chuỗi errors rỗng sau khi bỏ NaN, không suy ra được ngưỡng")

    qn = float(s.quantile(normal_quantile))
    qw = float(s.quantile(warning_quantile))
    if qn >= qw:
        eps = max(1e-9, abs(qn) * 1e-6)
        qw = qn + eps
    return ThreeBandThresholds(max_error_normal=qn, max_error_warning=qw)


def add_deviation_level_column(
    df: pd.DataFrame,
    *,
    error_col: str = "error",
    out_col: str = "deviation_level",
    thresholds: ThreeBandThresholds,
) -> pd.DataFrame:
    """Thêm cột mức normal/warning/drift cho từng dòng (theo cột error)."""
    if error_col not in df.columns:
        raise ValueError(f"Thiếu cột: {error_col}")
    out = df.copy()

    def _one(v: object) -> str:
        if pd.isna(v):
            return DeviationLevel.NORMAL.value
        return classify_deviation_level(float(v), thresholds=thresholds).value

    out[out_col] = out[error_col].map(_one)
    return out
