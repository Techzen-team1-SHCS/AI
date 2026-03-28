from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RollingErrorConfig:
    """Cấu hình rolling trên cột sai lệch (theo số dòng liên tiếp theo thời gian)."""

    window_days: int
    error_col: str = "error"
    min_periods: int = 1


def _require_sorted_ds(df: pd.DataFrame, ds_col: str) -> pd.DataFrame:
    out = df.copy()
    if ds_col not in out.columns:
        raise ValueError(f"Thiếu cột thời gian: {ds_col}")
    out[ds_col] = pd.to_datetime(out[ds_col])
    return out.sort_values(ds_col).reset_index(drop=True)


def add_rolling_mean_error(
    df: pd.DataFrame,
    *,
    config: RollingErrorConfig,
    ds_col: str = "ds",
    out_col: str = "rolling_mean_error",
) -> pd.DataFrame:
    """
    Trung bình sai lệch trong cửa sổ `window_days` ngày gần nhất (theo thứ tự dòng).

    Phù hợp chuỗi ngày đã sắp xếp liên tục (như sau preprocess daily).
    """
    if config.window_days < 1:
        raise ValueError("window_days phải >= 1")
    if config.error_col not in df.columns:
        raise ValueError(f"Thiếu cột: {config.error_col}")

    out = _require_sorted_ds(df, ds_col)
    s = out[config.error_col].astype("float64")
    out[out_col] = s.rolling(
        window=config.window_days,
        min_periods=config.min_periods,
    ).mean()
    return out


def _count_exceeds_in_window(values: np.ndarray, threshold: float) -> float:
    """Đếm số phần tử trong cửa sổ có error > threshold (bỏ qua NaN)."""
    a = np.asarray(values, dtype=float)
    mask_ok = ~np.isnan(a)
    return float(np.sum(mask_ok & (a > threshold)))


def add_rolling_exceed_count(
    df: pd.DataFrame,
    *,
    config: RollingErrorConfig,
    threshold: float,
    ds_col: str = "ds",
    out_col: str = "rolling_exceed_count",
) -> pd.DataFrame:
    """
    Trong mỗi cửa sổ: đếm có bao nhiêu ngày có error > ngưỡng.

    Dùng để phát hiện sai lệch **kéo dài** (nhiều ngày liên tiếp trong window).
    """
    if config.window_days < 1:
        raise ValueError("window_days phải >= 1")
    out = _require_sorted_ds(df, ds_col)
    s = out[config.error_col].astype("float64")

    out[out_col] = s.rolling(
        window=config.window_days,
        min_periods=config.min_periods,
    ).apply(lambda w: _count_exceeds_in_window(w, threshold), raw=True)
    return out


@dataclass(frozen=True)
class PersistentDeviationConfig:
    """Đánh dấu khi trong cửa sổ có đủ số ngày vượt ngưỡng."""

    window_days: int
    threshold: float
    min_exceed_days: int
    error_col: str = "error"


def mark_persistent_large_deviation(
    df: pd.DataFrame,
    *,
    config: PersistentDeviationConfig,
    ds_col: str = "ds",
    count_col: str = "rolling_exceed_count",
    flag_col: str = "rolling_persistent_deviation",
) -> pd.DataFrame:
    """
    True nếu trong `window_days` ngày gần nhất có ít nhất `min_exceed_days` ngày error > threshold.
    """
    if config.min_exceed_days < 1:
        raise ValueError("min_exceed_days phải >= 1")
    if config.min_exceed_days > config.window_days:
        raise ValueError("min_exceed_days không được lớn hơn window_days")

    roll_cfg = RollingErrorConfig(
        window_days=config.window_days,
        error_col=config.error_col,
    )
    out = add_rolling_exceed_count(
        df,
        config=roll_cfg,
        threshold=config.threshold,
        ds_col=ds_col,
        out_col=count_col,
    )
    out[flag_col] = out[count_col] >= float(config.min_exceed_days)
    return out
