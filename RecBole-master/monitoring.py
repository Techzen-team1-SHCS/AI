"""
Module quản lý metrics cho API server.
Theo dõi số lượng requests, response times, errors theo endpoint.
Lưu trữ dữ liệu trong memory (không persistent).

Lưu ý: Module này sử dụng in-memory storage, dữ liệu sẽ mất khi server restart.
Để persistent metrics, cần tích hợp với database hoặc external monitoring service.
"""

import time
import json
from datetime import datetime
from typing import Dict, Optional
from functools import wraps

# Biến global lưu trữ metrics trong memory
# Cấu trúc:
#   - requests_total: Tổng số requests đã nhận
#   - requests_by_endpoint: Dict đếm requests theo từng endpoint
#   - errors_total: Tổng số errors (status_code >= 400)
#   - errors_by_endpoint: Dict đếm errors theo từng endpoint
#   - response_times: List lưu response times (giới hạn 1000 phần tử gần nhất)
#   - last_request_time: Timestamp ISO của request cuối cùng
_metrics = {
    "requests_total": 0,
    "requests_by_endpoint": {},
    "errors_total": 0,
    "errors_by_endpoint": {},
    "response_times": [],
    "last_request_time": None,
}


def record_request(endpoint: str, response_time: float, status_code: int):
    """Ghi lại metrics cho một request.
    
    Hàm này được gọi sau mỗi request để cập nhật các thống kê:
    - Tăng counter tổng số requests
    - Cập nhật counter theo endpoint
    - Lưu response time (giới hạn 1000 giá trị gần nhất để tránh memory leak)
    - Đếm errors nếu status_code >= 400
    
    Args:
        endpoint: Tên endpoint (ví dụ: "/recommendations/123")
        response_time: Thời gian xử lý request (giây)
        status_code: HTTP status code (200, 404, 500, ...)
    
    Note:
        Response times được giới hạn ở 1000 giá trị gần nhất để tránh
        memory leak khi server chạy lâu dài.
    """
    _metrics["requests_total"] += 1
    _metrics["last_request_time"] = datetime.now().isoformat()
    
    # Đếm requests theo endpoint
    if endpoint not in _metrics["requests_by_endpoint"]:
        _metrics["requests_by_endpoint"][endpoint] = 0
    _metrics["requests_by_endpoint"][endpoint] += 1
    
    # Lưu response time (giới hạn 1000 giá trị để tránh memory leak)
    _metrics["response_times"].append(response_time)
    if len(_metrics["response_times"]) > 1000:
        # Giữ lại 1000 giá trị gần nhất (FIFO)
        _metrics["response_times"] = _metrics["response_times"][-1000:]
    
    # Đếm errors (status_code >= 400)
    if status_code >= 400:
        _metrics["errors_total"] += 1
        if endpoint not in _metrics["errors_by_endpoint"]:
            _metrics["errors_by_endpoint"][endpoint] = 0
        _metrics["errors_by_endpoint"][endpoint] += 1


def get_metrics() -> Dict:
    """Lấy metrics hiện tại.
    
    Tính toán và trả về các thống kê tổng hợp:
    - Tổng số requests
    - Số requests theo endpoint
    - Tổng số errors
    - Số errors theo endpoint
    - Response time trung bình (milliseconds)
    - Timestamp của request cuối cùng
    
    Returns:
        Dict chứa các metrics:
        {
            "requests_total": int,
            "requests_by_endpoint": Dict[str, int],
            "errors_total": int,
            "errors_by_endpoint": Dict[str, int],
            "average_response_time_ms": float,
            "last_request_time": str (ISO format) hoặc None
        }
    
    Note:
        Response time trung bình được tính từ 1000 giá trị gần nhất.
        Nếu chưa có request nào, trả về 0.0.
    """
    response_times = _metrics["response_times"]
    # Tính trung bình response time (chuyển từ giây sang milliseconds)
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    return {
        "requests_total": _metrics["requests_total"],
        "requests_by_endpoint": _metrics["requests_by_endpoint"],
        "errors_total": _metrics["errors_total"],
        "errors_by_endpoint": _metrics["errors_by_endpoint"],
        "average_response_time_ms": round(avg_response_time * 1000, 2),
        "last_request_time": _metrics["last_request_time"],
    }


def reset_metrics():
    """Reset tất cả metrics về giá trị ban đầu.
    
    Hàm này hữu ích khi:
    - Test/debug
    - Restart monitoring sau một khoảng thời gian
    - Cần clear dữ liệu cũ
    
    Warning:
        Hành động này không thể hoàn tác. Tất cả metrics sẽ bị mất.
    """
    global _metrics
    _metrics = {
        "requests_total": 0,
        "requests_by_endpoint": {},
        "errors_total": 0,
        "errors_by_endpoint": {},
        "response_times": [],
        "last_request_time": None,
    }

