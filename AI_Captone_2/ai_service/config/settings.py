from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ForecastSettings:
    horizon_days: int = 30  # Mặc định dự báo 30 ngày; FastAPI cho phép PHP gửi override (optional)


@dataclass(frozen=True)
class DataSettings:
    fill_missing_value: float = 0.0
    min_training_days: int = 180


@dataclass(frozen=True)
class ExplainSettings:
    recent_window_days: int = 14
    compare_window_days: int = 7


@dataclass(frozen=True)
class AdvancedSettings:
    hotel_capacity: int = 150  # Default number of rooms


@dataclass(frozen=True)
class AppSettings:
    forecast: ForecastSettings = ForecastSettings()
    data: DataSettings = DataSettings()
    explain: ExplainSettings = ExplainSettings()
    advanced: AdvancedSettings = AdvancedSettings()

