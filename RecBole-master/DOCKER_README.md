# Hướng dẫn chạy RecBole API trên Docker

## Kiến trúc hệ thống

Hệ thống gồm 2 containers:
- **recbole-api**: API server (FastAPI) nhận hành vi từ web, chạy cổng 5000
- **recbole-etl**: Cron job chạy ETL mỗi 3 phút để xử lý log → hotel.inter

## Yêu cầu

- Docker >= 20.10
- Docker Compose >= 2.0

## Cài đặt và chạy

### 1. Chuẩn bị dữ liệu

Đảm bảo có folder `dataset/hotel/` chứa:
- `hotel.user`
- `hotel.item`
- `hotel.inter`

### 2. (Tùy chọn) Tạo file `.env`

```bash
# .env file
API_KEY=your-secret-api-key-here
```

### 3. Build và chạy

```bash
# Build images
docker-compose build

# Chạy containers (detached mode)
docker-compose up -d

# Xem logs
docker-compose logs -f

# Xem logs của 1 service
docker-compose logs -f recbole-api
```

### 4. Test API

```bash
# Health check
curl http://localhost:5000/health

# Get schema
curl http://localhost:5000/schema

# Send user action (Windows PowerShell)
Invoke-WebRequest -Uri http://localhost:5000/user_action `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"user_id":"u123","item_id":"h456","action_type":"click","timestamp":1695400000.0}'

# Send user action (Linux/Mac)
curl -X POST http://localhost:5000/user_action \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u123","item_id":"h456","action_type":"click","timestamp":1695400000.0}'
```

### 5. Theo dõi ETL

```bash
# Xem logs ETL
docker-compose logs -f recbole-etl

# Kiểm tra data volumes
ls -lh ./dataset/hotel/hotel.inter
ls -lh ./data/
```

## Dừng và xóa

```bash
# Dừng containers
docker-compose down

# Xóa containers + volumes (CẢNH BÁO: xóa mất dữ liệu)
docker-compose down -v
```

## Cấu hình

### Thay đổi port API

Sửa `docker-compose.yml`:
```yaml
ports:
  - "YOUR_PORT:5000"
```

### Thay đổi tần suất ETL

Sửa `docker-compose.yml`:
```yaml
command: >
  sh -c "
    while true; do
      python etl_web_to_hotel_inter.py
      sleep YOUR_SECONDS
    done
  "
```

### Thêm API key

1. Tạo file `.env`
2. Thêm `API_KEY=your-key`
3. Restart: `docker-compose up -d`

## Troubleshooting

### Container không khởi động

```bash
# Xem logs chi tiết
docker-compose logs recbole-api

# Vào trong container
docker-compose exec recbole-api bash

# Kiểm tra Python packages
docker-compose exec recbole-api python -c "import fastapi, uvicorn; print('OK')"
```

### ETL không chạy

```bash
# Test ETL thủ công trong container
docker-compose exec recbole-etl python etl_web_to_hotel_inter.py

# Kiểm tra file log
docker-compose exec recbole-etl ls -lh /app/data/
```

### Dữ liệu bị mất sau khi restart

Đảm bảo volumes được mount đúng trong `docker-compose.yml`:
```yaml
volumes:
  - ./dataset:/app/dataset
  - ./data:/app/data
```

## Production Checklist

- [ ] Thay đổi `API_KEY` thành giá trị ngẫu nhiên mạnh
- [ ] Sửa CORS trong `api_server.py` để chỉ cho phép domain web của bạn
- [ ] Cấu hình firewall/security group chỉ mở cổng 5000
- [ ] Thiết lập backup định kỳ cho `./dataset`, `./data`, `./saved`
- [ ] Monitor logs với tools như Prometheus/Grafana
- [ ] Scale horizontally nếu cần: thêm nhiều replicas cho `recbole-api`

