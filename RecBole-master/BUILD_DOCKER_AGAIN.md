# HƯỚNG DẪN BUILD LẠI DOCKER SAU KHI SỬA CODE

## TÓM TẮT THAY ĐỔI

Sau khi sửa code để hỗ trợ ID int, bạn cần build lại Docker để áp dụng các thay đổi:

### Các file đã thay đổi:
- `api_server.py` - Chấp nhận Union[str, int] cho user_id và item_id
- `inference.py` - Convert recommendations về int
- `etl_web_to_hotel_inter.py` - Convert về int khi ghi vào dataset
- `monitoring.py` - Thêm monitoring cơ bản (mới)

### Dataset đã thay đổi:
- `hotel.item` - item_id từ string (h1, h2...) → int (1, 2...)
- `hotel.user` - user_id từ string (u1, u2...) → int (1, 2...)
- `hotel.inter` - Đã được tạo lại với 100k interactions, ID int

---

## CÁC BƯỚC BUILD LẠI DOCKER

### Bước 1: Dừng containers hiện tại

```powershell
cd D:\GitHub\AI\RecBole-master
docker-compose down
```

### Bước 2: Xóa images cũ (tùy chọn, để đảm bảo build mới hoàn toàn)

```powershell
# Xóa images cũ
docker-compose rm -f

# Hoặc xóa tất cả images liên quan
docker images | Select-String "recbole" | ForEach-Object { docker rmi $_.Split()[2] -f }
```

### Bước 3: Build lại images

```powershell
# Build lại với --no-cache để đảm bảo build mới hoàn toàn
docker-compose build --no-cache

# Hoặc build bình thường (nhanh hơn, dùng cache nếu có)
docker-compose build
```

**Lưu ý:** Build lần đầu có thể mất 10-15 phút do tải PyTorch và dependencies.

### Bước 4: Chạy containers

```powershell
docker-compose up -d
```

### Bước 5: Kiểm tra containers đang chạy

```powershell
docker-compose ps
```

**Kết quả mong đợi:**
```
NAME                STATUS          PORTS
recbole-api         Up X minutes    http://localhost:5000/
recbole-etl         Up X minutes
recbole-retrain     Up X minutes
```

### Bước 6: Kiểm tra logs

```powershell
# Xem logs của API server
docker-compose logs -f recbole-api

# Hoặc xem logs của tất cả services
docker-compose logs -f
```

**Nhấn `Ctrl+C` để thoát khỏi chế độ xem logs.**

### Bước 7: Test API

```powershell
# Health check
Invoke-WebRequest -Uri http://localhost:5000/health | Select-Object -ExpandProperty Content

# Test với user_id int
Invoke-WebRequest -Uri "http://localhost:5000/recommendations/1?top_k=5" | Select-Object -ExpandProperty Content
```

---

## KIỂM TRA SAU KHI BUILD

### 1. Kiểm tra model đã load

```powershell
$response = Invoke-WebRequest -Uri http://localhost:5000/health
$response.Content | ConvertFrom-Json
```

**Kết quả mong đợi:**
```json
{
  "ok": true,
  "model_loaded": true
}
```

### 2. Kiểm tra recommendations format

```powershell
$response = Invoke-WebRequest -Uri "http://localhost:5000/recommendations/1?top_k=5"
$data = $response.Content | ConvertFrom-Json
$data.recommendations
```

**Kết quả mong đợi:** Recommendations là array các số int (ví dụ: [10, 20, 30, 40, 50])

### 3. Test POST với int IDs

```powershell
$body = @{
    user_id = 123
    item_id = 456
    action_type = "click"
    timestamp = 1695400000.0
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:5000/user_action `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body | Select-Object -ExpandProperty Content
```

**Kết quả mong đợi:**
```json
{
  "status": "success",
  "data": {
    "user_id": "123",
    "item_id": "456",
    "action_type": "click",
    "timestamp": 1695400000.0
  }
}
```

---

## XỬ LÝ LỖI

### Lỗi: "Port 5000 is already in use"

**Giải pháp:**
```powershell
# Tìm process đang dùng port 5000
netstat -ano | findstr :5000

# Kill process (thay PID bằng process ID tìm được)
taskkill /PID <PID> /F
```

### Lỗi: "Model not found"

**Giải pháp:**
- Kiểm tra có file `.pth` trong `saved/` không
- Đảm bảo volume mount đúng trong `docker-compose.yml`

### Lỗi: "Cannot connect to the Docker daemon"

**Giải pháp:**
- Mở Docker Desktop và đợi nó khởi động hoàn toàn

---

## LƯU Ý QUAN TRỌNG

1. **Volumes:** Docker sử dụng volumes để mount dataset và saved models. Đảm bảo:
   - `./dataset` chứa dataset mới (ID int)
   - `./saved` chứa model mới đã train với dataset mới

2. **Environment Variables:** Kiểm tra file `.env` nếu có:
   ```env
   API_KEY=your-api-key-here
   ALLOWED_ORIGINS=http://localhost:3000,http://192.168.2.70:3000
   RETRAIN_HOUR=2
   RETRAIN_MINUTE=0
   ```

3. **Model mới:** Model mới đã được train với dataset có ID int. Đảm bảo model file mới nhất trong `saved/` là model mới.

---

## TÓM TẮT LỆNH NHANH

```powershell
# Dừng và xóa containers
docker-compose down

# Build lại
docker-compose build

# Chạy lại
docker-compose up -d

# Xem logs
docker-compose logs -f recbole-api

# Test
Invoke-WebRequest -Uri http://localhost:5000/health
```

---

**Chúc bạn thành công! 🎉**


