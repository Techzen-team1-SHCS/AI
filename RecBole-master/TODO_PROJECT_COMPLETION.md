# DANH SÁCH VIỆC CẦN LÀM ĐỂ HOÀN THÀNH DỰ ÁN

## TỔNG QUAN

Dự án: **Hotel Recommendation System với RecBole**

Mục tiêu: Xây dựng hệ thống gợi ý khách sạn cá nhân hóa với:
- Model DeepFM (Regression)
- API server nhận dữ liệu hành vi từ web
- ETL pipeline xử lý dữ liệu định kỳ
- Inference endpoint trả về recommendations

---

## ✅ ĐÃ HOÀN THÀNH

### 1. Dataset Preparation
- [x] `hotel.user` - Thông tin người dùng (601 users)
- [x] `hotel.item` - Thông tin khách sạn (595 hotels)
- [x] `hotel.inter` - Tương tác người dùng-khách sạn (20,000+ interactions)
- [x] Xử lý encoding (UTF-8, loại bỏ BOM)
- [x] Chuẩn hóa dữ liệu (action_type: float scores)

### 2. Model Training
- [x] Config file (`deepfm_config.yaml`)
- [x] Training script (`run_recbole.py`)
- [x] Model đã được train (DeepFM, RMSE=0.1829, MAE=0.1148)
- [x] Checkpoint đã được lưu (`saved/DeepFM-*.pth`)
- [x] Scripts hỗ trợ:
  - [x] `view_training_progress.py` - Xem kết quả training
  - [x] `check_training_result.py` - Kiểm tra checkpoint

### 3. ETL Pipeline
- [x] `etl_web_to_hotel_inter.py` - Xử lý dữ liệu từ web
- [x] Đọc `user_actions.log` (line-delimited JSON)
- [x] Group by (user_id, hotel_id) và lấy điểm cao nhất
- [x] Append vào `hotel.inter`
- [x] Archive processed logs vào `user_actions.archive.log`
- [x] Truncate `user_actions.log` sau khi xử lý

### 4. API Server
- [x] `api_server.py` - FastAPI server
- [x] POST `/user_action` - Nhận 1 hành vi người dùng
- [x] POST `/user_actions_batch` - Nhận nhiều hành vi
- [x] GET `/health` - Health check
- [x] GET `/schema` - API contract
- [x] CORS middleware
- [x] API Key authentication (optional)

### 5. Docker Setup
- [x] `Dockerfile` - Build image
- [x] `docker-compose.yml` - Orchestration
- [x] `DOCKER_README.md` - Hướng dẫn Docker

### 6. Documentation
- [x] `TRAINING_DOCUMENTATION.md` - Tài liệu training đầy đủ

---

## 🔨 CẦN LÀM

### 1. Inference Endpoint (ƯU TIÊN CAO)

**Mô tả**: Implement endpoint `/recommendations/{user_id}` để trả về recommendations thật từ model đã train.

**Công việc**:
- [ ] Tạo script `inference.py` để load model và predict
- [ ] Load checkpoint từ `saved/DeepFM-*.pth`
- [ ] Load dataset để có thông tin user/item
- [ ] Implement `get_recommendations(user_id, top_k)` function
- [ ] Tích hợp vào `api_server.py` endpoint `/recommendations/{user_id}`
- [ ] Xử lý edge cases:
  - User mới (chưa có trong dataset)
  - User không có interaction nào
  - Top-K items đã tương tác (filter out)
- [ ] Cache model để tránh load lại mỗi request
- [ ] Error handling và logging

**Files cần tạo/sửa**:
- `inference.py` (mới)
- `api_server.py` (sửa endpoint `/recommendations/{user_id}`)

**Tham khảo**:
```python
from recbole.quick_start import load_data_and_model
from recbole.utils import init_seed, init_logger
from recbole.config import Config

# Load model
config, model, dataset, train_data, valid_data, test_data = load_data_and_model(
    model_file='saved/DeepFM-*.pth'
)

# Predict
scores = model.full_sort_predict(interaction)
```

---

### 2. Retraining Pipeline (ƯU TIÊN TRUNG BÌNH)

**Mô tả**: Tự động retrain model khi có đủ dữ liệu mới.

