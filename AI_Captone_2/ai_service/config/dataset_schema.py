from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BookingLikeSchema:
    """
    Schema mapping for transaction-level booking datasets.

    The adapter/loader uses this mapping to convert raw datasets into
    standardized daily time series (ds, y). Core pipeline must not
    depend on raw column names.
    """

    # Optional scope column for per-hotel mode
    hotel_col: Optional[str]

    # Required columns to build arrival_date
    arrival_year_col: str
    arrival_month_col: str
    arrival_day_col: str

    # Cancellation/confirmation
    is_canceled_col: str


HOTEL_BOOKING_CSV_SCHEMA = BookingLikeSchema(
    hotel_col="hotel",
    arrival_year_col="arrival_date_year",
    arrival_month_col="arrival_date_month",
    arrival_day_col="arrival_date_day_of_month",
    is_canceled_col="is_canceled",
)

