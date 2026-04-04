from __future__ import annotations

from typing import Literal

import pandas as pd

TrendDirection = Literal["up", "down", "flat"]
ConfidenceLevel = Literal["high", "medium", "low"]


class DecisionTable:
    """
    Pure rule-based layer that maps:
    1. Trend (calculated mathematically from forecast yhat)
    2. Confidence (evaluated historically)
    ==> into Business string logic.
    """

    def evaluate_trend(self, forecast_df: pd.DataFrame) -> TrendDirection:
        """
        Tính xu hướng dự báo bằng cách cắt đôi khoảng thời gian.
        So sánh trung bình nửa cuối và nửa đầu để giảm độ nhiễu.
        """
        if len(forecast_df) < 2:
            return "flat"

        # Split into two halves
        half = len(forecast_df) // 2
        first_half = forecast_df["yhat"].iloc[:half].mean()
        second_half = forecast_df["yhat"].iloc[half:].mean()

        diff_pct = (second_half - first_half) / (first_half + 1e-9)

        if diff_pct > 0.05:  # Tăng trưởng lớn hơn 5%
            return "up"
        elif diff_pct < -0.05:  # Giảm sâu hơn 5%
            return "down"
        return "flat"

    def get_suggested_action(self, trend: TrendDirection, confidence: ConfidenceLevel) -> str:
        """
        Matrix Rule: Trả về Action text dựa theo độ an toàn (Confidence) và hướng đi (Trend).
        """
        if confidence == "high":
            if trend == "up":
                return "Xu hướng Tăng mạnh (Độ tin cậy tuyệt đối): Phê duyệt tăng cường tối đa chuẩn bị vật tư và nguồn nhân sự."
            elif trend == "down":
                return "Xu hướng Giảm rõ rệt (Độ tin cậy tuyệt đối): Chỉ thị kiểm duyệt sát sao, giảm chi phí nhân sự hằng ngày và tung ra các gói khuyến mãi sốc."
            else:
                return "Thị trường Đi ngang (Độ tin cậy cao): Duy trì quỹ bình ổn và giữ nguyên định kỳ hoạt động."
        
        elif confidence == "medium":
            if trend == "up":
                return "Xu hướng khởi sắc (Rủi ro cảnh báo): Khuyến nghị theo dõi động thái tăng, chuẩn bị sẵn sàng một phần nhân sự dự phòng."
            elif trend == "down":
                return "Có dấu hiệu suy thoái (Rủi ro cảnh báo): Chỉ thị cán bộ quan sát kỹ lượng phòng trống, cân nhắc thay đổi nhân sự nhỏ giọt."
            else:
                return "Đi ngang hỗn loạn (Rủi ro cảnh báo): Giám sát hệ thống đặt phòng trực tuyến mỗi 4 tiếng."
        
        else:  # low (Drift hoặc Fallback)
            if trend == "up":
                return "Tín hiệu Ảo Nhảy Vọt (Dữ liệu không đáng tin): Không nên mạo hiểm tuyển người. Yêu cầu quản lý phân tích thủ công."
            elif trend == "down":
                return "Tín hiệu Đổ vỡ (Dữ liệu không đáng tin): Chưa vội cắt giảm ngân sách, cần đội ngũ kinh doanh rà soát lại biến động dữ liệu."
            else:
                return "Mất phương hướng (Rủi ro toàn diện): Yêu cầu quản lý can thiệp phán đoán thủ công ngay lập tức."
