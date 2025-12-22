# BÁO CÁO ĐÁNH GIÁ ĐỘ TIN CẬY AI PHASE 1 - BEHAVIOR BOOST

**Ngày test:** 18/12/2025 20:27:26  
**Model sử dụng:** `saved\DeepFM-Dec-16-2025_19-57-01.pth`  
**Số lượng users tested:** 100  
**Top-K recommendations:** 10  

---

## 1. THÔNG TIN TEST VÀ ĐIỀU KIỆN

### 1.1. Mục đích test

Test này được thiết kế để **đánh giá độ tin cậy và hiệu quả của AI Phase 1 (Behavior Boost)** trong việc recommend items phù hợp với user profiles dựa trên các patterns:
- Gender → Style matching
- Age → Price matching  
- Region → City matching
- Age → Star/Score matching (tùy chọn)

### 1.2. Điều kiện test

| Thông số | Giá trị | Mô tả |
|----------|---------|-------|
| **Số lượng users** | 100 | Số users được test để đảm bảo tính đại diện |
| **Top-K** | 10 | Số lượng recommendations cho mỗi user |
| **Model** | DeepFM | Model recommendation được sử dụng |
| **Behavior Boost** | Enabled | Phase 1 boost dựa trên user actions gần đây |
| **Similarity Boost** | Disabled | Phase 2 tắt để test riêng Phase 1 |
| **Valid results** | 100 | Số kết quả hợp lệ |
| **Errors** | 0 | Số lỗi trong quá trình test |

### 1.3. Tiêu chí đánh giá (Evaluation Criteria)

#### Patterns Bắt Buộc (Mandatory - Phải đạt ít nhất 2/3)

| Pattern | Điều kiện Pass | Threshold | Mô tả |
|---------|----------------|-----------|-------|
| **Gender → Style** | ≥ 30% items HOẶC ≥ 3 items | max(3, 30% × Top-K) | Items có style phù hợp với gender của user |
| **Age → Price** | ≥ 30% items HOẶC ≥ 3 items | max(3, 30% × Top-K) | Items có price phù hợp với age của user |
| **Region → City** | ≥ 20% items HOẶC ≥ 2 items | max(2, 20% × Top-K) | Items có city khớp với region của user |

#### Patterns Tùy Chọn (Optional - Bonus)

| Pattern | Điều kiện Pass | Threshold | Mô tả |
|---------|----------------|-----------|-------|
| **Age → Star (≥30)** | ≥ 30% items HOẶC ≥ 2 items | max(2, 30% × Top-K) | Items có star ≥ 3.5 cho users age ≥ 30 |
| **Age → Score (<30)** | ≥ 30% items HOẶC ≥ 2 items | max(2, 30% × Top-K) | Items có score ≥ 9.0 cho users age < 30 |

#### Điều kiện Pass tổng thể

- **Mandatory patterns**: Ít nhất **2/3 patterns bắt buộc** phải pass
- **Total score**: Tổng điểm ≥ 3.0/4.0
  - Mandatory score: 0-3 điểm (mỗi pattern = 1 điểm)
  - Optional score: 0-1 điểm (nếu pass = 1 điểm)

---

## 2. KẾT QUẢ TỔNG QUAN

### 2.1. Thống kê tổng thể

| Chỉ số | Giá trị | Ghi chú |
|--------|---------|---------|
| **Tổng số users tested** | 100 | - |
| **Valid results** | 100 | Kết quả hợp lệ để đánh giá |
| **Errors** | 0 | Lỗi trong quá trình test |
| **Passed** | 81 | Số users đạt yêu cầu |
| **Failed** | 19 | Số users không đạt yêu cầu |
| **Pass Rate** | 81.0% | Tỷ lệ users pass |
| **95% Confidence Interval** | [73.3%, 88.7%] | Khoảng tin cậy 95% cho pass rate |
| **Average Accuracy** | 83.2% | Độ chính xác trung bình (0-100%) |
| **Average Score** | 2.92/4.0 | Điểm trung bình |
| **Average Mandatory Passed** | 1.93/3.0 | Số patterns bắt buộc pass trung bình |

### 2.2. Đánh giá độ tin cậy

