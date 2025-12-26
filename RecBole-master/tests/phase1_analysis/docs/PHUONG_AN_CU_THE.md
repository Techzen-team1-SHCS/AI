# PHƯƠNG ÁN CỤ THỂ CẢI THIỆN DATASET

**Ngày tạo:** 2025-12-13  
**Mục tiêu:** Cải thiện dataset để model học được patterns rõ ràng cho Phase 1

---

## 📋 TÓM TẮT

Bạn đã đồng thuận 3 phương án cải thiện dataset:

1. ✅ **Tăng Style Bias (Gender → Style)** - Từ COMPREHENSIVE_ANALYSIS_REPORT.md (281-284)
2. ✅ **Tăng Age → Price Correlation** - Từ COMPREHENSIVE_ANALYSIS_REPORT.md (329-335)
3. ✅ **Mở rộng Cities** - Từ 2 cities → 8 cities

---

## 1. PHƯƠNG ÁN 1: TĂNG STYLE BIAS (Gender → Style)

### 1.1. Mục Tiêu

**Hiện tại:**
- Chênh lệch lớn nhất: **3.6%** (Romantic: Nữ 27.8% vs Nam 24.2%)
- Chênh lệch trung bình: **2.2%**

**Mục tiêu:**
- Chênh lệch tối thiểu: **≥ 15%**
- Chênh lệch lý tưởng: **≥ 20%**

### 1.2. Phân Bố Mục Tiêu

**Nữ (F):**
- Romantic: 27.8% → **45%** (+17.2%)
- Love: 24.6% → **35%** (+10.4%)
- Modern: 16.1% → **8%** (-8.1%)
- Lively: 13.3% → **5%** (-8.3%)
- Classic: 8.4% → **5%** (-3.4%)
- Quiet: 9.8% → **2%** (-7.8%)

**Nam (M):**
- Romantic: 24.2% → **15%** (-9.2%)
- Love: 24.7% → **20%** (-4.7%)
- Modern: 13.4% → **30%** (+16.6%)
- Lively: 12.8% → **25%** (+12.2%)
- Classic: 11.9% → **5%** (-6.9%)
- Quiet: 12.9% → **5%** (-7.9%)

**Chênh lệch mới:**
- Romantic: 45% vs 15% = **30%** ✅
- Modern: 8% vs 30% = **22%** ✅
- Lively: 5% vs 25% = **20%** ✅
- Love: 35% vs 20% = **15%** ✅

### 1.3. Cách Thực Hiện

**Bước 1:** Phân tích interactions hiện tại theo gender và style

**Bước 2:** Tính số interactions cần thêm/bớt để đạt phân bố mục tiêu

**Bước 3:** 
- **Tăng interactions:**
  - Nữ: Tăng với items có style Romantic, Love
  - Nam: Tăng với items có style Modern, Lively
- **Giảm interactions:**
  - Nữ: Giảm với items có style Modern, Lively
  - Nam: Giảm với items có style Romantic, Love

**Bước 4:** Tạo interactions mới nếu cần (đảm bảo không duplicate)

---

## 2. PHƯƠNG ÁN 2: TĂNG AGE → PRICE CORRELATION

### 2.1. Mục Tiêu

**Hiện tại:**
- < 30 tuổi: Mean price = 1,742,301 VND
- ≥ 30 tuổi: Mean price = 1,938,342 VND
- Chênh lệch: **10.1%**

**Mục tiêu:**
- Chênh lệch: **≥ 20%**

### 2.2. Phân Loại Price

- **Giá rẻ:** < 1,200,000 VND (≈ 1.2M)
- **Giá trung bình:** 1,200,000 - 2,000,000 VND
- **Giá cao:** ≥ 2,000,000 VND (≈ 2M)

### 2.3. Mục Tiêu Phân Bố

**Users < 30 tuổi:**
- Tăng interactions với hotels giá rẻ (< 1.2M): **60%+**
- Giảm interactions với hotels giá cao (≥ 2M): **< 20%**

**Users ≥ 30 tuổi:**
- Tăng interactions với hotels giá cao (≥ 2M): **50%+**
- Giảm interactions với hotels giá rẻ (< 1.2M): **< 30%**

**Kết quả mong đợi:**
- < 30 tuổi: Mean price ≈ **1,200,000 VND**
- ≥ 30 tuổi: Mean price ≈ **2,000,000 VND**
- Chênh lệch: **≈ 40%** ✅

### 2.4. Cách Thực Hiện

**Bước 1:** Phân tích interactions hiện tại theo age và price range

**Bước 2:** Tính số interactions cần thêm để đạt tỷ lệ mục tiêu

**Bước 3:**
- **Users < 30:** Tăng interactions với items có price < 1.2M
- **Users ≥ 30:** Tăng interactions với items có price ≥ 2M

