# HIỆN TRẠNG HỆ THỐNG - HOTEL RECOMMENDATION AI

**Ngày cập nhật**: 2025-01-14  
**Version**: 1.0 (Production-ready với DeepFM model)

---

## MỤC LỤC

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Luồng hoạt động chi tiết](#3-luồng-hoạt-động-chi-tiết)
4. [Dataset và Model](#4-dataset-và-model)
5. [API Endpoints](#5-api-endpoints)
6. [Cấu hình Docker](#6-cấu-hình-docker)
7. [Files và Directories](#7-files-và-directories)
8. [Vấn đề hiện tại](#8-vấn-đề-hiện-tại)

---

## 1. TỔNG QUAN HỆ THỐNG

### 1.1. Mục đích

Hệ thống AI recommendation sử dụng **DeepFM model** để gợi ý khách sạn cho người dùng dựa trên:
- **User features**: Tuổi (age), giới tính (gender), khu vực (region)
- **Item features**: Phong cách (style), giá (price), sao (star), điểm đánh giá (score), thành phố (city)
- **Interaction history**: Lịch sử tương tác của user (click, like, share, booking)

### 1.2. 2 Luồng hoạt động độc lập

```
┌─────────────────────────────────────────────────────────────┐
│ LUỒNG 1: REAL-TIME INFERENCE (Gợi ý ngay lập tức)         │
│                                                             │
│  Web → API → Inference → DeepFM Model → Recommendations    │
│                                                             │
│  ⚡ Tốc độ: ~0.1-0.5 giây                                   │
│  🔄 Dùng: Model đã train sẵn                                │
│  ⚠️  Không dùng dữ liệu mới (chưa qua ETL)                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ LUỒNG 2: DATA COLLECTION & MODEL UPDATE (Background)       │
│                                                             │
│  Web → API → Log → ETL → Dataset → Retrain → Model mới    │
│                                                             │
│  ⏱️  ETL: Chạy mỗi 3 phút                                    │
│  🌙 Retrain: Chạy mỗi ngày 2h sáng                         │
│  ✅ Dữ liệu mới được học sau khi retrain                    │
└─────────────────────────────────────────────────────────────┘
```

### 1.3. Tech Stack

- **Framework**: RecBole (PyTorch-based)
- **Model**: DeepFM (Context-aware recommender)
- **API**: FastAPI
- **Containerization**: Docker + Docker Compose
- **Language**: Python 3.8+

---

## 2. KIẾN TRÚC HỆ THỐNG

### 2.1. Cấu trúc tổng thể

```
┌─────────────┐
│   Web App   │ (Laravel PHP)
│  (Frontend) │
└──────┬──────┘
       │
       │ HTTP Requests
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│              Docker Container Environment                    │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  recbole-api     │  │  recbole-etl     │                │
│  │                  │  │                  │                │
│  │  FastAPI Server  │  │  ETL Scheduler   │                │
│  │  Port: 5000      │  │  (3 phút/lần)    │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
│  ┌──────────────────┐                                       │
│  │ recbole-retrain  │                                       │
│  │                  │                                       │
│  │ Retrain Scheduler│                                       │
│  │  (2h sáng/ngày)  │                                       │
│  └──────────────────┘                                       │
└──────────────────────────────────────────────────────────────┘
       │
       │ Shared Volumes
       ▼
┌──────────────────────────────────────────────────────────────┐
│                  Persistent Data Storage                     │
│                                                              │
│  /app/dataset/    - Dataset files (hotel.inter, hotel.item) │
│  /app/data/       - Log files (user_actions.log)            │
│  /app/saved/      - Model checkpoints (DeepFM-*.pth)        │
│  /app/log/        - Training logs                           │
└──────────────────────────────────────────────────────────────┘
```

### 2.2. Components

#### A. API Server (`recbole-api`)
- **File**: `api_server.py`
- **Chức năng**:
  - Nhận requests từ web (GET /recommendations, POST /user_action)
  - Ghi user actions vào log file
  - Gọi inference module để generate recommendations
- **Port**: 5000
- **Dependencies**: FastAPI, uvicorn, inference.py

#### B. Inference Module
- **File**: `inference.py`
- **Chức năng**:
  - Load DeepFM model từ checkpoint
  - Cache model để tránh reload mỗi request
  - Generate recommendations cho user
  - Filter interacted items
- **Input**: user_id, top_k
- **Output**: List of item_id (recommendations)

#### C. ETL Service (`recbole-etl`)
- **File**: `etl_web_to_hotel_inter.py`
- **Chức năng**:
  - Đọc `data/user_actions.log` (line-delimited JSON)
  - Validate và group actions by (user_id, item_id)
  - Append vào `dataset/hotel/hotel.inter`
  - Archive log vào `data/user_actions.archive.log`
  - Truncate log file sau khi xử lý
- **Schedule**: Chạy mỗi 3 phút (config trong docker-compose.yml)

#### D. Retrain Service (`recbole-retrain`)
- **Files**: `retrain_model.py`, `retrain_scheduler.py`
- **Chức năng**:
  - Check điều kiện retrain (>= 100 interactions mới, >= 12h từ lần cuối)
  - Backup model cũ
  - Train model mới với toàn bộ dữ liệu
  - So sánh metrics (RMSE, MAE) với model cũ
  - Clear cache để load model mới
- **Schedule**: Chạy mỗi ngày 2h sáng (config trong docker-compose.yml)

---

## 3. LUỒNG HOẠT ĐỘNG CHI TIẾT

### 3.1. Luồng 1: Real-time Inference

**Khi nào chạy?**  
Khi user vào trang web, backend gọi API để lấy recommendations.

**Luồng chi tiết:**

```
Step 1: Web gửi request
──────────────────────
GET /recommendations/123?top_k=10

Headers:
  Authorization: Bearer <API_KEY> (nếu bật)

Step 2: API Server (api_server.py)
───────────────────────────────────
├─ Validate user_id và top_k
├─ Check API key (nếu bật)
└─ Gọi inference_get_recommendations()

Step 3: Inference Module (inference.py)
────────────────────────────────────────
├─ Load model (lần đầu hoặc dùng cache)
│  └─ Từ: saved/DeepFM-*.pth (file mới nhất)
│
├─ Kiểm tra user có trong dataset không
│  ├─ Có → Tiếp tục
│  └─ Không → Trả về [] (cold start)
│
├─ Lấy interacted items của user
│  └─ Từ: dataset.inter_matrix (CSR sparse matrix)
│  └─ Convert: internal IDs → external tokens
│
├─ Tạo interaction cho user với TẤT CẢ items
│  ├─ user_id: Repeat cho tất cả items (595 hotels)
│  ├─ item_id: All item internal IDs
│  ├─ user features: age, gender, region (repeat cho tất cả items)
│  └─ item features: style, price, star, score, city (tất cả items)
│
├─ Model predict
│  └─ DeepFM.predict(interaction) → scores array (595 scores)
│
├─ Post-processing
│  ├─ Sắp xếp scores giảm dần
│  ├─ Filter interacted items
│  ├─ Lấy top-K
│  └─ Convert internal IDs → external tokens
│
└─ Return: [item_id_1, item_id_2, ..., item_id_k]

Step 4: API Server trả về
──────────────────────────
{
  "user_id": "123",
  "recommendations": [501, 502, 503, 504, 505, 506, 507, 508, 509, 510],
  "model_version": "DeepFM-Nov-14-2025_08-21-05",
  "top_k": 10
}
```

**Thời gian xử lý:** ~0.1-0.5 giây

**Dữ liệu sử dụng:**
- ✅ Model đã train sẵn
- ✅ User features từ `hotel.user`
- ✅ Item features từ `hotel.item`
- ✅ Interaction history từ `hotel.inter` (đã train trong model)
- ❌ **KHÔNG** đọc `user_actions.log` (dữ liệu mới)

**Ví dụ cụ thể:**

```
User 123 (age: 25, gender: F, region: Hanoi):
- Đã tương tác: hotel 501 (click), hotel 502 (like)
- Model dự đoán điểm cho 595 hotels
- Loại bỏ hotel 501, 502 (đã tương tác)
- Top 10: [503, 504, 505, 506, 507, 508, 509, 510, 511, 512]
```

---

### 3.2. Luồng 2: Data Collection & Model Update

**Khi nào chạy?**
- **ETL**: Chạy tự động mỗi 3 phút
- **Retrain**: Chạy tự động mỗi ngày 2h sáng

#### A. Thu thập dữ liệu (POST /user_action)

```
Step 1: Web gửi user action
────────────────────────────
POST /user_actions_batch

Body:
[
  {
    "user_id": 123,
    "item_id": 501,
    "action_type": "click",
    "timestamp": 1695400000.0
  },
  ...
]

Step 2: API Server (api_server.py)
───────────────────────────────────
├─ Validate dữ liệu (Pydantic model)
│  ├─ user_id: Union[str, int] → convert to str
│  ├─ item_id: Union[str, int] → convert to str
│  ├─ action_type: "click" | "like" | "share" | "booking"
│  └─ timestamp: float (unix timestamp)
│
├─ Convert về int cho log file
│  └─ user_id, item_id → int (để giữ nguyên format từ web)
│
└─ Ghi vào data/user_actions.log (append mode)
   └─ Format: Line-delimited JSON (mỗi dòng 1 JSON object)

Step 3: Return success
──────────────────────
{
  "status": "success",
  "count": 2
}
```

**Thời gian xử lý:** ~0.01 giây (rất nhanh)

#### B. ETL Processing (mỗi 3 phút)

```
Step 1: ETL Script (etl_web_to_hotel_inter.py) chạy
─────────────────────────────────────────────────────
├─ Đọc data/user_actions.log
│  └─ Parse từng dòng JSON
│
├─ Validate dữ liệu
│  ├─ Required fields: user_id, item_id, action_type, timestamp
│  ├─ Format validation
│  └─ Timestamp range check (2000-2100)
│
├─ Convert action_type → action_score
│  ├─ booking: 1.0
│  ├─ share: 0.75
│  ├─ like: 0.5
│  └─ click: 0.25
│
├─ Group by (user_id, item_id)
│  └─ Max strategy: Lấy action_score cao nhất
│  └─ Timestamp: Lấy timestamp của action có score cao nhất
│  └─ Ví dụ:
│     User 123, Hotel 501:
│       - click (0.25) tại 1695400000
│       - like (0.5) tại 1695401000
│       - booking (1.0) tại 1695402000
│     → Kết quả: user_id=123, item_id=501, action_type=1.0, timestamp=1695402000
│
├─ Append vào dataset/hotel/hotel.inter
│  └─ Format: TSV (tab-separated)
│  └─ Header: user_id:token	item_id:token	action_type:float	timestamp:float
│  └─ Data: 123	501	1.0	1695402000
│
├─ Archive vào data/user_actions.archive.log
│  └─ Giữ nguyên raw JSON (để audit)
│
└─ Truncate data/user_actions.log (xóa dữ liệu đã xử lý)
```

**Schedule:** Chạy mỗi 3 phút (180 giây)

**Kết quả:** Dataset `hotel.inter` được cập nhật với dữ liệu mới

#### C. Model Retraining (mỗi ngày 2h sáng)

```
Step 1: Retrain Scheduler (retrain_scheduler.py) kiểm tra
──────────────────────────────────────────────────────────
├─ Check thời gian: Đã đến 2h sáng chưa?
│  └─ Check mỗi 1 giờ (check_interval=3600)
│
├─ Check điều kiện retrain
│  ├─ Số interactions mới >= 100?
│  └─ Thời gian từ lần retrain cuối >= 12 giờ?
│
└─ Nếu OK → Gọi retrain_model.py

Step 2: Retrain Script (retrain_model.py) chạy
───────────────────────────────────────────────
├─ Load retrain history (retrain_history.json)
│
├─ Backup model cũ
│  └─ Copy: saved/DeepFM-*.pth → saved/backups/DeepFM-*.pth.backup_<timestamp>
│
├─ Train model mới
│  └─ RecBole.run() với toàn bộ dataset (cũ + mới)
│  └─ Config: deepfm_config.yaml
│  └─ Output: saved/DeepFM-<timestamp>.pth
│
├─ So sánh metrics
│  ├─ RMSE (Root Mean Squared Error) - càng thấp càng tốt
│  ├─ MAE (Mean Absolute Error) - càng thấp càng tốt
│  └─ Nếu model mới tốt hơn → Giữ model mới
│  └─ Nếu model cũ tốt hơn → Vẫn giữ model mới (nhưng có backup)
│
├─ Clear model cache
│  └─ inference.clear_cache() → Model sẽ load lại ở request tiếp theo
│
└─ Update retrain_history.json
   ├─ last_retrain_time
   ├─ last_dataset_size
   ├─ last_retrain_metrics (RMSE, MAE)
   └─ retrain_count
```

**Schedule:** Chạy mỗi ngày 2h sáng (config: RETRAIN_HOUR=2, RETRAIN_MINUTE=0)

**Thời gian train:** ~5-15 phút (tùy dataset size)

**Kết quả:** Model mới được lưu, cache cleared → Requests tiếp theo sẽ dùng model mới

---

## 4. DATASET VÀ MODEL

### 4.1. Dataset Structure

**Location:** `dataset/hotel/`

#### A. `hotel.inter` (Interaction data)
**Format:** TSV (Tab-separated values)

```
Header:
user_id:token	item_id:token	action_type:float	timestamp:float

Data:
1	501	1.0	1695400000
1	502	0.5	1695401000
2	501	0.75	1695402000
...
```

**Fields:**
- `user_id`: Integer ID của user (1, 2, 3, ...)
- `item_id`: Integer ID của hotel (501, 502, 503, ...)
- `action_type`: Float score (0.25=click, 0.5=like, 0.75=share, 1.0=booking)
- `timestamp`: Unix timestamp (seconds since 1970-01-01)

**Size:** ~100,000 interactions (100k dòng)

#### B. `hotel.user` (User features)
**Format:** TSV

```
Header:
user_id:token	age:token	gender:token	region:token

Data:
1	25	F	Hanoi
2	30	M	HoChiMinh
...
```

**Fields:**
- `user_id`: Integer ID
- `age`: Age group token (string, e.g., "25", "30")
- `gender`: "M" hoặc "F"
- `region`: Region token (string, e.g., "Hanoi", "HoChiMinh")

**Size:** ~600 users

#### C. `hotel.item` (Item features)
**Format:** TSV

```
Header:
item_id:token	style:token	price:token	star:token	score:token	city:token

Data:
501	Romantic	2.8M	4.0	9.9	HoanKiem
502	Modern	3.5M	4.5	9.7	HoanKiem
...
```

**Fields:**
- `item_id`: Integer ID
- `style`: Style token (string, e.g., "Romantic", "Modern")
- `price`: Price token (string, e.g., "2.8M", "3.5M")
- `star`: Star rating token (string, e.g., "4.0", "4.5")
- `score`: Review score token (string, e.g., "9.9", "9.7")
- `city`: City token (string, e.g., "HoanKiem", "Hanoi")

**Size:** ~595 hotels

### 4.2. DeepFM Model

**Type:** Context-aware recommender

**Architecture:**
```
Input:
├─ User ID (embedding)
├─ User features (age, gender, region) → embeddings
├─ Item ID (embedding)
└─ Item features (style, price, star, score, city) → embeddings

Processing:
├─ Factorization Machine (FM) component
│  └─ Models pairwise feature interactions
├─ Deep Neural Network (DNN) component
│  └─ Multi-layer perceptron (MLP)
│  └─ Hidden layers: [64, 64, 64]
│  └─ Activation: ReLU
│  └─ Dropout: 0.0
└─ Output: Score (0-1) - probability of interaction

Output:
└─ Sigmoid activation → Final prediction score
```

**Training:**
- **Epochs**: 300 (max), early stopping với stopping_step=10
- **Batch size**: 2048
- **Optimizer**: Adam
- **Learning rate**: 0.001
- **Loss function**: BCEWithLogitsLoss (Binary Cross Entropy)
- **Metrics**: RMSE, MAE

**Checkpoints:**
- **Location**: `saved/DeepFM-*.pth`
- **Naming**: `DeepFM-{timestamp}.pth` (e.g., `DeepFM-Nov-14-2025_08-21-05.pth`)
- **Contains**: Model weights, config, optimizer state

**Performance:**
- **RMSE**: ~0.19 (trên validation set)
- **MAE**: ~0.16 (trên validation set)

---

## 5. API ENDPOINTS

### 5.1. GET /recommendations/{user_id}

**Mục đích:** Lấy recommendations cho user

**Request:**
```
GET /recommendations/123?top_k=10

Headers:
  Authorization: Bearer <API_KEY> (optional, nếu bật)
```

**Parameters:**
- `user_id` (path): ID của user (string hoặc int)
- `top_k` (query, optional): Số lượng recommendations (default: 10, max: 100)

**Response (Success):**
```json
{
  "user_id": "123",
  "recommendations": [501, 502, 503, 504, 505, 506, 507, 508, 509, 510],
  "model_version": "DeepFM-Nov-14-2025_08-21-05",
  "top_k": 10
}
```

**Response (Cold Start - user không tồn tại):**
```json
{
  "user_id": "999",
  "recommendations": [],
  "model_version": "DeepFM-Nov-14-2025_08-21-05",
  "top_k": 0,
  "message": "User mới (cold start) - không có dữ liệu trong dataset. Backend sẽ xử lý gợi ý theo IP location."
}
```

**Response (Error):**
```json
{
  "detail": "Model không tìm thấy. Vui lòng liên hệ admin."
}
```
Status: 503

---

### 5.2. POST /user_action

**Mục đích:** Ghi 1 user action vào log

**Request:**
```
POST /user_action

Headers:
  Authorization: Bearer <API_KEY> (optional, nếu bật)
  Content-Type: application/json

Body:
{
  "user_id": 123,
  "item_id": 501,
  "action_type": "click",
  "timestamp": 1695400000.0
}
```

**Validation:**
- `user_id`: Union[str, int], không rỗng, max 100 chars
- `item_id`: Union[str, int], không rỗng, max 100 chars
- `action_type`: "click" | "like" | "share" | "booking" (case-insensitive)
- `timestamp`: float >= 0, trong khoảng 2000-01-01 đến 2100-01-01

**Response:**
```json
{
  "status": "success",
  "data": {
    "user_id": "123",
    "item_id": "501",
    "action_type": "click",
    "timestamp": 1695400000.0
  }
}
```

---

### 5.3. POST /user_actions_batch

**Mục đích:** Ghi nhiều user actions vào log (batch)

**Request:**
```
POST /user_actions_batch

Headers:
  Authorization: Bearer <API_KEY> (optional, nếu bật)
  Content-Type: application/json

Body:
[
  {
    "user_id": 123,
    "item_id": 501,
    "action_type": "click",
    "timestamp": 1695400000.0
  },
  {
    "user_id": 123,
    "item_id": 502,
    "action_type": "like",
    "timestamp": 1695401000.0
  }
]
```

**Response:**
```json
{
  "status": "success",
  "count": 2
}
```

---

### 5.4. GET /health

**Mục đích:** Health check endpoint

**Request:**
```
GET /health
```

**Response:**
```json
{
  "ok": true,
  "model_loaded": true
}
```

---

### 5.5. GET /metrics

**Mục đích:** API usage statistics (nếu monitoring được enable)

**Request:**
```
GET /metrics
```

**Response:**
```json
{
  "total_requests": 1000,
  "total_recommendations": 500,
  "total_actions": 1500,
  ...
}
```

---

### 5.6. GET /schema

**Mục đích:** API contract documentation

**Request:**
```
GET /schema
```

**Response:**
```json
{
  "endpoint": "/user_action",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer <API_KEY>",
    "Content-Type": "application/json"
  },
  "body": {
    "user_id": "string",
    "item_id": "string",
    "action_type": ["click", "like", "share", "booking"],
    "timestamp": "unix_seconds(float)"
  }
}
```

---

## 6. CẤU HÌNH DOCKER

### 6.1. docker-compose.yml

**Services:**

#### A. recbole-api
```yaml
recbole-api:
  build:
    context: .
    dockerfile: Dockerfile
  container_name: recbole-api
  ports:
    - "5000:5000"
  environment:
    - USER_ACTION_LOG_FILE=/app/data/user_actions.log
    - USER_ACTION_ARCHIVE_FILE=/app/data/user_actions.archive.log
    - HOTEL_INTER_FILE=/app/dataset/hotel/hotel.inter
    - API_KEY=${API_KEY:-}
    - ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-*}
  volumes:
    - ./dataset:/app/dataset
    - ./data:/app/data
    - ./log:/app/log
    - ./log_tensorboard:/app/log_tensorboard
    - ./saved:/app/saved
  restart: unless-stopped
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/health').read()"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 120s
```

#### B. recbole-etl
```yaml
recbole-etl:
  build:
    context: .
    dockerfile: Dockerfile
  container_name: recbole-etl
  command: >
    sh -c "
      while true; do
        python etl_web_to_hotel_inter.py
        sleep 180  # 3 phút
      done
    "
  environment:
    - USER_ACTION_LOG_FILE=/app/data/user_actions.log
    - USER_ACTION_ARCHIVE_FILE=/app/data/user_actions.archive.log
    - HOTEL_INTER_FILE=/app/dataset/hotel/hotel.inter
  volumes:
    - ./dataset:/app/dataset
    - ./data:/app/data
  restart: unless-stopped
  depends_on:
    - recbole-api
```

#### C. recbole-retrain
```yaml
recbole-retrain:
  build:
    context: .
    dockerfile: Dockerfile
  container_name: recbole-retrain
  command: python retrain_scheduler.py
  environment:
    - RETRAIN_HOUR=2      # 2h sáng
    - RETRAIN_MINUTE=0    # 0 phút
    - RETRAIN_CHECK_INTERVAL=3600  # Kiểm tra mỗi 1 giờ
  volumes:
    - ./dataset:/app/dataset
    - ./data:/app/data
    - ./log:/app/log
    - ./log_tensorboard:/app/log_tensorboard
    - ./saved:/app/saved
  restart: unless-stopped
  depends_on:
    - recbole-api
```

### 6.2. Environment Variables

**File:** `.env` (tạo nếu chưa có)

```bash
# API Key (nếu bật authentication)
API_KEY=your_secret_api_key_here

# CORS origins (comma-separated, hoặc "*" để allow all)
ALLOWED_ORIGINS=http://localhost:3000,http://192.168.2.70:8000

# Retrain schedule
RETRAIN_HOUR=2
RETRAIN_MINUTE=0
RETRAIN_CHECK_INTERVAL=3600
```

---

## 7. FILES VÀ DIRECTORIES

### 7.1. Core Files

| File | Mục đích | Location |
|------|----------|----------|
| `api_server.py` | FastAPI server, API endpoints | Root |
| `inference.py` | Inference module, model loading, recommendations | Root |
| `etl_web_to_hotel_inter.py` | ETL script, process log → dataset | Root |
| `retrain_model.py` | Retrain script, train model mới | Root |
| `retrain_scheduler.py` | Retrain scheduler, chạy định kỳ | Root |
| `monitoring.py` | API monitoring utilities (optional) | Root |
| `deepfm_config.yaml` | RecBole config cho DeepFM model | Root |
| `docker-compose.yml` | Docker services configuration | Root |
| `Dockerfile` | Docker image definition | Root |
| `requirements.txt` | Python dependencies | Root |

### 7.2. Directories

| Directory | Mục đích | Contents |
|-----------|----------|----------|
| `dataset/hotel/` | Dataset files | `hotel.inter`, `hotel.item`, `hotel.user` |
| `data/` | Log files | `user_actions.log`, `user_actions.archive.log` |
| `saved/` | Model checkpoints | `DeepFM-*.pth`, `backups/` |
| `log/DeepFM/` | Training logs | `DeepFM-hotel-*.log` |
| `log_tensorboard/` | TensorBoard logs | Events files |

### 7.3. Config Files

| File | Mục đích |
|------|----------|
| `deepfm_config.yaml` | RecBole config (epochs, batch_size, learning_rate, ...) |
| `.env` | Environment variables (API_KEY, ALLOWED_ORIGINS, ...) |
| `retrain_history.json` | Retrain history (last_retrain_time, metrics, ...) |

---

## 8. VẤN ĐỀ HIỆN TẠI

### 8.1. Vấn đề chính: Recommendations không real-time

**Mô tả:**
- Luồng 1 (inference) **KHÔNG** đọc dữ liệu mới từ `user_actions.log`
- Dữ liệu mới chỉ được dùng sau khi:
  1. ETL xử lý (3 phút)
  2. Retrain (24 giờ sau)
- **Delay tối thiểu**: 3 phút (nếu retrain ngay)
- **Delay thực tế**: ~24 giờ (chờ retrain)

**Ví dụ:**
```
7:00 AM - User click hotel 4, 5, 6
7:01 AM - Web gọi GET /recommendations/123
         → AI vẫn recommend hotels 1, 2, 3 (từ model cũ)
         → Không biết về click 4, 5, 6
7:03 AM - ETL xử lý → Cập nhật hotel.inter
         → Nhưng model chưa học được (chưa retrain)
2:00 AM (ngày mai) - Retrain → Model mới học được
```

### 8.2. Vấn đề phụ: Recommendations máy móc

**Mô tả:**
- Model chỉ dựa vào demographic features (age, gender, region)
- Tất cả users cùng age/gender/region → recommendations giống nhau
- Không có trọng số theo thời gian (hành vi gần đây = hành vi cũ)
- Không personalize theo hành vi cá nhân (chỉ dùng features chung)

**Ví dụ:**
```
User A (age: 25, gender: F, region: Hanoi):
  → Recommendations: [hotel_cheap_1, hotel_cheap_2, ...]

User B (age: 25, gender: F, region: Hanoi):
  → Recommendations: [hotel_cheap_1, hotel_cheap_2, ...] (GIỐNG NHAU!)

User A click hotel_luxury_501 lúc 7:00
User A click hotel_luxury_502 lúc 7:15
  → Recommendations không thay đổi (vẫn là hotel_cheap_*)
```

### 8.3. Tóm tắt vấn đề

| Vấn đề | Mô tả | Impact |
|--------|-------|--------|
| **Delay quá lâu** | Dữ liệu mới phải đợi 24h mới được dùng | Recommendations không sát với hành vi gần đây |
| **Không có trọng số thời gian** | Hành vi 7:00 và 7:15 có trọng số như nhau | Không ưu tiên hành vi gần đây |
| **Quá máy móc** | Dựa vào demographic, không personalize | Nhiều users nhận recommendations giống nhau |
| **Không dùng hành vi real-time** | Inference không đọc `user_actions.log` | Bỏ lỡ dữ liệu mới nhất |

---

## KẾT LUẬN

Hệ thống hiện tại **hoạt động tốt** cho:
- ✅ Gợi ý dựa trên demographic (age, gender, region)
- ✅ Batch processing (ETL, retrain)
- ✅ Stable recommendations (không thay đổi liên tục)

**Nhưng cần cải thiện** để:
- ⚠️ Gợi ý real-time dựa trên hành vi mới nhất
- ⚠️ Personalized hơn (dựa trên hành vi cá nhân, không chỉ demographic)
- ⚠️ Trọng số theo thời gian (hành vi gần đây quan trọng hơn)

**Xem file `SYSTEM_FUTURE_PLAN.md` để biết kế hoạch cải tiến.**