| Metric | Giá trị | Đánh giá |
|--------|---------|----------|
| **Pass Rate** | 81.0% | ✅ Đạt yêu cầu (≥80%) |
| **Confidence Level** | 95% | Mức độ tin cậy của kết quả |
| **Sample Size** | 100 | Kích thước mẫu đủ lớn để đánh giá |
| **Error Rate** | 0.0% | Tỷ lệ lỗi trong quá trình test |

**Kết luận sơ bộ:** ✅ Hệ thống AI Phase 1 đạt độ tin cậy cao

---

## 3. PHÂN TÍCH CHI TIẾT TỪNG PATTERN

### 3.1. Patterns Bắt Buộc (Mandatory Patterns)

| Pattern | Passed | Total | Pass Rate | 95% CI | Đánh giá | Mô tả |
|---------|--------|-------|-----------|--------|----------|-------|
| **Gender → Style** | 100 | 100 | 100.0% | [100.0%, 100.0%] | ✅ Tốt | Items có style phù hợp với gender (Nữ: Romantic/Love/Modern/Lively, Nam: Love/Romantic/Modern/Lively) |
| **Age → Price** | 79 | 100 | 79.0% | [71.0%, 87.0%] | ✅ Tốt | Items có price phù hợp với age (Age < 30: Price < 1.6M, Age >= 30: Price >= 1.2M) |
| **Region → City** | 14 | 100 | 14.0% | [7.2%, 20.8%] | ❌ Yếu | Items có city khớp với region của user |

### 3.2. Patterns Tùy Chọn (Optional Patterns)

| Pattern | Passed | Total | Pass Rate | 95% CI | Đánh giá | Mô tả |
|---------|--------|-------|-----------|--------|----------|-------|
| **Age → Star (≥30)** | 54 | 54 | 100.0% | [100.0%, 100.0%] | ✅ Tốt | Items có star >= 3.5 cho users age >= 30 |
| **Age → Score (<30)** | 45 | 46 | 97.8% | [93.6%, 100.0%] | ✅ Tốt | Items có score >= 9.0 cho users age < 30 |

---

## 4. PHÂN TÍCH THEO NHÓM USER

### 4.1. Phân tích theo Gender

| Gender | Total | Passed | Pass Rate | 95% CI | Avg Score | Avg Accuracy | Đánh giá |
|--------|-------|--------|-----------|--------|-----------|--------------|----------|
| **Nữ** | 44 | 27 | 61.4% | [47.0%, 75.8%] | 2.68/4.0 | 84.1% | ⚠️ Cần cải thiện |
| **Nam** | 56 | 54 | 96.4% | [91.6%, 100.0%] | 3.11/4.0 | 82.6% | ✅ Tốt |

### 4.2. Phân tích theo Age Group

| Age Group | Total | Passed | Pass Rate | 95% CI | Avg Score | Avg Accuracy | Đánh giá |
|-----------|-------|--------|-----------|--------|-----------|--------------|----------|
| **< 30** | 46 | 27 | 58.7% | [44.5%, 72.9%] | 2.65/4.0 | 83.7% | ❌ Yếu |
| **30-40** | 54 | 54 | 100.0% | [100.0%, 100.0%] | 3.15/4.0 | 82.9% | ✅ Tốt |

---

## 5. CHI TIẾT KẾT QUẢ THEO USER

### 5.1. Tất cả Users Failed (Cần cải thiện) - Tổng: 19 users

| STT | User ID | Gender | Age | Region | Mandatory Passed | Total Score | Accuracy | Pattern Details |
|-----|---------|--------|-----|--------|------------------|-------------|----------|----------------|
| 1 | 3 | M | 26 | Hanoi | 1/3 | 2/4 | 100.0% | ✓ ✗ ✗ |
| 2 | 7 | M | 25 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |
| 3 | 15 | F | 27 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |
| 4 | 20 | F | 29 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |
| 5 | 22 | F | 23 | Hanoi | 1/3 | 2/4 | 100.0% | ✓ ✗ ✗ |
| 6 | 23 | F | 25 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |
| 7 | 27 | F | 27 | Hanoi | 1/3 | 2/4 | 100.0% | ✓ ✗ ✗ |
| 8 | 41 | F | 26 | Hanoi | 1/3 | 2/4 | 100.0% | ✓ ✗ ✗ |
| 9 | 43 | F | 23 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |
| 10 | 60 | F | 29 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |
| 11 | 67 | F | 28 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |
| 12 | 69 | F | 25 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |
| 13 | 75 | F | 25 | Hanoi | 1/3 | 2/4 | 100.0% | ✓ ✗ ✗ |
| 14 | 79 | F | 26 | Hanoi | 1/3 | 2/4 | 100.0% | ✓ ✗ ✗ |
| 15 | 82 | F | 26 | Hanoi | 1/3 | 2/4 | 100.0% | ✓ ✗ ✗ |
| 16 | 84 | F | 29 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |
| 17 | 88 | F | 26 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |
| 18 | 93 | F | 23 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |
| 19 | 98 | F | 29 | Hanoi | 1/3 | 2/4 | 75.0% | ✓ ✗ ✗ |

