# LUỒNG HOẠT ĐỘNG CHI TIẾT CỦA HỆ THỐNG

**Ngày cập nhật**: 2025-01-14

---

## TỔNG QUAN: 2 LUỒNG ĐỘC LẬP

Hệ thống có **2 luồng hoạt động ĐỘC LẬP**:

1. **Luồng 1: Real-time Inference (Gợi ý ngay lập tức)**
   - Web gửi request → AI trả về recommendations **NGAY LẬP TỨC**
   - **KHÔNG cần đợi ETL** xử lý dữ liệu
   - Dùng **model hiện tại** đã được train

2. **Luồng 2: Thu thập và Cập nhật Dữ liệu (Background)**
   - Web gửi hành vi user → API ghi log
   - ETL xử lý mỗi 3 phút → Cập nhật dataset
   - Retrain mỗi ngày 2h sáng → Cập nhật model

---

## LUỒNG 1: REAL-TIME INFERENCE (GỢI Ý NGAY LẬP TỨC)

### Web gửi request như thế nào?

**Khi user vào trang web**, backend sẽ gọi API AI để lấy recommendations:

```php
// Backend PHP gọi API AI
$userId = $request->user()->id; // Ví dụ: 123
$res = Http::get("http://192.168.2.70:5000/recommendations/{$userId}?top_k=10");
$data = $res->json();

// $data['recommendations'] là array item_id: [501, 502, 503, ...]
```

**Endpoint**: `GET /recommendations/{user_id}?top_k=10`

### AI xử lý và trả về như thế nào?

```
1. Web gửi: GET /recommendations/123?top_k=10
   ↓
2. API Server nhận request
   ↓
3. Inference Module (inference.py)
   ├─ Load model từ saved/DeepFM-*.pth (lần đầu, hoặc dùng cache)
   ├─ Kiểm tra user_id=123 có trong dataset không
   │   ├─ Có → Tiếp tục
   │   └─ Không → Trả về [] (cold start - backend xử lý)
   ├─ Lấy danh sách hotels user đã tương tác (từ hotel.inter)
   ├─ Tạo interaction cho user với TẤT CẢ hotels (595 hotels)
   ├─ Model dự đoán điểm số cho từng hotel
   ├─ Sắp xếp theo điểm số giảm dần
   ├─ Loại bỏ hotels đã tương tác
   ├─ Lấy top-10 hotels
   └─ Convert internal IDs → external tokens (1 → 1, 2 → 2, ...)
   ↓
4. Trả về cho Web (NGAY LẬP TỨC, ~0.1-0.5 giây)
{
    "user_id": "123",
    "recommendations": [501, 502, 503, 504, 505, 506, 507, 508, 509, 510],
    "model_version": "DeepFM-Jan-14-2025_10-30-00",
    "top_k": 10
}
```

### ⚠️ QUAN TRỌNG: Luồng 1 KHÔNG cần đợi ETL

- **Model đã được train sẵn** từ dữ liệu cũ
- **Dữ liệu mới từ user** (click, like, booking) **CHƯA được dùng** trong luồng này
- Dữ liệu mới chỉ được dùng sau khi:
  1. ETL xử lý (mỗi 3 phút) → Cập nhật `hotel.inter`
  2. Retrain (mỗi ngày 2h sáng) → Cập nhật model

**Ví dụ**:
- User click hotel 501 lúc 10:00
- Web gọi API lúc 10:01 → AI vẫn dùng model cũ (chưa có dữ liệu click mới)
- ETL xử lý lúc 10:03 → Cập nhật `hotel.inter`
- Retrain lúc 2h sáng ngày mai → Model mới học được hành vi click

---

## LUỒNG 2: THU THẬP VÀ CẬP NHẬT DỮ LIỆU (BACKGROUND)

### Web gửi hành vi user như thế nào?

**Khi user thao tác** (click, like, share, booking), backend gửi hành vi đến AI:

```php
// Backend PHP gửi hành vi user
Http::timeout(10)->post(
    'http://192.168.2.70:5000/user_actions_batch',
    $behaviors->map(fn($b) => [
        'user_id' => $b->user_id,        // int: 123
        'item_id' => $b->item_id,        // int: 501
        'action_type' => $b->action_type, // string: "click", "like", "share", "booking"
        'timestamp' => $b->timestamp,     // float: 1695400000.0
    ])
);
```

**Endpoint**: `POST /user_actions_batch` (batch) hoặc `POST /user_action` (single)

### AI xử lý như thế nào?

