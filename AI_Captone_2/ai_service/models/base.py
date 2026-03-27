from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class ForecastPoint:
    ds: pd.Timestamp
    yhat: float
    yhat_lower: float | None = None
    yhat_upper: float | None = None


class ForecastModel(Protocol):
    def fit(self, df_ds_y: pd.DataFrame) -> None: ...
    def predict(self, horizon_days: int) -> pd.DataFrame: ...

