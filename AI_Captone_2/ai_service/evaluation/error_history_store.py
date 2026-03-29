from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from ai_service.evaluation.threshold_policy import DeviationLevel, ThreeBandThresholds, add_deviation_level_column
from ai_service.evaluation.rolling_window import PersistentDeviationConfig, mark_persistent_large_deviation


@dataclass(frozen=True)
class ErrorHistoryStoreConfig:
    """Đường dẫn file CSV lưu lịch sử (append theo thời gian)."""

    csv_path: Path
    encoding: str = "utf-8"


def compute_run_operational_status(df: pd.DataFrame) -> DeviationLevel:
    """
    Trạng thái hoạt động cho **cả lần đánh giá** (một run), không phải từng dòng.

    Thứ tự ưu tiên (tệ nhất thắng):
    1. Có `rolling_persistent_deviation` True → drift
    2. Có `deviation_level` == drift → drift
    3. Có `deviation_level` == warning → warning
    4. Ngược lại → normal
    """
    if "rolling_persistent_deviation" in df.columns:
        if bool(df["rolling_persistent_deviation"].fillna(False).astype(bool).any()):
            return DeviationLevel.DRIFT

    if "deviation_level" in df.columns:
        levels = set(df["deviation_level"].dropna().astype(str).str.lower())
        if "drift" in levels:
            return DeviationLevel.DRIFT
        if "warning" in levels:
            return DeviationLevel.WARNING

    return DeviationLevel.NORMAL


def enrich_deviation_dataframe_for_history(
    compared_df: pd.DataFrame,
    *,
    thresholds: ThreeBandThresholds,
    persistent: Optional[PersistentDeviationConfig] = None,
) -> pd.DataFrame:
    """
    Chuẩn bị bảng sai lệch: thêm deviation_level (theo ngày) và tùy chọn rolling persistent.
    `compared_df` cần có `ds`, `error` (và các cột từ bước compare).
    """
    out = add_deviation_level_column(
        compared_df,
        error_col="error",
        out_col="deviation_level",
        thresholds=thresholds,
    )
    if persistent is not None:
        out = mark_persistent_large_deviation(out, config=persistent)
    return out


def append_forecast_error_history(
    df: pd.DataFrame,
    *,
    store: ErrorHistoryStoreConfig,
    operational_status: DeviationLevel,
    run_id: Optional[str] = None,
) -> tuple[Path, str, str, int]:
    """
    Ghi append các dòng vào CSV: mỗi dòng là một mốc `ds` + metadata run.

    Thêm cột: `run_id`, `run_at` (UTC ISO), `operational_status` (cùng giá trị cho cả run).

    Trả về: (đường dẫn file, run_id, run_at, số dòng ghi).
    """
    rid = run_id or str(uuid.uuid4())
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    out = df.copy()
    if "ds" in out.columns:
        out["ds"] = pd.to_datetime(out["ds"], errors="coerce").dt.strftime("%Y-%m-%d")

    out["run_id"] = rid
    out["run_at"] = run_at
    out["operational_status"] = operational_status.value

    store.csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = store.csv_path.exists() and store.csv_path.stat().st_size > 0
    out.to_csv(
        store.csv_path,
        mode="a",
        header=not file_exists,
        index=False,
        encoding=store.encoding,
    )
    return store.csv_path, rid, run_at, len(out)


def save_deviation_history_run(
    compared_df: pd.DataFrame,
    *,
    store: ErrorHistoryStoreConfig,
    thresholds: ThreeBandThresholds,
    persistent: Optional[PersistentDeviationConfig] = None,
    run_id: Optional[str] = None,
) -> dict:
    """
    Một lần gọi: enrich → tính operational_status → append CSV.

    Tiện cho pipeline/demo; không phụ thuộc dataset raw.
    """
    enriched = enrich_deviation_dataframe_for_history(
        compared_df,
        thresholds=thresholds,
        persistent=persistent,
    )
    status = compute_run_operational_status(enriched)
    path, rid, run_at, n = append_forecast_error_history(
        enriched,
        store=store,
        operational_status=status,
        run_id=run_id,
    )
    return {
        "path": str(path),
        "run_id": rid,
        "run_at": run_at,
        "operational_status": status.value,
        "rows_written": n,
    }
