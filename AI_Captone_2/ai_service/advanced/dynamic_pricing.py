from __future__ import annotations

import pandas as pd
from typing import Literal

# Kế thừa Trend Direction từ Decision Module
TrendDirection = Literal["up", "down", "flat"]


class DynamicPricingEngine:
    """
    Module xử lý Khuyến nghị Giá Động (Dynamic Pricing / RMS).
    Kết hợp Số lượng khách dự báo để tính Tỷ lệ lấp đầy (Occupancy Rate).
    Áp dụng điều kiện if/else thuần túy theo Master Plan.
    """

    def __init__(self, max_capacity: int) -> None:
        if max_capacity <= 0:
            raise ValueError("Hotel capacity must be greater than zero.")
        self._max_capacity = max_capacity

    def get_pricing_recommendation(
        self, 
        forecast_df: pd.DataFrame, 
        trend: TrendDirection
    ) -> str:
        """
        Phân tích 14 ngày tới để đưa ra một khuyến nghị chung.
        Sử dụng số trung bình hoặc số Max tùy chiến lược, trong MVP này ta lấy Peak (số lượng đỉnh).
        """
        if forecast_df.empty:
            return "Không đủ dữ liệu dự báo để tính toán giá động."
        
        # Chọn ra 3 ngày đông nhất (Peak Demand) để tính công suất cao nhất
        peak_demand = forecast_df["yhat"].nlargest(3).mean()
        
        occupancy_rate = peak_demand / self._max_capacity
        
        # Rule-based logic from advanced_proposals.md
        if occupancy_rate < 0.60 and trend == "down":
            return "Khuyến nghị Giảm 15% giá phòng Standard trên các kênh OTA để kích cầu."
        elif occupancy_rate > 0.85:
            return "Khuyến nghị Khóa phòng giá rẻ, tăng giá bán 15% đối với toàn bộ phòng cao cấp."
        else:
            pct = occupancy_rate * 100
            return f"Tỷ lệ lấp đầy khoảng {pct:.1f}%. Khuyến nghị: Giữ nguyên mức giá bán hiện tại."
