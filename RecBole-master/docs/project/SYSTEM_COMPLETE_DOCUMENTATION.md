# TÀI LIỆU TOÀN DIỆN VỀ HỆ THỐNG AI RECOMMENDATION

**Phiên bản:** 1.0  
**Ngày cập nhật:** 2025-01-16  
**Tác giả:** AI Development Team

---

## MỤC LỤC

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Mô hình DeepFM](#2-mô-hình-deepfm)
3. [Phase 1: Behavior Boost](#3-phase-1-behavior-boost)
4. [Phase 2: Similarity Boost](#4-phase-2-similarity-boost)
5. [Cấu trúc thư mục](#5-cấu-trúc-thư-mục)
6. [Các module quan trọng](#6-các-module-quan-trọng)
7. [Quy trình Training và Retraining](#7-quy-trình-training-và-retraining)
8. [API Endpoints](#8-api-endpoints)
9. [ETL Process](#9-etl-process)
10. [Testing và Validation](#10-testing-và-validation)
11. [Thuật ngữ và Khái niệm](#11-thuật-ngữ-và-khái-niệm)

---

## 1. TỔNG QUAN HỆ THỐNG

### 1.1. Mục đích

Hệ thống AI Recommendation này được thiết kế để **gợi ý khách sạn phù hợp** cho người dùng dựa trên:
- **Lịch sử tương tác** (interactions trong dataset)
- **Thông tin người dùng** (gender, age, region)
- **Thông tin khách sạn** (style, price, star, score, city)
- **Hành vi real-time** (actions gần đây từ log file)

### 1.2. Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────┐
│                    WEB APPLICATION                            │
│  (Gửi user actions, nhận recommendations)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    API SERVER (FastAPI)                      │
│  - POST /user_action: Nhận actions từ web                   │
│  - GET /recommendations/{user_id}: Trả về recommendations   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              INFERENCE MODULE (inference.py)                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Load DeepFM Model (từ checkpoint)                │  │
│  │ 2. Predict base scores cho tất cả items             │  │
│  │ 3. Phase 1: Behavior Boost (từ user_actions.log)    │  │
│  │ 4. Phase 2: Similarity Boost (từ similarity matrix)│  │
│  │ 5. Combine scores và trả về top-K items              │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              DEEP LEARNING MODEL (DeepFM)                    │
│  - Đã được train trên dataset hotel                         │
│  - Lưu trong thư mục saved/ (checkpoint .pth)               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              DATA PIPELINE                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ETL Module:                                          │  │
│  │  - Đọc actions từ web → hotel.inter                 │  │
│  │  - Retrain model mỗi ngày với dữ liệu mới           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.3. Luồng dữ liệu

**Luồng 1: Training (Offline)**
```
Web Actions → ETL → hotel.inter → Retrain Model → Checkpoint (.pth)
```

**Luồng 2: Inference (Online)**
```
User Request → API → Inference Module → DeepFM Model → Phase 1 Boost → Phase 2 Boost → Top-K Recommendations
```

**Luồng 3: Real-time Actions**
```
Web → API (/user_action) → user_actions.log → Inference Module (đọc khi có request)
```

---

## 2. MÔ HÌNH DEEPFM

### 2.1. DeepFM là gì?

**DeepFM (Deep Factorization Machine)** là một mô hình **Deep Learning** kết hợp:
- **Factorization Machine (FM)**: Học tương tác bậc 2 giữa các features
- **Deep Neural Network (DNN)**: Học tương tác bậc cao (non-linear)

**Ưu điểm:**
- Không cần feature engineering (tự động học từ raw features)
- Kết hợp cả low-order và high-order feature interactions
- Hiệu quả cho CTR prediction và recommendation

### 2.2. Kiến trúc DeepFM

```
Input Features (User + Item)
    │
    ├─► Embedding Layer (embedding_size=10)
    │       │
    │       ├─► FM Component ──┐
    │       │   (2nd order)     │
    │       │                   ├─► Final Score
    │       └─► DNN Component ──┘
    │           (high order)
    │           MLP: [64, 64, 64]
    │           Dropout: 0.0
    │
    └─► Output: Score (0-1, sigmoid)
```

### 2.3. Công thức toán học

#### 2.3.1. Factorization Machine (FM) Component

FM học tương tác bậc 2 giữa các features:

```
y_FM = w₀ + Σᵢ wᵢxᵢ + Σᵢ Σⱼ>ᵢ ⟨vᵢ, vⱼ⟩ xᵢxⱼ
```

**Giải thích:**
- `w₀`: Bias term (hệ số tự do)
- `wᵢ`: Trọng số cho feature thứ i (linear term)
- `⟨vᵢ, vⱼ⟩`: Tích vô hướng của embedding vectors (interaction term)
- `xᵢ, xⱼ`: Giá trị của features

**Ví dụ:**
- User có age=25, gender=F, region=Hanoi
- Hotel có price=2.5M, star=4.0, style=romantic
- FM sẽ học: age × price, gender × style, region × city, ...

#### 2.3.2. Deep Neural Network (DNN) Component

DNN học tương tác bậc cao (non-linear):

```
y_DNN = MLP(concat([e₁, e₂, ..., eₙ]))
```

**Giải thích:**
- `eᵢ`: Embedding vector của feature thứ i (dimension=10)
- `concat`: Nối tất cả embeddings thành 1 vector dài
- `MLP`: Multi-Layer Perceptron với hidden layers [64, 64, 64]

**Ví dụ:**
- Nếu có 5 features, mỗi feature có embedding size=10
- Input DNN: vector 50 chiều (5 × 10)
- Hidden layer 1: 64 neurons
- Hidden layer 2: 64 neurons
- Hidden layer 3: 64 neurons
- Output: 1 neuron (score)

#### 2.3.3. Final Score

```
y = y_FM + y_DNN
y_final = sigmoid(y)
```

**Giải thích:**
- `y`: Raw score (có thể âm hoặc dương)
- `sigmoid`: Chuyển về khoảng [0, 1]
- `y_final`: Xác suất user sẽ thích item (0 = không thích, 1 = rất thích)

### 2.4. Hyperparameters trong hệ thống

Từ file `deepfm_config.yaml`:

```yaml
model: DeepFM
dataset: hotel
epochs: 300
learning_rate: 0.001
embedding_size: 10          # Kích thước embedding vector
mlp_hidden_size: [64, 64, 64]  # Số neurons trong mỗi hidden layer
dropout_prob: 0.0           # Tắt dropout (không drop neurons)
stopping_step: 10            # Early stopping sau 10 epochs không cải thiện
valid_metric: RMSE          # Metric đánh giá (RMSE càng thấp càng tốt)
```

**Giải thích các hyperparameters:**

| Hyperparameter | Giá trị | Ý nghĩa |
|---------------|---------|---------|
| `embedding_size` | 10 | Mỗi feature được biểu diễn bằng vector 10 chiều |
| `mlp_hidden_size` | [64, 64, 64] | DNN có 3 hidden layers, mỗi layer 64 neurons |
| `dropout_prob` | 0.0 | Không drop neurons (giữ tất cả) |
| `learning_rate` | 0.001 | Tốc độ học (nhỏ = học chậm nhưng ổn định) |
| `epochs` | 300 | Tối đa 300 lần duyệt qua toàn bộ dataset |
| `stopping_step` | 10 | Dừng sớm nếu RMSE không cải thiện trong 10 epochs |

### 2.5. Loss Function

DeepFM sử dụng **Binary Cross-Entropy Loss** (BCE):

```
Loss = -[y_true × log(y_pred) + (1 - y_true) × log(1 - y_pred)]
```

**Giải thích:**
- `y_true`: Label thực tế (0 hoặc 1)
- `y_pred`: Score dự đoán từ model (0-1)
- Mục tiêu: Minimize loss → maximize accuracy

**Ví dụ:**
- Nếu user thực sự thích hotel (y_true=1) nhưng model dự đoán y_pred=0.3
  → Loss = -[1 × log(0.3) + 0 × log(0.7)] = -log(0.3) ≈ 1.2 (cao)
- Nếu model dự đoán y_pred=0.9
  → Loss = -log(0.9) ≈ 0.1 (thấp) ✅

---

## 3. PHASE 1: BEHAVIOR BOOST

### 3.1. Mục đích

**Phase 1 (Behavior Boost)** tăng điểm cho các hotels mà user đã **tương tác trực tiếp** gần đây, dựa trên:
- **Loại action** (click, like, share, booking)
- **Thời gian** (actions gần đây có trọng số cao hơn)

### 3.2. Công thức tính toán

#### 3.2.1. Action Score

Mỗi loại action có điểm số khác nhau:

```
Action Score:
  - booking: 1.0   (quan tâm cao nhất)
  - share:   0.75  (quan tâm cao)
  - like:    0.5   (quan tâm trung bình)
  - click:   0.25  (quan tâm thấp)
```

**Lý do:**
- Booking thể hiện user đã quyết định → quan tâm rất cao
- Share thể hiện user muốn giới thiệu → quan tâm cao
- Like thể hiện user thích → quan tâm trung bình
- Click chỉ là tương tác nhẹ → quan tâm thấp

#### 3.2.2. Time Weight (Exponential Decay)

Trọng số theo thời gian sử dụng **exponential decay**:

```
time_weight = exp(-decay_rate × hours_ago)
```

**Trong đó:**
- `hours_ago = (current_time - action.timestamp) / 3600`
- `decay_rate = 0.1` (hyperparameter, mặc định)
- `exp`: Hàm mũ (e^x)

**Ví dụ với decay_rate = 0.1:**

| Thời gian | hours_ago | time_weight | Giải thích |
|-----------|-----------|-------------|------------|
| Ngay bây giờ | 0 | 1.000 | 100% trọng số |
| 1 giờ trước | 1 | 0.905 | ~90% trọng số |
| 5 giờ trước | 5 | 0.607 | ~60% trọng số |
| 12 giờ trước | 12 | 0.301 | ~30% trọng số |
| 24 giờ trước | 24 | 0.091 | ~9% trọng số |

**Đồ thị:**
```
time_weight
   1.0 |●
       |  ●
   0.8 |    ●
       |      ●
   0.6 |        ●
       |          ●
   0.4 |            ●
       |              ●
   0.2 |                ●
       |                  ●
   0.0 |____________________●
       0  5  10  15  20  25  hours_ago
```

#### 3.2.3. Behavior Boost Score

Boost cho mỗi item được tính bằng tổng (cộng dồn) của tất cả actions:

```
boost[item_id] = Σ (action_score × time_weight)
```

**Lưu ý:** Nếu user có nhiều actions trên cùng 1 hotel, boost được **cộng dồn** (không lấy max).

**Ví dụ:**
- User click hotel 501 lúc 7:00 AM (20 phút trước)
- User like hotel 501 lúc 7:10 AM (10 phút trước)
- User booking hotel 501 lúc 7:20 AM (ngay bây giờ)

**Tính toán:**
```
Action 1 (click, 20 phút = 0.33 giờ):
  action_score = 0.25
  time_weight = exp(-0.1 × 0.33) = 0.967
  boost_1 = 0.25 × 0.967 = 0.242

Action 2 (like, 10 phút = 0.17 giờ):
  action_score = 0.5
  time_weight = exp(-0.1 × 0.17) = 0.983
  boost_2 = 0.5 × 0.983 = 0.492

Action 3 (booking, 0 giờ):
  action_score = 1.0
  time_weight = exp(-0.1 × 0) = 1.0
  boost_3 = 1.0 × 1.0 = 1.0

Total boost = 0.242 + 0.492 + 1.0 = 1.735
```

#### 3.2.4. Final Score (Phase 1)

Điểm cuối cùng sau khi áp dụng boost:

```
final_score = base_score × (1 + α × boost)
```

**Trong đó:**
- `base_score`: Điểm từ DeepFM model (0-1)
- `α (alpha)`: Boost coefficient (mặc định: 0.3 = tối đa 30% boost)
- `boost`: Behavior boost score (từ công thức trên)

**Ví dụ:**
- Base score từ model: 0.60
- Boost: 1.735 (từ ví dụ trên)
- Alpha: 0.3

**Tính toán:**
```
final_score = 0.60 × (1 + 0.3 × 1.735)
            = 0.60 × (1 + 0.521)
            = 0.60 × 1.521
            = 0.913
```

**Kết quả:** Điểm tăng từ 0.60 → 0.913 (tăng 52%) ✅

**Lý do dùng multiplicative (nhân) thay vì additive (cộng):**
- Items có base score cao → được boost nhiều hơn (tự nhiên hơn)
- Items có base score thấp → được boost ít hơn (không làm mất cân bằng)
- Giới hạn bởi alpha (0.3) → không boost quá mức

### 3.3. Quy trình xử lý

1. **Đọc log file** (`data/user_actions.log`)
2. **Lọc actions gần đây** (trong vòng `behavior_hours` giờ, mặc định 24 giờ)
3. **Tính boost** cho từng item
4. **Áp dụng boost** vào base scores
5. **Sort và trả về** top-K items

### 3.4. Code implementation

**File:** `inference.py`

**Functions chính:**
- `get_recent_user_actions()`: Đọc actions từ log file
- `get_action_score()`: Map action_type → score
- `calculate_time_weight()`: Tính time weight
- `calculate_behavior_boost()`: Tính boost cho tất cả items

---

## 4. PHASE 2: SIMILARITY BOOST

### 4.1. Mục đích

**Phase 2 (Similarity Boost)** tăng điểm cho các hotels **tương tự** hotels mà user đã tương tác, dựa trên:
- **Features tương đồng** (style, price, star, score, city)
- **Similarity score** (0-1, càng cao càng giống)

**Khác biệt với Phase 1:**
- Phase 1: Boost hotels đã tương tác trực tiếp
- Phase 2: Boost hotels **chưa tương tác** nhưng tương tự hotels đã tương tác

### 4.2. Công thức tính Similarity

#### 4.2.1. Jaccard Similarity (cho Style và City)

Jaccard similarity đo độ tương đồng giữa 2 sets (tokens):

```
Jaccard(A, B) = |A ∩ B| / |A ∪ B|
```

**Trong đó:**
- `A ∩ B`: Số tokens chung
- `A ∪ B`: Tổng số tokens (không trùng)

**Ví dụ:**
- Hotel A: style = "romantic love modern"
- Hotel B: style = "romantic lively"

**Tính toán:**
```
A = {romantic, love, modern}
B = {romantic, lively}
A ∩ B = {romantic}  (1 token chung)
A ∪ B = {romantic, love, modern, lively}  (4 tokens)
Jaccard = 1 / 4 = 0.25
```

**Ví dụ khác:**
- Hotel A: style = "romantic love"
- Hotel B: style = "romantic love modern"

```
A = {romantic, love}
B = {romantic, love, modern}
A ∩ B = {romantic, love}  (2 tokens chung)
A ∪ B = {romantic, love, modern}  (3 tokens)
Jaccard = 2 / 3 = 0.667
```

#### 4.2.2. Normalized Distance Similarity (cho Price, Star, Score)

Đo độ tương đồng dựa trên khoảng cách chuẩn hóa:

```
similarity = 1 - (|val₁ - val₂| / max_range)
```

**Trong đó:**
- `val₁, val₂`: Giá trị của 2 items
- `max_range`: Khoảng giá trị tối đa

**Ví dụ với Price:**
- Hotel A: price = 2,000,000 VND
- Hotel B: price = 2,500,000 VND
- max_range = 10,000,000 VND

**Tính toán:**
```
diff = |2,000,000 - 2,500,000| = 500,000
similarity = 1 - (500,000 / 10,000,000)
           = 1 - 0.05
           = 0.95
```

**Ví dụ với Star:**
- Hotel A: star = 4.0
- Hotel B: star = 3.5
- max_range = 5.0

**Tính toán:**
```
diff = |4.0 - 3.5| = 0.5
similarity = 1 - (0.5 / 5.0)
           = 1 - 0.1
           = 0.9
```

#### 4.2.3. Weighted Average Similarity

Similarity cuối cùng là trung bình có trọng số:

```
similarity = Σ(sim_i × weight_i) / Σ(weight_i)
```

**Trọng số (weights):**
- Style: 0.3
- City: 0.3
- Price: 0.25
- Score: 0.25
- Star: 0.2

**Ví dụ:**
- Hotel A: style="romantic", city="Hanoi", price=2M, star=4.0, score=9.0
- Hotel B: style="romantic love", city="Hanoi", price=2.5M, star=3.5, score=8.5

**Tính toán:**
```
Style: Jaccard = 0.5, weight = 0.3
City: Jaccard = 1.0, weight = 0.3
Price: Normalized = 0.95, weight = 0.25
Star: Normalized = 0.9, weight = 0.2
Score: Normalized = 0.95, weight = 0.25

similarity = (0.5×0.3 + 1.0×0.3 + 0.95×0.25 + 0.9×0.2 + 0.95×0.25) / (0.3+0.3+0.25+0.2+0.25)
          = (0.15 + 0.3 + 0.238 + 0.18 + 0.238) / 1.3
          = 1.106 / 1.3
          = 0.851
```

### 4.3. Công thức Similarity Boost

#### 4.3.1. Direct Boost (từ Phase 1)

Trước tiên, tính direct boost cho hotels đã tương tác (giống Phase 1):

```
direct_boost[item_id] = Σ (action_score × time_weight)
```

#### 4.3.2. Similarity Boost

Sau đó, boost hotels tương tự:

```
similarity_boost[similar_item] = Σ (direct_boost[clicked_item] × similarity × similarity_boost_factor)
```

**Trong đó:**
- `clicked_item`: Hotel user đã tương tác
- `similar_item`: Hotel tương tự (chưa tương tác)
- `similarity`: Similarity score giữa 2 hotels (0-1)
- `similarity_boost_factor`: Trọng số (mặc định: 0.5 = 50% của direct boost)

**Điều kiện:**
- Chỉ boost nếu `similarity >= similarity_threshold` (mặc định: 0.5)

#### 4.3.3. Final Boost (Phase 2)

```
final_boost[item] = direct_boost[item] + similarity_boost[item]
```

**Lưu ý:**
- Nếu item đã có direct boost → cộng thêm similarity boost
- Nếu item chỉ có similarity boost → chỉ có similarity boost

#### 4.3.4. Final Score (Phase 2)

```
final_score = base_score × (1 + α × final_boost)
```

**Công thức giống Phase 1, nhưng boost đã bao gồm similarity boost.**

### 4.4. Ví dụ tính toán chi tiết

**Scenario:**
- User click hotel 50 (style="romantic", city="Hanoi", price=2M, star=4.0)
- Hotel 100 tương tự (style="romantic love", city="Hanoi", price=2.2M, star=3.8)
- Similarity giữa hotel 50 và 100: 0.75
- Direct boost cho hotel 50: 0.5 (click gần đây)
- Similarity threshold: 0.5
- Similarity boost factor: 0.5

**Tính toán:**
```
1. Direct boost cho hotel 50:
   direct_boost[50] = 0.5

2. Similarity boost cho hotel 100:
   similarity_boost[100] = direct_boost[50] × similarity × similarity_boost_factor
                          = 0.5 × 0.75 × 0.5
                          = 0.1875

3. Final boost cho hotel 100:
   final_boost[100] = 0 + 0.1875 = 0.1875
   (hotel 100 chưa có direct boost)

4. Final score cho hotel 100 (giả sử base_score = 0.60):
   final_score = 0.60 × (1 + 0.3 × 0.1875)
               = 0.60 × (1 + 0.056)
               = 0.60 × 1.056
               = 0.634
```

**Kết quả:** Hotel 100 được boost từ 0.60 → 0.634 (tăng 5.6%) ✅

### 4.5. Similarity Matrix Caching

**Vấn đề:** Tính similarity cho tất cả cặp items rất tốn thời gian (O(n²))

**Giải pháp:** Pre-compute và cache similarity matrix

**Quy trình:**
1. Tính similarity matrix lần đầu (khi load model)
2. Cache vào memory (`_similarity_matrix_cache`)
3. Dùng lại cho các requests sau
4. Chỉ tính lại khi reload model

**Performance:**
- Thời gian tính: ~5-10 giây (cho ~595 hotels)
- Memory: ~50-100 MB
- Cache: Tính 1 lần, dùng nhiều lần

### 4.6. Code implementation

**File:** `inference.py`

**Functions chính:**
- `calculate_item_similarity()`: Tính similarity matrix (pre-compute)
- `_calculate_item_pair_similarity()`: Tính similarity giữa 2 items
- `calculate_behavior_boost_with_similarity()`: Tính boost bao gồm similarity

---

## 5. CẤU TRÚC THƯ MỤC

```
RecBole-master/
│
├── api_server.py              # FastAPI server (API endpoints)
├── inference.py               # Inference module (load model, predict, boost)
├── retrain_model.py           # Retraining pipeline (tự động retrain mỗi ngày)
├── retrain_scheduler.py       # Scheduler (chạy retrain_model.py theo lịch)
├── etl_web_to_hotel_inter.py  # ETL module (chuyển web actions → hotel.inter)
├── monitoring.py              # Metrics tracking (requests, errors, response times)
├── deepfm_config.yaml         # Config cho DeepFM model
│
├── dataset/                   # Dataset files
│   └── hotel/
│       ├── hotel.user         # User features (user_id, gender, age, region)
│       ├── hotel.item         # Item features (item_id, style, price, star, score, city)
│       └── hotel.inter        # Interactions (user_id, item_id, rating, timestamp)
│
├── data/                      # Runtime data
│   └── user_actions.log       # Real-time user actions (click, like, share, booking)
│
├── saved/                     # Trained models (checkpoints)
│   ├── DeepFM-*.pth          # Model checkpoints (theo timestamp)
│   └── backups/              # Backup checkpoints (trước khi retrain)
│
├── log/                       # Training logs
│   └── DeepFM/               # Logs từ mỗi lần train
│
├── log_tensorboard/          # TensorBoard logs (visualization)
│
├── recbole/                   # RecBole library (source code)
│   ├── model/
│   │   └── context_aware_recommender/
│   │       └── deepfm.py     # DeepFM model implementation
│   └── ...
│
├── tests/                     # Test files
│   ├── integration/          # Integration tests
│   └── phase1_analysis/      # Phase 1 testing scripts
│
├── docs/                      # Documentation
│   └── project/              # Project documentation
│
├── Dockerfile                 # Docker image definition
├── docker-compose.yml         # Docker Compose config
├── requirements.txt           # Python dependencies
└── retrain_history.json       # Retraining history (metrics, timestamps)
```

### 5.1. Giải thích các thư mục quan trọng

| Thư mục | Mục đích | Nội dung |
|---------|----------|----------|
| `dataset/hotel/` | Dataset cho training | hotel.user, hotel.item, hotel.inter |
| `data/` | Runtime data | user_actions.log (real-time actions) |
| `saved/` | Trained models | Checkpoints (.pth files) |
| `log/` | Training logs | Logs từ mỗi lần train |
| `log_tensorboard/` | Visualization | TensorBoard logs |
| `tests/` | Testing | Unit tests, integration tests |
| `docs/project/` | Documentation | Tài liệu dự án |

---

## 6. CÁC MODULE QUAN TRỌNG

### 6.1. `inference.py` - Inference Module

**Mục đích:** Load model, predict scores, và áp dụng boost

**Functions chính:**

#### `load_model(model_path, force_reload)`
- Load DeepFM model từ checkpoint
- Cache model để tránh load lại nhiều lần
- Trả về: (config, model, dataset)

#### `get_recommendations(user_id, top_k, ...)`
- Generate recommendations cho user
- Quy trình:
  1. Load model (dùng cache nếu có)
  2. Predict base scores cho tất cả items
  3. Áp dụng Phase 1 boost (nếu enabled)
  4. Áp dụng Phase 2 boost (nếu enabled)
  5. Sort và trả về top-K items

#### `calculate_behavior_boost(actions, current_time, decay_rate)`
- Tính boost cho Phase 1
- Input: List actions từ log file
- Output: Dict {item_id: boost_score}

#### `calculate_item_similarity(dataset, similarity_threshold)`
- Tính similarity matrix (pre-compute và cache)
- Output: Dict {item_id: {similar_item_id: similarity_score}}

#### `calculate_behavior_boost_with_similarity(...)`
- Tính boost bao gồm cả Phase 1 và Phase 2
- Output: Dict {item_id: final_boost_score}

### 6.2. `api_server.py` - API Server

**Mục đích:** REST API endpoints cho web application

**Endpoints:**

#### `POST /user_action`
- Nhận user action từ web
- Validate và ghi vào `user_actions.log`
- Input: `{user_id, item_id, action_type, timestamp}`

#### `POST /user_actions_batch`
- Nhận nhiều actions cùng lúc (batch)
- Validate và ghi vào `user_actions.log`

#### `GET /recommendations/{user_id}`
- Trả về recommendations cho user
- Parameters:
  - `top_k`: Số lượng recommendations (default: 10)
  - `use_behavior_boost`: Bật/tắt Phase 1 (default: true)
  - `use_similarity_boost`: Bật/tắt Phase 2 (default: true)
  - `alpha`: Boost coefficient (default: 0.3)
  - `decay_rate`: Time decay rate (default: 0.1)
  - `similarity_threshold`: Similarity threshold (default: 0.5)
  - `similarity_boost_factor`: Similarity boost factor (default: 0.5)

#### `GET /health`
- Health check endpoint
- Kiểm tra model đã load chưa

#### `GET /schema`
- Trả về API contract (schema) cho web team

### 6.3. `retrain_model.py` - Retraining Pipeline

**Mục đích:** Tự động retrain model mỗi ngày với dữ liệu mới

**Quy trình:**

1. **Kiểm tra dữ liệu mới:**
   - Đếm số interactions trong `hotel.inter`
   - So sánh với lần train trước
   - Nếu có ít nhất `MIN_NEW_INTERACTIONS` (100) interactions mới → retrain

2. **Backup checkpoint cũ:**
   - Copy checkpoint hiện tại vào `saved/backups/`
   - Đặt tên với timestamp

3. **Train model mới:**
   - Load toàn bộ dataset (cũ + mới)
   - Train với config từ `deepfm_config.yaml`
   - Early stopping nếu không cải thiện

4. **So sánh metrics:**
   - So sánh RMSE, MAE với model cũ
   - Cảnh báo nếu metrics tệ hơn

5. **Lưu model mới:**
   - **Lưu luôn** (ngay cả khi metrics tệ hơn)
   - Lý do: Model mới có dữ liệu mới nhất

6. **Clear cache:**
   - Clear inference cache để load model mới

7. **Lưu history:**
   - Ghi metrics và timestamp vào `retrain_history.json`

### 6.4. `retrain_scheduler.py` - Scheduler

**Mục đích:** Chạy `retrain_model.py` theo lịch (mặc định: 2:00 AM mỗi ngày)

**Quy trình:**
1. Kiểm tra thời gian hiện tại
2. Nếu đã đến giờ retrain → chạy `retrain_model.py`
3. Lặp lại mỗi giờ để kiểm tra

**Config:**
- `RETRAIN_HOUR`: Giờ retrain (default: 2)
- `RETRAIN_MINUTE`: Phút retrain (default: 0)

### 6.5. `etl_web_to_hotel_inter.py` - ETL Module

**Mục đích:** Chuyển đổi actions từ web sang format RecBole

**Quy trình:**

1. **Đọc dữ liệu từ web:**
   - Đọc JSON lines từ input file hoặc log file
   - Format: `{user_id, hotel_id, action_type, timestamp}`

2. **Validate:**
   - Kiểm tra các trường bắt buộc
   - Validate format và giá trị

3. **Group và aggregate:**
   - Group theo (user_id, hotel_id)
   - Nếu có nhiều actions → lấy action có điểm cao nhất
   - Ví dụ: Nếu có cả click và booking → chỉ lấy booking

4. **Convert sang RecBole format:**
   - Map action_type → rating (0-1)
   - Format: `user_id:token\thotel_id:token\trating:float\ttimestamp:float`

5. **Ghi vào hotel.inter:**
   - Append vào file (không ghi đè)
   - Hỗ trợ incremental processing

### 6.6. `monitoring.py` - Metrics Tracking

**Mục đích:** Theo dõi metrics của API server

**Metrics:**
- `requests_total`: Tổng số requests
- `requests_by_endpoint`: Số requests theo endpoint
- `errors_total`: Tổng số errors (status_code >= 400)
- `errors_by_endpoint`: Số errors theo endpoint
- `response_times`: List response times (giới hạn 1000 giá trị gần nhất)
- `average_response_time_ms`: Response time trung bình (milliseconds)

**Lưu ý:** Metrics lưu trong memory (không persistent), sẽ mất khi server restart.

---

## 7. QUY TRÌNH TRAINING VÀ RETRAINING

### 7.1. Training lần đầu

**Bước 1: Chuẩn bị dataset**
```
dataset/hotel/
├── hotel.user    # User features
├── hotel.item    # Item features
└── hotel.inter   # Interactions
```

**Bước 2: Chạy training**
```bash
python retrain_model.py --force
```

**Quy trình:**
1. Load config từ `deepfm_config.yaml`
2. Load dataset từ `dataset/hotel/`
3. Split train/valid/test (theo config)
4. Train model với RecBole
5. Evaluate trên valid/test set
6. Lưu checkpoint vào `saved/DeepFM-{timestamp}.pth`

**Output:**
- Checkpoint: `saved/DeepFM-{timestamp}.pth`
- Logs: `log/DeepFM/`
- TensorBoard logs: `log_tensorboard/`

### 7.2. Retraining tự động

**Lịch:** Mỗi ngày lúc 2:00 AM (có thể config)

**Quy trình:**

1. **Kiểm tra dữ liệu mới:**
   ```python
   current_size = get_dataset_size()  # Đếm dòng trong hotel.inter
   last_size = history['last_dataset_size']
   new_interactions = current_size - last_size
   
   if new_interactions >= MIN_NEW_INTERACTIONS:
       retrain()
   ```

2. **Backup checkpoint cũ:**
   ```python
   backup_path = f"saved/backups/DeepFM-{timestamp}.pth"
   shutil.copy(current_checkpoint, backup_path)
   ```

3. **Train model mới:**
   - Load toàn bộ dataset (bao gồm dữ liệu mới)
   - Train với cùng config
   - Early stopping nếu không cải thiện

4. **So sánh metrics:**
   ```python
   old_rmse = old_metrics['RMSE']
   new_rmse = new_metrics['RMSE']
   
   if new_rmse > old_rmse:
       print("[WARNING] Model mới có RMSE cao hơn!")
   ```

5. **Lưu model mới:**
   - **Luôn lưu** (ngay cả khi metrics tệ hơn)
   - Lý do: Model mới có dữ liệu mới nhất

6. **Clear cache:**
   ```python
   from inference import clear_cache
   clear_cache()  # Để load model mới
   ```

7. **Lưu history:**
   ```json
   {
     "last_retrain_time": "2025-01-16T02:00:00",
     "last_dataset_size": 15000,
     "last_retrain_metrics": {
       "RMSE": 0.85,
       "MAE": 0.65
     },
     "retrain_count": 5
   }
   ```

### 7.3. Metrics và Evaluation

**Metrics sử dụng:**
- **RMSE (Root Mean Squared Error)**: Càng thấp càng tốt
- **MAE (Mean Absolute Error)**: Càng thấp càng tốt

**Công thức:**

```
RMSE = √(Σ(y_true - y_pred)² / n)
MAE = Σ|y_true - y_pred| / n
```

**Ví dụ:**
- 5 predictions: [0.8, 0.6, 0.9, 0.7, 0.5]
- 5 labels: [1.0, 0.5, 1.0, 0.8, 0.4]
- Errors: [0.2, 0.1, 0.1, 0.1, 0.1]

```
RMSE = √((0.2² + 0.1² + 0.1² + 0.1² + 0.1²) / 5)
     = √(0.08 / 5)
     = √0.016
     = 0.126

MAE = (0.2 + 0.1 + 0.1 + 0.1 + 0.1) / 5
    = 0.6 / 5
    = 0.12
```

---

## 8. API ENDPOINTS

### 8.1. POST /user_action

**Mục đích:** Nhận 1 user action từ web

**Request:**
```json
{
  "user_id": "123",
  "item_id": "50",
  "action_type": "click",
  "timestamp": 1705123456.789
}
```

**Response:**
```json
{
  "success": true,
  "message": "Action recorded"
}
```

**Validation:**
- `user_id`: Không rỗng, max 100 ký tự
- `item_id`: Không rỗng, max 100 ký tự
- `action_type`: Phải là một trong {click, like, share, booking}
- `timestamp`: >= 0, trong khoảng hợp lý (2000-2100)

### 8.2. POST /user_actions_batch

**Mục đích:** Nhận nhiều actions cùng lúc (batch)

**Request:**
```json
{
  "actions": [
    {"user_id": "123", "item_id": "50", "action_type": "click", "timestamp": 1705123456.789},
    {"user_id": "123", "item_id": "51", "action_type": "like", "timestamp": 1705123457.123}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "recorded": 2,
  "failed": 0
}
```

### 8.3. GET /recommendations/{user_id}

**Mục đích:** Lấy recommendations cho user

**Request:**
```
GET /recommendations/123?top_k=10&use_behavior_boost=true&use_similarity_boost=true
```

**Parameters:**

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `top_k` | int | 10 | Số lượng recommendations |
| `use_behavior_boost` | bool | true | Bật/tắt Phase 1 |
| `use_similarity_boost` | bool | true | Bật/tắt Phase 2 |
| `alpha` | float | 0.3 | Boost coefficient |
| `decay_rate` | float | 0.1 | Time decay rate |
| `behavior_hours` | int | 24 | Số giờ gần đây |
| `similarity_threshold` | float | 0.5 | Similarity threshold |
| `similarity_boost_factor` | float | 0.5 | Similarity boost factor |

**Response:**
```json
{
  "user_id": "123",
  "recommendations": [284, 520, 427, 350, 555, ...],
  "model_version": "DeepFM-Dec-16-2025_19-57-01",
  "top_k": 10
}
```

### 8.4. GET /health

**Mục đích:** Health check

**Response:**
```json
{
  "ok": true,
  "model_loaded": true
}
```

### 8.5. GET /schema

**Mục đích:** Trả về API contract

**Response:**
```json
{
  "endpoints": {
    "/user_action": {...},
    "/recommendations/{user_id}": {...}
  }
}
```

---

## 9. ETL PROCESS

### 9.1. Mục đích

Chuyển đổi actions từ web sang format RecBole để training

### 9.2. Input Format

**Từ web (JSON lines):**
```json
{"user_id": "123", "hotel_id": "50", "action_type": "click", "timestamp": 1705123456.789}
{"user_id": "123", "hotel_id": "50", "action_type": "like", "timestamp": 1705123457.123}
```

### 9.3. Processing

1. **Validate:** Kiểm tra format và giá trị
2. **Group:** Group theo (user_id, hotel_id)
3. **Aggregate:** Lấy action có điểm cao nhất
4. **Convert:** Map action_type → rating (0-1)

**Mapping:**
```
booking → 1.0
share   → 0.75
like    → 0.5
click   → 0.25
```

### 9.4. Output Format

**RecBole format (TSV):**
```
user_id:token	hotel_id:token	rating:float	timestamp:float
123	50	0.5	1705123457.123
```

### 9.5. Incremental Processing

- Đọc từ `user_actions.log` (real-time)
- Chỉ xử lý actions mới (chưa có trong `hotel.inter`)
- Append vào `hotel.inter` (không ghi đè)

---

## 10. TESTING VÀ VALIDATION

### 10.1. Phase 1 Testing

**Script:** `tests/phase1_analysis/test_phase1_batch_100.py`

**Mục đích:** Test Phase 1 với 100 users

**Quy trình:**
1. Load model và dataset
2. Test từng user:
   - Lấy recommendations (chỉ Phase 1)
   - Kiểm tra patterns:
     - Gender → Style
     - Age → Price
     - Region → City
     - Age → Star (nếu age >= 30)
     - Age → Score (nếu age < 30)
3. Đánh giá kết quả với thresholds
4. Generate report

**Report:** `tests/phase1_analysis/docs/PHASE1_REPORT.md`

### 10.2. Phase 2 Testing

**Script:** `tests/phase1_analysis/test_phase2_similarity.py`

**Mục đích:** Chứng minh Phase 2 hoạt động đúng

**Quy trình:**
1. Tạo test actions (click hotels cụ thể)
2. So sánh recommendations với/không có similarity boost
3. Phân tích items nào được boost do similarity
4. Hiển thị similarity scores và features

### 10.3. Integration Testing

**Script:** `tests/integration/`

**Mục đích:** Test toàn bộ flow từ API → Inference → Recommendations

---

## 11. THUẬT NGỮ VÀ KHÁI NIỆM

### 11.1. Deep Learning Terms

| Thuật ngữ | Giải thích | Ví dụ |
|-----------|------------|-------|
| **Embedding** | Vector biểu diễn feature | age=25 → [0.1, 0.3, -0.2, ...] (10 chiều) |
| **Neural Network** | Mạng nơ-ron (học patterns) | DeepFM có DNN component |
| **Loss Function** | Hàm đo lỗi | BCE Loss |
| **Gradient Descent** | Thuật toán tối ưu | Cập nhật weights để giảm loss |
| **Epoch** | 1 lần duyệt qua toàn bộ dataset | 300 epochs = duyệt 300 lần |
| **Batch** | Nhóm samples xử lý cùng lúc | Batch size = 256 |
| **Learning Rate** | Tốc độ học | 0.001 = học chậm nhưng ổn định |

### 11.2. Recommendation Terms

| Thuật ngữ | Giải thích | Ví dụ |
|-----------|------------|-------|
| **Cold Start** | User/item mới (chưa có data) | User 999 chưa có interactions |
| **Collaborative Filtering** | Gợi ý dựa trên users tương tự | User A và B giống nhau → recommend items B đã thích |
| **Content-Based** | Gợi ý dựa trên features | User thích romantic → recommend hotels có style=romantic |
| **Hybrid** | Kết hợp nhiều phương pháp | DeepFM = Collaborative + Content-Based |
| **Top-K** | K items tốt nhất | Top-10 = 10 items có điểm cao nhất |

### 11.3. System Terms

| Thuật ngữ | Giải thích | Ví dụ |
|-----------|------------|-------|
| **Checkpoint** | File lưu model đã train | `DeepFM-Dec-16-2025_19-57-01.pth` |
| **Inference** | Dự đoán (predict) | Load model → predict scores |
| **Training** | Huấn luyện model | Train với dataset → tạo checkpoint |
| **Retraining** | Train lại với dữ liệu mới | Retrain mỗi ngày |
| **ETL** | Extract, Transform, Load | Web actions → hotel.inter |
| **Cache** | Lưu tạm để tăng tốc | Cache model để không load lại |

### 11.4. Mathematical Terms

| Thuật ngữ | Giải thích | Công thức |
|-----------|------------|-----------|
| **Sigmoid** | Hàm chuyển về [0,1] | σ(x) = 1/(1+e^(-x)) |
| **Exponential Decay** | Giảm theo hàm mũ | exp(-rate × time) |
| **Jaccard Similarity** | Độ tương đồng sets | |A∩B| / |A∪B| |
| **Weighted Average** | Trung bình có trọng số | Σ(x_i × w_i) / Σ(w_i) |
| **RMSE** | Root Mean Squared Error | √(Σ(y_true-y_pred)²/n) |
| **MAE** | Mean Absolute Error | Σ|y_true-y_pred|/n |

---

## KẾT LUẬN

Tài liệu này đã trình bày toàn diện về hệ thống AI Recommendation, bao gồm:

1. ✅ **Mô hình DeepFM**: Kiến trúc, công thức, hyperparameters
2. ✅ **Phase 1 (Behavior Boost)**: Công thức, ví dụ, implementation
3. ✅ **Phase 2 (Similarity Boost)**: Công thức, ví dụ, implementation
4. ✅ **Cấu trúc thư mục**: Giải thích từng thư mục quan trọng
5. ✅ **Các module**: Chi tiết từng module và functions
6. ✅ **Training và Retraining**: Quy trình đầy đủ
7. ✅ **API Endpoints**: Tất cả endpoints với examples
8. ✅ **ETL Process**: Quy trình chuyển đổi dữ liệu
9. ✅ **Testing**: Các loại test và validation
10. ✅ **Thuật ngữ**: Giải thích các khái niệm khó hiểu

**Lưu ý:** Tài liệu này sẽ được cập nhật khi hệ thống phát triển thêm tính năng mới.

---

**Tác giả:** AI Development Team  
**Ngày:** 2025-01-16  
**Phiên bản:** 1.0


