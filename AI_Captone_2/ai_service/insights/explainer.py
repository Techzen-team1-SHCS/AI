from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ExplainConfig:
    recent_window_days: int = 14
    compare_window_days: int = 7


class SimpleExplainer:
    """
    Rule-based explanation generator (no chatbot/LLM).
    Uses recent history (actual series) and forecast to produce short text.
    """

    def explain(self, history_df: pd.DataFrame, forecast_df: pd.DataFrame, config: ExplainConfig) -> str:
        parts: list[str] = []

        hist = history_df[["ds", "y"]].copy()
        hist["ds"] = pd.to_datetime(hist["ds"])
        hist["y"] = hist["y"].astype("float64")
        hist = hist.sort_values("ds")

        fc = forecast_df.copy()
        fc["ds"] = pd.to_datetime(fc["ds"])
        fc = fc.sort_values("ds")

        if not fc.empty:
            w = max(2, min(int(config.compare_window_days), len(fc) // 2 or 2))
            start_mean = float(fc["yhat"].head(w).mean())
            end_mean = float(fc["yhat"].tail(w).mean())
            delta = end_mean - start_mean
            pct_change = (delta / (start_mean + 1e-9)) * 100

            if abs(pct_change) < 3.0:
                parts.append("Nhu cầu cơ bản đi ngang, duy trì sự ổn định.")
            elif pct_change > 0:
                parts.append(f"Có xu hướng tăng trưởng tích cực (+{pct_change:.1f}%).")
            else:
                parts.append(f"Ghi nhận đà sụt giảm (-{abs(pct_change):.1f}%).")

        if len(hist) >= 14:
            recent = hist.tail(int(config.recent_window_days)).copy()
            recent["dow"] = recent["ds"].dt.dayofweek  # 0=Mon ... 6=Sun
            weekend = recent[recent["dow"].isin([5, 6])]["y"]
            weekday = recent[~recent["dow"].isin([5, 6])]["y"]
            
            w_mean = weekend.mean()
            d_mean = weekday.mean()
            
            if len(weekend) >= 2 and len(weekday) >= 5 and w_mean > 0 and d_mean > 0:
                if w_mean > 1.1 * d_mean:
                    diff = ((w_mean - d_mean) / d_mean) * 100
                    parts.append(f"Lượng khách rớt trũng vào giữa tuần và bật tăng cường độ mạnh vào Cuối tuần (cao hơn khoảng {diff:.0f}%).")
                elif d_mean > 1.1 * w_mean:
                    diff = ((d_mean - w_mean) / w_mean) * 100
                    parts.append(f"Thị hiếu thiên về Ngày thường (cao hơn cuối tuần {diff:.0f}%), tệp khách đi công tác chiếm ưu thế.")
                else:
                    parts.append("Phân bổ khách đều dàn trải cả tuần, không có đỉnh chênh lệch rõ ràng.")

        if not parts:
            return "Chưa đủ tín hiệu dữ liệu để sinh báo cáo phân tích Insight."
        return " ".join(parts)

