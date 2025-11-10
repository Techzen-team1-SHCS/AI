# TÀI LIỆU GIẢI THÍCH HỆ THỐNG RECOMMENDATION

**Ngày tạo**: 2025-11-06  
**Mục đích**: Giải thích chi tiết về các thành phần đã tạo, cách hoạt động và cơ chế gợi ý

---

## MỤC LỤC

1. [Tổng quan các file đã tạo](#1-tổng-quan-các-file-đã-tạo)
2. [Cơ chế Cache](#2-cơ-chế-cache)
3. [Cơ chế Gợi ý (Recommendation)](#3-cơ-chế-gợi-ý-recommendation)
4. [ETL Pipeline](#4-etl-pipeline)
5. [Luồng hoạt động của hệ thống](#5-luồng-hoạt-động-của-hệ-thống)

---

## 1. TỔNG QUAN CÁC FILE ĐÃ TẠO

### 1.1. File `inference.py` (MỚI)

**Mục đích**: Load model và dự đoán recommendations cho user.

**Các chức năng chính**:

- `load_model()`: 
  - Load checkpoint từ `saved/DeepFM-*.pth`
  - Cache model trong RAM để tránh load lại
  - Trả về config, model, dataset

- `get_recommendations()`: 
  - Dự đoán và trả về top-K hotels cho user
  - Filter out interacted items
  - Xử lý cold start (user mới)

- `_get_user_interacted_items()`: 
  - Lấy danh sách hotels user đã tương tác
  - Sử dụng `inter_matrix` từ dataset

- `is_model_loaded()`: 
  - Kiểm tra model đã load chưa

**Lưu ý**: Model được cache trong RAM để tránh load lại mỗi request.

---

### 1.2. File `api_server.py` (ĐÃ CẬP NHẬT)

**Mục đích**: API server nhận dữ liệu từ web và trả về recommendations.

**Các thay đổi chính**:

1. **Endpoint `/recommendations/{user_id}`**:
   - Trước: Placeholder, trả về dữ liệu giả
   - Sau: Sử dụng inference thật từ model đã train

2. **Validation**:
   - Validate user_id, item_id (không rỗng, max 100 chars)
   - Validate action_type (phải là click, like, share, booking)
   - Validate timestamp (>= 0, trong khoảng hợp lý)

3. **Error handling**:
   - Xử lý lỗi rõ ràng với HTTP status codes đúng
   - Graceful degradation nếu model không load được
   - Error messages rõ ràng cho web team

4. **Model auto-load**:
   - Tự động load model khi server start
   - Hoặc load khi có request đầu tiên nếu chưa load

---

### 1.3. File `etl_web_to_hotel_inter.py` (ĐÃ CẬP NHẬT)

**Mục đích**: Xử lý dữ liệu từ web và ghi vào dataset.

**Các thay đổi chính**:

1. **`validate_action_data()`**:
   - Validate dữ liệu trước khi xử lý
   - Kiểm tra required fields, format, range

2. **Retry logic**:
   - Retry khi file bị lock (max 3 lần)
   - Exponential backoff (0.5s, 1s, 1.5s)

3. **Error handling**:
   - Xử lý lỗi an toàn, không mất dữ liệu
   - Không truncate log nếu xử lý thất bại
   - Đếm và báo cáo số dòng invalid

4. **Improved logging**:
   - Báo cáo chi tiết lỗi với line number
   - Thống kê số dòng processed/skipped

---

## 2. CƠ CHẾ CACHE

### 2.1. Cache là gì?

**Cache** là lưu model trong bộ nhớ RAM để tránh phải đọc lại file từ đĩa cứng.

### 2.2. Vấn đề không có Cache

Load model từ file `.pth` rất chậm (vài giây đến vài chục giây) vì phải:

- Đọc file từ đĩa (hàng trăm MB)
- Load weights vào RAM
- Khởi tạo model architecture
- Load dataset và config

**Ví dụ không có Cache (chậm)**:
```
Request 1: Load model từ file → Mất 10 giây
Request 2: Load model từ file → Mất 10 giây (lãng phí!)
Request 3: Load model từ file → Mất 10 giây (lãng phí!)
```

### 2.3. Giải pháp: Cache trong RAM

**Ví dụ có Cache (nhanh)**:
```
Request 1: Load model từ file → Mất 10 giây → Lưu vào RAM
Request 2: Dùng model từ RAM → Mất 0.01 giây ⚡
Request 3: Dùng model từ RAM → Mất 0.01 giây ⚡
```

### 2.4. Cách hoạt động trong Code

```python
# Biến global để lưu cache (trong RAM)
_model_cache = None      # Lưu model đã load
_config_cache = None     # Lưu config
_dataset_cache = None    # Lưu dataset

def load_model():
    # Nếu đã có trong cache → Dùng luôn, không load lại
    if _model_cache is not None:
        return _model_cache  # Trả về từ RAM (nhanh!)
    
    # Nếu chưa có → Load từ file
    model = load_from_file("saved/DeepFM-xxx.pth")  # Chậm
    _model_cache = model  # Lưu vào RAM
    return model
```

### 2.5. Lưu ý

- **Lần đầu tiên**: Load từ file (chậm, ~10 giây)
- **Các lần sau**: Dùng từ RAM (nhanh, ~0.01 giây)
- **Khi có model mới**: Cần clear cache hoặc reload
- **Memory usage**: Model chiếm vài trăm MB RAM

---

## 3. CƠ CHẾ GỢI Ý (RECOMMENDATION)

### 3.1. Dữ liệu Model học từ đâu?

Model học từ 3 nguồn dữ liệu:

#### A. User Features (`hotel.user`)
```
user_id: u1
- age: 25.0
- gender: F
- region: Hanoi
```

#### B. Item Features (`hotel.item`)
```
item_id: h1
- style: Romantic
- price: 2836440.0
- star: 4.0
- score: 9.9
- city: Hoan Kiem
```

#### C. Interaction History (`hotel.inter`)
```
user_id: u1, item_id: h1, action_type: 0.25 (click), timestamp: 1695400000
user_id: u1, item_id: h2, action_type: 0.5 (like), timestamp: 1695401000
user_id: u2, item_id: h1, action_type: 1.0 (booking), timestamp: 1695402000
```

### 3.2. Model học Pattern gì?

Model học các pattern như:

- **User pattern**: Users nữ, 20-30 tuổi, ở Hanoi thường thích hotels style Romantic ở Hoan Kiem
- **Item pattern**: Users nam, 30-40 tuổi thường booking hotels 4 sao, giá 2-4M
- **Interaction pattern**: Users đã like hotels Romantic thường sẽ booking hotels tương tự
- **Similarity pattern**: Hotels cùng style, cùng khu vực thường được recommend cùng nhau

### 3.3. Quy trình Gợi ý khi có Request

#### Ví dụ: `GET /recommendations/u1?top_k=5`

**Bước 1: Lấy thông tin user u1**
```python
User u1:
- age: 25
- gender: F
- region: Hanoi
- Đã tương tác: h1 (click), h2 (like)
```

**Bước 2: Tạo input cho model**
```python
# Tạo interaction cho u1 với TẤT CẢ 595 hotels:
for mỗi hotel trong 595 hotels:
    Input = {
        user_id: u1,
        user_age: 25,
        user_gender: F,
        user_region: Hanoi,
        item_id: h1, h2, h3, ..., h595
        item_style: Romantic, Quiet Love, Modern, ...
        item_price: 2.8M, 3.7M, 1.4M, ...
        item_star: 4.0, 4.0, 4.0, ...
        item_score: 9.9, 9.7, 9.9, ...
        item_city: Hoan Kiem, Hoan Kiem, Hanoi, ...
    }
```

**Bước 3: Model dự đoán điểm số**
```python
Model DeepFM tính điểm cho từng hotel:
h1: score = 0.85 (cao - vì user đã click)
h2: score = 0.92 (cao - vì user đã like)
h5: score = 0.78 (cao - style Romantic, gần region)
h12: score = 0.75 (cao - cùng city Hoan Kiem)
h8: score = 0.72 (trung bình)
...
h100: score = 0.15 (thấp - không phù hợp)
```

**Bước 4: Sắp xếp và lọc**
```python
Sắp xếp theo điểm giảm dần:
1. h2: 0.92 (nhưng đã tương tác → LOẠI BỎ)
2. h1: 0.85 (nhưng đã tương tác → LOẠI BỎ)
3. h5: 0.78 ✅
4. h12: 0.75 ✅
5. h8: 0.72 ✅
6. h20: 0.70 ✅
7. h15: 0.68 ✅
```

**Bước 5: Trả về top-5**
```json
{
    "user_id": "u1",
    "recommendations": ["h5", "h12", "h8", "h20", "h15"],
    "model_version": "DeepFM-Nov-06-2025_15-23-44"
}
```

### 3.4. Cái gì được gợi ý ra?

- **Hotels (item_id)**: h1, h2, h3, ..., h595
- **Dựa trên**:
  - **User features**: Tuổi, giới tính, khu vực
  - **Item features**: Style, giá, sao, điểm đánh giá, thành phố
  - **Pattern đã học**: Từ lịch sử tương tác của các user tương tự

### 3.5. Xử lý Cold Start

- **User mới** (chưa có trong dataset):
  - API trả về empty list: `{"recommendations": []}`
  - Backend team sẽ xử lý gợi ý theo IP location

- **User đã có nhưng chưa tương tác**:
  - Model vẫn dự đoán dựa trên user features
  - Có thể gợi ý popular items hoặc items phù hợp với profile

---

## 4. ETL PIPELINE

### 4.1. ETL là gì?

**ETL** = Extract, Transform, Load

- **Extract**: Lấy dữ liệu từ web (file `user_actions.log`)
- **Transform**: Xử lý và chuẩn hóa dữ liệu
- **Load**: Ghi vào dataset (`hotel.inter`)

### 4.2. ETL chạy như thế nào?

Có **3 cách** để chạy ETL:

#### Cách 1: Chạy Thủ Công (Ngay lập tức)

```bash
# Bạn có thể chạy ETL bất cứ lúc nào bằng lệnh:
python etl_web_to_hotel_inter.py
```

**Hoạt động**:
- Đọc `user_actions.log`
- Xử lý và ghi vào `hotel.inter`
- Archive và truncate log
- **Không cần server**

#### Cách 2: Tự động qua Docker (Mỗi 3 phút)

**Khi chạy Docker**:
```bash
docker-compose up
```

**ETL container sẽ**:
```bash
while true; do
    python etl_web_to_hotel_inter.py  # Chạy ETL
    sleep 180                          # Đợi 180 giây (3 phút)
done
```

**Lưu ý**:
- ETL chạy tự động khi Docker container đang chạy
- Mỗi 3 phút chạy một lần
- **Không cần API server** (ETL chạy độc lập)

#### Cách 3: Windows Task Scheduler (Chưa làm)

Có thể lên lịch chạy ETL mỗi 3 phút bằng Windows Task Scheduler.

### 4.3. Quy trình xử lý của ETL

```
1. Đọc user_actions.log (line-delimited JSON)
   ↓
2. Parse từng dòng JSON
   ↓
3. Validate dữ liệu:
   - Required fields (user_id, hotel_id, action_type, timestamp)
   - Format (user_id, hotel_id không rỗng, max 100 chars)
   - Action type hợp lệ (click, like, share, booking)
   - Timestamp hợp lệ (>= 0, trong khoảng 2000-2100)
   ↓
4. Group by (user_id, hotel_id)
   - Lấy action_score cao nhất (Max strategy)
   - Lấy timestamp mới nhất
   ↓
5. Append vào dataset/hotel/hotel.inter
   ↓
6. Archive vào user_actions.archive.log
   ↓
7. Truncate user_actions.log (xóa dữ liệu đã xử lý)
```

### 4.4. Max Strategy Grouping

**Ví dụ 1**:
```
User u1 với hotel h1 có nhiều hành động:
- click (0.25) tại 1695400000
- like (0.5) tại 1695401000
- share (0.75) tại 1695402000
- booking (1.0) tại 1695403000

ETL sẽ chọn:
- action_type: 1.0 (booking - điểm cao nhất)
- timestamp: 1695403000 (timestamp của booking)

Kết quả: u1 h1 1.0 1695403000
```

**Ví dụ 2** (Trường hợp đặc biệt):
```
User u1 với hotel h1 có 3 hành động:
1. click (0.25) tại 1695400000
2. booking (1.0) tại 1695401000
3. click (0.25) tại 1695402000

ETL sẽ:
1. Tìm điểm cao nhất: 1.0 (từ booking)
2. Tìm các hành động có điểm 1.0: chỉ có booking tại 1695401000
3. Lấy timestamp của booking: 1695401000

Kết quả: u1 h1 1.0 1695401000 ✅

Lưu ý: Timestamp luôn khớp với hành động có điểm cao nhất.
Nếu có nhiều hành động cùng điểm cao nhất, lấy timestamp mới nhất.
```

**Logic**:
- Lấy `action_score` cao nhất
- Trong các hành động có điểm cao nhất đó, lấy `timestamp` mới nhất
- Đảm bảo timestamp luôn khớp với hành động có điểm cao nhất

### 4.5. Retry Logic

- **Khi file bị lock**: Retry tối đa 3 lần
- **Exponential backoff**: Đợi 0.5s, 1s, 1.5s giữa các lần retry
- **An toàn dữ liệu**: Không truncate log nếu xử lý thất bại

---

## 5. LUỒNG HOẠT ĐỘNG CỦA HỆ THỐNG

### 5.1. Luồng 1: Real-time Inference (Gợi ý ngay lập tức)

```
User trên Web 
    ↓
Gửi request: GET /recommendations/u1?top_k=10
    ↓
API Server (api_server.py)
    ├─ Validate user_id và top_k
    ├─ Kiểm tra model đã load chưa
    │   └─ Nếu chưa → load model từ saved/DeepFM-*.pth
    ↓
Inference Module (inference.py)
    ├─ Load model (lần đầu hoặc dùng cache)
    ├─ Kiểm tra user có trong dataset không
    │   ├─ Có → Tiếp tục
    │   └─ Không → Trả về [] (cold start - backend sẽ xử lý)
    ├─ Lấy danh sách hotels user đã tương tác
    ├─ Tạo interaction cho user với TẤT CẢ hotels
    ├─ Predict điểm số cho từng hotel
    ├─ Sắp xếp theo điểm số giảm dần
    ├─ Loại bỏ hotels đã tương tác
    ├─ Lấy top-K hotels
    └─ Convert internal IDs → external tokens (h1, h2, ...)
    ↓
Trả về cho Web
{
    "user_id": "u1",
    "recommendations": ["h5", "h12", "h8", ...],
    "model_version": "DeepFM-Nov-06-2025_15-23-44",
    "top_k": 10
}
```

### 5.2. Luồng 2: Thu thập và xử lý dữ liệu

```
User thao tác trên Web (click, like, share, booking)
    ↓
Web gửi POST /user_action
{
    "user_id": "u1",
    "item_id": "h1",
    "action_type": "click",
    "timestamp": 1695400000
}
    ↓
API Server (api_server.py)
    ├─ Validate dữ liệu (user_id, item_id, action_type, timestamp)
    ├─ Ghi vào user_actions.log (append mode)
    └─ Trả về success
    ↓
ETL Script (etl_web_to_hotel_inter.py) - Chạy định kỳ mỗi 3 phút
    ├─ Đọc user_actions.log (line-delimited JSON)
    ├─ Parse từng dòng JSON
    ├─ Validate dữ liệu:
    │   ├─ Required fields
    │   ├─ Format (user_id, hotel_id)
    │   ├─ Action type hợp lệ
    │   └─ Timestamp hợp lệ
    ├─ Group by (user_id, hotel_id)
    │   └─ Lấy điểm cao nhất (Max strategy)
    │   └─ Lấy timestamp mới nhất
    ├─ Append vào dataset/hotel/hotel.inter
    ├─ Archive vào user_actions.archive.log
    └─ Truncate user_actions.log (xóa dữ liệu đã xử lý)
```

### 5.3. Luồng 3: Retraining (Chạy hàng ngày lúc 2h sáng)

```
ETL đã tích lũy dữ liệu mới trong hotel.inter
    ↓
Retrain Script (sẽ làm sau)
    ├─ Kiểm tra số lượng interactions mới
    ├─ Backup checkpoint cũ
    ├─ Train model với toàn bộ dữ liệu (cũ + mới)
    ├─ So sánh metrics (RMSE, MAE)
    ├─ Nếu tốt hơn → Lưu checkpoint mới
    └─ Clear model cache (để load model mới)
    ↓
Inference sẽ tự động dùng model mới (checkpoint mới nhất)
```

---

## 6. TÓM TẮT

### 6.1. Cache
- **Lưu model trong RAM** sau lần load đầu tiên
- **Các request sau** dùng model từ RAM, không đọc lại file
- **Nhanh hơn nhiều**: Từ 10s → 0.01s

### 6.2. Cơ chế Gợi ý
- **Dựa trên**: User features + Item features + Pattern học từ dữ liệu
- **Model dự đoán** điểm số cho tất cả hotels
- **Sắp xếp** theo điểm, loại bỏ hotels đã tương tác, trả về top-K

### 6.3. ETL
- **Chạy thủ công**: `python etl_web_to_hotel_inter.py` (bất cứ lúc nào)
- **Tự động (Docker)**: Chạy mỗi 3 phút khi Docker đang chạy
- **Không cần API server**: ETL chạy độc lập, chỉ cần file `user_actions.log`

---

## 7. LỢI ÍCH

1. **Real-time Inference**: Model được cache, trả về kết quả nhanh
2. **An toàn dữ liệu**: Validation, retry, archive, không mất dữ liệu khi lỗi
3. **Cold start**: Trả về empty list, backend xử lý theo IP
4. **Tích lũy dữ liệu**: ETL group theo Max strategy, tránh trùng lặp
5. **Dễ bảo trì**: Error messages rõ ràng, logging đầy đủ

---

**Cập nhật lần cuối**: 2025-11-06

