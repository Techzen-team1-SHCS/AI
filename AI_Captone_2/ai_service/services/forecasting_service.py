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
from ai_service.evaluation.errors import ErrorConfig, ErrorType
from ai_service.evaluation.threshold_policy import ThreeBandThresholds, infer_three_band_thresholds_from_errors, DeviationLevel
from ai_service.evaluation.rolling_window import PersistentDeviationConfig
from ai_service.evaluation.comparison import ComparisonConfig, compare_forecast_with_actual_over_time
from ai_service.evaluation.error_history_store import ErrorHistoryStoreConfig, save_deviation_history_run


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

        # Fallback Strategy: If hotel data is insufficient, use Global data
        fallback_used = False
        if hotel and len(daily) < self._settings.data.min_training_days:
            daily = self._adapter.to_daily_series(raw_df, AdaptConfig(schema=self._schema, hotel=None))
            fallback_used = True


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

        # Phase 2: Evaluation (In-sample error tracking)
        try:
            in_sample_forecast = self._model.predict_in_sample(series)
            compared_df = compare_forecast_with_actual_over_time(
                forecast_df=in_sample_forecast,
                actual_df=series,
                error_config=ErrorConfig(error_type=ErrorType.ABSOLUTE),
                config=ComparisonConfig()
            )
            
            try:
                thresholds = infer_three_band_thresholds_from_errors(
                    compared_df["error"], 
                    normal_quantile=0.75, 
                    warning_quantile=0.95
                )
            except Exception:
                thresholds = ThreeBandThresholds(max_error_normal=10.0, max_error_warning=25.0)

            persistent_config = PersistentDeviationConfig(
                window_days=3,
                threshold=thresholds.max_error_warning,
                min_exceed_days=2,
                error_col="error",
            )

            hotel_slug = hotel.replace(' ', '_').lower() if hotel else "global"
            out_path = Path("outputs") / f"evaluation_history_{hotel_slug}.csv"
            
            eval_result = save_deviation_history_run(
                compared_df,
                store=ErrorHistoryStoreConfig(csv_path=out_path),
                thresholds=thresholds,
                persistent=persistent_config,
            )
            op_status = DeviationLevel(eval_result["operational_status"])
            deviation_flag = (op_status in [DeviationLevel.WARNING, DeviationLevel.DRIFT])
            
            # Map operational status to Confidence string
            conf_map = {
                DeviationLevel.NORMAL: "high",
                DeviationLevel.WARNING: "medium",
                DeviationLevel.DRIFT: "low",
            }
            raw_confidence = conf_map.get(op_status, "medium")
        except Exception as e:
            # Safe fallback if evaluation fails
            deviation_flag = False
            raw_confidence = "medium"

        # Apply Fallback Penalty: Downgrade confidence if global fallback was used
        confidence = raw_confidence
        if fallback_used:
            penalty_map = {"high": "medium", "medium": "low", "low": "low"}
            confidence = penalty_map.get(raw_confidence, "low")

        # Phase 1: decision is placeholder (phase 2+)
        return Phase1Result(
            forecast=forecast_payload,
            confidence=confidence,
            deviation=deviation_flag,
            suggested_action="monitor",
            explanation=explanation,
        )

