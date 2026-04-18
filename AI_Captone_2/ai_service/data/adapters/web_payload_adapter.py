from __future__ import annotations

from typing import Any
import pandas as pd


class WebPayloadAdapter:
    """
    Convert JSON array payload from Web into a standardized daily series (ds, y).
    Allows loose coupling with the dictionary structure sent by Web API.
    """

    def to_daily_series(self, payload: list[dict[str, Any]]) -> pd.DataFrame:
        """
        Nhận mảng dữ liệu từ API và ép kiểu về DataFrame có 2 cột (ds, y).
        Hỗ trợ cả trường hợp payload có cột 'rooms_booked' (từ PHP) hoặc 'y' (hệ thống trong).
        """
        if not payload:
            raise ValueError("Payload không được rỗng.")

        df = pd.DataFrame(payload)

        if "ds" not in df.columns:
            raise ValueError("Mỗi phần tử payload phải có trường 'ds'.")

        # Ánh xạ từ PHP request format sang Internal format
        if "y" not in df.columns and "rooms_booked" in df.columns:
            df["y"] = df["rooms_booked"]
            
        if "y" not in df.columns:
            raise ValueError("Mỗi phần tử payload phải có trường 'y' hoặc 'rooms_booked'.")

        # Ép kiểu chuẩn
        df["ds"] = pd.to_datetime(df["ds"], errors="coerce")
        df = df.dropna(subset=["ds"])
        df["y"] = df["y"].astype("float64")

        return df.sort_values("ds").reset_index(drop=True)
