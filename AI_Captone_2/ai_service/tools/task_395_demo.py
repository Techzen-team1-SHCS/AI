from __future__ import annotations

import json
import sys

import pandas as pd

from ai_service.decision.decision_table import DecisionTable


def main() -> int:
    """Demo task #395: Test độc lập module Decision Table."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    decision_engine = DecisionTable()

    # Kịch bản 1: Lượng dư báo nửa sau bùng nổ lên 200 phòng
    df_up = pd.DataFrame({"yhat": [50.0, 55.0, 60.0, 180.0, 200.0, 210.0]})
    # Kịch bản 2: Lượng dự báo đang bình thường cắm đầu xuống 10
    df_down = pd.DataFrame({"yhat": [100.0, 95.0, 90.0, 20.0, 15.0, 10.0]})
    # Kịch bản 3: Đi ngang không biến đổi quá 5%
    df_flat = pd.DataFrame({"yhat": [50.0, 52.0, 51.0, 53.0, 50.0, 49.0]})

    print("\n--- TEST: HỆ MAPPING QUYẾT ĐỊNH ---")
    
    # 1. Test Conf: HIGH
    trend_up = decision_engine.evaluate_trend(df_up)
    print(f"[HIGH] + [{trend_up.upper()}] => {decision_engine.get_suggested_action(trend_up, 'high')}")
    
    # 2. Test Conf: MEDIUM
    trend_flat = decision_engine.evaluate_trend(df_flat)
    print(f"[MEDIUM] + [{trend_flat.upper()}] => {decision_engine.get_suggested_action(trend_flat, 'medium')}")
    
    # 3. Test Conf: LOW
    trend_down = decision_engine.evaluate_trend(df_down)
    print(f"[LOW] + [{trend_down.upper()}] => {decision_engine.get_suggested_action(trend_down, 'low')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
