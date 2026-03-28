from __future__ import annotations

import json
import sys

import pandas as pd

from ai_service.evaluation.rolling_window import (
    PersistentDeviationConfig,
    RollingErrorConfig,
    add_rolling_mean_error,
    mark_persistent_large_deviation,
)


def main() -> int:
    """Demo task #380: rolling window theo dõi sai lệch (mean + cờ kéo dài)."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # 7 ngày: đầu ổn, cuối 3 ngày lỗi cao liên tiếp → rolling phát hiện "kéo dài"
    df = pd.DataFrame(
        {
            "ds": pd.date_range("2024-01-01", periods=7, freq="D"),
            "error": [2.0, 3.0, 4.0, 15.0, 18.0, 20.0, 5.0],
        }
    )

    win = 3
    # Trung bình lỗi trong cửa sổ + đếm số ngày vượt ngưỡng trong cửa sổ
    df_full = add_rolling_mean_error(
        df,
        config=RollingErrorConfig(window_days=win, error_col="error"),
    )
    # Trong 3 ngày liên tiếp, cần >= 2 ngày có error > 10 → cờ persistent
    df_full = mark_persistent_large_deviation(
        df_full,
        config=PersistentDeviationConfig(
            window_days=win,
            threshold=10.0,
            min_exceed_days=2,
            error_col="error",
        ),
    )

    rows = df_full.assign(ds=df_full["ds"].dt.date.astype(str)).to_dict("records")

    payload = {
        "task": 380,
        "window_days": win,
        "rule_mean": f"rolling_mean_error = mean(error) trong {win} ngày gần nhất",
        "rule_persistent": "rolling_persistent_deviation = True khi trong window có >= min_exceed_days ngày error > threshold",
        "threshold_for_count": 10.0,
        "min_exceed_days": 2,
        "rows": rows,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
