from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

try:
    from prophet import Prophet  # type: ignore[import-not-found]
except Exception as e:  # pragma: no cover
    Prophet = None  # type: ignore[assignment]
    _PROPHET_IMPORT_ERROR = e


@dataclass(frozen=True)
class ProphetConfig:
    daily_seasonality: bool = False
    weekly_seasonality: bool = True
    yearly_seasonality: bool = True


class ProphetModel:
    def __init__(self, config: ProphetConfig | None = None) -> None:
        if Prophet is None:  # pragma: no cover
            raise ImportError(
                "prophet is not installed or failed to import. "
                "Install dependencies from requirements.txt."
            ) from _PROPHET_IMPORT_ERROR
        self._config = config or ProphetConfig()
        self._model: Prophet | None = None
        self._train_max_ds: pd.Timestamp | None = None

    def fit(self, df_ds_y: pd.DataFrame) -> None:
        df = df_ds_y[["ds", "y"]].copy()
        df["ds"] = pd.to_datetime(df["ds"])
        df["y"] = df["y"].astype("float64")

        self._train_max_ds = df["ds"].max()
        self._model = Prophet(
            daily_seasonality=self._config.daily_seasonality,
            weekly_seasonality=self._config.weekly_seasonality,
            yearly_seasonality=self._config.yearly_seasonality,
        )
        self._model.fit(df)

    def predict(self, horizon_days: int) -> pd.DataFrame:
        if self._model is None or self._train_max_ds is None:
            raise RuntimeError("Model is not fitted yet")

        future = pd.date_range(
            start=self._train_max_ds + pd.Timedelta(days=1),
            periods=int(horizon_days),
            freq="D",
        )
        future_df = pd.DataFrame({"ds": future})
        fcst = self._model.predict(future_df)
        return fcst[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()