### 5.2. Tất cả Users Passed (Thành công) - Tổng: 81 users

| STT | User ID | Gender | Age | Region | Mandatory Passed | Total Score | Accuracy | Pattern Details |
|-----|---------|--------|-----|--------|------------------|-------------|----------|----------------|
| 1 | 12 | M | 31 | Hanoi | 3/3 | 4/4 | 100.0% | ✓ ✓ ✓ |
| 2 | 14 | M | 32 | Hanoi | 3/3 | 4/4 | 100.0% | ✓ ✓ ✓ |
| 3 | 28 | M | 34 | Hanoi | 3/3 | 4/4 | 100.0% | ✓ ✓ ✓ |
| 4 | 38 | F | 25 | Hanoi | 3/3 | 4/4 | 100.0% | ✓ ✓ ✓ |
| 5 | 44 | M | 34 | Hanoi | 3/3 | 4/4 | 100.0% | ✓ ✓ ✓ |
| 6 | 52 | F | 28 | Hanoi | 3/3 | 4/4 | 100.0% | ✓ ✓ ✓ |
| 7 | 57 | M | 33 | Hanoi | 3/3 | 4/4 | 100.0% | ✓ ✓ ✓ |
| 8 | 64 | F | 26 | Hanoi | 3/3 | 4/4 | 100.0% | ✓ ✓ ✓ |
| 9 | 77 | M | 34 | Hanoi | 3/3 | 4/4 | 100.0% | ✓ ✓ ✓ |
| 10 | 90 | M | 37 | Hanoi | 3/3 | 4/4 | 100.0% | ✓ ✓ ✓ |
| 11 | 99 | M | 32 | Hanoi | 3/3 | 4/4 | 100.0% | ✓ ✓ ✓ |
| 12 | 1 | M | 32 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 13 | 2 | M | 35 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 14 | 4 | F | 33 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 15 | 5 | M | 36 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 16 | 6 | F | 23 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 17 | 8 | F | 26 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 18 | 9 | M | 32 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 19 | 10 | M | 37 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 20 | 11 | F | 23 | Hanoi | 3/3 | 3/4 | 100.0% | ✓ ✓ ✓ |
| 21 | 13 | F | 29 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 22 | 16 | M | 30 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 23 | 17 | F | 28 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 24 | 18 | M | 33 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 25 | 19 | F | 26 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 26 | 21 | M | 36 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 27 | 24 | M | 38 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 28 | 25 | M | 30 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 29 | 26 | F | 26 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 30 | 29 | F | 28 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✗ ✓ |
| 31 | 30 | M | 31 | DaNang | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 32 | 31 | F | 26 | DaNang | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 33 | 32 | M | 36 | DaNang | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 34 | 33 | F | 27 | DaNang | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 35 | 34 | F | 22 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 36 | 35 | M | 29 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 37 | 36 | M | 34 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 38 | 37 | M | 36 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 39 | 39 | M | 32 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 40 | 40 | M | 30 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 41 | 42 | M | 37 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 42 | 45 | M | 30 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 43 | 46 | F | 26 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 44 | 47 | M | 33 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 45 | 48 | F | 29 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 46 | 49 | M | 33 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 47 | 50 | M | 35 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 48 | 51 | M | 37 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 49 | 53 | M | 30 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 50 | 54 | M | 34 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 51 | 55 | F | 27 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 52 | 56 | M | 30 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 53 | 58 | M | 31 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 54 | 59 | M | 35 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 55 | 61 | F | 28 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 56 | 62 | M | 33 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 57 | 63 | M | 34 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 58 | 65 | M | 32 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 59 | 66 | M | 30 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 60 | 68 | M | 33 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 61 | 70 | M | 37 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 62 | 71 | F | 28 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✗ ✓ |
| 63 | 72 | M | 31 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 64 | 73 | F | 24 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 65 | 74 | M | 33 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 66 | 76 | M | 31 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 67 | 78 | M | 35 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 68 | 80 | F | 27 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 69 | 81 | M | 30 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 70 | 83 | F | 24 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 71 | 85 | F | 25 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 72 | 86 | M | 36 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 73 | 87 | M | 32 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 74 | 89 | M | 33 | Hanoi | 2/3 | 3/4 | 100.0% | ✓ ✓ ✗ |
| 75 | 91 | F | 28 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 76 | 92 | M | 30 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 77 | 94 | M | 34 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 78 | 95 | F | 27 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 79 | 96 | F | 26 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 80 | 97 | M | 35 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |
| 81 | 100 | M | 34 | Hanoi | 2/3 | 3/4 | 75.0% | ✓ ✓ ✗ |