```
1. Web gửi: POST /user_actions_batch
   [
       {"user_id": 123, "item_id": 501, "action_type": "click", "timestamp": 1695400000.0},
       {"user_id": 123, "item_id": 502, "action_type": "like", "timestamp": 1695401000.0}
   ]
   ↓
2. API Server (api_server.py)
   ├─ Validate dữ liệu (user_id, item_id, action_type, timestamp)
   ├─ Ghi vào data/user_actions.log (append mode, mỗi dòng 1 JSON)
   └─ Trả về success (NGAY LẬP TỨC, ~0.01 giây)
   ↓
3. ETL Script (etl_web_to_hotel_inter.py) - Chạy TỰ ĐỘNG mỗi 3 phút
   ├─ Đọc data/user_actions.log (line-delimited JSON)
   ├─ Parse từng dòng JSON
   ├─ Validate dữ liệu
   ├─ Group by (user_id, hotel_id)
   │   └─ Lấy action_score cao nhất (Max strategy)
   │   └─ Lấy timestamp mới nhất
   ├─ Append vào dataset/hotel/hotel.inter
   ├─ Archive vào data/user_actions.archive.log
   └─ Truncate data/user_actions.log (xóa dữ liệu đã xử lý)
   ↓
4. Retrain Scheduler (retrain_scheduler.py) - Chạy TỰ ĐỘNG mỗi ngày 2h sáng
   ├─ Kiểm tra số interactions mới (>= 100)
   ├─ Kiểm tra thời gian từ lần retrain cuối (>= 12 giờ)
   ├─ Backup model cũ
   ├─ Train model với toàn bộ dữ liệu (cũ + mới)
   ├─ So sánh metrics với model cũ
   ├─ Lưu checkpoint mới
   └─ Clear model cache (để load model mới)
```

---

## CẤU HÌNH TỰ ĐỘNG

### ETL: Chạy mỗi 3 phút

**File**: `docker-compose.yml` (dòng 37-64)

```yaml
recbole-etl:
  command: >
    sh -c "
      while true; do
        python etl_web_to_hotel_inter.py
        sleep 180  # 180 giây = 3 phút
      done
    "
```

**Hoạt động**:
- Chạy liên tục trong Docker container
- Mỗi 3 phút chạy ETL một lần
- Xử lý tất cả dữ liệu mới trong `data/user_actions.log`

### Retrain: Chạy mỗi ngày 2h sáng

**File**: `docker-compose.yml` (dòng 66-90)

```yaml
recbole-retrain:
  command: python retrain_scheduler.py
  environment:
    - RETRAIN_HOUR=2      # 2h sáng
    - RETRAIN_MINUTE=0    # 0 phút
    - RETRAIN_CHECK_INTERVAL=3600  # Kiểm tra mỗi 1 giờ
```

**File**: `retrain_scheduler.py`

**Hoạt động**:
- Chạy liên tục trong Docker container
- Kiểm tra mỗi 1 giờ xem đã đến 2h sáng chưa
- Khi đến 2h sáng → Chạy retrain
- Chỉ chạy 1 lần mỗi ngày

**Điều kiện retrain**:
- Số interactions mới >= 100
- Thời gian từ lần retrain cuối >= 12 giờ

---

## VÍ DỤ THỰC TẾ

### Timeline trong 1 ngày:

```
00:00 - User A click hotel 501
        → Web gửi POST /user_action → API ghi vào log
        → Web gọi GET /recommendations/A → AI trả về (dùng model cũ)

00:03 - ETL chạy (tự động)
        → Xử lý log → Cập nhật hotel.inter

00:05 - User B like hotel 502
        → Web gửi POST /user_action → API ghi vào log
        → Web gọi GET /recommendations/B → AI trả về (vẫn dùng model cũ)

00:08 - ETL chạy (tự động)
        → Xử lý log → Cập nhật hotel.inter

... (ETL chạy mỗi 3 phút suốt ngày)

02:00 - Retrain chạy (tự động)
        → Train model với tất cả dữ liệu (cũ + mới từ 00:00 đến 02:00)
        → Lưu model mới
        → Clear cache

02:05 - User C vào trang
        → Web gọi GET /recommendations/C
        → AI load model MỚI → Trả về recommendations (đã học được hành vi từ 00:00-02:00)
```

---

## TÓM TẮT

### Luồng 1 (Real-time Inference):
- **Web gửi**: `GET /recommendations/{user_id}?top_k=10`
- **AI trả về**: Recommendations **NGAY LẬP TỨC** (~0.1-0.5s)
- **Dùng**: Model hiện tại (đã train sẵn)
- **KHÔNG cần đợi**: ETL hoặc retrain

### Luồng 2 (Data Collection):
- **Web gửi**: `POST /user_actions_batch` (khi user thao tác)
- **AI xử lý**: Ghi vào log → ETL xử lý (mỗi 3 phút) → Retrain (mỗi ngày 2h sáng)
- **Kết quả**: Model được cập nhật với dữ liệu mới

### Hai luồng ĐỘC LẬP:
- Luồng 1: **Real-time**, dùng model hiện tại
- Luồng 2: **Background**, cập nhật model cho tương lai

---

**Lưu ý**: Dữ liệu mới từ user chỉ được dùng trong recommendations **SAU KHI** retrain (mỗi ngày 2h sáng).

