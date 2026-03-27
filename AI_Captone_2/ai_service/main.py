from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from ai_service.config.dataset_schema import HOTEL_BOOKING_CSV_SCHEMA
from ai_service.config.settings import AppSettings
from ai_service.models.prophet_model import ProphetModel
from ai_service.services.forecasting_service import ForecastingService


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AI demand forecasting (Phase 1).")
    p.add_argument(
        "--csv",
        type=str,
        default=str(Path("Document_code") / "hotel_booking.csv"),
        help="Path to input CSV (raw dataset).",
    )
    p.add_argument("--horizon", type=int, default=30, help="Forecast horizon in days.")
    p.add_argument(
        "--scope",
        type=str,
        default="global",
        choices=["global", "per_hotel"],
        help="Forecast scope.",
    )
    p.add_argument(
        "--hotel",
        type=str,
        default=None,
        help="Hotel name to filter when scope=per_hotel.",
    )
    return p.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = _parse_args()
    csv_path = Path(args.csv)

    settings = AppSettings()
    model = ProphetModel()
    service = ForecastingService(
        settings=settings,
        schema=HOTEL_BOOKING_CSV_SCHEMA,
        model=model,
    )

    hotel: Optional[str] = args.hotel if args.scope == "per_hotel" else None
    result = service.run_phase1(csv_path=csv_path, horizon_days=int(args.horizon), hotel=hotel)

    print(
        json.dumps(
            {
                "forecast": result.forecast,
                "confidence": result.confidence,
                "deviation": result.deviation,
                "suggested_action": result.suggested_action,
                "explanation": result.explanation,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

