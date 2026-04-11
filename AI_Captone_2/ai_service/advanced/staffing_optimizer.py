from __future__ import annotations

import math
import pandas as pd


class StaffingOptimizer:
    """
    Module xử lý Khuyến nghị Xếp ca nhân sự (Staffing).
    Quy đổi số lượng phòng dự báo thành số lượng nhân sự Housekeeping và Lễ tân.
    """

    def __init__(self, hours_per_shift: int = 8) -> None:
        self._hours_per_shift = hours_per_shift

    def get_staffing_recommendation(self, forecast_df: pd.DataFrame) -> str:
        """
        Phân tích ngày mai (dòng đầu tiên của dự báo) để tính số lượng nhân sự làm việc.
        - Mỗi phòng = 0.5 giờ dọn dẹp (Housekeeping)
        - Mỗi phòng = 0.2 giờ phục vụ Lễ tân (Reception)
        """
        if forecast_df.empty:
            return "Không có dữ liệu dự báo để sắp xếp nhân sự."

        # Lấy dự báo của "ngày mai" (dòng đầu tiên)
        tomorrow_row = forecast_df.iloc[0]
        rooms_booked = float(tomorrow_row["yhat"])
        rooms_booked = max(0, rooms_booked)

        # Tính toán tổng số giờ cần thiết
        housekeeping_hours = rooms_booked * 0.5
        reception_hours = rooms_booked * 0.2

        # Tính toán số lượng nhân sự (làm tròn lên)
        housekeepers_needed = math.ceil(housekeeping_hours / self._hours_per_shift)
        receptionists_needed = math.ceil(reception_hours / self._hours_per_shift)
        
        # Đảm bảo có ít nhất 1 nhân viên cho mỗi vị trí nếu có khách
        if rooms_booked > 0:
            housekeepers_needed = max(1, housekeepers_needed)
            receptionists_needed = max(1, receptionists_needed)

        date_str = pd.to_datetime(tomorrow_row["ds"]).strftime("%d/%m/%Y")
        
        return (
            f"Ngày mai ({date_str}) dự kiến có {int(rooms_booked)} phòng có khách. "
            f"Khuyến nghị sắp ca: Cần tối thiểu {housekeepers_needed} nhân viên dọn phòng (Housekeeping) "
            f"và {receptionists_needed} nhân viên Lễ tân (Reception) cho mỗi ca làm việc."
        )
