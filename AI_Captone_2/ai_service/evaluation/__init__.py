"""Evaluation layer (metrics, errors, confidence, deviation)."""

from ai_service.evaluation.comparison import ComparisonConfig, compare_forecast_with_actual_over_time
from ai_service.evaluation.large_deviation import (
    LargeDeviationConfig,
    count_large_deviations,
    mark_large_deviations,
)

