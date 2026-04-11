from __future__ import annotations

import sys
import pandas as pd

from ai_service.advanced.staffing_optimizer import StaffingOptimizer


def main() -> int:
    """Demo task #419: Tính năng gợi ý Ca Nhân sự (Staffing)."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    optimizer = StaffingOptimizer(hours_per_shift=8)

    # Kịch bản 1: Cực kỳ vắng khách (chỉ 10 phòng)
    df_empty = pd.DataFrame({
        "ds": ["2017-09-01", "2017-09-02"],
        "yhat": [10.0, 12.0]
    })

    # Kịch bản 2: Bùng nổ (150 phòng)
    df_full = pd.DataFrame({
        "ds": ["2017-09-10", "2017-09-11"],
        "yhat": [150.0, 148.0]
    })

    print("\n--- TEST: MÔ HÌNH TỐI ƯU NHÂN SỰ ---")
    print(f"[Vắng vẻ   -  10 phòng] => {optimizer.get_staffing_recommendation(df_empty)}")
    print(f"[Đông đúc  - 150 phòng] => {optimizer.get_staffing_recommendation(df_full)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
