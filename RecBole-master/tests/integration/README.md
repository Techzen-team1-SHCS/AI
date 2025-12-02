# Integration Tests

Thư mục này chứa các test tích hợp (integration tests) cho hệ thống recommendation.

## Các file test

- **`test_api_endpoints.py`**: Test các API endpoints (GET/POST requests)
- **`test_behavior_boost.py`**: Test Behavior Boost functionality (Phase 1 + Phase 2)
- **`test_behavior_boost_simple.py`**: Test đơn giản Behavior Boost (không cần torch/recbole)
- **`test_comprehensive_system.py`**: Test tổng thể hệ thống theo TEST_PLAN.md
- **`test_docker_system.py`**: Test hệ thống Docker sau khi build
- **`test_inference.py`**: Test inference module và load model

## Cách chạy tests

### ⚠️ LƯU Ý QUAN TRỌNG

**Phải chạy từ root directory của project** với đường dẫn đầy đủ:

```bash
# Đảm bảo đang ở root directory
cd D:\GitHub\AI\RecBole-master

# Sau đó chạy với đường dẫn đầy đủ:
python tests/integration/test_inference.py
```

### Danh sách lệnh chạy tests

```bash
# Test API endpoints
python tests/integration/test_api_endpoints.py

# Test Behavior Boost
python tests/integration/test_behavior_boost.py

# Test đơn giản (không cần model)
python tests/integration/test_behavior_boost_simple.py

# Test tổng thể hệ thống
python tests/integration/test_comprehensive_system.py

# Test Docker system
python tests/integration/test_docker_system.py

# Test inference
python tests/integration/test_inference.py
```

### Nếu gặp lỗi "No such file or directory"

- ❌ **SAI**: `python test_inference.py` (file không còn ở root)
- ✅ **ĐÚNG**: `python tests/integration/test_inference.py` (chạy từ root với đường dẫn đầy đủ)

## Yêu cầu

- API server phải đang chạy (cho các test API)
- Model phải đã được train (cho các test inference)
- Docker containers phải đang chạy (cho test_docker_system.py)

## Lưu ý

Các file test tự động thêm root directory vào `sys.path` để có thể import các module từ root (`inference.py`, `api_server.py`, etc.).

