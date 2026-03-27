from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

from ai_service.evaluation.comparison import ComparisonConfig, compare_forecast_with_actual_over_time
from ai_service.evaluation.errors import ErrorConfig, ErrorType


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Demo tối giản cho task #377:
    # - so sánh theo ds
    # - xuất bảng sai lệch (và tuỳ chọn lưu CSV)
    forecast_df = pd.DataFrame(
        {
            "ds": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "yhat": [90, 10, 30],
        }
    )
    actual_df = pd.DataFrame(
        {
            "ds": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "y": [100, 0, 25],
        }
    )

    out_path = Path("outputs") / "task_377_errors.csv"
    out = compare_forecast_with_actual_over_time(
        forecast_df=forecast_df,
        actual_df=actual_df,
        error_config=ErrorConfig(error_type=ErrorType.ABSOLUTE),
        config=ComparisonConfig(save_csv_path=out_path),
    )

    payload = {
        "task": 377,
        "saved_csv": str(out_path),
        "rows": out.assign(ds=out["ds"].dt.date.astype(str)).to_dict("records"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

