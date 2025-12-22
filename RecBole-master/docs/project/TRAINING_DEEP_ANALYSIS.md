# PHÂN TÍCH CHI TIẾT QUÁ TRÌNH TRAINING CỦA AI RECOMMENDATION

**Phiên bản:** 1.0  
**Ngày cập nhật:** 2025-01-16  
**Tác giả:** AI Development Team

---

## MỤC LỤC

1. [Tổng quan về Training](#1-tổng-quan-về-training)
2. [Xử lý Dataset - Từ Raw Data đến Tensors](#2-xử-lý-dataset---từ-raw-data-đến-tensors)
3. [Embedding - Tại sao và Như thế nào](#3-embedding---tại-sao-và-như-thế-nào)
4. [Feature Encoding - Chi tiết từng loại Feature](#4-feature-encoding---chi-tiết-từng-loại-feature)
5. [Feature Interaction - Cách các Features tương tác](#5-feature-interaction---cách-các-features-tương-tác)
6. [Forward Pass - Quá trình Dự đoán](#6-forward-pass---quá-trình-dự-đoán)
7. [Backward Pass - Quá trình Học](#7-backward-pass---quá-trình-học)
8. [Training Loop - Vòng lặp Training](#8-training-loop---vòng-lặp-training)
9. [Gradient Descent - Cách Model Cập nhật](#9-gradient-descent---cách-model-cập-nhật)
10. [Loss Function - Đo lường Lỗi](#10-loss-function---đo-lường-lỗi)
11. [Ví dụ Training Step-by-Step](#11-ví-dụ-training-step-by-step)
12. [Câu hỏi thường gặp](#12-câu-hỏi-thường-gặp)

---

## 1. TỔNG QUAN VỀ TRAINING

### 1.1. Training là gì?

**Training (Huấn luyện)** là quá trình model học từ dữ liệu để có thể dự đoán chính xác. Giống như việc dạy một đứa trẻ nhận biết các mẫu, model được "dạy" bằng cách:

1. **Xem** nhiều ví dụ (user-item interactions)
2. **Dự đoán** kết quả (user có thích item không?)
3. **So sánh** với kết quả thực tế (label)
4. **Điều chỉnh** để dự đoán chính xác hơn (cập nhật weights)

### 1.2. Quy trình Training tổng quát

```
┌─────────────────────────────────────────────────────────┐
│ 1. LOAD DATASET                                         │
│    - hotel.user: User features                          │
│    - hotel.item: Item features                          │
│    - hotel.inter: Interactions (labels)                 │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 2. PREPROCESS DATA                                      │
│    - Parse features                                     │
│    - Encode categorical → indices                       │
│    - Normalize numerical                                │
│    - Create Interaction objects                         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 3. CREATE EMBEDDINGS                                   │
│    - Token fields → Embedding table                     │
│    - Float fields → Weighted embeddings                 │
│    - Mỗi feature → Vector 10 chiều                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 4. FORWARD PASS (Dự đoán)                              │
│    - Input: User + Item features                        │
│    - FM Component: 2nd order interactions              │
│    - DNN Component: High-order interactions            │
│    - Output: Score (0-1)                                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 5. CALCULATE LOSS                                       │
│    - Compare prediction vs label                        │
│    - BCE Loss: -[y_true×log(y_pred) + ...]              │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 6. BACKWARD PASS (Học)                                 │
│    - Calculate gradients                                │
│    - Update weights (Gradient Descent)                  │
│    - Repeat cho đến khi hội tụ                          │
└─────────────────────────────────────────────────────────┘
```

---

## 2. XỬ LÝ DATASET - TỪ RAW DATA ĐẾN TENSORS

### 2.1. Dataset Files

Hệ thống sử dụng 3 file dataset:

#### 2.1.1. `hotel.user` - User Features

**Format:**
```
user_id:token	age:float	gender:token	region:token
1	32.0	M	Hanoi
2	35.0	M	Hanoi
3	26.0	F	Ho Chi Minh
```

**Giải thích:**
- `user_id:token`: ID user (categorical, dạng token)
- `age:float`: Tuổi (numerical, số thực)
- `gender:token`: Giới tính (categorical: M/F)
- `region:token`: Vùng (categorical: Hanoi, Ho Chi Minh, ...)

#### 2.1.2. `hotel.item` - Item Features

**Format:**
```
item_id:token	style:token_seq	price:float	star:float	score:float	city:token_seq
1	Quiet Love	3724000.0	4.0	9.7	Hanoi
2	Modern Romantic	1917664.0	4.0	9.3	Hanoi
```

**Giải thích:**
- `item_id:token`: ID item (categorical)
- `style:token_seq`: Style (sequence of tokens: "Quiet", "Love", ...)
- `price:float`: Giá (numerical)
- `star:float`: Số sao (numerical)
- `score:float`: Điểm đánh giá (numerical)
- `city:token_seq`: Thành phố (sequence of tokens)

#### 2.1.3. `hotel.inter` - Interactions (Labels)

**Format:**
```
user_id:token	item_id:token	action_type:float	timestamp:float
114	211	0.25	1714496742
154	229	0.5	1714497394
```

**Giải thích:**
- `user_id:token`: ID user
- `item_id:token`: ID item
- `action_type:float`: Rating (0.25=click, 0.5=like, 0.75=share, 1.0=booking)
- `timestamp:float`: Thời gian tương tác

**Đây chính là labels (kết quả thực tế)** mà model cần học!

### 2.2. Feature Types trong RecBole

RecBole phân loại features thành 4 loại:

| Feature Type | Mô tả | Ví dụ | Cách xử lý |
|--------------|-------|-------|------------|
| **TOKEN** | Categorical (1 giá trị) | gender="M", region="Hanoi" | → Embedding table |
| **TOKEN_SEQ** | Categorical (nhiều giá trị) | style="Quiet Love" | → Embedding cho mỗi token, rồi pooling |
| **FLOAT** | Numerical (1 giá trị) | age=32.0, price=3724000.0 | → Weighted embedding |
| **FLOAT_SEQ** | Numerical (nhiều giá trị) | (ít dùng) | → Embedding cho mỗi giá trị |

### 2.3. Quá trình Parse Dataset

**Bước 1: Đọc file**

RecBole đọc từng dòng trong file và parse theo format TSV (Tab-Separated Values).

**Ví dụ với hotel.user:**
```python
# Dòng 1: Header
"user_id:token	age:float	gender:token	region:token"

# Dòng 2: Data
"1	32.0	M	Hanoi"
```

**Bước 2: Parse header**

```python
fields = ["user_id:token", "age:float", "gender:token", "region:token"]
field2type = {
    "user_id": FeatureType.TOKEN,
    "age": FeatureType.FLOAT,
    "gender": FeatureType.TOKEN,
    "region": FeatureType.TOKEN
}
```

**Bước 3: Parse data**

```python
# Dòng: "1	32.0	M	Hanoi"
values = ["1", "32.0", "M", "Hanoi"]

# Convert theo type:
user_data = {
    "user_id": 1,        # TOKEN → int
    "age": 32.0,         # FLOAT → float
    "gender": "M",       # TOKEN → string
    "region": "Hanoi"    # TOKEN → string
}
```

**Bước 4: Build vocabulary**

RecBole tạo vocabulary (từ điển) cho các TOKEN fields:

```python
# gender vocabulary
gender_vocab = {
    "M": 0,
    "F": 1
}

# region vocabulary
region_vocab = {
    "Hanoi": 0,
    "Ho Chi Minh": 1,
    "Da Nang": 2,
    ...
}
```

**Tại sao cần vocabulary?**
- Neural networks không thể xử lý trực tiếp strings
- Cần convert strings → numbers (indices)
- Mỗi string được map thành một số nguyên duy nhất

**Bước 5: Encode features**

```python
# Trước khi encode:
user = {
    "user_id": 1,
    "age": 32.0,
    "gender": "M",      # String
    "region": "Hanoi"   # String
}

# Sau khi encode:
user_encoded = {
    "user_id": 1,       # Giữ nguyên (đã là số)
    "age": 32.0,        # Giữ nguyên (đã là số)
    "gender": 0,        # "M" → 0 (từ vocabulary)
    "region": 0         # "Hanoi" → 0 (từ vocabulary)
}
```

**Bước 6: Create Interaction objects**

RecBole tạo Interaction objects (PyTorch tensors) để feed vào model:

```python
# Interaction cho 1 sample:
interaction = {
    "user_id": torch.LongTensor([1]),      # [batch_size=1]
    "age": torch.FloatTensor([32.0]),      # [batch_size=1]
    "gender": torch.LongTensor([0]),       # [batch_size=1]
    "region": torch.LongTensor([0]),        # [batch_size=1]
    "item_id": torch.LongTensor([211]),     # [batch_size=1]
    "style": torch.LongTensor([[5, 3]]),   # [batch_size=1, seq_len=2]
    "price": torch.FloatTensor([3724000.0]), # [batch_size=1]
    "label": torch.FloatTensor([0.25])      # [batch_size=1] - rating thực tế
}
```

---

## 3. EMBEDDING - TẠI SAO VÀ NHƯ THẾ NÀO

### 3.1. Tại sao cần Embedding?

#### 3.1.1. Vấn đề với Categorical Features

**Vấn đề 1: One-Hot Encoding quá sparse**

Nếu dùng one-hot encoding cho gender:
```
M → [1, 0]
F → [0, 1]
```

**Vấn đề:**
- Với 1000 regions → vector 1000 chiều, chỉ có 1 vị trí = 1, 999 vị trí = 0
- Rất tốn memory và không hiệu quả
- Không thể học được mối quan hệ giữa các categories

**Vấn đề 2: Numerical encoding không có ý nghĩa**

Nếu dùng số thứ tự:
```
Hanoi → 0
Ho Chi Minh → 1
Da Nang → 2
```

**Vấn đề:**
- Model sẽ nghĩ: Da Nang (2) "lớn hơn" Ho Chi Minh (1) → SAI!
- Không có ý nghĩa toán học

#### 3.1.2. Giải pháp: Embedding

**Embedding** là cách biểu diễn categorical features bằng **vectors có ý nghĩa**:

```
Hanoi → [0.1, 0.3, -0.2, 0.5, ...]  (vector 10 chiều)
Ho Chi Minh → [0.2, 0.1, 0.4, -0.1, ...]
Da Nang → [0.15, 0.25, 0.1, 0.2, ...]
```

**Ưu điểm:**
- ✅ Dense representation (không sparse)
- ✅ Có thể học được mối quan hệ (similarity, distance)
- ✅ Hiệu quả về memory
- ✅ Model tự học ý nghĩa của từng dimension

### 3.2. Embedding hoạt động như thế nào?

#### 3.2.1. Embedding Table

**Embedding table** là một ma trận có kích thước `[vocab_size, embedding_size]`:

```python
# Ví dụ với region (có 10 regions, embedding_size=10):
embedding_table = nn.Embedding(
    num_embeddings=10,  # vocab_size (số lượng regions)
    embedding_dim=10    # embedding_size (số chiều vector)
)

# Ma trận weights (được khởi tạo ngẫu nhiên, sẽ được học):
# Shape: [10, 10]
[
    [0.1, 0.3, -0.2, 0.5, 0.2, -0.1, 0.4, 0.0, -0.3, 0.1],  # Region 0 (Hanoi)
    [0.2, 0.1, 0.4, -0.1, 0.3, 0.2, -0.2, 0.1, 0.0, 0.3],  # Region 1 (Ho Chi Minh)
    [0.15, 0.25, 0.1, 0.2, -0.1, 0.3, 0.1, -0.2, 0.2, 0.0], # Region 2 (Da Nang)
    ...
]
```

#### 3.2.2. Lookup Operation

Khi cần embedding của một category, model **lookup** (tra cứu) trong table:

```python
# Input: region_index = 0 (Hanoi)
region_embedding = embedding_table(0)  # Lookup row 0

# Output: [0.1, 0.3, -0.2, 0.5, 0.2, -0.1, 0.4, 0.0, -0.3, 0.1]
```

**Đây là phép toán rất nhanh** (chỉ cần lấy 1 dòng từ ma trận)!

### 3.3. Tại sao Embedding Size = 10?

#### 3.3.1. Trade-off giữa Capacity và Efficiency

**Embedding size quá nhỏ (ví dụ: 2):**
- ✅ Tiết kiệm memory
- ✅ Training nhanh
- ❌ Không đủ capacity để học patterns phức tạp
- ❌ Không thể biểu diễn đủ thông tin

**Embedding size quá lớn (ví dụ: 100):**
- ✅ Có thể học patterns rất phức tạp
- ❌ Tốn memory (10x so với size=10)
- ❌ Training chậm
- ❌ Dễ overfitting (học thuộc lòng data)

**Embedding size = 10:**
- ✅ Cân bằng giữa capacity và efficiency
- ✅ Đủ để học patterns phức tạp
- ✅ Không quá tốn memory
- ✅ Training nhanh

#### 3.3.2. Thực nghiệm

Trong thực tế, embedding size thường được chọn dựa trên:
- **Dataset size**: Dataset lớn → có thể dùng embedding lớn hơn
- **Feature complexity**: Features phức tạp → cần embedding lớn hơn
- **Memory constraints**: Memory hạn chế → dùng embedding nhỏ hơn

**Với dataset hotel (600 users, 800 items):**
- Embedding size = 10 là hợp lý
- Đủ để học patterns
- Không quá tốn memory

### 3.4. Embedding được học như thế nào?

**Quan trọng:** Embedding **KHÔNG được thiết kế thủ công**, mà được **model tự học** trong quá trình training!

**Quá trình:**
1. **Khởi tạo ngẫu nhiên:**
   ```python
   # Xavier initialization (phân phối chuẩn)
   embedding_table.weight.data ~ Normal(0, 0.1)
   ```

2. **Training:**
   - Model dự đoán → so sánh với label → tính loss
   - Backpropagation → tính gradients
   - Update embedding weights → embeddings thay đổi

3. **Hội tụ:**
   - Sau nhiều epochs, embeddings sẽ có ý nghĩa
   - Similar categories sẽ có embeddings gần nhau
   - Different categories sẽ có embeddings xa nhau

**Ví dụ sau training:**
```
# Trước training (ngẫu nhiên):
Hanoi: [0.1, 0.3, -0.2, 0.5, ...]
Ho Chi Minh: [0.2, 0.1, 0.4, -0.1, ...]
Da Nang: [0.15, 0.25, 0.1, 0.2, ...]

# Sau training (có ý nghĩa):
Hanoi: [0.8, 0.2, -0.1, 0.3, ...]      # Gần với Da Nang (cùng miền Bắc)
Ho Chi Minh: [0.1, 0.9, 0.2, -0.5, ...] # Khác với Hanoi (miền Nam)
Da Nang: [0.7, 0.3, 0.0, 0.2, ...]     # Gần với Hanoi (cùng miền Bắc)
```

**Lưu ý:** Chúng ta không biết chính xác mỗi dimension có ý nghĩa gì, nhưng model đã học được mối quan hệ!

---

## 4. FEATURE ENCODING - CHI TIẾT TỪNG LOẠI FEATURE

### 4.1. TOKEN Fields (Categorical - 1 giá trị)

#### 4.1.1. Ví dụ: gender, region, user_id, item_id

**Input:**
```
gender = "M"
region = "Hanoi"
```

**Quy trình:**

**Bước 1: Vocabulary lookup**
```python
gender_vocab = {"M": 0, "F": 1}
region_vocab = {"Hanoi": 0, "Ho Chi Minh": 1, "Da Nang": 2, ...}

gender_index = gender_vocab["M"]  # = 0
region_index = region_vocab["Hanoi"]  # = 0
```

**Bước 2: Embedding lookup**
```python
# Embedding table cho gender (vocab_size=2, embedding_size=10)
gender_embedding_table = nn.Embedding(2, 10)

# Embedding table cho region (vocab_size=10, embedding_size=10)
region_embedding_table = nn.Embedding(10, 10)

# Lookup
gender_embedding = gender_embedding_table(0)  # [10]
region_embedding = region_embedding_table(0)  # [10]
```

**Output:**
```
gender_embedding = [0.1, 0.3, -0.2, 0.5, 0.2, -0.1, 0.4, 0.0, -0.3, 0.1]
region_embedding = [0.2, 0.1, 0.4, -0.1, 0.3, 0.2, -0.2, 0.1, 0.0, 0.3]
```

**Shape:** `[embedding_size]` = `[10]`

### 4.2. TOKEN_SEQ Fields (Categorical - nhiều giá trị)

#### 4.2.1. Ví dụ: style, city

**Input:**
```
style = "Quiet Love"  # 2 tokens: "Quiet", "Love"
city = "Hanoi"        # 1 token: "Hanoi"
```

**Quy trình:**

**Bước 1: Tokenize**
```python
style_tokens = ["Quiet", "Love"]
city_tokens = ["Hanoi"]
```

**Bước 2: Vocabulary lookup cho mỗi token**
```python
style_vocab = {"Quiet": 0, "Love": 1, "Modern": 2, "Romantic": 3, ...}
city_vocab = {"Hanoi": 0, "Ho Chi Minh": 1, ...}

style_indices = [style_vocab["Quiet"], style_vocab["Love"]]  # [0, 1]
city_indices = [city_vocab["Hanoi"]]  # [0]
```

**Bước 3: Embedding lookup cho mỗi token**
```python
style_embedding_table = nn.Embedding(vocab_size, 10)

# Lookup cho mỗi token
style_embeddings = [
    style_embedding_table(0),  # "Quiet" → [10]
    style_embedding_table(1)   # "Love" → [10]
]
# Shape: [seq_len=2, embedding_size=10]
```

**Bước 4: Pooling (trung bình)**
```python
# Mean pooling: lấy trung bình của tất cả token embeddings
style_embedding = mean(style_embeddings)  # [10]

# Hoặc sum pooling, max pooling
```

**Output:**
```
style_embedding = [0.15, 0.2, 0.1, 0.3, ...]  # [10] - trung bình của "Quiet" và "Love"
city_embedding = [0.2, 0.1, 0.4, -0.1, ...]  # [10]
```

**Shape:** `[embedding_size]` = `[10]`

**Tại sao dùng pooling?**
- Sequence có thể có độ dài khác nhau (1 token, 2 tokens, 3 tokens, ...)
- Cần convert về cùng 1 vector có độ dài cố định (10)
- Mean pooling: giữ được thông tin của tất cả tokens

### 4.3. FLOAT Fields (Numerical - 1 giá trị)

#### 4.3.1. Ví dụ: age, price, star, score

**Input:**
```
age = 32.0
price = 3724000.0
star = 4.0
score = 9.7
```

**Vấn đề:** Numerical values không thể lookup trực tiếp trong embedding table!

**Giải pháp:** **Weighted Embedding (FLEmbedding)**

#### 4.3.2. Quy trình FLEmbedding (Chi tiết)

**Bước 1: Discretization (Chia thành bins)**

RecBole tự động chia giá trị numerical thành các bins dựa trên phân phối dữ liệu.

**Cách chia bins:**

RecBole sử dụng **quantile-based discretization** (chia dựa trên phân vị):

```python
# Ví dụ với age (có 600 users, giá trị từ 18-60):
# Chia thành 10 bins dựa trên quantiles:

# Tính quantiles:
quantiles = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
values_at_quantiles = [18, 22, 24, 26, 28, 30, 32, 35, 40, 50, 60]

# Tạo bins:
bins = [
    [18, 22),   # Bin 0: 10% users (18-22 tuổi)
    [22, 24),   # Bin 1: 10% users (22-24 tuổi)
    [24, 26),   # Bin 2: 10% users (24-26 tuổi)
    [26, 28),   # Bin 3: 10% users (26-28 tuổi)
    [28, 30),   # Bin 4: 10% users (28-30 tuổi)
    [30, 32),   # Bin 5: 10% users (30-32 tuổi)
    [32, 35),   # Bin 6: 10% users (32-35 tuổi)  ← age=32.0 thuộc bin này
    [35, 40),   # Bin 7: 10% users (35-40 tuổi)
    [40, 50),   # Bin 8: 10% users (40-50 tuổi)
    [50, 60]    # Bin 9: 10% users (50-60 tuổi)
]

# age = 32.0 → thuộc bin 6
bin_index = 6
```

**Tại sao dùng quantile-based?**
- Đảm bảo mỗi bin có số lượng samples tương đương
- Tránh bins quá rỗng hoặc quá đầy
- Phù hợp với phân phối không đều

**Bước 2: Tính base và index**

RecBole lưu float value dưới dạng `[base, index]`:
- `base`: Giá trị gốc (normalized hoặc giữ nguyên)
- `index`: Bin index (0-9)

```python
# age = 32.0, bin = [32, 35)
bin_start = 32
bin_end = 35
value = 32.0

# Tính base (normalized trong bin):
base = (value - bin_start) / (bin_end - bin_start)
     = (32.0 - 32.0) / (35.0 - 32.0)
     = 0.0 / 3.0
     = 0.0

# Nếu value = 33.5:
base = (33.5 - 32.0) / (35.0 - 32.0)
     = 1.5 / 3.0
     = 0.5

# index = bin_index = 6
index = 6
```

**Lưu ý:** Trong code thực tế, `base` có thể là giá trị gốc (không normalize), tùy vào config.

**Bước 3: Embedding lookup**

```python
# Embedding table cho age (num_bins=10, embedding_size=10)
age_embedding_table = nn.Embedding(10, 10)

# Lookup bin index
age_embedding = age_embedding_table(6)  # [10]
# = [0.1, 0.3, -0.2, 0.5, 0.2, -0.1, 0.4, 0.0, -0.3, 0.1]
```

**Bước 4: Weighted embedding**

```python
# Final embedding = base × embedding
# base = 0.0 (age=32.0 ở đầu bin)
age_final_embedding = base × age_embedding
                   = 0.0 × [0.1, 0.3, -0.2, ...]
                   = [0.0, 0.0, 0.0, ...]

# Nếu age = 33.5 (giữa bin):
base = 0.5
age_final_embedding = 0.5 × [0.1, 0.3, -0.2, ...]
                   = [0.05, 0.15, -0.1, ...]
```

**Output:**
```
age_embedding = [0.0, 0.0, 0.0, ...]  # [10] (nếu ở đầu bin)
# hoặc
age_embedding = [0.05, 0.15, -0.1, ...]  # [10] (nếu ở giữa bin)
```

**Shape:** `[embedding_size]` = `[10]`

**Tại sao dùng weighted embedding?**
- ✅ Giữ được thông tin chính xác của giá trị numerical
- ✅ Không mất thông tin như one-hot encoding
- ✅ Có thể học được mối quan hệ giữa các giá trị gần nhau
- ✅ Smooth interpolation giữa các bins

**Ví dụ minh họa:**

```
age = 32.0 (đầu bin [32, 35)):
  base = 0.0
  embedding = 0.0 × emb[6] = [0, 0, 0, ...]

age = 33.5 (giữa bin [32, 35)):
  base = 0.5
  embedding = 0.5 × emb[6] = [0.05, 0.15, -0.1, ...]

age = 34.9 (cuối bin [32, 35)):
  base = 0.967
  embedding = 0.967 × emb[6] = [0.097, 0.29, -0.19, ...]

→ Giá trị gần nhau → embeddings gần nhau ✅
```

### 4.4. Tổng hợp Embeddings

Sau khi encode tất cả features, ta có:

```python
# User features (từ hotel.user):
user_id_embedding = [10]      # TOKEN
age_embedding = [10]          # FLOAT (weighted)
gender_embedding = [10]       # TOKEN
region_embedding = [10]       # TOKEN

# Item features (từ hotel.item):
item_id_embedding = [10]      # TOKEN
style_embedding = [10]        # TOKEN_SEQ (pooled)
price_embedding = [10]        # FLOAT (weighted)
star_embedding = [10]         # FLOAT (weighted)
score_embedding = [10]        # FLOAT (weighted)
city_embedding = [10]         # TOKEN_SEQ (pooled)
```

**Tất cả đều có shape `[10]`** → có thể concat hoặc tương tác với nhau!

### 4.5. Cách các Features từ các File khác nhau được Join

#### 4.5.1. Quy trình Join

**Bước 1: Load từng file**

```python
# Load hotel.user
user_df = pd.read_csv("hotel.user", sep='\t')
# user_df: [user_id, age, gender, region]

# Load hotel.item
item_df = pd.read_csv("hotel.item", sep='\t')
# item_df: [item_id, style, price, star, score, city]

# Load hotel.inter
inter_df = pd.read_csv("hotel.inter", sep='\t')
# inter_df: [user_id, item_id, action_type, timestamp]
```

**Bước 2: Join với Interactions**

RecBole join features với interactions dựa trên `user_id` và `item_id`:

```python
# Với mỗi interaction (user_id, item_id):
interaction = {
    "user_id": 1,
    "item_id": 211
}

# Join user features:
user_features = user_df[user_df['user_id'] == 1]
# → age=32.0, gender="F", region="Hanoi"

# Join item features:
item_features = item_df[item_df['item_id'] == 211]
# → style="Romantic", price=2.5M, star=4.0, score=9.7, city="Hanoi"

# Kết hợp:
combined = {
    "user_id": 1,
    "age": 32.0,
    "gender": "F",
    "region": "Hanoi",
    "item_id": 211,
    "style": "Romantic",
    "price": 2500000.0,
    "star": 4.0,
    "score": 9.7,
    "city": "Hanoi",
    "label": 0.5  # từ hotel.inter
}
```

**Bước 3: Encode và Embed**

Tất cả features được encode và embed như đã giải thích ở trên.

#### 4.5.2. Tại sao cần Join?

**Lý do:**
- `hotel.inter` chỉ có `user_id` và `item_id` (không có features)
- Cần features từ `hotel.user` và `hotel.item` để model học
- Join để kết hợp tất cả thông tin thành 1 sample

**Ví dụ:**

```
Interaction: user_id=1, item_id=211, label=0.5

Sau khi join:
- User features: age=32, gender="F", region="Hanoi"
- Item features: style="Romantic", price=2.5M, star=4.0
- Label: 0.5

→ Model học: "Nữ 32 tuổi ở Hanoi thích hotels romantic giá 2.5M, star 4.0"
```

#### 4.5.3. Feature Interaction giữa các Files

**Các interactions có thể xảy ra:**

1. **User × Item interactions:**
   - `user_id × item_id`: User cụ thể thích item cụ thể
   - `age × price`: Tuổi ảnh hưởng đến preference về giá
   - `gender × style`: Giới tính ảnh hưởng đến preference về style
   - `region × city`: Region ảnh hưởng đến preference về city

2. **User × User interactions:**
   - `age × gender`: Tuổi và giới tính tương tác
   - `age × region`: Tuổi và region tương tác

3. **Item × Item interactions:**
   - `price × star`: Giá và số sao tương tác
   - `style × city`: Style và city tương tác

**Ví dụ cụ thể:**

```
# Interaction: age × price
age_emb = [0.1, 0.2, 0.0, 0.3, ...]      # từ hotel.user
price_emb = [0.2, 0.1, 0.4, -0.1, ...]   # từ hotel.item

# FM interaction:
age_price_interaction = ⟨age_emb, price_emb⟩ × age × price
                      = 0.15 × 32.0 × 2.5M
                      = 12.0M

# Model học: "Tuổi 32 thích giá 2.5M" → interaction mạnh
```

**Tất cả interactions này được học tự động** bởi FM và DNN components!

---

## 5. FEATURE INTERACTION - CÁCH CÁC FEATURES TƯƠNG TÁC

### 5.1. Tại sao cần Feature Interaction?

#### 5.1.1. Vấn đề với Linear Model

Nếu chỉ dùng linear model (không có interaction):

```
score = w₀ + w₁×age + w₂×price + w₃×gender + ...
```

**Vấn đề:**
- Không thể học được patterns như: "Nữ thích hotels có style romantic"
- Không thể học được: "Tuổi < 30 thích giá < 1.6M"
- Chỉ học được linear relationships

#### 5.1.2. Giải pháp: Feature Interaction

**Feature interaction** là cách model học mối quan hệ giữa các features:

- **2nd order interaction:** age × price, gender × style
- **High-order interaction:** age × price × star, gender × style × city

### 5.2. Factorization Machine (FM) - 2nd Order Interactions

#### 5.2.1. Công thức FM

```
y_FM = w₀ + Σᵢ wᵢxᵢ + Σᵢ Σⱼ>ᵢ ⟨vᵢ, vⱼ⟩ xᵢxⱼ
```

**Giải thích:**
- `w₀`: Bias term
- `Σᵢ wᵢxᵢ`: Linear terms (không có interaction)
- `Σᵢ Σⱼ>ᵢ ⟨vᵢ, vⱼ⟩ xᵢxⱼ`: **2nd order interactions**

#### 5.2.2. Inner Product ⟨vᵢ, vⱼ⟩

**Inner product (tích vô hướng)** giữa 2 embedding vectors:

```python
# Ví dụ: gender × style interaction
gender_embedding = [0.1, 0.3, -0.2, 0.5, 0.2, -0.1, 0.4, 0.0, -0.3, 0.1]
style_embedding = [0.2, 0.1, 0.4, -0.1, 0.3, 0.2, -0.2, 0.1, 0.0, 0.3]

# Inner product = sum of element-wise multiplication
inner_product = sum(gender_embedding[i] × style_embedding[i] for i in range(10))
              = 0.1×0.2 + 0.3×0.1 + (-0.2)×0.4 + 0.5×(-0.1) + 0.2×0.3 + (-0.1)×0.2 + 0.4×(-0.2) + 0.0×0.1 + (-0.3)×0.0 + 0.1×0.3
              = 0.02 + 0.03 + (-0.08) + (-0.05) + 0.06 + (-0.02) + (-0.08) + 0.0 + 0.0 + 0.03
              = -0.09
```

**Công thức toán học:**

```
⟨vᵢ, vⱼ⟩ = Σₖ vᵢₖ × vⱼₖ
```

**Trong đó:**
- `vᵢₖ`: Phần tử thứ k của embedding vector vᵢ
- `vⱼₖ`: Phần tử thứ k của embedding vector vⱼ
- `k`: Từ 1 đến embedding_size (10)

**Ý nghĩa:**
- Nếu 2 embeddings giống nhau → inner product cao → interaction mạnh
- Nếu 2 embeddings khác nhau → inner product thấp → interaction yếu
- Inner product có thể âm → interaction tiêu cực (features không hợp nhau)

**Ví dụ minh họa:**

```
# Case 1: Embeddings giống nhau
v₁ = [0.5, 0.5, 0.5, ...]
v₂ = [0.5, 0.5, 0.5, ...]
⟨v₁, v₂⟩ = 0.5² + 0.5² + ... = 2.5 (cao) ✅

# Case 2: Embeddings khác nhau
v₁ = [0.5, 0.5, 0.5, ...]
v₂ = [-0.5, -0.5, -0.5, ...]
⟨v₁, v₂⟩ = 0.5×(-0.5) + 0.5×(-0.5) + ... = -2.5 (thấp, âm) ❌

# Case 3: Embeddings trực giao (orthogonal)
v₁ = [1, 0, 0, ...]
v₂ = [0, 1, 0, ...]
⟨v₁, v₂⟩ = 1×0 + 0×1 + 0×0 + ... = 0 (không có interaction)
```

#### 5.2.3. Công thức FM tối ưu (Optimized Formula)

**Công thức gốc (chậm):**

```
y_FM = Σᵢ Σⱼ>ᵢ ⟨vᵢ, vⱼ⟩ xᵢxⱼ
```

**Vấn đề:** Tính O(n²) interactions → chậm với n lớn

**Công thức tối ưu (nhanh):**

RecBole sử dụng công thức tối ưu từ paper:

```
y_FM = 0.5 × [(Σᵢ vᵢxᵢ)² - Σᵢ (vᵢxᵢ)²]
```

**Chứng minh:**

```
(Σᵢ vᵢxᵢ)² = Σᵢ (vᵢxᵢ)² + 2 × Σᵢ Σⱼ>ᵢ (vᵢxᵢ)(vⱼxⱼ)

→ Σᵢ Σⱼ>ᵢ (vᵢxᵢ)(vⱼxⱼ) = 0.5 × [(Σᵢ vᵢxᵢ)² - Σᵢ (vᵢxᵢ)²]
```

**Ví dụ tính toán:**

```python
# Giả sử có 3 features:
v₁x₁ = [0.1, 0.2, 0.3]  # embedding × value
v₂x₂ = [0.2, 0.1, 0.4]
v₃x₃ = [0.1, 0.3, 0.2]

# Công thức tối ưu:
sum_emb = v₁x₁ + v₂x₂ + v₃x₃
        = [0.4, 0.6, 0.9]

square_of_sum = sum_emb²
               = [0.16, 0.36, 0.81]
               → sum = 1.33

sum_of_square = (v₁x₁)² + (v₂x₂)² + (v₃x₃)²
              = [0.01+0.04+0.01, 0.04+0.01+0.09, 0.09+0.16+0.04]
              = [0.06, 0.14, 0.29]
              → sum = 0.49

y_FM = 0.5 × (1.33 - 0.49)
     = 0.5 × 0.84
     = 0.42
```

**Ưu điểm:**
- ✅ Tính O(n) thay vì O(n²) → nhanh hơn nhiều
- ✅ Kết quả giống hệt công thức gốc
- ✅ Dễ implement với vectorized operations

#### 5.2.3. Ví dụ tính toán FM

**Input:**
```
user: age=32, gender="F", region="Hanoi"
item: price=2.5M, style="Romantic", star=4.0
```

**Embeddings:**
```
age_emb = [0.1, 0.2, 0.0, 0.3, ...]      # [10]
gender_emb = [0.2, 0.1, 0.3, -0.1, ...]  # [10]
region_emb = [0.3, 0.0, 0.2, 0.1, ...]   # [10]
price_emb = [0.1, 0.3, -0.2, 0.2, ...]   # [10]
style_emb = [0.2, 0.2, 0.1, 0.0, ...]    # [10]
star_emb = [0.0, 0.1, 0.2, 0.3, ...]     # [10]
```

**Tính interactions:**

```python
# Linear terms:
linear = w₀ + w₁×age + w₂×gender + w₃×region + w₄×price + w₅×style + w₆×star

# 2nd order interactions:
interactions = [
    ⟨age_emb, gender_emb⟩ × age × gender,
    ⟨age_emb, price_emb⟩ × age × price,
    ⟨gender_emb, style_emb⟩ × gender × style,  # ← Quan trọng!
    ⟨region_emb, city_emb⟩ × region × city,
    ...
]

# Ví dụ: gender × style interaction
gender_style_interaction = inner_product(gender_emb, style_emb) × gender × style
                         = 0.15 × 1.0 × 1.0  # (giả sử gender="F"=1.0, style="Romantic"=1.0)
                         = 0.15
```

**Output FM:**
```
y_FM = linear + sum(interactions)
     = 0.5 + 0.15 + 0.12 + 0.08 + ...
     = 1.2
```

### 5.3. Deep Neural Network (DNN) - High-Order Interactions

#### 5.3.1. Công thức DNN

```
y_DNN = MLP(concat([e₁, e₂, ..., eₙ]))
```

**Giải thích:**
- `concat`: Nối tất cả embeddings thành 1 vector dài
- `MLP`: Multi-Layer Perceptron (mạng nơ-ron nhiều lớp)

#### 5.3.2. Concat Embeddings

```python
# Tất cả embeddings (mỗi cái [10]):
embeddings = [
    age_emb,      # [10]
    gender_emb,   # [10]
    region_emb,   # [10]
    price_emb,    # [10]
    style_emb,    # [10]
    star_emb,     # [10]
    score_emb,    # [10]
    city_emb      # [10]
]

# Concat:
concat_emb = concat(embeddings)  # [80] = 8 features × 10 dimensions
```

**Shape:** `[num_features × embedding_size]` = `[8 × 10]` = `[80]`

#### 5.3.3. MLP Layers

```python
# Input: [80]
# Hidden layer 1: [64]
# Hidden layer 2: [64]
# Hidden layer 3: [64]
# Output: [1]

mlp = MLPLayers(
    size_list=[80, 64, 64, 64, 1],
    dropout_prob=0.0
)

# Forward pass:
h1 = ReLU(W₁ × concat_emb + b₁)  # [80] → [64]
h2 = ReLU(W₂ × h1 + b₂)           # [64] → [64]
h3 = ReLU(W₃ × h2 + b₃)           # [64] → [64]
y_DNN = W₄ × h3 + b₄              # [64] → [1]
```

**Tại sao DNN học được high-order interactions?**

**Ví dụ:**
- Layer 1 có thể học: age × price, gender × style
- Layer 2 có thể học: (age × price) × star, (gender × style) × city
- Layer 3 có thể học: ((age × price) × star) × score

→ **DNN tự động học interactions bậc cao** mà không cần thiết kế thủ công!

### 5.4. Kết hợp FM và DNN

```
y = y_FM + y_DNN
```

**Tại sao kết hợp?**
- **FM**: Học 2nd order interactions hiệu quả (ít parameters)
- **DNN**: Học high-order interactions (nhiều parameters, phức tạp hơn)
- **Kết hợp**: Tận dụng ưu điểm của cả hai!

---

## 6. FORWARD PASS - QUÁ TRÌNH DỰ ĐOÁN

### 6.1. Quy trình Forward Pass

**Input:** Interaction object (user + item features)  
**Output:** Score (0-1, xác suất user thích item)

```
┌─────────────────────────────────────────────────────────┐
│ INPUT: Interaction                                       │
│   user_id=1, age=32, gender="F", region="Hanoi"        │
│   item_id=211, price=2.5M, style="Romantic", star=4.0   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Embed Input Fields                             │
│   - user_id → embedding [10]                            │
│   - age → weighted embedding [10]                       │
│   - gender → embedding [10]                             │
│   - region → embedding [10]                             │
│   - item_id → embedding [10]                            │
│   - price → weighted embedding [10]                     │
│   - style → pooled embedding [10]                       │
│   - star → weighted embedding [10]                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Concat All Embeddings                          │
│   all_embeddings = [batch_size, num_fields, embed_dim]  │
│   = [1, 8, 10]                                          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 3: FM Component                                    │
│   y_FM = first_order_linear + FM(all_embeddings)        │
│   = 0.5 + 0.7 = 1.2                                     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 4: DNN Component                                   │
│   concat_emb = flatten(all_embeddings)  # [80]         │
│   y_DNN = MLP(concat_emb)  # [1]                        │
│   = 0.3                                                 │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 5: Combine                                        │
│   y = y_FM + y_DNN = 1.2 + 0.3 = 1.5                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ STEP 6: Sigmoid                                        │
│   y_final = sigmoid(1.5) = 1/(1+e^(-1.5)) = 0.82       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ OUTPUT: Score = 0.82 (82% xác suất user thích item)   │
└─────────────────────────────────────────────────────────┘
```

### 6.2. Code Implementation

```python
def forward(self, interaction):
    # Step 1: Embed all input fields
    all_embeddings = self.concat_embed_input_fields(interaction)
    # Shape: [batch_size, num_fields, embed_dim] = [1, 8, 10]
    
    batch_size = all_embeddings.shape[0]
    
    # Step 2: FM Component
    y_fm = self.first_order_linear(interaction) + self.fm(all_embeddings)
    # y_fm shape: [batch_size] = [1]
    
    # Step 3: DNN Component
    concat_emb = all_embeddings.view(batch_size, -1)
    # Shape: [batch_size, num_fields × embed_dim] = [1, 80]
    
    y_deep = self.deep_predict_layer(
        self.mlp_layers(concat_emb)
    )
    # y_deep shape: [batch_size, 1] = [1, 1]
    
    # Step 4: Combine
    y = y_fm + y_deep.squeeze(-1)
    # y shape: [batch_size] = [1]
    
    return y  # Raw score (chưa sigmoid)
```

---

## 7. BACKWARD PASS - QUÁ TRÌNH HỌC

### 7.1. Loss Function

**Binary Cross-Entropy Loss:**

```
Loss = -[y_true × log(y_pred) + (1 - y_true) × log(1 - y_pred)]
```

**Ví dụ:**
- `y_true = 1.0` (user thực sự thích)
- `y_pred = 0.82` (model dự đoán)

```
Loss = -[1.0 × log(0.82) + 0 × log(0.18)]
     = -log(0.82)
     = 0.198
```

**Nếu dự đoán sai:**
- `y_true = 1.0`
- `y_pred = 0.2` (dự đoán sai)

```
Loss = -log(0.2) = 1.609  (cao hơn nhiều!)
```

### 7.2. Gradient Calculation

**Gradient** đo lường "độ dốc" của loss function tại mỗi weight:

```
gradient = ∂Loss/∂weight
```

**Ý nghĩa:**
- Gradient > 0: Tăng weight → loss tăng → cần giảm weight
- Gradient < 0: Tăng weight → loss giảm → cần tăng weight
- Gradient = 0: Đã tối ưu (local minimum)

**Backpropagation** tính gradients cho tất cả weights từ output → input:

```
Loss → Output Layer → Hidden Layer 3 → Hidden Layer 2 → Hidden Layer 1 → Embeddings
```

### 7.3. Weight Update (Gradient Descent)

**Công thức:**

```
weight_new = weight_old - learning_rate × gradient
```

**Ví dụ:**
- `weight = 0.5`
- `gradient = 0.3`
- `learning_rate = 0.001`

```
weight_new = 0.5 - 0.001 × 0.3
           = 0.5 - 0.0003
           = 0.4997
```

**Tại sao trừ?**
- Gradient > 0 → loss tăng khi weight tăng → cần giảm weight
- Gradient < 0 → loss giảm khi weight tăng → cần tăng weight

### 7.4. Ví dụ Backward Pass

**Scenario:**
- Prediction: `y_pred = 0.82`
- Label: `y_true = 1.0`
- Loss: `0.198`

**Quy trình:**

**Step 1: Calculate loss gradient**
```
∂Loss/∂y_pred = -(y_true/y_pred - (1-y_true)/(1-y_pred))
              = -(1.0/0.82 - 0/0.18)
              = -1.22
```

**Step 2: Backpropagate through sigmoid**
```
∂y_pred/∂y = y_pred × (1 - y_pred)
           = 0.82 × 0.18
           = 0.148

∂Loss/∂y = ∂Loss/∂y_pred × ∂y_pred/∂y
         = -1.22 × 0.148
         = -0.181
```

**Step 3: Backpropagate through DNN**
```
# Output layer
∂Loss/∂W₄ = ∂Loss/∂y × h₃
           = -0.181 × h₃

# Hidden layer 3
∂Loss/∂W₃ = ∂Loss/∂h₃ × h₂
           = ...

# ... (tương tự cho các layers khác)
```

**Step 4: Backpropagate through embeddings**
```
# Embedding gradients
∂Loss/∂embedding = ∂Loss/∂y × ∂y/∂embedding
                 = -0.181 × (gradients từ FM + DNN)
```

**Step 5: Update weights**
```python
for weight, gradient in zip(weights, gradients):
    weight = weight - learning_rate × gradient
```

---

## 8. TRAINING LOOP - VÒNG LẶP TRAINING

### 8.1. Epoch

**1 Epoch** = 1 lần duyệt qua toàn bộ dataset

**Ví dụ:**
- Dataset có 10,000 interactions
- Batch size = 256
- Số batches = 10,000 / 256 = 40 batches

→ 1 epoch = 40 training steps

### 8.2. Training Step

**1 Training Step** = xử lý 1 batch

```python
for epoch in range(num_epochs):  # 300 epochs
    for batch in dataloader:      # 40 batches/epoch
        # Forward pass
        predictions = model(batch)
        
        # Calculate loss
        loss = loss_function(predictions, batch['label'])
        
        # Backward pass
        loss.backward()
        
        # Update weights
        optimizer.step()
        optimizer.zero_grad()
```

### 8.3. Early Stopping

**Mục đích:** Dừng training sớm nếu model không cải thiện

**Quy trình:**
1. Sau mỗi epoch, evaluate trên validation set
2. Tính RMSE
3. Nếu RMSE không cải thiện trong `stopping_step` epochs → dừng

**Ví dụ:**
- Epoch 50: RMSE = 0.85
- Epoch 51: RMSE = 0.86 (tệ hơn)
- Epoch 52: RMSE = 0.87 (tệ hơn)
- ...
- Epoch 60: RMSE = 0.88 (vẫn tệ hơn)
- → Dừng training (đã 10 epochs không cải thiện)

---

## 9. GRADIENT DESCENT - CÁCH MODEL CẬP NHẬT

### 9.1. Gradient Descent là gì?

**Gradient Descent** là thuật toán tối ưu để tìm minimum của loss function.

**Tưởng tượng:**
- Loss function như một ngọn núi
- Model đang ở một điểm trên núi
- Gradient chỉ hướng xuống dốc nhất
- Model đi theo hướng đó để xuống thung lũng (minimum)

### 9.2. Learning Rate

**Learning rate** (tốc độ học) quyết định bước đi lớn hay nhỏ:

**Learning rate quá nhỏ (0.0001):**
- ✅ Ổn định, không bị overshoot
- ❌ Học chậm, cần nhiều epochs
- ❌ Có thể bị kẹt ở local minimum

**Learning rate quá lớn (0.1):**
- ✅ Học nhanh
- ❌ Không ổn định, có thể overshoot minimum
- ❌ Loss có thể tăng thay vì giảm

**Learning rate = 0.001:**
- ✅ Cân bằng giữa tốc độ và ổn định
- ✅ Phù hợp cho DeepFM

### 9.3. Batch Gradient Descent vs Stochastic Gradient Descent

**Batch Gradient Descent:**
- Dùng toàn bộ dataset để tính gradient
- ✅ Gradient chính xác
- ❌ Chậm (phải xử lý toàn bộ data)

**Stochastic Gradient Descent (SGD):**
- Dùng 1 sample để tính gradient
- ✅ Nhanh
- ❌ Gradient không chính xác (nhiều noise)

**Mini-batch Gradient Descent (dùng trong hệ thống):**
- Dùng batch nhỏ (256 samples)
- ✅ Cân bằng giữa tốc độ và độ chính xác
- ✅ Phù hợp cho deep learning

---

## 10. LOSS FUNCTION - ĐO LƯỜNG LỖI

### 10.1. Binary Cross-Entropy Loss

**Công thức:**

```
BCE_Loss = -[y_true × log(y_pred) + (1 - y_true) × log(1 - y_pred)]
```

**Đồ thị:**

```
Loss
 2.0 |     ●
     |    ●
 1.5 |   ●
     |  ●
 1.0 | ●
     |●
 0.5 |●
     |●
 0.0 |●________________
     0.0  0.2  0.4  0.6  0.8  1.0  y_pred
     (y_true = 1.0)
```

**Đặc điểm:**
- Khi `y_pred → 0` và `y_true = 1`: Loss → ∞ (rất lớn)
- Khi `y_pred → 1` và `y_true = 1`: Loss → 0 (rất nhỏ)
- Penalty lớn cho predictions sai nhiều

### 10.2. Tại sao dùng BCE Loss?

**Lý do:**
1. **Phù hợp với binary classification:** Output là xác suất (0-1)
2. **Penalty lớn cho errors:** Khuyến khích model dự đoán chính xác
3. **Differentiable:** Có thể tính gradient dễ dàng
4. **Stable:** Không bị numerical instability

---

## 11. VÍ DỤ TRAINING STEP-BY-STEP

### 11.1. Scenario

**Training sample từ dataset:**
```
Interaction (từ hotel.inter):
  user_id=1, item_id=211, action_type=0.5, timestamp=1714496742

User features (từ hotel.user):
  user_id=1, age=32.0, gender="F", region="Hanoi"

Item features (từ hotel.item):
  item_id=211, style="Romantic", price=2500000.0, star=4.0, score=9.7, city="Hanoi"

Label: 0.5 (user đã like)
```

### 11.2. Step-by-Step Chi tiết

#### Step 1: Load và Parse Data

```python
# Parse từ 3 files:

# 1. hotel.user
user_df = pd.read_csv("hotel.user", sep='\t')
user_row = user_df[user_df['user_id'] == 1]
# → age=32.0, gender="F", region="Hanoi"

# 2. hotel.item
item_df = pd.read_csv("hotel.item", sep='\t')
item_row = item_df[item_df['item_id'] == 211]
# → style="Romantic", price=2500000.0, star=4.0, score=9.7, city="Hanoi"

# 3. hotel.inter
inter_row = {"user_id": 1, "item_id": 211, "action_type": 0.5}
label = 0.5
```

#### Step 2: Build Vocabulary

```python
# RecBole tự động build vocabulary khi load dataset:

# Gender vocabulary:
gender_vocab = {
    "M": 0,
    "F": 1
}
gender_vocab_size = 2

# Region vocabulary:
region_vocab = {
    "Hanoi": 0,
    "Ho Chi Minh": 1,
    "Da Nang": 2,
    ...
}
region_vocab_size = 10

# Style vocabulary:
style_vocab = {
    "Quiet": 0,
    "Love": 1,
    "Modern": 2,
    "Romantic": 3,
    ...
}
style_vocab_size = 20
```

#### Step 3: Encode Features

```python
# Encode user features:
user_id_encoded = 1  # Giữ nguyên
age_encoded = 32.0    # Giữ nguyên
gender_encoded = gender_vocab["F"]  # = 1
region_encoded = region_vocab["Hanoi"]  # = 0

# Encode item features:
item_id_encoded = 211  # Giữ nguyên
style_encoded = [style_vocab["Romantic"]]  # = [3]
price_encoded = 2500000.0  # Giữ nguyên
star_encoded = 4.0  # Giữ nguyên
score_encoded = 9.7  # Giữ nguyên
city_encoded = [city_vocab["Hanoi"]]  # = [0]

# Create Interaction tensor:
interaction = {
    "user_id": torch.LongTensor([1]),
    "age": torch.FloatTensor([32.0]),
    "gender": torch.LongTensor([1]),
    "region": torch.LongTensor([0]),
    "item_id": torch.LongTensor([211]),
    "style": torch.LongTensor([[3]]),  # Sequence
    "price": torch.FloatTensor([2500000.0]),
    "star": torch.FloatTensor([4.0]),
    "score": torch.FloatTensor([9.7]),
    "city": torch.LongTensor([[0]]),  # Sequence
    "label": torch.FloatTensor([0.5])
}
```

#### Step 4: Discretize Float Features

```python
# Age discretization (giả sử bins):
age_bins = [
    [18, 22), [22, 24), [24, 26), [26, 28), [28, 30),
    [30, 32), [32, 35), [35, 40), [40, 50), [50, 60]
]
# age = 32.0 → bin 6 [32, 35)
age_bin_index = 6
age_base = (32.0 - 32.0) / (35.0 - 32.0) = 0.0

# Price discretization:
price_bins = [
    [0, 1M), [1M, 1.5M), [1.5M, 2M), [2M, 2.5M), [2.5M, 3M),
    [3M, 4M), [4M, 5M), [5M, 7M), [7M, 9M), [9M, 10M]
]
# price = 2.5M → bin 4 [2.5M, 3M)
price_bin_index = 4
price_base = (2.5M - 2.5M) / (3M - 2.5M) = 0.0

# Star discretization:
star_bins = [
    [0, 1), [1, 2), [2, 3), [3, 3.5), [3.5, 4),
    [4, 4.5), [4.5, 5), [5, 5), [5, 5), [5, 5]
]
# star = 4.0 → bin 5 [4, 4.5)
star_bin_index = 5
star_base = (4.0 - 4.0) / (4.5 - 4.0) = 0.0
```

#### Step 5: Embed Features

```python
# Token embeddings (lookup trong embedding table):

# User features:
user_id_emb = token_embedding_table(user_id_offset + 1)  # [10]
# = [0.1, 0.2, -0.1, 0.3, 0.0, 0.1, -0.2, 0.2, 0.1, -0.1]

gender_emb = token_embedding_table(gender_offset + 1)  # [10]
# = [0.2, 0.1, 0.3, -0.1, 0.2, 0.0, 0.1, -0.2, 0.3, 0.1]

region_emb = token_embedding_table(region_offset + 0)  # [10]
# = [0.3, 0.0, 0.2, 0.1, -0.1, 0.2, 0.0, 0.1, -0.1, 0.2]

# Item features:
item_id_emb = token_embedding_table(item_id_offset + 211)  # [10]
# = [0.1, 0.3, -0.2, 0.2, 0.1, -0.1, 0.3, 0.0, -0.2, 0.1]

style_emb = mean([
    token_seq_embedding_table(style_vocab["Romantic"])  # [10]
])
# = [0.25, 0.15, 0.1, 0.0, 0.2, -0.1, 0.15, 0.1, 0.0, 0.2]

city_emb = mean([
    token_seq_embedding_table(city_vocab["Hanoi"])  # [10]
])
# = [0.2, 0.1, 0.4, -0.1, 0.3, 0.2, -0.2, 0.1, 0.0, 0.3]

# Float embeddings (weighted):
age_emb = age_base × float_embedding_table(age_offset + 6)
       = 0.0 × [0.1, 0.2, 0.0, 0.3, ...]
       = [0.0, 0.0, 0.0, 0.0, ...]  # [10]

price_emb = price_base × float_embedding_table(price_offset + 4)
          = 0.0 × [0.2, 0.1, 0.4, -0.1, ...]
          = [0.0, 0.0, 0.0, 0.0, ...]  # [10]

star_emb = star_base × float_embedding_table(star_offset + 5)
         = 0.0 × [0.0, 0.2, 0.3, 0.1, ...]
         = [0.0, 0.0, 0.0, 0.0, ...]  # [10]

score_emb = score_base × float_embedding_table(score_offset + 9)
          = 0.7 × [0.1, 0.3, 0.2, 0.0, ...]
          = [0.07, 0.21, 0.14, 0.0, ...]  # [10]
```

**Lưu ý:** Vì age, price, star đều ở đầu bin nên base=0.0 → embedding = [0, 0, ...]. Đây là trường hợp đặc biệt.

#### Step 6: Concat All Embeddings

```python
# Tất cả embeddings (mỗi cái [10]):
all_embeddings = torch.stack([
    user_id_emb,   # [10]
    age_emb,       # [10]
    gender_emb,    # [10]
    region_emb,    # [10]
    item_id_emb,   # [10]
    style_emb,     # [10]
    price_emb,     # [10]
    star_emb,      # [10]
    score_emb,     # [10]
    city_emb       # [10]
], dim=0)

# Shape: [num_fields=10, embedding_size=10] = [10, 10]
```

#### Step 7: FM Component

```python
# First-order linear terms:
first_order = w₀ + w₁×user_id + w₂×age + w₃×gender + ...
            = 0.1 + 0.05×1 + 0.02×32.0 + 0.03×1 + ...
            = 0.1 + 0.05 + 0.64 + 0.03 + ...
            = 0.82

# FM interactions (dùng công thức tối ưu):
# sum_emb = Σᵢ vᵢxᵢ (sum của tất cả embeddings)
sum_emb = user_id_emb + age_emb + gender_emb + ... + city_emb
        = [0.1+0.0+0.2+0.3+0.1+0.25+0.0+0.0+0.07+0.2, ...]
        = [1.22, 1.35, 0.8, 0.6, ...]  # [10]

square_of_sum = sum_emb²
               = [1.4884, 1.8225, 0.64, 0.36, ...]  # [10]
               → sum = 4.31

sum_of_square = (user_id_emb)² + (age_emb)² + ... + (city_emb)²
              = [0.01+0.0+0.04+0.09+0.01+0.0625+0.0+0.0+0.0049+0.04, ...]
              = [0.2564, 0.1825, 0.16, 0.04, ...]  # [10]
              → sum = 0.64

fm_interactions = 0.5 × (square_of_sum - sum_of_square)
                = 0.5 × (4.31 - 0.64)
                = 0.5 × 3.67
                = 1.835

# FM output:
y_fm = first_order + fm_interactions
     = 0.82 + 1.835
     = 2.655
```

#### Step 8: DNN Component

```python
# Flatten embeddings:
concat_emb = all_embeddings.view(-1)  # [100] = 10 fields × 10 dims

# MLP forward:
h1 = ReLU(W₁ × concat_emb + b₁)  # [100] → [64]
    = ReLU([...])  # [64]

h2 = ReLU(W₂ × h1 + b₂)  # [64] → [64]
    = ReLU([...])  # [64]

h3 = ReLU(W₃ × h2 + b₃)  # [64] → [64]
    = ReLU([...])  # [64]

y_deep = W₄ × h3 + b₄  # [64] → [1]
       = 0.4
```

#### Step 9: Combine và Sigmoid

```python
# Combine:
y = y_fm + y_deep
  = 2.655 + 0.4
  = 3.055

# Sigmoid:
y_pred = sigmoid(3.055)
       = 1 / (1 + exp(-3.055))
       = 1 / (1 + 0.047)
       = 1 / 1.047
       = 0.955
```

#### Step 10: Calculate Loss

```python
# BCE Loss:
y_true = 0.5
y_pred = 0.955

loss = -[y_true × log(y_pred) + (1 - y_true) × log(1 - y_pred)]
     = -[0.5 × log(0.955) + 0.5 × log(0.045)]
     = -[0.5 × (-0.046) + 0.5 × (-3.101)]
     = -[-0.023 - 1.551]
     = 1.574
```

**Loss cao** → Model dự đoán quá cao (0.955) so với label (0.5) → Cần điều chỉnh!

#### Step 11: Backward Pass

```python
# Calculate gradients:
loss.backward()

# Gradients cho embeddings:
# ∂Loss/∂embedding = ∂Loss/∂y_pred × ∂y_pred/∂y × ∂y/∂embedding

# Ví dụ với gender_embedding:
grad_gender = -1.574 × 0.955×(1-0.955) × (gradients từ FM + DNN)
            = -1.574 × 0.043 × 0.5
            = -0.034

# Gradient âm → cần tăng embedding để giảm loss
```

#### Step 12: Update Weights

```python
# Gradient Descent:
learning_rate = 0.001

# Update gender embedding:
gender_emb_old = [0.2, 0.1, 0.3, -0.1, ...]
grad_gender = [-0.034, 0.012, -0.021, 0.008, ...]

gender_emb_new = gender_emb_old - learning_rate × grad_gender
               = [0.2, 0.1, 0.3, -0.1, ...] - 0.001 × [-0.034, 0.012, -0.021, 0.008, ...]
               = [0.200034, 0.099988, 0.300021, -0.100008, ...]

# Tương tự cho tất cả weights
```

#### Step 13: Repeat

Lặp lại cho:
- Tất cả samples trong batch (256 samples)
- Tất cả batches trong epoch (~40 batches)
- Tất cả epochs (300 epochs hoặc early stopping)

**Sau nhiều iterations, model sẽ học được:**
- Embeddings có ý nghĩa
- Patterns: "Nữ thích romantic", "Tuổi < 30 thích giá < 1.6M"
- Interactions giữa các features

---

## 12. CÂU HỎI THƯỜNG GẶP

### Q1: Tại sao không dùng one-hot encoding thay vì embedding?

**A:** 
- One-hot encoding: Sparse, tốn memory, không học được relationships
- Embedding: Dense, tiết kiệm memory, học được relationships, tự động học ý nghĩa

### Q2: Tại sao embedding size = 10, không phải 5 hay 20?

**A:**
- Size quá nhỏ: Không đủ capacity
- Size quá lớn: Tốn memory, dễ overfitting
- Size = 10: Cân bằng, phù hợp với dataset size

### Q3: Model học được gì từ embeddings?

**A:**
- Similarity: Categories giống nhau → embeddings gần nhau
- Relationships: Categories có quan hệ → embeddings có patterns
- Patterns: Model tự phát hiện patterns mà con người không thấy

### Q4: Tại sao cần cả FM và DNN?

**A:**
- FM: Học 2nd order interactions hiệu quả (ít parameters)
- DNN: Học high-order interactions (nhiều parameters)
- Kết hợp: Tận dụng ưu điểm cả hai

### Q5: Training mất bao lâu?

**A:**
- Dataset: ~10,000 interactions
- Epochs: 300 (hoặc early stopping)
- Batch size: 256
- Thời gian: ~30-60 phút (tùy hardware)

### Q6: Làm sao biết model đã học tốt?

**A:**
- Metrics: RMSE, MAE trên validation set
- Early stopping: Dừng khi không cải thiện
- Overfitting: Kiểm tra gap giữa train và validation loss

### Q7: Tại sao dùng BCE Loss thay vì MSE Loss?

**A:**
- BCE: Phù hợp với binary classification, penalty lớn cho errors
- MSE: Phù hợp với regression, penalty nhỏ hơn
- Recommendation là classification (user thích/không thích) → dùng BCE

### Q8: Gradient Descent có thể bị kẹt ở local minimum không?

**A:**
- Có thể, nhưng với deep learning thường không phải vấn đề lớn
- Local minima trong high-dimensional space thường không tệ lắm
- Có thể dùng techniques như momentum, Adam optimizer để tránh

### Q9: Tại sao cần normalize numerical features?

**A:**
- Features có scale khác nhau (age: 18-60, price: 0-10M)
- Model sẽ ưu tiên features có scale lớn hơn
- Normalize để tất cả features có cùng scale

### Q10: Model có thể học được patterns phức tạp như "Nữ tuổi 25-30 ở Hanoi thích hotels romantic giá 1-2M" không?

**A:**
- Có! Đây là high-order interaction (5 features: gender × age × region × style × price)
- DNN component sẽ học được pattern này qua các hidden layers
- Cần đủ data và training time
- Pattern này được học tự động, không cần thiết kế thủ công

### Q11: Tại sao cần discretize float features thay vì dùng trực tiếp?

**A:**
- Embedding table chỉ nhận integer indices (0, 1, 2, ...)
- Float values (32.0, 2.5M) không thể lookup trực tiếp
- Discretization: Chia thành bins → có integer index
- Weighted embedding: Giữ thông tin chính xác của giá trị

### Q12: Tại sao dùng công thức FM tối ưu thay vì tính trực tiếp?

**A:**
- Công thức gốc: O(n²) → chậm với n lớn
- Công thức tối ưu: O(n) → nhanh hơn nhiều
- Kết quả giống hệt nhau
- Dễ implement với vectorized operations

### Q13: Làm sao biết model đã học được patterns?

**A:**
- Kiểm tra embeddings: Similar categories → embeddings gần nhau
- Kiểm tra interactions: Features có quan hệ → interactions mạnh
- Kiểm tra accuracy: Model dự đoán chính xác → đã học được patterns
- Visualization: T-SNE để visualize embeddings

### Q14: Tại sao cần cả user features và item features?

**A:**
- User features: Mô tả user (age, gender, region)
- Item features: Mô tả item (style, price, star)
- Interactions: User × Item → học được preferences
- Chỉ có user_id và item_id → không đủ thông tin để học patterns

### Q15: Model học được gì từ mỗi dimension trong embedding?

**A:**
- **Không thể giải thích chính xác** mỗi dimension có ý nghĩa gì
- Model tự học ý nghĩa trong quá trình training
- Có thể là: "Dimension 0 = luxury level", "Dimension 1 = price sensitivity", ...
- Quan trọng là **tổng thể**: Similar items → similar embeddings

### Q16: Tại sao cần normalize numerical features?

**A:**
- Features có scale khác nhau: age (18-60), price (0-10M)
- Model sẽ ưu tiên features có scale lớn hơn
- Normalize để tất cả features có cùng scale (0-1 hoặc -1 to 1)
- Đảm bảo model học công bằng từ tất cả features

### Q17: Làm sao model biết được "Nữ thích romantic" mà không phải "Nam thích romantic"?

**A:**
- Model học từ data: Nếu nhiều nữ thích hotels romantic → học được pattern
- Embeddings tự điều chỉnh: gender="F" và style="romantic" → embeddings gần nhau
- FM interaction: ⟨gender_emb, style_emb⟩ cao cho nữ + romantic
- DNN: Học được high-order patterns phức tạp hơn

### Q18: Tại sao cần nhiều epochs?

**A:**
- 1 epoch: Model mới học được một phần
- Nhiều epochs: Model học được patterns phức tạp hơn
- Early stopping: Dừng khi không cải thiện
- 300 epochs: Đảm bảo model học đủ, nhưng có thể dừng sớm nếu hội tụ

### Q19: Model có thể học được patterns mới không có trong training data?

**A:**
- **Không trực tiếp**, nhưng có thể **suy luận**:
  - Nếu học được "Nữ thích romantic" và "Tuổi < 30 thích giá < 1.6M"
  - Có thể suy luận: "Nữ tuổi < 30 thích romantic giá < 1.6M"
- DNN component học được high-order interactions → có thể suy luận
- Nhưng cần đủ data để học được các patterns cơ bản trước

### Q20: Tại sao cần cả FM và DNN, không chỉ dùng một trong hai?

**A:**
- **FM**: Học 2nd order interactions hiệu quả (ít parameters, nhanh)
- **DNN**: Học high-order interactions (nhiều parameters, chậm hơn)
- **Kết hợp**: Tận dụng ưu điểm cả hai
- **Thực nghiệm**: DeepFM tốt hơn chỉ dùng FM hoặc chỉ dùng DNN

---

## KẾT LUẬN

Tài liệu này đã phân tích chi tiết quá trình training của AI Recommendation, bao gồm:

1. ✅ **Xử lý Dataset**: Từ raw data đến tensors
2. ✅ **Embedding**: Tại sao và như thế nào
3. ✅ **Feature Encoding**: Chi tiết từng loại feature
4. ✅ **Feature Interaction**: Cách features tương tác
5. ✅ **Forward Pass**: Quá trình dự đoán
6. ✅ **Backward Pass**: Quá trình học
7. ✅ **Training Loop**: Vòng lặp training
8. ✅ **Gradient Descent**: Cách model cập nhật
9. ✅ **Loss Function**: Đo lường lỗi
10. ✅ **Ví dụ Step-by-Step**: Minh họa cụ thể

**Lưu ý:** Tài liệu này giải thích bản chất của training process. Để hiểu sâu hơn, nên thực hành với code và thử nghiệm với các hyperparameters khác nhau.

---

**Tác giả:** AI Development Team  
**Ngày:** 2025-01-16  
**Phiên bản:** 1.0

