# HƯỚNG DẪN CHẠY RECBOLE API - CHO TEAM

## 📋 YÊU CẦU

- **Docker Desktop** đã cài đặt (Windows/Mac/Linux)
- **Windows 10/11** hoặc **Linux** hoặc **Mac**

## 🚀 CÁC BƯỚC CHẠY NHANH

### Bước 1: Giải nén file ZIP

Giải nén file `RecBole-Docker-Package.zip` vào một thư mục (ví dụ: `C:\RecBole`)

### Bước 2: Mở PowerShell/Terminal

**Windows:**
- Mở PowerShell
- Di chuyển đến thư mục đã giải nén:
  ```powershell
  cd C:\RecBole
  ```

**Linux/Mac:**
```bash
cd /path/to/RecBole
```

### Bước 3: Tạo file cấu hình (Tùy chọn)

```powershell
# Copy file .env.example thành .env
Copy-Item .env.example .env

# Mở file .env để chỉnh sửa (tùy chọn)
notepad .env
```

**Lưu ý:** File `.env` là tùy chọn. Nếu không có, hệ thống sẽ dùng cấu hình mặc định.

### Bước 4: Build Docker Image

```powershell
docker-compose build
```

**Lưu ý:** Lần đầu build sẽ mất 5-10 phút (tải các package Python).

### Bước 5: Chạy hệ thống

```powershell
docker-compose up -d
```

### Bước 6: Kiểm tra hệ thống

```powershell
# Kiểm tra containers đang chạy
docker-compose ps

# Xem logs
docker-compose logs -f
```

**Nhấn `Ctrl+C` để thoát khỏi chế độ xem logs.**

### Bước 7: Test API

**Mở trình duyệt hoặc PowerShell:**

```powershell
# Health check
Invoke-WebRequest -Uri http://localhost:5000/health
```

**Hoặc mở trình duyệt:** http://localhost:5000/health

**Kết quả mong đợi:**
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

---

## 📡 API ENDPOINTS

### 1. Health Check
```
GET http://localhost:5000/health
```

### 2. API Schema
```
GET http://localhost:5000/schema
```

### 3. Gửi User Action
```
POST http://localhost:5000/user_action
Content-Type: application/json

{
  "user_id": "u123",
  "item_id": "h456",
  "action_type": "click",
  "timestamp": 1695400000.0
}
```

### 4. Lấy Recommendations
```
GET http://localhost:5000/recommendations/{user_id}?top_k=10
```

**Ví dụ:**
```
GET http://localhost:5000/recommendations/u1?top_k=5
```

---

## 🔧 CÁC LỆNH HỮU ÍCH

### Xem logs
```powershell
# Xem logs của tất cả containers
docker-compose logs -f

# Xem logs của API
docker-compose logs -f recbole-api

# Xem logs của ETL
docker-compose logs -f recbole-etl

# Xem logs của Retrain
docker-compose logs -f recbole-retrain
```

### Dừng hệ thống
```powershell
# Dừng containers
docker-compose down

# Dừng và xóa volumes (CẢNH BÁO: xóa mất dữ liệu)
docker-compose down -v
```

### Khởi động lại
```powershell
# Khởi động lại containers
docker-compose restart

# Hoặc dừng và chạy lại
docker-compose down
docker-compose up -d
```

### Vào trong container
```powershell
# Vào container API
docker-compose exec recbole-api bash

# Vào container ETL
docker-compose exec recbole-etl bash
```

---

## 🐛 XỬ LÝ LỖI

### Lỗi: "docker: command not found"

**Giải pháp:** Cài đặt Docker Desktop từ https://www.docker.com/products/docker-desktop

### Lỗi: "Port 5000 is already in use"

**Giải pháp:** Đổi port trong file `docker-compose.yml`:
```yaml
ports:
  - "5001:5000"  # Đổi từ 5000 sang 5001
```

### Lỗi: "Cannot connect to the Docker daemon"

**Giải pháp:** Mở Docker Desktop và đợi nó khởi động hoàn toàn.

### Lỗi: "Model not found"

**Giải pháp:** 
1. Kiểm tra xem có file `.pth` trong thư mục `saved/` không
2. Nếu không có, liên hệ team AI để lấy model file

---

## 📁 CẤU TRÚC THỨ MỤC

```
RecBole/
├── dataset/          # Dataset files (hotel.user, hotel.item, hotel.inter)
├── saved/            # Model files (.pth)
├── data/             # User actions log (tự động tạo)
├── log/              # Training logs
├── api_server.py     # API server
├── inference.py      # Inference module
├── etl_web_to_hotel_inter.py  # ETL pipeline
├── docker-compose.yml # Docker compose config
├── Dockerfile        # Docker image config
└── requirements.txt  # Python dependencies
```

---

## ⚙️ CẤU HÌNH

### Thay đổi port API

Sửa file `docker-compose.yml`:
```yaml
ports:
  - "YOUR_PORT:5000"
```

### Thay đổi thời gian retrain

Sửa file `.env`:
```env
RETRAIN_HOUR=2      # Giờ retrain (0-23)
RETRAIN_MINUTE=0    # Phút retrain (0-59)
```

### Thêm API Key

Sửa file `.env`:
```env
API_KEY=your-secret-api-key
```

---

## 📞 HỖ TRỢ

Nếu gặp vấn đề, liên hệ team AI để được hỗ trợ.

---

## ✅ CHECKLIST

- [ ] Docker Desktop đã cài đặt
- [ ] Đã giải nén file ZIP
- [ ] Đã build Docker image (`docker-compose build`)
- [ ] Đã chạy hệ thống (`docker-compose up -d`)
- [ ] Đã test API (`http://localhost:5000/health`)
- [ ] Đã test gửi user action
- [ ] Đã test recommendations

---

**Chúc bạn thành công! 🎉**

