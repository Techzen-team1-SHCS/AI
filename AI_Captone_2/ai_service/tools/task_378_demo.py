from __future__ import annotations

import json
import sys

import pandas as pd

from ai_service.evaluation.comparison import ComparisonConfig, compare_forecast_with_actual_over_time
from ai_service.evaluation.errors import ErrorConfig, ErrorType
from ai_service.evaluation.large_deviation import LargeDeviationConfig, count_large_deviations, mark_large_deviations


def main() -> int:
    """Demo task #378: đánh dấu điểm có sai lệch lớn (vượt ngưỡng) trên bảng so sánh."""
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

    # Ngưỡng: absolute error > 15 thì coi là sai lệch lớn (demo)
    threshold = 15.0
    marked = mark_large_deviations(
        compared,
        config=LargeDeviationConfig(threshold=threshold, error_col="error"),
    )
    n_large = count_large_deviations(marked)

    payload = {
        "task": 378,
        "threshold_absolute": threshold,
        "rule": "large_deviation = (absolute_error > threshold), NaN error không đánh dấu",
        "rows": marked.assign(ds=marked["ds"].dt.date.astype(str)).to_dict("records"),
        "count_large_deviations": n_large,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
