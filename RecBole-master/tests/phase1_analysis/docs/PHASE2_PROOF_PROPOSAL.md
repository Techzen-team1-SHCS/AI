# ĐỀ XUẤT CHỨNG MINH PHASE 2 - SIMILARITY BOOST

## 📋 MỤC ĐÍCH

Chứng minh rằng **Phase 2 (Similarity Boost)** hoạt động đúng và có giá trị thực tế trong việc cải thiện recommendations personalized.

---

## 🎯 PHASE 2 LÀ GÌ?

### Định nghĩa

**Phase 2 (Similarity Boost):** Boost các hotels **tương tự** hotels mà user đã tương tác gần đây, dựa trên features (style, price, star, score, city).

### Công thức

```
final_boost = direct_boost + Σ(direct_boost_item × similarity_score × similarity_boost_factor)

Trong đó:
- direct_boost: Boost từ actions trực tiếp trên item (Phase 1)
- similarity_score: Similarity giữa item và items đã tương tác (0-1)
- similarity_boost_factor: Trọng số cho similarity boost (default: 0.5)
```

### So sánh với Phase 1

| Đặc điểm | Phase 1 (Basic Boost) | Phase 2 (Similarity Boost) |
|----------|----------------------|---------------------------|
| Boost gì? | Hotels đã tương tác trực tiếp | Hotels **tương tự** hotels đã tương tác |
| Giá trị thực tế | Thấp (hotels đã tương tác thường bị exclude) | **Cao** (boost hotels mới, chưa tương tác) |
| Personalized | Ít (chỉ boost hotels đã biết) | **Nhiều** (boost hotels mới dựa trên preference) |

---

## ✅ CÁCH CHỨNG MINH PHASE 2

### 1. Test Case Cơ Bản

#### Scenario:
- User click một hotel cụ thể (ví dụ: hotel có style="romantic", city="Hanoi", price=2.8M)
- So sánh recommendations với/không có similarity boost

#### Steps:
1. **Ghi action vào log:**
   ```python
   # User 123 click hotel 50 (style="romantic", city="Hanoi", price=2.8M)
   write_test_action(user_id="123", item_id="50", action_type="click")
   ```

2. **Test Phase 1 only (không có similarity boost):**
   ```python
   recs_phase1 = get_recommendations(
       user_id="123",
       use_behavior_boost=True,
       use_similarity_boost=False  # Phase 1 only
   )
   ```

3. **Test Phase 1 + Phase 2 (có similarity boost):**
   ```python
   recs_phase2 = get_recommendations(
       user_id="123",
       use_behavior_boost=True,
       use_similarity_boost=True  # Phase 2 enabled
   )
   ```

4. **Phân tích kết quả:**
   - So sánh `recs_phase1` vs `recs_phase2`
   - Xác định items mới xuất hiện trong `recs_phase2`
   - Kiểm tra items mới có features tương tự hotel đã click không

#### Expected Results:
- ✅ Items mới xuất hiện trong `recs_phase2` có similarity cao với hotel đã click
- ✅ Items có cùng style/city/price range được boost lên
- ✅ Recommendations thay đổi (không giống Phase 1)

---

### 2. Test Case Chi Tiết: Phân Tích Similarity

#### Mục đích:
Chứng minh similarity được tính đúng và items tương tự được boost đúng cách.

#### Steps:
1. **Chọn hotel để click:**
   - Hotel A: style="romantic", city="Hanoi", price=2.8M, star=4.5, score=9.0

2. **Tìm hotels tương tự trong dataset:**
   - Hotel B: style="romantic", city="Hanoi", price=2.5M (similarity cao)
   - Hotel C: style="romantic", city="HoChiMinh", price=2.8M (similarity trung bình)
   - Hotel D: style="modern", city="Hanoi", price=2.8M (similarity thấp)

3. **Ghi action và test:**
   ```python
   write_test_action(user_id="123", item_id="A", action_type="click")
   recs_phase2 = get_recommendations(user_id="123", use_similarity_boost=True)
   ```

4. **Kiểm tra:**
   - ✅ Hotel B xuất hiện trong `recs_phase2` (similarity cao)
   - ✅ Hotel C có thể xuất hiện (similarity trung bình)
   - ✅ Hotel D không xuất hiện hoặc rank thấp (similarity thấp)

#### Expected Similarity Scores:
```
Hotel A vs Hotel B: similarity ≈ 0.85 (cùng style + city, price gần)
Hotel A vs Hotel C: similarity ≈ 0.65 (cùng style, city khác, price gần)
Hotel A vs Hotel D: similarity ≈ 0.40 (style khác, cùng city, price gần)
```

---

### 3. Test Case Nâng Cao: Multiple Items

#### Scenario:
User click nhiều hotels khác nhau → Kiểm tra similarity boost tổng hợp.

#### Steps:
1. **Click nhiều hotels:**
   ```python
   # User click 3 hotels khác nhau
   write_test_action(user_id="123", item_id="50", action_type="click")  # romantic, Hanoi
   write_test_action(user_id="123", item_id="100", action_type="click") # modern, HoChiMinh
   write_test_action(user_id="123", item_id="150", action_type="like")  # luxury, DaNang
   ```

2. **Test recommendations:**
   ```python
   recs_phase2 = get_recommendations(user_id="123", use_similarity_boost=True)
   ```

