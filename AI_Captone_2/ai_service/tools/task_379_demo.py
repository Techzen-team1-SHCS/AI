from __future__ import annotations

import json
import sys

import pandas as pd

from ai_service.evaluation.threshold_policy import (
    DeviationLevel,
    ThreeBandThresholds,
    add_deviation_level_column,
    classify_deviation_level,
    infer_three_band_thresholds_from_errors,
)


def main() -> int:
    """Demo task #379: ngưỡng 3 dải (normal / warning / drift) — cố định và suy ra từ dữ liệu."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # 1) Ngưỡng cố định (do team cấu hình)
    static = ThreeBandThresholds(max_error_normal=10.0, max_error_warning=25.0)
    sample_errors = [5.0, 15.0, 30.0, float("nan")]
    static_classify = [
        {"error": e, "level": classify_deviation_level(e, thresholds=static).value}
        for e in sample_errors
    ]

    # 2) Suy ra ngưỡng từ chuỗi sai lệch lịch sử (đặc trưng dataset)
    hist = pd.Series([1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 40.0, 50.0])
    inferred = infer_three_band_thresholds_from_errors(hist, normal_quantile=0.75, warning_quantile=0.95)

    df = pd.DataFrame({"error": [2.0, 10.0, 35.0, 60.0]})
    df_tagged = add_deviation_level_column(df, error_col="error", thresholds=inferred)

    payload = {
        "task": 379,
        "static_thresholds": {
            "max_error_normal": static.max_error_normal,
            "max_error_warning": static.max_error_warning,
            "classify_samples": static_classify,
        },
        "inferred_from_history": {
            "history_errors": hist.tolist(),
            "normal_quantile": 0.75,
            "warning_quantile": 0.95,
            "max_error_normal": inferred.max_error_normal,
            "max_error_warning": inferred.max_error_warning,
            "tagged_rows": df_tagged.to_dict("records"),
        },
        "levels_meaning": {
            DeviationLevel.NORMAL.value: "error <= max_error_normal",
            DeviationLevel.WARNING.value: "max_error_normal < error <= max_error_warning",
            DeviationLevel.DRIFT.value: "error > max_error_warning",
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