**Bước 4:** Tạo interactions mới nếu cần

---

## 3. PHƯƠNG ÁN 3: MỞ RỘNG CITIES (Region → City)

### 3.1. Danh Sách Cities Mới

**8 cities:**
1. Hà Nội (Hanoi)
2. Đà Nẵng (DaNang)
3. Hồ Chí Minh (HoChiMinh)
4. Nha Trang (NhaTrang)
5. Huế (Hue)
6. Hải Phòng (HaiPhong)
7. Đà Lạt (DaLat)
8. Phú Quốc (PhuQuoc)

### 3.2. Đề Xuất Số Lượng Hotels Cho Mỗi City

**Nguyên tắc:**
- Tổng số hotels: ~600 (giữ nguyên hoặc tăng nhẹ)
- Phân bố dựa trên tầm quan trọng của city (tourism, business)

**Đề xuất phân bố:**

| City | Số Hotels | Tỷ lệ | Lý do |
|------|-----------|-------|-------|
| **Hà Nội** | 160 | 20% | Thủ đô, trung tâm kinh tế, nhiều users |
| **Hồ Chí Minh** | 160 | 20% | Thành phố lớn nhất, trung tâm kinh tế |
| **Đà Nẵng** | 134 | 16.7% | Thành phố du lịch lớn, hiện có nhiều users |
| **Nha Trang** | 106 | 13.3% | Thành phố du lịch biển nổi tiếng |
| **Phú Quốc** | 94 | 11.7% | Đảo du lịch cao cấp |
| **Đà Lạt** | 80 | 10% | Thành phố du lịch núi |
| **Huế** | 40 | 5% | Thành phố di sản văn hóa |
| **Hải Phòng** | 26 | 3.3% | Thành phố cảng, ít du lịch hơn |
| **Tổng** | **800** | **100%** | |

**Lưu ý:**
- Có thể tăng tổng số hotels lên 700-800 nếu cần
- Đảm bảo mỗi city có đủ hotels với các style khác nhau

### 3.3. Đề Xuất Phân Bố Users

**Nguyên tắc:**
- Phân bố users theo 8 regions tương ứng với 8 cities
- Đảm bảo đủ users cho mỗi region để test

**Đề xuất phân bố:**

| Region | Số Users | Tỷ lệ | Lý do |
|--------|----------|-------|-------|
| **Hà Nội** | 100 | 16.7% | Thủ đô, nhiều users |
| **Hồ Chí Minh** | 100 | 16.7% | Thành phố lớn nhất |
| **Đà Nẵng** | 90 | 15% | Thành phố du lịch lớn |
| **Nha Trang** | 80 | 13.3% | Thành phố du lịch biển |
| **Phú Quốc** | 70 | 11.7% | Đảo du lịch |
| **Đà Lạt** | 60 | 10% | Thành phố du lịch núi |
| **Huế** | 50 | 8.3% | Thành phố di sản |
| **Hải Phòng** | 50 | 8.3% | Thành phố cảng |
| **Tổng** | **600** | **100%** | |

### 3.4. Mục Tiêu Match Rate

**Hiện tại:**
- Match rate: **57.4%** (chỉ có 2 cities)

**Mục tiêu:**
- Match rate: **≥ 80%** (với 8 cities)
- Mỗi user ở region X → ≥ 80% recommendations có city X

### 3.5. Cách Thực Hiện

**Bước 1:** Tạo items mới cho 6 cities mới
- HoChiMinh, NhaTrang, Hue, HaiPhong, DaLat, PhuQuoc
- Đảm bảo đủ số lượng theo đề xuất
- Đảm bảo đủ diversity về style, price, star, score

**Bước 2:** Điều chỉnh items hiện tại
- Giữ lại items ở Hanoi và DaNang
- Điều chỉnh số lượng nếu cần để đạt target

**Bước 3:** Tạo users mới cho 6 regions mới
- HoChiMinh, NhaTrang, Hue, HaiPhong, DaLat, PhuQuoc
- Đảm bảo đủ số lượng theo đề xuất
- Đảm bảo đủ diversity về age, gender

**Bước 4:** Điều chỉnh users hiện tại
- Giữ lại users ở Hanoi và DaNang
- Điều chỉnh số lượng nếu cần để đạt target

**Bước 5:** Tạo interactions mới
- Users ở region X → Tăng interactions với items ở city X
- Đảm bảo match rate ≥ 80%

---

## 4. SCRIPT THỰC HIỆN

### 4.1. Script Tổng Hợp

Đã tạo script `improve_dataset.py` để thực hiện tất cả các cải thiện:

**Chức năng:**
1. ✅ Backup dataset gốc trước khi thay đổi
2. ✅ Tăng Style Bias (Gender → Style)
3. ✅ Tăng Age → Price Correlation
4. ✅ Mở rộng Cities (Region → City)
5. ✅ Lưu datasets đã cải thiện

**Cách chạy:**
```bash
cd "D:\mon hoc\CAPTONE 1\testcode\test2\RecBole-master\RecBole-master"
.\recbole-env\Scripts\Activate.ps1
python tests/phase1_analysis/improve_dataset.py
```

### 4.2. Lưu Ý Quan Trọng

**Backup:**
- Script sẽ tự động backup dataset gốc vào `dataset/hotel_backup/`
- Nếu có lỗi, có thể restore từ backup

**Format:**
- Script đảm bảo format đúng (TSV với headers)
- Đảm bảo tất cả user_id và item_id là unique
- Đảm bảo tất cả interactions có user_id và item_id hợp lệ

**Diversity:**
- Đảm bảo mỗi city có đủ hotels với các style khác nhau
- Đảm bảo mỗi city có đủ hotels với các price range khác nhau
- Đảm bảo mỗi region có đủ users với các age và gender khác nhau

---

## 5. KẾ HOẠCH THỰC HIỆN

### 5.1. Thứ Tự Ưu Tiên

**Bước 1: Mở rộng Cities (Ưu tiên cao nhất)**
- Tạo items và users mới cho 6 cities mới
- Điều chỉnh interactions để đảm bảo match rate ≥ 80%
- **Thời gian:** 2-3 giờ

**Bước 2: Tăng Style Bias**
- Điều chỉnh interactions để tăng chênh lệch Nam/Nữ
- **Thời gian:** 1-2 giờ

**Bước 3: Tăng Age → Price Correlation**
- Điều chỉnh interactions để tăng chênh lệch age groups
- **Thời gian:** 1-2 giờ

### 5.2. Kiểm Tra Sau Khi Cải Thiện

**Bước 1: Phân tích dataset mới**
```bash
python tests/phase1_analysis/analyze_dataset.py
```
- Kiểm tra Style distribution by gender
- Kiểm tra Age → Price correlation
- Kiểm tra Region → City match rate

**Bước 2: Retrain model**
- Train lại model với dataset mới
- Đảm bảo model học được patterns

**Bước 3: Test Phase 1**
```bash
python tests/phase1_analysis/test_phase1_detailed.py --num_users 50
```
- Kiểm tra accuracy có cải thiện không

---

## 6. KẾT QUẢ MONG ĐỢI

Sau khi thực hiện 3 phương án:

1. ✅ **Style Bias:** Chênh lệch Nam/Nữ ≥ 15-20%
   - Romantic: 30% chênh lệch
   - Modern: 22% chênh lệch
   - Lively: 20% chênh lệch

2. ✅ **Age → Price:** Chênh lệch ≥ 20%
   - < 30 tuổi: Mean price ≈ 1.2M
   - ≥ 30 tuổi: Mean price ≈ 2M
   - Chênh lệch: ≈ 40%

3. ✅ **Region → City:** Match rate ≥ 80% với 8 cities
   - Mỗi user ở region X → ≥ 80% recommendations có city X

**Kết quả mong đợi:**
- ✅ Model học được patterns rõ ràng
- ✅ Test Phase 1 có accuracy cao hơn
- ✅ Recommendations phù hợp với patterns

---

## 7. LƯU Ý QUAN TRỌNG

### 7.1. Backup Dataset Gốc
- **QUAN TRỌNG:** Script sẽ tự động backup dataset gốc
- Backup được lưu tại `dataset/hotel_backup/`
- Nếu có lỗi, có thể restore từ backup

### 7.2. Đảm Bảo Tính Hợp Lệ
- Đảm bảo tất cả user_id và item_id là unique
- Đảm bảo tất cả interactions có user_id và item_id hợp lệ
- Đảm bảo format của files đúng (TSV với headers)

### 7.3. Đảm Bảo Diversity
- Đảm bảo mỗi city có đủ hotels với các style khác nhau
- Đảm bảo mỗi city có đủ hotels với các price range khác nhau
- Đảm bảo mỗi region có đủ users với các age và gender khác nhau

---

## 8. KẾT LUẬN

Phương án cụ thể đã được chuẩn bị sẵn với:

1. ✅ **Phân tích chi tiết** từng phương án
2. ✅ **Script tự động** để thực hiện tất cả cải thiện
3. ✅ **Kế hoạch kiểm tra** sau khi cải thiện

**Bước tiếp theo:**
1. Xem xét phương án và số lượng hotels/users cho mỗi city
2. Chạy script `improve_dataset.py` để thực hiện cải thiện
3. Kiểm tra kết quả và retrain model

---

**Tài liệu được tạo ngày 2025-12-13**