3. **Phân tích:**
   - Items tương tự hotel 50 (romantic, Hanoi) được boost
   - Items tương tự hotel 100 (modern, HoChiMinh) được boost
   - Items tương tự hotel 150 (luxury, DaNang) được boost
   - Items tương tự nhiều hotels được boost cao hơn (cộng dồn)

---

### 4. Metrics để Đánh Giá

#### Metrics Chính:

1. **Similarity Score Distribution:**
   - Tính similarity giữa clicked hotel và các items trong recommendations
   - Expected: Items trong recommendations có similarity >= threshold (0.5)

2. **Feature Match Rate:**
   - % items có cùng style với clicked hotel
   - % items có cùng city với clicked hotel
   - % items có price range tương tự (±30%)

3. **Recommendation Change Rate:**
   - Số lượng items mới xuất hiện (Phase 2 vs Phase 1)
   - Thay đổi thứ hạng của items

4. **Personalization Score:**
   - So sánh recommendations giữa 2 users khác nhau (click hotels khác nhau)
   - Expected: Recommendations khác nhau đáng kể

---

## 🔧 SCRIPT TEST ĐÃ TẠO

### `test_phase2_similarity.py`

Script test Phase 2 chi tiết với các chức năng:

1. **Tự động test:**
   ```bash
   python test_phase2_similarity.py --auto
   ```

2. **Test với user và items cụ thể:**
   ```bash
   python test_phase2_similarity.py --user-id 123 --item-id 50
   ```

3. **Test với nhiều items:**
   ```bash
   python test_phase2_similarity.py --user-id 123 --item-id 50,51,52
   ```

4. **Tùy chỉnh parameters:**
   ```bash
   python test_phase2_similarity.py --user-id 123 --item-id 50 --similarity-threshold 0.6 --top-k 30
   ```

### Output của Script:

- ✅ Thông tin hotels đã click
- ✅ Recommendations Phase 1 vs Phase 2
- ✅ Items được boost do similarity
- ✅ Similarity scores và features comparison
- ✅ Thống kê và kết luận

---

## 📊 BẢNG KẾT QUẢ MONG ĐỢI

| Test Case | Phase 1 Results | Phase 2 Results | Chứng Minh |
|-----------|----------------|-----------------|------------|
| **Click 1 hotel** | Recommendations giống baseline | Items tương tự xuất hiện | ✅ Similarity boost hoạt động |
| **Similarity scores** | N/A | Scores >= threshold | ✅ Similarity được tính đúng |
| **Feature match** | Ngẫu nhiên | Style/city/price match cao | ✅ Boost dựa trên features |
| **Multiple clicks** | Boost hotels đã click | Boost hotels tương tự nhiều | ✅ Similarity tổng hợp |

---

## 🎯 ĐIỀU KIỆN ĐẠT (Pass Criteria)

### Phase 2 được coi là hoạt động đúng nếu:

1. **Functional:**
   - ✅ Recommendations thay đổi khi bật similarity boost
   - ✅ Items mới xuất hiện trong recommendations
   - ✅ Items mới có similarity >= threshold với clicked hotels

2. **Quality:**
   - ✅ Items tương tự có features phù hợp (style/city/price)
   - ✅ Similarity scores hợp lý (0.5-1.0 cho items tương tự)
   - ✅ Recommendations personalized hơn (khác nhau giữa users)

3. **Performance:**
   - ✅ Latency chấp nhận được (< 2 giây cho similarity calculation)
   - ✅ Similarity matrix được cache đúng cách

---

## 📝 KẾ HOẠCH THỰC HIỆN

### Step 1: Test Cơ Bản
- [x] Tạo script `test_phase2_similarity.py`
- [ ] Chạy test với 1 user và 1 hotel
- [ ] Xác nhận items tương tự xuất hiện

### Step 2: Test Chi Tiết
- [ ] Chạy test với nhiều hotels khác nhau
- [ ] Phân tích similarity scores
- [ ] So sánh features (style/city/price)

### Step 3: Test Nâng Cao
- [ ] Test với multiple users
- [ ] Đo personalization score
- [ ] Đo performance (latency)

### Step 4: Tổng Hợp Kết Quả
- [ ] Viết báo cáo kết quả
- [ ] Đề xuất cải thiện (nếu có)
- [ ] Document best practices

---

## 💡 GỢI Ý CẢI THIỆN

### Nếu Test Fail:

1. **Không có items mới xuất hiện:**
   - Giảm `similarity_threshold` (từ 0.5 → 0.3)
   - Tăng `similarity_boost_factor` (từ 0.5 → 0.7)
   - Kiểm tra similarity calculation logic

2. **Similarity scores quá thấp:**
   - Kiểm tra feature extraction (style, city, price)
   - Điều chỉnh weights trong similarity calculation
   - Xem lại normalization cho price/star/score

3. **Performance chậm:**
   - Đảm bảo similarity matrix được cache
   - Tối ưu similarity calculation (vectorize)
   - Giảm số lượng items được tính similarity

---

## 📚 TÀI LIỆU THAM KHẢO

- `SYSTEM_FUTURE_PLAN.md`: Mô tả Phase 2 implementation
- `IMPLEMENTATION_SUMMARY.md`: Chi tiết implementation
- `inference.py`: Code Phase 2 (functions `calculate_item_similarity`, `calculate_behavior_boost_with_similarity`)


