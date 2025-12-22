# PHƯƠNG ÁN CỤ THỂ CẢI THIỆN DATASET

**Ngày tạo:** 2025-12-13  
**Mục tiêu:** Cải thiện dataset để model học được patterns rõ ràng cho Phase 1

---

## 1. HIỂU RÕ VỀ PHASE 1 VÀ PHASE 2

### 1.1. Phase 1: Kiểm Tra Đúng Pattern
- **Mục tiêu:** Recommendations phải match với patterns (Gender → Style, Age → Price, Region → City)
- **Logic:** Test đang làm ĐÚNG - kiểm tra patterns
- **Vấn đề:** Dataset không đủ để model học được patterns

### 1.2. Phase 2: Cá Nhân Hóa Theo User Mong Muốn
- **Mục tiêu:** Recommendations phù hợp với sở thích cá nhân của user
- **Logic:** Dựa trên Phase 1 + boost Phase 2 (similarity boost)
- **Không ảnh hưởng:** Phase 2 không liên quan đến việc cải thiện dataset cho Phase 1

---

## 2. PHƯƠNG ÁN 1: TĂNG STYLE BIAS (Gender → Style)

### 2.1. Mục Tiêu

**Hiện tại:**
- Chênh lệch lớn nhất: 3.6% (Romantic: Nữ 27.8% vs Nam 24.2%)
- Chênh lệch trung bình: 2.2%

**Mục tiêu:**
- Chênh lệch tối thiểu: **≥ 15%**
- Chênh lệch lý tưởng: **≥ 20%**

### 2.2. Phân Bố Mục Tiêu

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

### 2.3. Cách Thực Hiện

**Bước 1: Phân tích interactions hiện tại**
- Đếm số interactions của mỗi gender với mỗi style
- Tính số interactions cần thêm/bớt

**Bước 2: Điều chỉnh interactions**
- **Tăng interactions:**
  - Nữ: Tăng interactions với items có style Romantic, Love
  - Nam: Tăng interactions với items có style Modern, Lively
- **Giảm interactions:**
  - Nữ: Giảm interactions với items có style Modern, Lively
  - Nam: Giảm interactions với items có style Romantic, Love

**Bước 3: Tạo interactions mới (nếu cần)**
- Nếu không đủ items để tăng interactions → Tạo interactions mới
- Đảm bảo items có style phù hợp với gender

---

## 3. PHƯƠNG ÁN 2: TĂNG AGE → PRICE CORRELATION

### 3.1. Mục Tiêu

**Hiện tại:**
- < 30 tuổi: Mean price = 1,742,301 VND
- ≥ 30 tuổi: Mean price = 1,938,342 VND
- Chênh lệch: 10.1%

**Mục tiêu:**
- Chênh lệch: **≥ 20%**

### 3.2. Phân Tích Age Distribution

**Hiện tại:**
- Mean age: 29.58
- Min: 22, Max: 41
- Users < 30: ~300 users (50%)
- Users ≥ 30: ~300 users (50%)

### 3.3. Phân Tích Price Distribution

**Hiện tại:**
- Mean price: 1,510,609 VND
- Min: 9,213 VND, Max: 17,010,000 VND
- 25%: 744,322 VND
- 50%: 1,150,280 VND
- 75%: 1,866,493 VND

**Đề xuất phân loại:**
- **Giá rẻ:** < 1,200,000 VND (≈ 1.2M)
- **Giá trung bình:** 1,200,000 - 2,000,000 VND
- **Giá cao:** ≥ 2,000,000 VND (≈ 2M)

### 3.4. Mục Tiêu Phân Bố

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

### 3.5. Cách Thực Hiện

**Bước 1: Phân tích interactions hiện tại**
- Đếm số interactions của mỗi age group với mỗi price range
- Tính số interactions cần thêm/bớt

**Bước 2: Điều chỉnh interactions**
- **Users < 30:**
  - Tăng interactions với items có price < 1.2M
  - Giảm interactions với items có price ≥ 2M
- **Users ≥ 30:**
  - Tăng interactions với items có price ≥ 2M
  - Giảm interactions với items có price < 1.2M

**Bước 3: Tạo interactions mới (nếu cần)**
- Nếu không đủ items → Tạo interactions mới
- Đảm bảo items có price phù hợp với age group

---

## 4. PHƯƠNG ÁN 3: MỞ RỘNG CITIES (Region → City)

### 4.1. Danh Sách Cities Mới

**8 cities:**
1. Hà Nội (Hanoi)
2. Đà Nẵng (DaNang)
3. Hồ Chí Minh (HoChiMinh)
4. Nha Trang (NhaTrang)
5. Huế (Hue)
6. Hải Phòng (HaiPhong)
7. Đà Lạt (DaLat)
8. Phú Quốc (PhuQuoc)

### 4.2. Đề Xuất Số Lượng Hotels Cho Mỗi City

**Nguyên tắc:**
- Tổng số hotels: **800**
- Phân bố dựa trên:
  - Tầm quan trọng của city (tourism, business)
  - Số lượng users ở mỗi region
  - Đảm bảo đủ diversity

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
- Đảm bảo mỗi city có đủ hotels với các style khác nhau

### 4.3. Đề Xuất Phân Bố Users

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

