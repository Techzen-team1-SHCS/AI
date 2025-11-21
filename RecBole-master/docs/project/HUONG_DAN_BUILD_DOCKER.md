# HƯỚNG DẪN BUILD DOCKER - TỪNG BƯỚC CỤ THỂ

## ⚡ TÓM TẮT NHANH

**Quan trọng:** Trước khi build, **dừng các build treo** trên Docker Desktop!

1. **Dừng build treo**: Docker Desktop → Builds → Cancel/Delete các build đang chạy
2. **Build**: `docker-compose build` (lần đầu ~15-20 phút)
3. **Chạy**: `docker-compose up -d`
4. **Test**: `Invoke-WebRequest -Uri http://localhost:5000/health`

## 📋 MỤC LỤC

1. [Chuẩn bị](#1-chuẩn-bị)
2. [Cài đặt Docker](#2-cài-đặt-docker)
3. [Build và chạy](#3-build-và-chạy)
4. [Tạo package cho team](#4-tạo-package-cho-team)
5. [Test](#5-test)

---

## 1. CHUẨN BỊ

### Kiểm tra các file cần thiết:

```powershell
# Kiểm tra các file quan trọng
Test-Path "docker-compose.yml"
Test-Path "Dockerfile"
Test-Path "api_server.py"
Test-Path "inference.py"
Test-Path "saved\*.pth"
Test-Path "dataset\hotel\hotel.inter"
```

**Kết quả mong đợi:** Tất cả đều trả về `True`

### Kiểm tra model files:

```powershell
# Kiểm tra có model file không
Get-ChildItem -Path "saved" -Filter "*.pth" | Select-Object Name
```

**Kết quả mong đợi:** Có ít nhất 1 file `.pth`

---

## 2. CÀI ĐẶT DOCKER

### Bước 1: Tải Docker Desktop

1. Truy cập: https://www.docker.com/products/docker-desktop
2. Chọn **"Download for Windows"**
3. Tải và cài đặt

### Bước 2: Khởi động Docker Desktop

1. Mở **Docker Desktop** từ Start Menu
2. Đợi Docker khởi động (biểu tượng Docker màu xanh)

### Bước 3: Kiểm tra Docker

```powershell
docker --version
docker-compose --version
```

**Kết quả mong đợi:**
```
Docker version 24.0.x
Docker Compose version v2.x.x
```

---

## 3. BUILD VÀ CHẠY

### Bước 1: Tạo file .env (tùy chọn)

```powershell
# Tạo file .env
@"
API_KEY=
RETRAIN_HOUR=2
RETRAIN_MINUTE=0
RETRAIN_CHECK_INTERVAL=3600
ALLOWED_ORIGINS=
"@ | Out-File -FilePath .env -Encoding utf8
```

### Bước 2: Dừng các build đang treo (nếu có)

**Vấn đề:** Nếu có nhiều build đang chạy trên Docker Desktop, chúng có thể gây xung đột hoặc làm chậm build mới.

**Giải pháp:**

1. Mở **Docker Desktop**
2. Vào tab **"Builds"** (hoặc "Build History")
3. Tìm các build đang ở trạng thái **"Building"** hoặc **"Active"**
4. Nhấn nút **"Cancel"** hoặc **"Stop"** để dừng các build không cần thiết
5. Xóa các build cũ nếu cần: chọn build → nhấn **"Delete"**

**Hoặc dùng lệnh:**
```powershell
# Xóa tất cả build cache (cẩn thận, sẽ xóa cache)
docker builder prune -f
```

### Bước 3: Build Docker image

```powershell
# Build image (lần đầu mất 10-15 phút do tải PyTorch CPU)
# Lưu ý: Build sẽ tải PyTorch CPU (~500MB) và các dependencies
docker-compose build
```

**Quá trình build:**
- Bước 1: Tải base image Python 3.11 (~50MB)
- Bước 2: Cài system dependencies (gcc, g++) (~5 phút)
- Bước 3: Cài PyTorch CPU (~500MB, ~5 phút)
- Bước 4: Cài các Python packages từ requirements.txt (~5 phút)
- **Tổng thời gian:** ~15-20 phút lần đầu

**Kết quả mong đợi:**
```
[+] Building 900.0s (15/15) FINISHED
 => => writing image sha256:xxxxx
Successfully built xxxxx
```

**Nếu build bị treo hoặc lỗi:**
1. Kiểm tra kết nối internet (cần tải packages từ PyPI)
2. Kiểm tra dung lượng ổ cứng (cần ~3-5GB cho build)
3. Thử build lại: `docker-compose build --no-cache`
4. Kiểm tra logs: Xem output chi tiết trong terminal

### Bước 4: Chạy hệ thống

```powershell
# Chạy containers
docker-compose up -d
```

**Kết quả mong đợi:**
```
[+] Running 4/4
 ✔ Container recbole-api       Started
 ✔ Container recbole-etl       Started
 ✔ Container recbole-retrain   Started
```

### Bước 5: Kiểm tra containers

```powershell
# Kiểm tra containers đang chạy
docker-compose ps
```

**Kết quả mong đợi:**
```
NAME                STATUS          PORTS
recbole-api         Up 2 minutes    http://localhost:5000/
recbole-etl         Up 2 minutes
recbole-retrain     Up 2 minutes
```

### Bước 6: Xem logs

```powershell
# Xem logs
docker-compose logs -f recbole-api
```

**Nhấn `Ctrl+C` để thoát**

**Kết quả mong đợi:**
```
recbole-api  | [API] Model đã được load thành công!
recbole-api  | INFO:     Uvicorn running on http://0.0.0.0:5000
```

---

## 4. TẠO PACKAGE CHO TEAM

### Bước 1: Chạy script tạo package

```powershell
# Chạy script
.\create_docker_package.ps1
```

**Kết quả mong đợi:**
```
===========================================
TẠO DOCKER PACKAGE CHO TEAM
===========================================

Bước 1: Tạo thư mục tạm...
Bước 2: Copy các file cần thiết...
  ✓ api_server.py
  ✓ inference.py
  ...
Bước 7: Tạo file ZIP...
  ✓ Đã tạo file ZIP: RecBole-Docker-Package.zip

HOÀN THÀNH!
```

### Bước 2: Kiểm tra file ZIP

```powershell
# Kiểm tra file ZIP
Get-Item RecBole-Docker-Package.zip | Select-Object Name, Length
```

**Kết quả mong đợi:**
- File: `RecBole-Docker-Package.zip`
- Kích thước: ~500MB - 2GB

### Bước 3: Gửi cho team

1. Upload file ZIP lên Google Drive/OneDrive
2. Gửi link cho team
3. Kèm theo hướng dẫn ngắn gọn

---

## 5. TEST

### Test 1: Health check

```powershell
# Test health check
Invoke-WebRequest -Uri http://localhost:5000/health | Select-Object -ExpandProperty Content
```

**Kết quả mong đợi:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "timestamp": "2025-01-XX..."
}
```

### Test 2: Gửi user action

```powershell
# Gửi user action
$body = @{
    user_id = "u123"
    item_id = "h456"
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
  "message": "User action logged successfully"
}
```

### Test 3: Lấy recommendations

```powershell
# Lấy recommendations
Invoke-WebRequest -Uri "http://localhost:5000/recommendations/u1?top_k=5" | Select-Object -ExpandProperty Content
```

**Kết quả mong đợi:**
```json
{
  "user_id": "u1",
  "recommendations": ["h123", "h456", "h789", "h101", "h112"],
  "model_version": "DeepFM-Nov-11-2025_16-15-41"
}
```

---

## 🐛 XỬ LÝ LỖI

### Lỗi: "docker: command not found"

**Giải pháp:** Cài đặt Docker Desktop

### Lỗi: "Port 5000 is already in use"

**Giải pháp:** Đổi port trong `docker-compose.yml`:
```yaml
ports:
  - "5001:5000"
```

### Lỗi: "Model not found"

**Giải pháp:** Kiểm tra có file `.pth` trong `saved/` không

### Lỗi: "Cannot connect to the Docker daemon"

**Giải pháp:** Mở Docker Desktop và đợi nó khởi động

---

## 📖 XEM THÊM

- **Hướng dẫn chi tiết:** `BUILD_DOCKER_GUIDE.md`
- **Hướng dẫn cho team:** `README_FOR_TEAM.md`
- **Quick start:** `QUICK_START.md`
- **Các bước tóm tắt:** `DOCKER_BUILD_STEPS.md`

---

## ✅ CHECKLIST

- [ ] Docker Desktop đã cài đặt
- [ ] Đã build Docker image (`docker-compose build`)
- [ ] Đã chạy hệ thống (`docker-compose up -d`)
- [ ] Đã test API (`http://localhost:5000/health`)
- [ ] Đã test gửi user action
- [ ] Đã test recommendations
- [ ] Đã tạo package ZIP (`.\create_docker_package.ps1`)
- [ ] Đã kiểm tra file ZIP

---

**Chúc bạn thành công! 🎉**

