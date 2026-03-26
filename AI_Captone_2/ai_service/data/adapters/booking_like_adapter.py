from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
from pandas.api.types import is_string_dtype

from ai_service.config.dataset_schema import BookingLikeSchema


_MONTH_NAME_TO_NUMBER = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


@dataclass(frozen=True)
class AdaptConfig:
    schema: BookingLikeSchema
    hotel: Optional[str] = None  # if provided, filter by hotel (per_hotel mode)


class BookingLikeAdapter:
    """
    Convert transaction-level booking data into a standardized daily series (ds, y).

    MVP definition:
    - confirmed bookings only (is_canceled == 0)
    - grouped by arrival_date
    - aggregated across all hotels unless hotel filter is provided
    """

    def to_daily_series(self, raw_df: pd.DataFrame, config: AdaptConfig) -> pd.DataFrame:
        s = config.schema
        df = raw_df.copy()

        if config.hotel is not None:
            if not s.hotel_col:
                raise ValueError("hotel filter provided but schema.hotel_col is None")
            df = df[df[s.hotel_col] == config.hotel]

        df = df[df[s.is_canceled_col] == 0]

        year = df[s.arrival_year_col].astype("int64")
        day = df[s.arrival_day_col].astype("int64")
        month_raw = df[s.arrival_month_col]

        if is_string_dtype(month_raw) or month_raw.dtype == "object":
            month = month_raw.map(_MONTH_NAME_TO_NUMBER).astype("Int64")
            if month.isna().any():
                bad = month_raw[month.isna()].dropna().unique()[:5]
                raise ValueError(f"Unrecognized month names: {bad}")
            month = month.astype("int64")
        else:
            month = month_raw.astype("int64")

        ds = pd.to_datetime(
            {"year": year, "month": month, "day": day},
            errors="coerce",
        )
        df = df.assign(ds=ds)
        df = df.dropna(subset=["ds"])

        daily = df.groupby("ds", as_index=False).size().rename(columns={"size": "y"})
        daily["y"] = daily["y"].astype("float64")
        return daily.sort_values("ds").reset_index(drop=True)

