from __future__ import annotations

import sys
import pandas as pd

from ai_service.advanced.dynamic_pricing import DynamicPricingEngine


def main() -> int:
    """Demo task #418: Tính năng gợi ý Dynamic Pricing."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    engine = DynamicPricingEngine(max_capacity=150)

    # Kịch bản 1: Cực kỳ vắng khách (50 khách)
    df_empty = pd.DataFrame({"yhat": [50.0, 52.0, 48.0, 50.0]})
    trend_empty = "down"

    # Kịch bản 2: Bùng nổ vượt 140 khách (gần full 150)
    df_full = pd.DataFrame({"yhat": [140.0, 142.0, 138.0, 145.0]})
    trend_full = "up"
    
    # Kịch bản 3: Ở mức bình thường 100 khách (~66%)
    df_normal = pd.DataFrame({"yhat": [100.0, 105.0, 95.0, 98.0]})
    trend_normal = "flat"

    print("\n--- TEST: HỆ MAPPING DYNAMIC PRICING ---")
    print(f"[Vắng Khách < 60% + Trend Down] => {engine.get_pricing_recommendation(df_empty, trend_empty)}")
    print(f"[Cháy Phòng > 85%]             => {engine.get_pricing_recommendation(df_full, trend_full)}")
    print(f"[Bình thường ~ 66%]            => {engine.get_pricing_recommendation(df_normal, trend_normal)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
