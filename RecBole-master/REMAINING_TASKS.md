# DANH SÁCH CÔNG VIỆC CÒN LẠI (NGOÀI DOCKER)

## ✅ ĐÃ HOÀN THÀNH
- ✅ Inference endpoint với caching
- ✅ Retraining pipeline tự động
- ✅ Error handling cơ bản
- ✅ ETL pipeline với validation
- ✅ API server với authentication

---

## 🔴 BẮT BUỘC (Phải làm để hệ thống hoạt động với web)

### 1. Cấu hình CORS cho domain web (≈15 phút) ⚠️ QUAN TRỌNG

**Hiện trạng**: CORS đang cho phép tất cả origins (`allow_origins=["*"]`)

**Cần làm**:
- Thêm biến môi trường `ALLOWED_ORIGINS` (danh sách domain được phép)
- Cập nhật `api_server.py` để đọc từ biến môi trường
- Hỗ trợ nhiều domain (development, production)

**Files cần sửa**:
- `api_server.py` (sửa CORS middleware)

**Ví dụ**:
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

### 2. Test kết nối với web (≈1 giờ) ⚠️ QUAN TRỌNG

**Cần làm**:
- Test POST `/user_action` với dữ liệu từ web
- Test GET `/recommendations/{user_id}` với user_id từ web
- Kiểm tra error handling khi web gửi dữ liệu sai format
- Kiểm tra performance với load thực tế

**Files cần tạo**:
- `test_web_integration.py` (script test với web)

---

## 🟡 NÊN LÀM (Để hệ thống ổn định hơn)

### 3. Monitoring cơ bản (≈1-2 giờ)

**Cần làm**:
- Log structured (JSON format)
- Log rotation (tránh log files quá lớn)
- Metrics tracking:
  - Số lượng requests/giờ
  - API response time
  - ETL processing time
  - Model inference latency
  - Error rate
- Health check endpoint mở rộng (check model, dataset, disk space)

**Files cần tạo/sửa**:
- `logging_config.py` (mới)
- `monitoring.py` (mới)
- `api_server.py` (sửa - thêm logging)

---

### 4. Backup Strategy (≈30 phút)

**Cần làm**:
- Backup `dataset/`, `saved/`, `data/` định kỳ
- Tự động hóa backup (có thể dùng script hoặc cron job)
- Lưu backup vào thư mục riêng với timestamp

**Files cần tạo**:
- `backup_data.py` (script backup)
- `backup_schedule.sh` (script chạy backup định kỳ)

---

### 5. Unit Tests cơ bản (≈2-3 giờ)

**Cần làm**:
- Unit tests cho ETL pipeline
  - Test `get_action_score()`
  - Test `_group_and_append()`
  - Test parsing JSON lines
- Unit tests cho API endpoints
  - Test POST `/user_action`
  - Test GET `/recommendations/{user_id}`
  - Test error handling
- Unit tests cho inference
  - Test `load_model()`
  - Test `get_recommendations()`
  - Test cache functionality

**Files cần tạo**:
- `tests/test_etl.py` (mới)
- `tests/test_api.py` (mới)
- `tests/test_inference.py` (mới)

---

## 🟢 CÓ THỂ LÀM SAU (Không bắt buộc ngay)

### 6. Model Versioning (≈1-2 giờ)

**Cần làm**:
- Lưu metadata cho mỗi version (metrics, dataset size, training date)
- API endpoint để list available models
- API endpoint để switch model version

**Files cần tạo**:
- `model_manager.py` (mới)
- `model_metadata.json` (mới)

---

### 7. Advanced Monitoring (≈2-3 giờ)

**Cần làm**:
- Prometheus/Grafana integration
- Alerting (email/Slack khi có lỗi)
- Dashboard để theo dõi metrics

**Files cần tạo**:
- `prometheus_config.yml` (mới)
- `grafana_dashboard.json` (mới)

---

### 8. Performance Optimization (≈2-3 giờ)

**Cần làm**:
- Batch inference (nếu có nhiều requests)
- Async processing cho ETL
- Database indexing (nếu dùng database)

**Files cần sửa**:
- `api_server.py` (sửa - async endpoints)
- `etl_web_to_hotel_inter.py` (sửa - async processing)

---

## 📊 TỔNG KẾT

### Bắt buộc (≈1.5 giờ)
1. ✅ Cấu hình CORS (15 phút)
2. ✅ Test kết nối với web (1 giờ)

### Nên làm (≈4-6 giờ)
3. ✅ Monitoring cơ bản (1-2 giờ)
4. ✅ Backup Strategy (30 phút)
5. ✅ Unit Tests cơ bản (2-3 giờ)

### Có thể làm sau
6. Model Versioning
7. Advanced Monitoring
8. Performance Optimization

---

## 🎯 KHUYẾN NGHỊ

### Trước khi kết nối với web:
1. **Cấu hình CORS** (BẮT BUỘC)
2. **Test kết nối với web** (BẮT BUỘC)

### Sau khi kết nối với web:
3. **Monitoring cơ bản** (NÊN LÀM)
4. **Backup Strategy** (NÊN LÀM)
5. **Unit Tests** (NÊN LÀM)

### Làm sau:
6. Model Versioning
7. Advanced Monitoring
8. Performance Optimization

---

**Tổng thời gian ước tính**: ~6-8 giờ (bắt buộc + nên làm)

