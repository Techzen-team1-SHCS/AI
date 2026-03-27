from __future__ import annotations

import json
import sys

import pandas as pd

from ai_service.evaluation.errors import ErrorConfig, ErrorType, compute_forecast_actual_error


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Demo tối giản cho task #376:
    # - 2 mốc thời gian
    # - có case actual=0 để thấy percentage_error = NaN
    df = pd.DataFrame(
        {
            "ds": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "y": [100, 0],
            "yhat": [90, 10],
        }
    )

    out_abs = compute_forecast_actual_error(df, config=ErrorConfig(error_type=ErrorType.ABSOLUTE))
    out_pct = compute_forecast_actual_error(df, config=ErrorConfig(error_type=ErrorType.PERCENTAGE))

    payload = {
        "task": 376,
        "input": df.assign(ds=df["ds"].dt.date.astype(str)).to_dict("records"),
        "absolute": out_abs.assign(ds=out_abs["ds"].dt.date.astype(str)).to_dict("records"),
        "percentage": out_pct.assign(ds=out_pct["ds"].dt.date.astype(str)).to_dict("records"),
        "note": "percentage_error: nếu actual=0 thì NaN để tránh chia 0",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

