from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from ai_service.evaluation.comparison import ComparisonConfig, compare_forecast_with_actual_over_time
from ai_service.evaluation.error_history_store import ErrorHistoryStoreConfig, save_deviation_history_run
from ai_service.evaluation.errors import ErrorConfig, ErrorType
from ai_service.evaluation.threshold_policy import ThreeBandThresholds
from ai_service.evaluation.rolling_window import PersistentDeviationConfig


def main() -> int:
    """Demo task #381: lưu lịch sử sai lệch theo thời gian + trạng thái hoạt động (theo run)."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    forecast_df = pd.DataFrame(
        {
            "ds": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
            "yhat": [90.0, 10.0, 30.0, 50.0],
        }
    )
    actual_df = pd.DataFrame(
        {
            "ds": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
            "y": [100.0, 0.0, 25.0, 80.0],
        }
    )

    compared = compare_forecast_with_actual_over_time(
        forecast_df=forecast_df,
        actual_df=actual_df,
        error_config=ErrorConfig(error_type=ErrorType.ABSOLUTE),
        config=ComparisonConfig(save_csv_path=None),
    )

    thresholds = ThreeBandThresholds(max_error_normal=10.0, max_error_warning=25.0)
    persistent = PersistentDeviationConfig(
        window_days=2,
        threshold=10.0,
        min_exceed_days=2,
        error_col="error",
    )

    out_path = Path("outputs") / "forecast_error_history.csv"
    result = save_deviation_history_run(
        compared,
        store=ErrorHistoryStoreConfig(csv_path=out_path),
        thresholds=thresholds,
        persistent=persistent,
    )

    payload = {
        "task": 381,
        "title": "Lưu sai lệch theo thời gian + trạng thái hoạt động",
        "save_result": result,
        "note": "Mỗi lần chạy append thêm dòng vào CSV; operational_status là mức cho cả run.",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
