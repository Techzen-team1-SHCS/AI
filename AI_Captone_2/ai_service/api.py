"""
FastAPI Server — AI Demand Forecasting Service
Task #432 (5.1): Khởi tạo FastAPI Server với Endpoint Dự báo chính.

Endpoint duy nhất: POST /forecast
Nhận JSON payload từ Backend Web (PHP) và trả về Phase1Result.
Swagger UI tự động tại: /docs
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai_service.config.settings import AppSettings, AdvancedSettings, DataSettings, ExplainSettings, ForecastSettings
from ai_service.config.dataset_schema import HOTEL_BOOKING_CSV_SCHEMA
from ai_service.models.prophet_model import ProphetModel
from ai_service.services.forecasting_service import ForecastingService


# ---------------------------------------------------------------------------
# Pydantic Request / Response Models
# ---------------------------------------------------------------------------

class HistoricalDataPoint(BaseModel):
    """Một điểm dữ liệu lịch sử theo ngày (đã được group-by từ phía PHP)."""

    ds: str = Field(
        ...,
        description="Ngày theo định dạng ISO-8601 (YYYY-MM-DD). VD: '2017-07-01'",
        examples=["2017-07-01"],
    )
    rooms_booked: int = Field(
        ...,
        ge=0,
        description="Số phòng đặt xác nhận trong ngày đó (is_canceled=0, đã group-by từ DB).",
        examples=[78],
    )


class ForecastRequest(BaseModel):
    """Payload PHP gửi lên để yêu cầu dự báo."""

    hotel_id: str = Field(
        ...,
        description="Tên/ID khách sạn. Dùng để slug hoá tên file evaluation history.",
        examples=["City Hotel"],
    )
    hotel_capacity: int = Field(
        default=150,
        ge=1,
        description=(
            "Tổng số phòng của khách sạn. Dùng cho Dynamic Pricing. "
            "Mặc định 150 nếu PHP không truyền."
        ),
        examples=[150],
    )
    historical_data: list[HistoricalDataPoint] = Field(
        ...,
        min_length=2,
        description=(
            "Mảng lịch sử đặt phòng theo ngày. PHP tự query DB, group-by date "
            "rồi gửi lên. AI không cần tự group."
        ),
    )
    horizon_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=90,
        description="Số ngày cần dự báo. Mặc định 30 nếu không truyền. Tối đa 90.",
        examples=[14],
    )


class ForecastResponse(BaseModel):
    """Cấu trúc JSON trả về — khớp hoàn toàn với Phase1Result."""

    forecast: list[dict[str, Any]]
    confidence: str
    deviation: bool
    suggested_action: str
    explanation: str
    advanced_insights: dict[str, Any]


# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Hotel Demand Forecasting Service",
    description=(
        "AI Service dự báo nhu cầu đặt phòng khách sạn ngắn hạn (7–30 ngày). "
        "Tích hợp với Website PHP qua HTTP POST JSON. "
        "Xem tài liệu kiến trúc: Document_code/API_INTEGRATION_ARCHITECTURE.md"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Default settings cho horizon (dùng khi PHP không truyền horizon_days)
_default_settings = AppSettings()


def _build_service(hotel_capacity: int) -> ForecastingService:
    """
    Factory tạo ForecastingService với hotel_capacity từ request.
    Mỗi request có capacity khác nhau (City Hotel vs Resort Hotel).
    """
    settings = AppSettings(
        forecast=ForecastSettings(),
        data=DataSettings(),
        explain=ExplainSettings(),
        advanced=AdvancedSettings(hotel_capacity=hotel_capacity),
    )
    return ForecastingService(
        settings=settings,
        schema=HOTEL_BOOKING_CSV_SCHEMA,
        model=ProphetModel(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", summary="Health Check", tags=["System"])
def health_check() -> dict[str, str]:
    """Kiểm tra service đang chạy. Dùng cho Docker health check."""
    return {"status": "ok", "service": "AI Forecasting Service v1.0.0"}


@app.post(
    "/forecast",
    response_model=ForecastResponse,
    summary="Dự báo nhu cầu đặt phòng",
    tags=["Forecasting"],
    responses={
        200: {"description": "Dự báo thành công, trả về JSON đầy đủ."},
        400: {"description": "Dữ liệu đầu vào không hợp lệ."},
        422: {"description": "Lỗi validation Pydantic (kiểu dữ liệu sai)."},
        500: {"description": "Lỗi nội bộ trong AI pipeline."},
    },
)
def forecast(request: ForecastRequest) -> ForecastResponse:
    """
    **Endpoint chính** — PHP gửi lịch sử đặt phòng, AI trả về dự báo.

    ### Luồng xử lý:
    1. Nhận JSON payload từ PHP (đã pre-grouped theo ngày)
    2. Chuyển `historical_data[].rooms_booked` → cột `y` trong DataFrame
    3. Chạy toàn bộ AI Pipeline (Prophet → Evaluation → Decision → Insights)
    4. Trả về JSON chuẩn gồm 6 trường

    ### Ghi chú:
    - `horizon_days` là tuỳ chọn — mặc định 30 ngày nếu PHP không truyền.
    - `hotel_capacity` là tuỳ chọn — mặc định 150 nếu PHP không truyền.
    - PHP **phải tự group-by date** trước khi gửi (AI không tự aggregate).
    """
    horizon = request.horizon_days or _default_settings.forecast.horizon_days

    try:
        service = _build_service(hotel_capacity=request.hotel_capacity)

        # Chuyển HistoricalDataPoint → dict chuẩn {ds, y} cho ForecastingService
        payload_dicts = [
            {"ds": point.ds, "y": point.rooms_booked}
            for point in request.historical_data
        ]

        result = service.run_from_web_payload(
            payload=payload_dicts,
            horizon_days=horizon,
            hotel_id=request.hotel_id,
        )

        return ForecastResponse(
            forecast=result.forecast,
            confidence=result.confidence,
            deviation=result.deviation,
            suggested_action=result.suggested_action,
            explanation=result.explanation,
            advanced_insights=result.advanced_insights,
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi AI pipeline: {type(exc).__name__}: {exc}",
        ) from exc
