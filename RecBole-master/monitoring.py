import time
import json
from datetime import datetime
from typing import Dict, Optional
from functools import wraps

# Simple in-memory metrics storage
_metrics = {
    "requests_total": 0,
    "requests_by_endpoint": {},
    "errors_total": 0,
    "errors_by_endpoint": {},
    "response_times": [],
    "last_request_time": None,
}

def record_request(endpoint: str, response_time: float, status_code: int):
    """Record a request metric"""
    _metrics["requests_total"] += 1
    _metrics["last_request_time"] = datetime.now().isoformat()
    
    if endpoint not in _metrics["requests_by_endpoint"]:
        _metrics["requests_by_endpoint"][endpoint] = 0
    _metrics["requests_by_endpoint"][endpoint] += 1
    
    _metrics["response_times"].append(response_time)
    # Keep only last 1000 response times
    if len(_metrics["response_times"]) > 1000:
        _metrics["response_times"] = _metrics["response_times"][-1000:]
    
    if status_code >= 400:
        _metrics["errors_total"] += 1
        if endpoint not in _metrics["errors_by_endpoint"]:
            _metrics["errors_by_endpoint"][endpoint] = 0
        _metrics["errors_by_endpoint"][endpoint] += 1

def get_metrics() -> Dict:
    """Get current metrics"""
    response_times = _metrics["response_times"]
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
    """Reset all metrics"""
    global _metrics
    _metrics = {
        "requests_total": 0,
        "requests_by_endpoint": {},
        "errors_total": 0,
        "errors_by_endpoint": {},
        "response_times": [],
        "last_request_time": None,
    }

