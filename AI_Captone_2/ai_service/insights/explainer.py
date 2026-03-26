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
            if abs(delta) < max(1.0, 0.02 * max(start_mean, 1.0)):
                parts.append("Nhu cầu dự báo nhìn chung ổn định trong giai đoạn tới.")
            elif delta > 0:
                parts.append("Nhu cầu dự báo có xu hướng tăng trong giai đoạn tới.")
            else:
                parts.append("Nhu cầu dự báo có xu hướng giảm trong giai đoạn tới.")

        if len(hist) >= 14:
            recent = hist.tail(int(config.recent_window_days)).copy()
            recent["dow"] = recent["ds"].dt.dayofweek  # 0=Mon ... 6=Sun
            weekend = recent[recent["dow"].isin([5, 6])]["y"]
            weekday = recent[~recent["dow"].isin([5, 6])]["y"]
            if len(weekend) >= 2 and len(weekday) >= 5:
                if weekend.mean() > 1.1 * weekday.mean():
                    parts.append("Cuối tuần thường cao hơn ngày thường.")
                elif weekday.mean() > 1.1 * weekend.mean():
                    parts.append("Ngày thường đang cao hơn cuối tuần.")

            if len(recent) >= 14:
                first = recent.head(len(recent) // 2)["y"].mean()
                last = recent.tail(len(recent) // 2)["y"].mean()
                if first > 0 and last < 0.8 * first:
                    parts.append("Gần đây có dấu hiệu giảm so với giai đoạn trước đó.")

        if not parts:
            return "Chưa đủ tín hiệu để giải thích rõ; vui lòng theo dõi thêm dữ liệu."
        return " ".join(parts)

