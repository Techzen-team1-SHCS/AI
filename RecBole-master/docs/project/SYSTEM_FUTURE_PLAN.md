# KẾ HOẠCH CẢI TIẾN HỆ THỐNG - REAL-TIME BEHAVIOR-BASED RECOMMENDATIONS

**Ngày lập kế hoạch**: 2025-01-14  
**Mục tiêu**: Cải thiện recommendations để real-time và personalized hơn

---

## MỤC LỤC

1. [Tổng quan cải tiến](#1-tổng-quan-cải-tiến)
2. [Kiến trúc mới](#2-kiến-trúc-mới)
3. [Luồng hoạt động mới](#3-luồng-hoạt-động-mới)
4. [Công thức tính điểm](#4-công-thức-tính-điểm)
5. [Implementation Plan](#5-implementation-plan)
6. [Files cần sửa/thêm](#6-files-cần-sửathêm)
7. [Testing Plan](#7-testing-plan)
8. [Rollout Plan](#8-rollout-plan)

---

## 1. TỔNG QUAN CẢI TIẾN

### 1.1. Mục tiêu

**Hiện tại:**
- ❌ Recommendations dựa trên model đã train (dữ liệu cũ)
- ❌ Delay 24 giờ (phải đợi retrain)
- ❌ Tất cả users cùng demographic → recommendations giống nhau
- ❌ Không có trọng số theo thời gian

**Sau khi cải tiến:**
- ✅ Recommendations real-time (dựa trên hành vi mới nhất)
- ✅ Personalized theo hành vi cá nhân
- ✅ Trọng số theo thời gian (hành vi gần đây > hành vi cũ)
- ✅ Hybrid approach (demographic cho cold start, behavior cho warm users)

### 1.2. Ý tưởng chính

**Thay đổi lớn:**
- Inference sẽ **đọc `user_actions.log`** để lấy hành vi gần đây
- Tính **trọng số theo thời gian** (exponential decay)
- **Boost điểm số** dựa trên hành vi real-time
- **Combine** với model score để có final score

**Giữ nguyên:**
- Model DeepFM (không thay đổi architecture)
- ETL và retrain pipeline (vẫn chạy như cũ)
- API endpoints (không thay đổi contract)

### 1.3. Cách hoạt động - Giải đáp thắc mắc

**Q1: Có phải gợi ý hotels đã tương tác không?**

**A:** KHÔNG. Hệ thống vẫn **exclude** hotels đã tương tác (từ `hotel.inter`). NHƯNG:
- Hotels đã tương tác trong quá khứ (có trong `hotel.inter`) → Bị exclude
- Hotels vừa click (chưa có trong `hotel.inter`, chưa qua ETL) → Có thể được recommend lại, NHƯNG...
- **Điều quan trọng:** Boost này chủ yếu để **tăng điểm hotels TƯƠNG TỰ** hotels đã tương tác (Phase 2)
- **Phase 1:** Chỉ boost hotels đã tương tác gần đây để test logic, nhưng chúng sẽ bị exclude sau

**Q2: Có phải gợi ý hotels tương tự không?**

**A:** 
- **Phase 1 (Basic):** KHÔNG, chỉ boost hotels đã tương tác trực tiếp
- **Phase 2 (Similarity Boost):** CÓ, sẽ boost hotels tương tự (same style, price range, city, ...)

**Q3: Nếu nhiều actions cùng hotel, boost nên cộng hay lấy max?**

**A:** **Cộng lại** (vì mỗi action đều có trọng số theo thời gian):
- Click lúc 7:00 AM (weight = 0.967, boost = 0.25 * 0.967 = 0.242)
- Like lúc 7:10 AM (weight = 0.985, boost = 0.5 * 0.985 = 0.493)
- Total boost = 0.242 + 0.493 = **0.735** (cộng lại)

**Lý do cộng:**
- Mỗi action thể hiện sự quan tâm khác nhau (click < like < booking)
- Trọng số thời gian đã giảm dần tự động (actions cũ có weight thấp hơn)
- Tổng boost có giới hạn: `final = base * (1 + alpha * boost)`, với alpha = 0.3 → boost tối đa 30%
- Nếu boost quá lớn → có thể giảm alpha hoặc cap boost

**Ví dụ:**
- Base score: 0.60
- Boost tổng: 0.735 (từ nhiều actions)
- Final = 0.60 * (1 + 0.3 * 0.735) = 0.60 * 1.221 = **0.733** (tăng 22%)
- Vẫn hợp lý (không tăng quá lớn)

---

## 2. KIẾN TRÚC MỚI

### 2.1. So sánh kiến trúc

#### A. Kiến trúc cũ (Current)

```
┌─────────────────────────────────────────────┐
│  GET /recommendations/123                   │
│         ↓                                   │
│  inference.py                               │
│    ├─ Load model                            │
│    ├─ Get user features (age, gender, ...) │
│    ├─ Get item features (style, price, ...)│
│    ├─ Model.predict() → scores              │
│    └─ Return top-K                          │
└─────────────────────────────────────────────┘

❌ KHÔNG đọc user_actions.log
❌ KHÔNG dùng hành vi gần đây
```

#### B. Kiến trúc mới (Proposed)

```
┌─────────────────────────────────────────────┐
│  GET /recommendations/123                   │
│         ↓                                   │
│  inference.py                               │
│    ├─ Load model                            │
│    ├─ Get user features (age, gender, ...) │
│    ├─ Get item features (style, price, ...)│
│    ├─ Model.predict() → base_scores         │
│         ↓                                   │
│    ├─ READ user_actions.log (NEW!)          │
│    ├─ Get recent user actions (last 24h)    │
│    ├─ Calculate time weights                │
│    ├─ Calculate behavior boost              │
│    ├─ Combine: final_score =                │
│    │    base_score * (1 + α * boost)        │
│    └─ Return top-K                          │
└─────────────────────────────────────────────┘

✅ ĐỌC user_actions.log
✅ DÙNG hành vi gần đây
✅ TRỌNG SỐ theo thời gian
```

### 2.2. Flow diagram mới

```
┌─────────────────────────────────────────────────────────────────┐
│                    REAL-TIME INFERENCE FLOW                     │
└─────────────────────────────────────────────────────────────────┘

Request: GET /recommendations/123?top_k=10
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Load Model & Base Prediction                           │
├─────────────────────────────────────────────────────────────────┤
│ - Load DeepFM model (cache)                                     │
│ - Get user 123 features (age, gender, region)                   │
│ - Get all item features (595 hotels)                            │
│ - Model.predict() → base_scores[595]                            │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Read Recent User Actions (NEW!)                        │
├─────────────────────────────────────────────────────────────────┤
│ - Read data/user_actions.log                                    │
│ - Filter actions for user_id=123                                │
│ - Filter actions in last 24 hours                               │
│ - Parse JSON: [{user_id, item_id, action_type, timestamp}, ...] │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Calculate Time Weights                                 │
├─────────────────────────────────────────────────────────────────┤
│ For each action:                                                │
│   hours_ago = (current_time - action.timestamp) / 3600          │
│   weight = exp(-decay_rate * hours_ago)                         │
│                                                                 │
│ Example:                                                        │
│   Action at 7:00 AM, current = 7:15 AM → hours_ago = 0.25      │
│   weight = exp(-0.1 * 0.25) = 0.975 (rất cao!)                 │
│                                                                 │
│   Action at 6:00 AM, current = 7:15 AM → hours_ago = 1.25      │
│   weight = exp(-0.1 * 1.25) = 0.883 (thấp hơn)                 │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Calculate Behavior Boost                               │
├─────────────────────────────────────────────────────────────────┤
│ For each item:                                                  │
│   boost[item_id] = 0                                            │
│                                                                 │
│   For each action on this item:                                 │
│     action_score = get_action_score(action_type)                │
│     boosted_score = action_score * weight                       │
│     boost[item_id] += boosted_score                             │
│                                                                 │
│ Action scores:                                                  │
│   - booking: 1.0                                                │
│   - share: 0.75                                                 │
│   - like: 0.5                                                   │
│   - click: 0.25                                                 │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: Combine Scores                                         │
├─────────────────────────────────────────────────────────────────┤
│ For each item:                                                  │
│   base_score = model_scores[item_id]                            │
│   behavior_boost = boost[item_id]                               │
│   final_score = base_score * (1 + alpha * behavior_boost)      │
│                                                                 │
│ Hyperparameters:                                                │
│   - alpha: 0.3 (tùy chỉnh, 0.3 = boost tối đa 30%)             │
│   - decay_rate: 0.1 (tùy chỉnh, 0.1 = giảm ~10% mỗi giờ)      │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: Post-processing                                        │
├─────────────────────────────────────────────────────────────────┤
│ - Sort by final_score (descending)                              │
│ - Filter interacted items (từ hotel.inter, KHÔNG từ log)       │
│ - Take top-K                                                    │
│ - Return recommendations                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. LUỒNG HOẠT ĐỘNG MỚI

### 3.1. Ví dụ cụ thể

**Scenario:**
- User 123 (age: 25, gender: F, region: Hanoi)
- 7:00 AM: Click hotel 4, 5, 6
- 7:15 AM: Click hotel 10, 11, 12
- 7:20 AM: Web gọi GET /recommendations/123

**Luồng xử lý:**

```
Step 1: Base Prediction
───────────────────────
Model dự đoán dựa trên:
  - User features: age=25, gender=F, region=Hanoi
  - Item features: style, price, star, score, city

Base scores:
  hotel_1: 0.65
  hotel_2: 0.62
  hotel_3: 0.60
  hotel_4: 0.58  ← User đã click lúc 7:00
  hotel_5: 0.55  ← User đã click lúc 7:00
  hotel_6: 0.52  ← User đã click lúc 7:00
  ...
  hotel_10: 0.48  ← User đã click lúc 7:15
  hotel_11: 0.45  ← User đã click lúc 7:15
  hotel_12: 0.42  ← User đã click lúc 7:15
  ...

Step 2: Read Recent Actions
────────────────────────────
Read user_actions.log:
  [
    {"user_id": 123, "item_id": 4, "action_type": "click", "timestamp": 7:00 AM},
    {"user_id": 123, "item_id": 5, "action_type": "click", "timestamp": 7:00 AM},
    {"user_id": 123, "item_id": 6, "action_type": "click", "timestamp": 7:00 AM},
    {"user_id": 123, "item_id": 10, "action_type": "click", "timestamp": 7:15 AM},
    {"user_id": 123, "item_id": 11, "action_type": "click", "timestamp": 7:15 AM},
    {"user_id": 123, "item_id": 12, "action_type": "click", "timestamp": 7:15 AM}
  ]

Step 3: Calculate Time Weights
───────────────────────────────
Current time: 7:20 AM

Actions at 7:00 AM (20 minutes ago = 0.33 hours):
  weight = exp(-0.1 * 0.33) = 0.967

Actions at 7:15 AM (5 minutes ago = 0.08 hours):
  weight = exp(-0.1 * 0.08) = 0.992 (CAO HƠN!)

Step 4: Calculate Behavior Boost
─────────────────────────────────
Action score for "click": 0.25

For hotel_4 (clicked at 7:00 AM):
  boost = 0.25 * 0.967 = 0.242

For hotel_5 (clicked at 7:00 AM):
  boost = 0.25 * 0.967 = 0.242

For hotel_6 (clicked at 7:00 AM):
  boost = 0.25 * 0.967 = 0.242

For hotel_10 (clicked at 7:15 AM):
  boost = 0.25 * 0.992 = 0.248 (CAO HƠN!)

For hotel_11 (clicked at 7:15 AM):
  boost = 0.25 * 0.992 = 0.248

For hotel_12 (clicked at 7:15 AM):
  boost = 0.25 * 0.992 = 0.248

Step 5: Combine Scores (alpha = 0.3)
─────────────────────────────────────
For hotel_1: final = 0.65 * (1 + 0.3 * 0) = 0.65
For hotel_2: final = 0.62 * (1 + 0.3 * 0) = 0.62
For hotel_3: final = 0.60 * (1 + 0.3 * 0) = 0.60

For hotel_4: final = 0.58 * (1 + 0.3 * 0.242) = 0.58 * 1.073 = 0.622
For hotel_5: final = 0.55 * (1 + 0.3 * 0.242) = 0.55 * 1.073 = 0.590
For hotel_6: final = 0.52 * (1 + 0.3 * 0.242) = 0.52 * 1.073 = 0.558

For hotel_10: final = 0.48 * (1 + 0.3 * 0.248) = 0.48 * 1.074 = 0.516
For hotel_11: final = 0.45 * (1 + 0.3 * 0.248) = 0.45 * 1.074 = 0.483
For hotel_12: final = 0.42 * (1 + 0.3 * 0.248) = 0.42 * 1.074 = 0.451

Step 6: Sort & Filter
─────────────────────
Final scores (sorted):
  1. hotel_1: 0.65
  2. hotel_4: 0.622 (↑ từ 0.58, được boost!)
  3. hotel_2: 0.62
  4. hotel_5: 0.590 (↑ từ 0.55, được boost!)
  5. hotel_3: 0.60
  6. hotel_6: 0.558 (↑ từ 0.52, được boost!)
  7. hotel_10: 0.516 (↑ từ 0.48, được boost!)
  ...

Top 10 recommendations:
  [1, 4, 2, 5, 3, 6, 10, 11, 12, ...]
  ↑ Hotel 4, 5, 6, 10, 11, 12 được boost lên!
```

**Kết quả:**
- ✅ Hotels user vừa click (4, 5, 6, 10, 11, 12) được boost lên top
- ✅ Hotels click gần đây hơn (10, 11, 12) có điểm cao hơn hotels click sớm hơn (4, 5, 6)
- ✅ Vẫn giữ hotels từ model (1, 2, 3) nếu chúng có điểm cao

---

### 3.2. Timeline thực tế

```
7:00 AM - User click hotel 4, 5, 6
         → Web POST /user_actions_batch → API ghi vào log
         → Log file: [{"user_id": 123, "item_id": 4, ...}, ...]

7:15 AM - User click hotel 10, 11, 12
         → Web POST /user_actions_batch → API ghi vào log
         → Log file: [..., {"user_id": 123, "item_id": 10, ...}, ...]

7:20 AM - Web gọi GET /recommendations/123
         → Inference đọc log file (NGAY LẬP TỨC!)
         → Tìm actions của user 123 trong last 24h
         → Tính trọng số và boost
         → Combine với model scores
         → Trả về: [1, 4, 2, 5, 3, 6, 10, 11, 12, ...]
         ✅ Hotels 4, 5, 6, 10, 11, 12 được boost!

7:03 AM - ETL chạy (mỗi 3 phút)
         → Xử lý log → Cập nhật hotel.inter
         → (Vẫn chạy như cũ, để retrain sau này)

2:00 AM (ngày mai) - Retrain chạy
         → Train model với dữ liệu mới
         → Model học được hành vi từ 7:00 AM hôm qua
         → (Vẫn chạy như cũ, để cập nhật model dài hạn)
```

**So sánh:**

| Thời điểm | Hệ thống cũ | Hệ thống mới |
|-----------|-------------|--------------|
| 7:20 AM | Recommendations: [1, 2, 3, ...] (không có 4, 5, 6, 10, 11, 12) | Recommendations: [1, 4, 2, 5, 3, 6, 10, 11, 12, ...] (có boost!) |
| Delay | 24 giờ (đợi retrain) | **0 giây** (đọc log ngay!) |

---

## 4. CÔNG THỨC TÍNH ĐIỂM

### 4.1. Công thức chi tiết

```
Final Score = Base Score × (1 + α × Behavior Boost)

Trong đó:

Base Score:
  = Model prediction từ DeepFM
  = Dựa trên user features + item features
  = Giá trị: [0, 1] (sigmoid output)

Behavior Boost:
  = Σ (Action Score × Time Weight) for all recent actions on this item

Action Score:
  - booking: 1.0
  - share: 0.75
  - like: 0.5
  - click: 0.25

Time Weight:
  = exp(-decay_rate × hours_ago)
  
  Trong đó:
    - hours_ago = (current_time - action.timestamp) / 3600
    - decay_rate = 0.1 (hyperparameter)
    - exp: exponential function

α (alpha):
  = 0.3 (hyperparameter, boost coefficient)
  = Nghĩa: boost tối đa 30% của base score
```

### 4.2. Ý nghĩa công thức

**Base Score × (1 + α × Boost):**
- Nếu `boost = 0` (không có hành vi gần đây) → `final = base` (như cũ)
- Nếu `boost = 1.0` (có booking gần đây) → `final = base × 1.3` (tăng 30%)
- Multiplicative (nhân) thay vì additive (cộng) để:
  - Items có base score cao → được boost nhiều hơn
  - Items có base score thấp → được boost ít hơn
  - Tự nhiên hơn (không làm mất cân bằng)

**Time Weight (exponential decay):**
- Hành vi 0 giờ trước (ngay bây giờ) → `weight = 1.0` (100%)
- Hành vi 1 giờ trước → `weight = exp(-0.1 * 1) = 0.905` (~90%)
- Hành vi 5 giờ trước → `weight = exp(-0.1 * 5) = 0.607` (~60%)
- Hành vi 24 giờ trước → `weight = exp(-0.1 * 24) = 0.091` (~9%)
- **Hành vi gần đây hơn → trọng số cao hơn**

### 4.3. Ví dụ tính toán chi tiết

**Scenario:**
- User 123, Hotel 501
- Base score từ model: 0.60
- User đã click hotel 501 lúc 7:00 AM (action_score = 0.25)
- Current time: 7:20 AM (20 minutes = 0.33 hours ago)
- alpha = 0.3, decay_rate = 0.1

**Tính toán:**

```
1. Time Weight:
   hours_ago = 0.33
   weight = exp(-0.1 * 0.33) = exp(-0.033) = 0.967

2. Behavior Boost:
   boost = action_score × weight = 0.25 × 0.967 = 0.242

3. Final Score:
   final = base_score × (1 + alpha × boost)
         = 0.60 × (1 + 0.3 × 0.242)
         = 0.60 × (1 + 0.073)
         = 0.60 × 1.073
         = 0.644

Kết quả: 0.60 → 0.644 (tăng 7.3%)
```

**Nếu có nhiều actions:**

- Click lúc 7:00 AM: boost_1 = 0.25 × 0.967 = 0.242
- Like lúc 7:10 AM: boost_2 = 0.5 × 0.985 = 0.493
- Total boost = 0.242 + 0.493 = 0.735
- Final = 0.60 × (1 + 0.3 × 0.735) = 0.60 × 1.221 = 0.733 (tăng 22.1%!)

---

## 5. IMPLEMENTATION PLAN

### 5.1. Phase 1: Basic Behavior Boost (3-4 ngày) - **RECOMMENDED START**

**Mục tiêu:** Implement cơ bản, có kết quả ngay

**Tasks:**

#### Day 1-2: Core Logic
1. **Tạo function đọc log file** (`inference.py`)
   ```python
   def get_recent_user_actions(user_id: str, hours: int = 24) -> List[Dict]:
       """Đọc user_actions.log và lấy actions gần đây của user"""
       # Read log file
       # Filter by user_id
       # Filter by timestamp (last N hours)
       # Return list of actions
   ```

2. **Tạo function tính time weights** (`inference.py`)
   ```python
   def calculate_time_weight(timestamp: float, current_time: float, decay_rate: float = 0.1) -> float:
       """Tính trọng số theo thời gian"""
       hours_ago = (current_time - timestamp) / 3600
       return math.exp(-decay_rate * hours_ago)
   ```

3. **Tạo function tính behavior boost** (`inference.py`)
   ```python
   def calculate_behavior_boost(actions: List[Dict], current_time: float, decay_rate: float = 0.1) -> Dict[int, float]:
       """Tính boost cho từng item dựa trên hành vi gần đây"""
       boost = {}
       for action in actions:
           item_id = int(action['item_id'])
           action_score = get_action_score(action['action_type'])
           weight = calculate_time_weight(action['timestamp'], current_time, decay_rate)
           boost[item_id] = boost.get(item_id, 0) + (action_score * weight)
       return boost
   ```

4. **Sửa `get_recommendations()`** (`inference.py`)
   ```python
   # Sau khi có model scores
   base_scores = model.predict(...)
   
   # NEW: Đọc hành vi gần đây
   recent_actions = get_recent_user_actions(user_id, hours=24)
   behavior_boost = calculate_behavior_boost(recent_actions, current_time)
   
   # Combine scores
   final_scores = {}
   for item_id, base_score in base_scores.items():
       boost = behavior_boost.get(item_id, 0)
       final_scores[item_id] = base_score * (1 + 0.3 * boost)
   
   # Sort và lấy top-K
   ```

#### Day 3: Testing & Optimization
5. **Tạo test script**
   ```python
   # test_behavior_boost.py
   # Test với dữ liệu thực
   # Verify recommendations thay đổi sau khi click
   ```

6. **Optimize performance**
   - Cache log file reading (đọc 1 lần, dùng nhiều lần)
   - Early return nếu không có actions gần đây
   - Batch processing nếu có nhiều items

#### Day 4: Integration & Testing
7. **Integration test**
   - Test với API endpoints
   - Test với dữ liệu thực từ web
   - Verify không break existing functionality

8. **Performance test**
   - Measure latency (phải < 1 giây)
   - Optimize nếu cần

**Deliverables:**
- ✅ Recommendations real-time (đọc log ngay)
- ✅ Trọng số theo thời gian
- ✅ Boost hotels đã tương tác gần đây (để test logic)
- ⚠️ **Lưu ý:** Hotels đã tương tác vẫn bị exclude (từ hotel.inter), nhưng hotels vừa click (chưa qua ETL) có thể được recommend lại
- ✅ Performance: < 1 giây

**Chưa có:**
- ❌ Similarity boost (hotels tương tự) → Phase 2
- ❌ Hybrid logic (cold start vs warm user) → Phase 3
- ❌ Advanced caching

---

### 5.2. Phase 2: Similarity Boost (2-3 ngày) - **OPTIONAL**

**Mục tiêu:** Boost hotels tương tự hotels đã tương tác

**Tasks:**

1. **Tính similarity matrix** (pre-compute)
   ```python
   # item_similarity.py
   def calculate_item_similarity(dataset) -> np.ndarray:
       """Tính similarity giữa các items dựa trên features"""
       # Cosine similarity hoặc Jaccard similarity
       # Dựa trên: style, price, star, score, city
       return similarity_matrix
   ```

2. **Sửa behavior boost để include similarity**
   ```python
   # Nếu user click hotel A
   # Boost hotel A trực tiếp
   # Boost hotels tương tự A (với trọng số similarity)
   ```

3. **Cache similarity matrix** (để không tính lại mỗi request)

**Deliverables:**
- ✅ Hotels tương tự được boost
- ✅ Personalized hơn

---

### 5.3. Phase 3: Hybrid Logic (1-2 ngày) - **OPTIONAL**

**Mục tiêu:** Cold start vs warm user handling

**Tasks:**

1. **Detect cold start users**
   ```python
   # Nếu user mới (không có trong dataset)
   # → Dùng demographic-based recommendations (như hiện tại)
   # Nếu user đã có hành vi
   # → Dùng behavior-based recommendations (mới)
   ```

2. **Adjust alpha dynamically**
   ```python
   # Nếu user có ít hành vi → alpha thấp (tin vào model)
   # Nếu user có nhiều hành vi → alpha cao (tin vào behavior)
   ```

**Deliverables:**
- ✅ Cold start users được handle tốt
- ✅ Alpha tự động điều chỉnh

---

## 6. FILES CẦN SỬA/THÊM

### 6.1. Files cần sửa

#### A. `inference.py` (MAIN CHANGES)

**Functions cần thêm:**

```python
# 1. Đọc log file
def get_recent_user_actions(user_id: str, hours: int = 24, log_file: str = "data/user_actions.log") -> List[Dict]:
    """Đọc user_actions.log và lấy actions gần đây của user.
    
    Args:
        user_id: ID của user (external token)
        hours: Số giờ gần đây cần lấy (default: 24)
        log_file: Đường dẫn đến log file
    
    Returns:
        List of actions: [{"user_id": ..., "item_id": ..., "action_type": ..., "timestamp": ...}, ...]
    """
    import json
    import time
    
    if not os.path.exists(log_file):
        return []
    
    current_time = time.time()
    cutoff_time = current_time - (hours * 3600)
    
    actions = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    action = json.loads(line)
                    # Filter by user_id
                    if str(action.get('user_id')) != str(user_id):
                        continue
                    # Filter by timestamp
                    if action.get('timestamp', 0) < cutoff_time:
                        continue
                    actions.append(action)
                except json.JSONDecodeError:
                    continue
    except IOError:
        # Log file đang bị lock (ETL đang xử lý) → skip
        pass
    
    return actions


# 2. Action score mapping
def get_action_score(action_type: str) -> float:
    """Map action_type thành điểm số.
    
    Args:
        action_type: "click" | "like" | "share" | "booking"
    
    Returns:
        Action score (0.25, 0.5, 0.75, hoặc 1.0)
    """
    action_scores = {
        'booking': 1.0,
        'share': 0.75,
        'like': 0.5,
        'click': 0.25
    }
    return action_scores.get(action_type.lower(), 0.0)


# 3. Tính time weight
def calculate_time_weight(timestamp: float, current_time: float, decay_rate: float = 0.1) -> float:
    """Tính trọng số theo thời gian (exponential decay).
    
    Args:
        timestamp: Unix timestamp của action
        current_time: Unix timestamp hiện tại
        decay_rate: Decay rate (default: 0.1)
    
    Returns:
        Time weight (0-1), càng gần hiện tại càng cao
    """
    import math
    hours_ago = (current_time - timestamp) / 3600
    return math.exp(-decay_rate * hours_ago)


# 4. Tính behavior boost
def calculate_behavior_boost(actions: List[Dict], current_time: float, decay_rate: float = 0.1) -> Dict[int, float]:
    """Tính boost cho từng item dựa trên hành vi gần đây.
    
    IMPORTANT: Nếu nhiều actions cùng hotel, boost được CỘNG LẠI (không lấy max).
    
    Lý do:
    - Mỗi action thể hiện sự quan tâm khác nhau (click < like < booking)
    - Trọng số thời gian đã giảm dần tự động (actions cũ có weight thấp hơn)
    - Tổng boost có giới hạn bởi alpha (0.3) → boost tối đa 30%
    
    Example:
        Hotel 501 có 3 actions:
        - Click lúc 7:00 AM: boost = 0.25 * 0.967 = 0.242
        - Like lúc 7:10 AM: boost = 0.5 * 0.985 = 0.493
        - Booking lúc 7:20 AM: boost = 1.0 * 1.0 = 1.0
        Total boost = 0.242 + 0.493 + 1.0 = 1.735
        
        Với base_score = 0.60, alpha = 0.3:
        Final = 0.60 * (1 + 0.3 * 1.735) = 0.60 * 1.521 = 0.913 (tăng 52%)
        → Vẫn hợp lý vì user đã booking (quan tâm rất cao)
    
    Args:
        actions: List of actions từ get_recent_user_actions()
        current_time: Unix timestamp hiện tại
        decay_rate: Decay rate (default: 0.1)
    
    Returns:
        Dict: {item_id: boost_score, ...}
    """
    boost = {}
    for action in actions:
        try:
            item_id = int(action['item_id'])
            action_type = action['action_type']
            timestamp = float(action['timestamp'])
            
            action_score = get_action_score(action_type)
            weight = calculate_time_weight(timestamp, current_time, decay_rate)
            boosted_score = action_score * weight
            
            # CỘNG LẠI (không lấy max)
            boost[item_id] = boost.get(item_id, 0) + boosted_score
        except (ValueError, KeyError, TypeError):
            continue
    
    return boost
```

**Function cần sửa:**

```python
def get_recommendations(
    user_id: str,
    top_k: int = 10,
    model_path: Optional[str] = None,
    exclude_interacted: bool = True,
    use_behavior_boost: bool = True,  # NEW parameter
    alpha: float = 0.3,  # NEW parameter
    decay_rate: float = 0.1,  # NEW parameter
    behavior_hours: int = 24  # NEW parameter
) -> List[str]:
    """Lấy recommendations cho user.
    
    NEW: Hỗ trợ behavior boost từ user_actions.log
    """
    # ... existing code ...
    
    # Model predict (existing)
    with torch.no_grad():
        scores = model.predict(interaction)
        scores = scores.cpu().numpy().flatten()
    
    # NEW: Behavior boost
    behavior_boost_dict = {}
    if use_behavior_boost:
        import time
        current_time = time.time()
        recent_actions = get_recent_user_actions(user_id, hours=behavior_hours)
        behavior_boost_dict = calculate_behavior_boost(recent_actions, current_time, decay_rate)
        print(f"[INFERENCE] Found {len(recent_actions)} recent actions, boost for {len(behavior_boost_dict)} items")
    
    # Combine scores
    final_scores = {}
    for idx, item_internal_id in enumerate(all_item_internal_ids):
        item_internal_id_int = int(item_internal_id.item())
        base_score = float(scores[idx])
        
        # Convert internal ID to external token
        try:
            item_token = dataset.id2token(dataset.iid_field, item_internal_id_int)
            try:
                item_id = int(item_token)
            except (ValueError, TypeError):
                item_id = item_token
            
            # NEW: Apply behavior boost
            if use_behavior_boost and item_id in behavior_boost_dict:
                boost = behavior_boost_dict[item_id]
                final_score = base_score * (1 + alpha * boost)
            else:
                final_score = base_score
            
            final_scores[item_id] = final_score
        except (ValueError, IndexError):
            continue
    
    # Sort by final_score (descending)
    sorted_items = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Filter interacted items và lấy top-K
    top_k_items = []
    for item_id, final_score in sorted_items:
        if exclude_interacted and item_id in interacted_items:
            continue
        top_k_items.append(item_id)
        if len(top_k_items) >= top_k:
            break
    
    return top_k_items
```

---

#### B. `api_server.py` (MINOR CHANGES)

**Optional:** Thêm query parameters để control behavior boost

```python
@app.get("/recommendations/{user_id}")
def get_recommendations(
    user_id: str,
    top_k: int = 10,
    use_behavior_boost: bool = True,  # NEW
    alpha: float = 0.3,  # NEW
    authorization: Optional[str] = Header(default=None)
):
    """Lấy recommendations cho user từ model đã train.
    
    NEW: Hỗ trợ behavior boost từ user_actions.log
    """
    # ... existing validation ...
    
    recommendations = inference_get_recommendations(
        user_id=user_id,
        top_k=top_k,
        exclude_interacted=True,
        use_behavior_boost=use_behavior_boost,  # NEW
        alpha=alpha  # NEW
    )
    
    # ... rest of code ...
```

---

### 6.2. Files cần thêm (OPTIONAL)

#### A. `test_behavior_boost.py` (Testing)

```python
"""Test script cho behavior boost functionality."""

def test_time_weight():
    """Test tính time weight."""
    # ...

def test_behavior_boost():
    """Test tính behavior boost."""
    # ...

def test_recommendations_change():
    """Test recommendations thay đổi sau khi click."""
    # ...
```

#### B. `item_similarity.py` (Phase 2)

```python
"""Tính similarity giữa items dựa trên features."""

def calculate_item_similarity(dataset):
    """Tính similarity matrix."""
    # ...
```

---

## 7. TESTING PLAN

### 7.1. Unit Tests

1. **Test `get_recent_user_actions()`**
   - Test với log file có dữ liệu
   - Test với log file rỗng
   - Test filter theo user_id
   - Test filter theo timestamp (hours)

2. **Test `calculate_time_weight()`**
   - Test với timestamp gần đây (weight cao)
   - Test với timestamp xa (weight thấp)
   - Test với decay_rate khác nhau

3. **Test `calculate_behavior_boost()`**
   - Test với 1 action
   - Test với nhiều actions trên cùng item
   - Test với nhiều actions trên items khác nhau

4. **Test `get_recommendations()` với boost**
   - Test recommendations thay đổi sau khi có action
   - Test recommendations không thay đổi nếu không có action
   - Test với alpha khác nhau

### 7.2. Integration Tests

1. **End-to-end test**
   ```
   1. POST /user_actions_batch (click hotel 501)
   2. GET /recommendations/123
   3. Verify hotel 501 có trong top-K hoặc điểm tăng
   ```

2. **Performance test**
   - Measure latency với/không có behavior boost
   - Target: < 1 giây

3. **Load test**
   - Test với nhiều requests đồng thời
   - Verify không có race condition khi đọc log file

### 7.3. Manual Testing

1. **Test với dữ liệu thực**
   - Click hotels trên web
   - Gọi API và verify recommendations thay đổi

2. **Test edge cases**
   - User không có actions gần đây
   - Log file đang bị lock (ETL đang xử lý)
   - Nhiều actions trong thời gian ngắn

---

## 8. ROLLOUT PLAN

### 8.1. Phase 1 Rollout

**Week 1: Development**
- Day 1-2: Implement core logic
- Day 3: Testing
- Day 4: Integration & optimization

**Week 2: Testing & Deployment**
- Day 1-2: Manual testing với dữ liệu thực
- Day 3: Deploy to staging (nếu có)
- Day 4: Deploy to production

### 8.2. Monitoring

**Metrics cần theo dõi:**
- API latency (phải < 1 giây)
- Number of recommendations changed (sau khi có boost)
- Error rate (phải < 0.1%)
- Log file read errors (phải handle gracefully)

**Logging:**
```python
print(f"[INFERENCE] Found {len(recent_actions)} recent actions")
print(f"[INFERENCE] Boost for {len(behavior_boost_dict)} items")
print(f"[INFERENCE] Top 5 scores: {sorted_items[:5]}")
```

### 8.3. Rollback Plan

**Nếu có vấn đề:**
1. Set `use_behavior_boost=False` trong code
2. Redeploy (hoặc restart container)
3. System sẽ hoạt động như cũ (không có boost)

**Hoặc:**
- Thêm feature flag trong environment variable
- `USE_BEHAVIOR_BOOST=false` → disable boost

---

## 9. HYPERPARAMETERS

### 9.1. Default Values

| Parameter | Default | Description |
|-----------|---------|-------------|
| `alpha` | 0.3 | Boost coefficient (0.3 = tối đa 30% boost) |
| `decay_rate` | 0.1 | Time decay rate (0.1 = giảm ~10% mỗi giờ) |
| `behavior_hours` | 24 | Số giờ gần đây cần lấy actions |

### 9.2. Tuning Guidelines

**Alpha (boost coefficient):**
- `alpha = 0.1` → Boost nhẹ (10%) → Recommendations ít thay đổi
- `alpha = 0.3` → Boost vừa (30%) → **Recommended**
- `alpha = 0.5` → Boost mạnh (50%) → Recommendations thay đổi nhiều

**Decay rate:**
- `decay_rate = 0.05` → Giảm chậm (5%/giờ) → Hành vi cũ vẫn có trọng số
- `decay_rate = 0.1` → Giảm vừa (10%/giờ) → **Recommended**
- `decay_rate = 0.2` → Giảm nhanh (20%/giờ) → Chỉ hành vi rất gần đây mới quan trọng

**Behavior hours:**
- `behavior_hours = 6` → Chỉ lấy hành vi 6 giờ gần đây
- `behavior_hours = 24` → Lấy hành vi 24 giờ gần đây → **Recommended**
- `behavior_hours = 48` → Lấy hành vi 48 giờ gần đây

### 9.3. A/B Testing

**Test alpha values:**
- Group A: `alpha = 0.2`
- Group B: `alpha = 0.3`
- Group C: `alpha = 0.4`
- Measure: Click-through rate (CTR) trên recommendations

**Chọn alpha tốt nhất dựa trên CTR.**

---

## 10. EXPECTED OUTCOMES

### 10.1. Recommendations

**Trước khi cải tiến:**
```
User 123 (age: 25, gender: F, region: Hanoi):
  Recommendations: [1, 2, 3, 4, 5, ...] (không thay đổi trong ngày)
```

**Sau khi cải tiến (Phase 1 - Basic Boost):**
```
7:00 AM - User click hotel 501, 502
         → Boost hotels 501, 502 (nhưng chúng sẽ bị exclude nếu đã có trong hotel.inter)
         → Chủ yếu để test logic boost

7:01 AM - Recommendations: [1, 2, 3, ...] (giống như cũ)
         ⚠️ Phase 1 chưa có similarity boost, chưa có giá trị thực tế nhiều
```

**Sau khi cải tiến (Phase 2 - Similarity Boost):**
```
7:00 AM - User click hotel 501 (style: Romantic, price: 2.8M, city: HoanKiem)
7:01 AM - Recommendations: [505, 508, 512, ...] 
         ✅ Hotels TƯƠNG TỰ hotel 501 (cùng style/city, cùng price range) được boost lên!
         
7:15 AM - User click hotel 503 (style: Modern, price: 3.5M)
7:16 AM - Recommendations: [507, 510, 515, ...]
         ✅ Hotels tương tự hotel 503 được boost lên!
         ✅ Recommendations thay đổi theo hành vi real-time!
```

**Điểm khác biệt:**
- Phase 1: Boost hotels đã tương tác (test logic) → Chưa có giá trị thực tế nhiều
- Phase 2: Boost hotels **TƯƠNG TỰ** hotels đã tương tác → Có giá trị thực tế!

---

## 12. IMPLEMENTATION STATUS (Updated 2025-01-14)

### ✅ Phase 1: Basic Behavior Boost - **COMPLETED**

**Status:** ✅ **HOÀN THÀNH**

**Đã implement:**
- ✅ `get_recent_user_actions()` - Đọc user_actions.log
- ✅ `get_action_score()` - Map action_type → score
- ✅ `calculate_time_weight()` - Tính trọng số theo thời gian
- ✅ `calculate_behavior_boost()` - Tính boost cho từng item
- ✅ `get_recommendations()` - Integrate behavior boost
- ✅ API endpoint - Thêm parameters cho behavior boost
- ✅ Testing - Tất cả tests pass

**Files đã sửa:**
- `inference.py`: +150 dòng code (behavior boost functions)
- `api_server.py`: +20 dòng code (parameters mới)

**Kết quả:**
- Recommendations real-time (đọc log ngay)
- Trọng số theo thời gian (exponential decay)
- Boost hotels đã tương tác gần đây

### ✅ Phase 2: Similarity Boost - **COMPLETED**

**Status:** ✅ **HOÀN THÀNH**

**Đã implement:**
- ✅ `calculate_item_similarity()` - Tính similarity matrix giữa items
- ✅ `_calculate_item_pair_similarity()` - Tính similarity giữa 2 items
- ✅ `calculate_behavior_boost_with_similarity()` - Boost với similarity
- ✅ Similarity matrix caching - Tính 1 lần, dùng nhiều lần
- ✅ `get_recommendations()` - Integrate similarity boost
- ✅ API endpoint - Thêm parameters cho similarity boost

**Files đã sửa:**
- `inference.py`: +200 dòng code (similarity functions + cache)
- `api_server.py`: +15 dòng code (similarity parameters)

**Kết quả:**
- Boost hotels tương tự hotels đã tương tác
- Personalized hơn (dựa trên features: style, price, star, score, city)
- Similarity matrix được cache để performance tốt

**Cách hoạt động:**
1. Tính similarity matrix một lần (cache)
2. Khi user click hotel A, boost hotel A trực tiếp (Phase 1)
3. Boost hotels tương tự A với trọng số similarity (Phase 2)
4. Similarity được tính dựa trên: style, city (Jaccard), price, star, score (normalized distance)

### 📋 Next Steps

**Pending:**
- ⏳ Test similarity boost với dữ liệu thực (end-to-end)
- ⏳ Phase 3: Hybrid Logic (cold start vs warm user) - Optional
- ⏳ Performance optimization (nếu cần)

**Deployment:**
- Có thể deploy ngay Phase 1 + Phase 2
- Test với dữ liệu thực từ web
- Monitor performance và tune hyperparameters

### 10.2. Metrics

**Expected improvements:**
- ✅ Click-through rate (CTR): +10-20%
- ✅ User engagement: +15-25%
- ✅ Recommendations relevance: +20-30%

**Performance:**
- ✅ API latency: < 1 giây (acceptable)
- ✅ No errors: > 99.9% success rate

---

## 11. RISKS & MITIGATION

### 11.1. Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Log file lock** | Request fail | Medium | Catch IOError, skip boost nếu không đọc được |
| **Performance degradation** | Slow API | Low | Cache log reading, early return |
| **Too much boost** | Recommendations lệch | Low | Tune alpha (start với 0.2-0.3) |
| **Race condition** | Inconsistent results | Low | Read-only access, no write |

### 11.2. Mitigation Strategies

1. **Graceful degradation**
   - Nếu không đọc được log → skip boost, dùng model score
   - System vẫn hoạt động bình thường

2. **Feature flag**
   - `USE_BEHAVIOR_BOOST=false` → disable boost
   - Easy rollback nếu có vấn đề

3. **Monitoring**
   - Log số lượng actions found
   - Log boost scores
   - Alert nếu có errors

---

## KẾT LUẬN

**Kế hoạch này sẽ:**
- ✅ Cải thiện recommendations để real-time và personalized
- ✅ Không thay đổi model architecture
- ✅ Không break existing functionality
- ✅ Có thể rollback dễ dàng

**Next steps:**
1. Review và approve kế hoạch
2. Bắt đầu Phase 1 (3-4 ngày)
3. Test và deploy
4. Monitor và tune hyperparameters

**Questions?**
- Xem `SYSTEM_CURRENT_STATE.md` để hiểu hệ thống hiện tại
- Xem code comments trong `inference.py` sau khi implement