### 4.4. Mục Tiêu Match Rate

**Hiện tại:**
- Match rate: 57.4% (chỉ có 2 cities)

**Mục tiêu:**
- Match rate: **≥ 80%** (với 8 cities)
- Mỗi user ở region X → ≥ 80% recommendations có city X

### 4.5. Cách Thực Hiện

**Bước 1: Tạo items mới cho 6 cities mới**
- Tạo hotels cho: HoChiMinh, NhaTrang, Hue, HaiPhong, DaLat, PhuQuoc
- Đảm bảo đủ số lượng theo đề xuất
- Đảm bảo đủ diversity về style, price, star, score

**Bước 2: Điều chỉnh items hiện tại**
- Giữ lại items ở Hanoi và DaNang
- Có thể điều chỉnh số lượng nếu cần

**Bước 3: Tạo users mới cho 6 regions mới**
- Tạo users cho: HoChiMinh, NhaTrang, Hue, HaiPhong, DaLat, PhuQuoc
- Đảm bảo đủ số lượng theo đề xuất
- Đảm bảo đủ diversity về age, gender

**Bước 4: Điều chỉnh users hiện tại**
- Giữ lại users ở Hanoi và DaNang
- Có thể điều chỉnh số lượng nếu cần

**Bước 5: Tạo interactions mới**
- Users ở region X → Tăng interactions với items ở city X
- Đảm bảo match rate ≥ 80%

---

## 5. SCRIPT THỰC HIỆN

### 5.1. Script Tổng Hợp

Tạo script `improve_dataset.py` để thực hiện tất cả các cải thiện:

```python
# improve_dataset.py
import pandas as pd
import numpy as np
import random
from typing import Dict, List, Tuple

def improve_dataset():
    """
    Cải thiện dataset theo 3 phương án:
    1. Tăng Style Bias (Gender → Style)
    2. Tăng Age → Price Correlation
    3. Mở rộng Cities (Region → City)
    """
    
    # Load datasets
    user_df = pd.read_csv('dataset/hotel/hotel.user', sep='\t')
    item_df = pd.read_csv('dataset/hotel/hotel.item', sep='\t')
    inter_df = pd.read_csv('dataset/hotel/hotel.inter', sep='\t')
    
    # Fix column names
    user_df.columns = [col.split(':')[0] for col in user_df.columns]
    item_df.columns = [col.split(':')[0] for col in item_df.columns]
    inter_df.columns = [col.split(':')[0] for col in inter_df.columns]
    
    # 1. Tăng Style Bias
    inter_df = improve_style_bias(inter_df, user_df, item_df)
    
    # 2. Tăng Age → Price Correlation
    inter_df = improve_age_price_correlation(inter_df, user_df, item_df)
    
    # 3. Mở rộng Cities
    user_df, item_df, inter_df = expand_cities(user_df, item_df, inter_df)
    
    # Save datasets
    save_datasets(user_df, item_df, inter_df)
    
    return user_df, item_df, inter_df

def improve_style_bias(inter_df, user_df, item_df):
    """Tăng style bias theo gender."""
    # Implementation...
    pass

def improve_age_price_correlation(inter_df, user_df, item_df):
    """Tăng age → price correlation."""
    # Implementation...
    pass

def expand_cities(user_df, item_df, inter_df):
    """Mở rộng cities từ 2 → 8."""
    # Implementation...
    pass

def save_datasets(user_df, item_df, inter_df):
    """Lưu datasets đã cải thiện."""
    # Implementation...
    pass
```

### 5.2. Script Chi Tiết

Tạo các script riêng cho từng phương án:
- `improve_style_bias.py` - Cải thiện style bias
- `improve_age_price.py` - Cải thiện age → price correlation
- `expand_cities.py` - Mở rộng cities

---

## 6. KẾ HOẠCH THỰC HIỆN

### 6.1. Thứ Tự Ưu Tiên

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

### 6.2. Kiểm Tra Sau Khi Cải Thiện

**Bước 1: Phân tích dataset mới**
- Chạy `analyze_dataset.py` để kiểm tra:
  - Style distribution by gender
  - Age → Price correlation
  - Region → City match rate

**Bước 2: Retrain model**
- Train lại model với dataset mới
- Đảm bảo model học được patterns

**Bước 3: Test Phase 1**
- Chạy `test_phase1_detailed.py` với dataset mới
- Kiểm tra accuracy có cải thiện không

---

## 7. LƯU Ý QUAN TRỌNG

### 7.1. Backup Dataset Gốc
- **QUAN TRỌNG:** Backup dataset gốc trước khi thay đổi
- Tạo thư mục `dataset/hotel_backup/` để lưu dataset gốc

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

Sau khi thực hiện 3 phương án:
1. ✅ **Style Bias:** Chênh lệch Nam/Nữ ≥ 15-20%
2. ✅ **Age → Price:** Chênh lệch ≥ 20%
3. ✅ **Region → City:** Match rate ≥ 80% với 8 cities

**Kết quả mong đợi:**
- Model học được patterns rõ ràng
- Test Phase 1 có accuracy cao hơn
- Recommendations phù hợp với patterns

---

**Tài liệu được tạo ngày 2025-12-13**

