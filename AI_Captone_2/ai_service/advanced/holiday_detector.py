from __future__ import annotations

import pandas as pd


class HolidayDetector:
    """
    Module Cảnh báo Ngoại lai / Lễ Tết.
    Bắt các sự kiện ngày Lễ cố định để đưa ra khuyến cáo đột biến khách.
    """

    def __init__(self) -> None:
        # Danh sách các ngày lễ cố định theo Dương lịch (Tháng, Ngày)
        self._fixed_holidays = {
            (1, 1): "Tết Dương Lịch",
            (4, 30): "Ngày Giải phóng Miền Nam",
            (5, 1): "Ngày Quốc tế Lao động",
            (9, 2): "Ngày Quốc khánh Việt Nam",
            (12, 24): "Lễ Giáng Sinh",
            (12, 31): "Giao thừa Dương lịch",
        }

    def detect_holidays(self, forecast_df: pd.DataFrame) -> list[str]:
        """
        Quét mảng ngày dự báo (ds) để tìm xem nó có đâm xuyên qua ngày lễ nào không.
        Trả về mảng chứa các câu cảnh báo.
        """
        warnings = []
        if forecast_df.empty:
            return warnings

        # Chuyển đổi ds sang datetime an toàn
        dates = pd.to_datetime(forecast_df["ds"])

        detected = set()

        for d in dates:
            month_day = (d.month, d.day)
            if month_day in self._fixed_holidays:
                holiday_name = self._fixed_holidays[month_day]
                if holiday_name not in detected:
                    detected.add(holiday_name)
                    # Quy tắc từ Master Plan
                    warnings.append(
                        f"Cảnh báo Lễ Tết: Rơi vào {holiday_name}. "
                        "Dự kiến số lượng khách bùng nổ do Lễ lớn. "
                        "Đề xuất ngưng duyệt đơn xin nghỉ phép của nhân sự khối Vận hành!"
                    )

        return warnings
