from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ai_service.config.dataset_schema import BookingLikeSchema
from ai_service.config.settings import AppSettings
from ai_service.data.adapters.booking_like_adapter import AdaptConfig, BookingLikeAdapter
from ai_service.data.loaders.csv_loader import CsvLoadConfig, CsvLoader
from ai_service.data.preprocessors.continuous_daily_series import (
    ContinuousDailySeriesPreprocessor,
    ContinuousSeriesConfig,
)
from ai_service.insights.explainer import ExplainConfig, SimpleExplainer
from ai_service.models.base import ForecastModel


@dataclass(frozen=True)
class Phase1Result:
    forecast: list[dict[str, Any]]
    confidence: str
    deviation: bool
    suggested_action: str
    explanation: str


class ForecastingService:
    def __init__(
        self,
        *,
        settings: AppSettings,
        schema: BookingLikeSchema,
        model: ForecastModel,
        loader: Optional[CsvLoader] = None,
        adapter: Optional[BookingLikeAdapter] = None,
        preprocessor: Optional[ContinuousDailySeriesPreprocessor] = None,
        explainer: Optional[SimpleExplainer] = None,
    ) -> None:
        self._settings = settings
        self._schema = schema
        self._model = model
        self._loader = loader or CsvLoader()
        self._adapter = adapter or BookingLikeAdapter()
        self._preprocessor = preprocessor or ContinuousDailySeriesPreprocessor()
        self._explainer = explainer or SimpleExplainer()

    def run_phase1(
        self,
        *,
        csv_path: Path,
        horizon_days: int,
        hotel: Optional[str] = None,
    ) -> Phase1Result:
        # Load (dataset-specific mapping lives here, not in core logic)
        usecols = [
            c
            for c in [
                self._schema.hotel_col,
                self._schema.arrival_year_col,
                self._schema.arrival_month_col,
                self._schema.arrival_day_col,
                self._schema.is_canceled_col,
            ]
            if c is not None
        ]
        raw_df = self._loader.load(CsvLoadConfig(path=csv_path, usecols=usecols))

        # Adapt raw → standardized ds,y
        daily = self._adapter.to_daily_series(raw_df, AdaptConfig(schema=self._schema, hotel=hotel))

        # Preprocess: continuous daily series
        series = self._preprocessor.make_continuous(
            daily,
            ContinuousSeriesConfig(fill_value=self._settings.data.fill_missing_value),
        )

        # Forecast (model-agnostic)
        self._model.fit(series)
        forecast_df = self._model.predict(horizon_days)

        # Explain (rule-based)
        explanation = self._explainer.explain(
            history_df=series,
            forecast_df=forecast_df,
            config=ExplainConfig(
                recent_window_days=self._settings.explain.recent_window_days,
                compare_window_days=self._settings.explain.compare_window_days,
            ),
        )

        forecast_payload = []
        for _, row in forecast_df.iterrows():
            item = {
                "date": pd.to_datetime(row["ds"]).date().isoformat(),
                "yhat": float(row["yhat"]),
            }
            if "yhat_lower" in forecast_df.columns and not pd.isna(row.get("yhat_lower")):
                item["yhat_lower"] = float(row["yhat_lower"])
            if "yhat_upper" in forecast_df.columns and not pd.isna(row.get("yhat_upper")):
                item["yhat_upper"] = float(row["yhat_upper"])
            forecast_payload.append(item)

        # Phase 1: confidence/deviation/decision are placeholders (phase 2+)
        return Phase1Result(
            forecast=forecast_payload,
            confidence="medium",
            deviation=False,
            suggested_action="monitor",
            explanation=explanation,
        )