---

## 6. ĐÁNH GIÁ ĐỘ TIN CẬY CHI TIẾT

### 6.1. Metrics Độ Tin Cậy

| Metric | Giá trị | Ngưỡng | Đánh giá |
|--------|---------|--------|----------|
| **Pass Rate** | 81.0% | 80.0% | ✅ Đạt |
| *(Tỷ lệ users pass test)* | | | |
| **Average Accuracy** | 83.2% | 70.0% | ✅ Đạt |
| *(Độ chính xác trung bình)* | | | |
| **Average Score** | 73.0% | 75.0% | ⚠️ Chưa đạt |
| *(Điểm trung bình (normalized))* | | | |
| **Mandatory Patterns Pass Rate** | 64.3% | 67.0% | ⚠️ Chưa đạt |
| *(Tỷ lệ patterns bắt buộc pass)* | | | |

### 6.2. Phân tích Độ Tin Cậy theo Pattern

| Pattern | Pass Rate | 95% CI | Độ tin cậy | Kết luận |
|---------|-----------|--------|------------|----------|
| Gender → Style | 100.0% | [100.0%, 100.0%] | Cao | ✅ Đáng tin cậy |
| Age → Price | 79.0% | [71.0%, 87.0%] | Trung bình | ✅ Đáng tin cậy |
| Region → City | 14.0% | [7.2%, 20.8%] | Cao | ❌ Không đáng tin cậy |
| Age → Star (≥30) | 100.0% | [100.0%, 100.0%] | Cao | ✅ Đáng tin cậy |
| Age → Score (<30) | 97.8% | [93.6%, 100.0%] | Cao | ✅ Đáng tin cậy |

---

## 7. KẾT LUẬN VÀ KHUYẾN NGHỊ

### 7.1. Tóm tắt Độ Tin Cậy

✅ **Hệ thống AI Phase 1 đạt độ tin cậy CAO**

- Pass rate: 81.0% (≥ 80% - Đạt yêu cầu)
- Confidence interval 95%: [73.3%, 88.7%]
- Average accuracy: 83.2%
- Hệ thống có thể được triển khai vào production với độ tin cậy cao.

### 7.2. Điểm Mạnh

- **Patterns hoạt động tốt:**
  - Gender → Style: Pass rate 100.0% (100/100)
  - Age → Price: Pass rate 79.0% (79/100)
  - Age → Star (≥30): Pass rate 100.0% (54/54)
  - Age → Score (<30): Pass rate 97.8% (45/46)

- **Average accuracy cao:** 83.2% - Hệ thống đang recommend items phù hợp với user profiles.

### 7.3. Điểm Cần Cải Thiện

- **Patterns cần cải thiện:**
  - Region → City: Pass rate 14.0% (14/100) - Cần cải thiện logic matching hoặc tăng số lượng items phù hợp trong dataset.

### 7.4. Khuyến Nghị

1. ✅ **Triển khai vào production:** Hệ thống đã đạt độ tin cậy cao, có thể triển khai.
2. 📊 **Monitor liên tục:** Theo dõi pass rate và accuracy trong production để đảm bảo chất lượng.
3. 🔄 **Retrain định kỳ:** Retrain model định kỳ với dữ liệu mới để duy trì chất lượng.
4. 📈 **Mở rộng test:** Test với nhiều users hơn để đảm bảo tính nhất quán.

---

**Báo cáo được tạo tự động vào:** 18/12/2025 20:27:36
**Bởi:** AI Test Report Generator