**Công việc**:
- [ ] Tạo script `retrain_model.py`
- [ ] Kiểm tra số lượng interactions mới (so với lần train trước)
- [ ] Quyết định khi nào retrain (ví dụ: > 1000 interactions mới)
- [ ] Backup checkpoint cũ trước khi retrain
- [ ] Chạy training với dữ liệu mới
- [ ] So sánh metrics (RMSE, MAE) với model cũ
- [ ] Chỉ thay thế model nếu metrics tốt hơn
- [ ] Log retraining history
- [ ] Tích hợp vào ETL hoặc chạy định kỳ (cron job)

**Files cần tạo**:
- `retrain_model.py` (mới)
- `retrain_config.yaml` (mới - config cho retraining)

**Lưu ý**:
- Retrain có thể mất thời gian (vài phút đến vài giờ)
- Nên chạy offline (không ảnh hưởng API)
- Có thể chạy vào giờ thấp điểm (đêm)

---

### 3. Model Versioning (ƯU TIÊN THẤP)

**Mô tả**: Quản lý nhiều version của model.

**Công việc**:
- [ ] Tạo cấu trúc thư mục cho model versions:
  ```
  saved/
    DeepFM-v1.0-2025-11-06.pth
    DeepFM-v1.1-2025-11-10.pth
    DeepFM-v1.2-2025-11-15.pth
  ```
- [ ] Lưu metadata cho mỗi version (metrics, dataset size, training date)
- [ ] API endpoint để list available models
- [ ] API endpoint để switch model version
- [ ] A/B testing support (chạy 2 models song song)

**Files cần tạo**:
- `model_manager.py` (mới)
- `model_metadata.json` (mới)

---

### 4. Testing (ƯU TIÊN CAO)

**Mô tả**: Viết tests cho các components chính.

**Công việc**:
- [ ] Unit tests cho ETL pipeline
  - Test `get_action_score()`
  - Test `_group_and_append()`
  - Test parsing JSON lines
- [ ] Unit tests cho API endpoints
  - Test POST `/user_action`
  - Test GET `/recommendations/{user_id}`
  - Test error handling
- [ ] Integration tests
  - Test ETL → Dataset → Training flow
  - Test API → ETL → Inference flow
- [ ] Performance tests
  - Test API response time
  - Test inference latency
  - Test ETL processing time

**Files cần tạo**:
- `tests/test_etl.py` (mới)
- `tests/test_api.py` (mới)
- `tests/test_inference.py` (mới)

---

### 5. Monitoring & Logging (ƯU TIÊN TRUNG BÌNH)

**Mô tả**: Theo dõi hệ thống và log các sự kiện quan trọng.

**Công việc**:
- [ ] Structured logging (JSON format)
- [ ] Log levels (INFO, WARNING, ERROR)
- [ ] Log rotation (tránh log files quá lớn)
- [ ] Metrics tracking:
  - Số lượng requests/giờ
  - API response time
  - ETL processing time
  - Model inference latency
  - Error rate
- [ ] Health check endpoint mở rộng (check model, dataset, disk space)
- [ ] Alerting (email/Slack khi có lỗi)

**Files cần tạo/sửa**:
- `logging_config.py` (mới)
- `monitoring.py` (mới)
- `api_server.py` (sửa - thêm logging)

---

### 6. Error Handling & Validation (ƯU TIÊN CAO)

**Mô tả**: Xử lý lỗi và validate dữ liệu tốt hơn.

**Công việc**:
- [ ] Validate user_id và item_id tồn tại trong dataset
- [ ] Handle missing fields trong JSON
- [ ] Handle malformed JSON gracefully
- [ ] Retry logic cho ETL (nếu file bị lock)
- [ ] Graceful degradation (nếu model không load được)
- [ ] Error messages rõ ràng cho web team

**Files cần sửa**:
- `api_server.py` (sửa - thêm validation)
- `etl_web_to_hotel_inter.py` (sửa - cải thiện error handling)

---

### 7. Performance Optimization (ƯU TIÊN THẤP)

**Mô tả**: Tối ưu hiệu suất hệ thống.

**Công việc**:
- [ ] Cache model trong memory (tránh load lại)
- [ ] Batch inference (nếu có nhiều requests)
- [ ] Async processing cho ETL
- [ ] Database indexing (nếu dùng database)
- [ ] CDN cho static files (nếu có)

