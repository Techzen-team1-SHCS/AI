from __future__ import annotations

import sys
import pandas as pd

from ai_service.advanced.holiday_detector import HolidayDetector


def main() -> int:
    """Demo task #420: Tính năng theo dõi Lễ Tết."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    detector = HolidayDetector()

    # Kịch bản 1: Ngày bình thường, không có Lễ
    df_normal = pd.DataFrame({
        "ds": ["2017-09-03", "2017-09-04", "2017-09-05"]
    })

    # Kịch bản 2: Vuốt qua ngày 1/5 và 30/4
    df_holiday = pd.DataFrame({
        "ds": ["2017-04-29", "2017-04-30", "2017-05-01"]
    })

    print("\n--- TEST: PHÁT HIỆN LỄ TẾT (HOLIDAY REGRESSORS) ---")
    
    warnings_pt = detector.detect_holidays(df_normal)
    print(f"[Ngày Bình Thường 3/9 - 5/9]: {warnings_pt or 'Không phát hiện Lễ Tết.'}")
    
    warnings_hd = detector.detect_holidays(df_holiday)
    for i, w in enumerate(warnings_hd, 1):
         print(f"[Ngày Lễ {i}]: {w}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