**Files cần sửa**:
- `inference.py` (sửa - thêm caching)
- `api_server.py` (sửa - async endpoints)

---

### 8. Documentation (ƯU TIÊN TRUNG BÌNH)

**Mô tả**: Tài liệu đầy đủ cho dự án.

**Công việc**:
- [ ] `API_DOCUMENTATION.md` - Tài liệu API đầy đủ
- [ ] `DEPLOYMENT_GUIDE.md` - Hướng dẫn deploy production
- [ ] `ARCHITECTURE.md` - Kiến trúc hệ thống
- [ ] `ETL_DOCUMENTATION.md` - Tài liệu ETL pipeline
- [ ] `INFERENCE_DOCUMENTATION.md` - Tài liệu inference
- [ ] Update `README.md` với thông tin tổng quan
- [ ] Code comments và docstrings

**Files cần tạo**:
- `API_DOCUMENTATION.md` (mới)
- `DEPLOYMENT_GUIDE.md` (mới)
- `ARCHITECTURE.md` (mới)
- `ETL_DOCUMENTATION.md` (mới)
- `INFERENCE_DOCUMENTATION.md` (mới)

---

### 9. Production Deployment (ƯU TIÊN CAO)

**Mô tả**: Chuẩn bị cho production deployment.

**Công việc**:
- [ ] Environment variables cho production
- [ ] Secrets management (API keys, database credentials)
- [ ] SSL/TLS certificates
- [ ] Rate limiting cho API
- [ ] Backup strategy (checkpoints, datasets)
- [ ] Disaster recovery plan
- [ ] Load balancing (nếu cần)
- [ ] Auto-scaling (nếu cần)

**Files cần tạo/sửa**:
- `.env.example` (mới)
- `docker-compose.prod.yml` (mới)
- `deploy.sh` (mới)

---

### 10. Integration với Web (ƯU TIÊN CAO)

**Mô tả**: Kết nối với web application.

**Công việc**:
- [ ] Test API với web team
- [ ] Đảm bảo CORS hoạt động đúng
- [ ] Đảm bảo authentication hoạt động
- [ ] Test với real data từ web
- [ ] Performance testing với load thực tế
- [ ] Error handling cho các edge cases từ web

**Files cần sửa**:
- `api_server.py` (sửa - test với web)

---

## 📋 KẾ HOẠCH THỰC HIỆN

### Phase 1: Core Functionality (Tuần 1-2)
1. ✅ Inference Endpoint
2. ✅ Error Handling & Validation
3. ✅ Testing cơ bản

### Phase 2: Production Ready (Tuần 3-4)
4. ✅ Retraining Pipeline
5. ✅ Monitoring & Logging
6. ✅ Production Deployment
7. ✅ Integration với Web

### Phase 3: Enhancement (Tuần 5+)
8. ✅ Model Versioning
9. ✅ Performance Optimization
10. ✅ Documentation đầy đủ

---

## 🎯 MỤC TIÊU HOÀN THÀNH

### Minimum Viable Product (MVP)
- [x] Dataset preparation
- [x] Model training
- [x] ETL pipeline
- [x] API server (nhận dữ liệu)
- [ ] **Inference endpoint (THIẾU)**
- [ ] **Error handling cơ bản (THIẾU)**
- [ ] **Testing cơ bản (THIẾU)**

### Production Ready
- [ ] Inference endpoint với caching
- [ ] Retraining pipeline
- [ ] Monitoring & logging
- [ ] Error handling đầy đủ
- [ ] Testing đầy đủ
- [ ] Documentation đầy đủ
- [ ] Production deployment

---

## 📝 NOTES

### Ưu tiên cao nhất
1. **Inference Endpoint** - Đây là core feature, không có thì hệ thống không hoạt động
2. **Error Handling** - Cần thiết cho production
3. **Testing** - Đảm bảo chất lượng code

### Có thể làm sau
- Model Versioning
- Performance Optimization
- Advanced Monitoring

### Dependencies
- Inference endpoint cần model đã train (✅ có)
- Retraining pipeline cần ETL pipeline (✅ có)
- Testing cần tất cả components (đang làm)

---

**Cập nhật lần cuối**: 2025-11-06  
**Người phụ trách**: [Điền tên]  
**Trạng thái**: Đang thực hiện

