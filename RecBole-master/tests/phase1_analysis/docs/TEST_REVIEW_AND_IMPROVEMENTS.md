# PHÂN TÍCH VÀ ĐỀ XUẤT CẢI THIỆN TEST SCRIPTS

**Ngày:** 2025-01-14  
**Files được review:** `test_phase1_with_model.py`, `test_phase1_ultra_detailed.py`

---

## 🔍 PHÂN TÍCH VẤN ĐỀ

### 1. `test_phase1_with_model.py`

#### ❌ Vấn đề 1: Logic tính Accuracy SAI
**Location:** Dòng 170
```python
matched_patterns = sum(1 for count in pattern_counts.values() if count > 0)
accuracy = matched_patterns / len([p for p in pattern_counts.keys() if pattern_counts[p] > 0]) if matched_patterns > 0 else 0.0
```

**Vấn đề:**
- `matched_patterns` = số patterns có ít nhất 1 item match
- Mẫu số = số patterns có count > 0 (giống tử số!)
- **Kết quả:** Accuracy luôn = 1.0 nếu có ít nhất 1 pattern matched

**Ví dụ:**
- Có 5 patterns, 3 patterns có count > 0
- `matched_patterns = 3`
- Mẫu số = 3 (vì có 3 patterns với count > 0)
- Accuracy = 3/3 = 1.0 ❌ (KHÔNG ĐÚNG!)

**Đúng nên là:**
```python
# Accuracy = số patterns matched / tổng số patterns có thể áp dụng
applicable_patterns = 3  # gender_style, age_price, region_city (mandatory)
# + 1 optional pattern (age_star hoặc age_score tùy age)
max_patterns = 3 + (1 if age >= 30 or age < 30 else 0)  # = 4
accuracy = matched_patterns / max_patterns
```

#### ❌ Vấn đề 2: Không có điều kiện Pass/Fail
- Chỉ hiển thị accuracy, không có kết luận pass/fail
- Người dùng không biết kết quả test có đạt yêu cầu không

#### ❌ Vấn đề 3: Hiển thị quá đơn giản
- Không hiển thị thông tin items được recommend
- Không có chi tiết pattern analysis
- Khó debug khi test fail

---

### 2. `test_phase1_ultra_detailed.py`

#### ⚠️ Vấn đề 1: Logic Pass/Fail có thể quá strict
**Location:** Dòng 394
```python
final_passed = mandatory_passed and total_score >= 3.0
```

**Vấn đề:**
- `mandatory_passed` = True nếu TẤT CẢ 3 mandatory patterns đều có count > 0
- `total_score >= 3.0` = cần ít nhất 3 điểm (từ 4 điểm tối đa)
- **Kết quả:** Cần pass tất cả mandatory + ít nhất 1 optional pattern

**Có thể quá strict không?**
- Nếu 2/3 mandatory patterns pass → fail (mandatory_passed = False)
- Nhưng có thể acceptable nếu 2 patterns quan trọng nhất pass

**Đề xuất:**
- Nên có threshold linh hoạt hơn: 2/3 mandatory patterns pass có thể acceptable
- Hoặc có 2 mức: PASS (strict) và ACCEPTABLE (flexible)

#### ⚠️ Vấn đề 2: Logic tính điểm có thể cần cải thiện
**Location:** Dòng 376-386

**Hiện tại:**
- Mandatory patterns: Chỉ cần count > 0 (ít nhất 1 item match)
- Optional patterns: Chỉ cần count > 0

**Vấn đề:**
- Nếu chỉ có 1/10 items match pattern → vẫn pass (count > 0)
- Có thể nên yêu cầu tỷ lệ cao hơn: ví dụ ≥ 20% hoặc ≥ 2 items

**Đề xuất:**
- Mandatory patterns: ≥ 20% items match HOẶC ≥ 2 items (whichever is higher)
- Optional patterns: ≥ 30% items match HOẶC ≥ 2 items

#### ⚠️ Vấn đề 3: Region → City Matching có thể không chính xác
**Location:** Dòng 158-164

**Hiện tại:**
```python
city_tokens = set(city.split()) if city else set()
region_tokens = set(region_norm.split()) if region_norm else set()
checks['region_city'] = bool(city_tokens & region_tokens)
```

**Vấn đề:**
- "HoChiMinh" (city) vs "Ho Chi Minh" (region) → tokens = {"hochiminh"} vs {"ho", "chi", "minh"} → NO MATCH ❌
- "DaNang" (city) vs "Da Nang" (region) → tokens = {"danang"} vs {"da", "nang"} → NO MATCH ❌

**Đề xuất:**
- Normalize cả 2: remove spaces, convert to lowercase trước khi split
- Hoặc dùng fuzzy matching: check substring hoặc common words

#### ⚠️ Vấn đề 4: Output quá dài khi test nhiều users
- Khi test 10+ users, output rất dài
- Khó đọc và phân tích tổng hợp

**Đề xuất:**
- Thêm option `--summary-only` để chỉ hiển thị tổng kết
- Hoặc hiển thị tóm tắt cho mỗi user, chi tiết chỉ khi `--verbose`

---

## ✅ ĐỀ XUẤT CẢI THIỆN

### 1. Sửa `test_phase1_with_model.py`

#### Cải thiện 1: Sửa logic tính Accuracy
```python
def calculate_accuracy(pattern_counts: Dict, age: float) -> float:
    """Tính accuracy đúng cách."""
    mandatory_patterns = ['gender_style', 'age_price', 'region_city']
    optional_patterns = ['age_star'] if age >= 30 else ['age_score']
    
    applicable_patterns = mandatory_patterns + optional_patterns
    max_patterns = len(applicable_patterns)  # = 4
    
    matched_patterns = sum(1 for p in applicable_patterns if pattern_counts.get(p, 0) > 0)
    
    return matched_patterns / max_patterns if max_patterns > 0 else 0.0
```

#### Cải thiện 2: Thêm điều kiện Pass/Fail
```python
def evaluate_test_result(pattern_counts: Dict, age: float) -> Dict:
    """Đánh giá kết quả test."""
    mandatory_patterns = ['gender_style', 'age_price', 'region_city']
    optional_patterns = ['age_star'] if age >= 30 else ['age_score']
    
    # Mandatory: ít nhất 2/3 phải pass
    mandatory_matched = sum(1 for p in mandatory_patterns if pattern_counts.get(p, 0) > 0)
    mandatory_passed = mandatory_matched >= 2
    
    # Optional: có thể không có
    optional_matched = sum(1 for p in optional_patterns if pattern_counts.get(p, 0) > 0)
    
    # Tính điểm
    total_score = mandatory_matched + optional_matched
    max_score = len(mandatory_patterns) + len(optional_patterns)
    
    # Pass nếu: mandatory_passed AND total_score >= 3
    passed = mandatory_passed and total_score >= 3
    
    return {
        'mandatory_matched': mandatory_matched,
        'mandatory_passed': mandatory_passed,
        'optional_matched': optional_matched,
        'total_score': total_score,
        'max_score': max_score,
        'passed': passed,
        'accuracy': total_score / max_score if max_score > 0 else 0.0
    }
```

#### Cải thiện 3: Thêm hiển thị tóm tắt items (optional)
```python
def print_items_summary(recommendations: List[str], item_df: pd.DataFrame, top_n: int = 5):
    """Hiển thị tóm tắt top items."""
    print(f"   Top {top_n} recommendations:")
    for idx, item_id in enumerate(recommendations[:top_n], 1):
        features = get_item_features(item_id, item_df)
        if features:
            print(f"      {idx}. Item {item_id}: {features.get('style', 'N/A')} | "
                  f"{features.get('city', 'N/A')} | {format_currency(features.get('price', 0))}")
```

---

### 2. Sửa `test_phase1_ultra_detailed.py`

#### Cải thiện 1: Cải thiện Region → City Matching
```python
def check_region_city_match(city: str, region: str) -> bool:
    """Kiểm tra region và city có match không (improved)."""
    # Normalize: remove spaces, lowercase
    city_norm = city.replace(' ', '').replace('-', '').lower()
    region_norm = region.replace(' ', '').replace('-', '').lower()
    
    # Exact match sau khi normalize
    if city_norm == region_norm:
        return True
    
    # Substring match (một trong hai chứa cái kia)
    if city_norm in region_norm or region_norm in city_norm:
        return True
    
    # Common word match (nếu có từ chung)
    city_words = set(city_norm.split())
    region_words = set(region_norm.split())
    if city_words & region_words:
        return True
    
    # Manual mapping cho các trường hợp đặc biệt
    mappings = {
        'hochiminh': ['ho chi minh', 'hcm', 'saigon'],
        'danang': ['da nang'],
        'nhagtrang': ['nha trang'],
        'hue': ['hue'],
        'haiphong': ['hai phong'],
        'dalat': ['da lat'],
        'phuquoc': ['phu quoc'],
        'hanoi': ['ha noi', 'hanoi']
    }
    
    for key, variants in mappings.items():
        if key in city_norm and any(v in region_norm for v in variants):
            return True
        if key in region_norm and any(v in city_norm for v in variants):
            return True
    
    return False
```

#### Cải thiện 2: Cải thiện logic Pass/Fail (linh hoạt hơn)
```python
def evaluate_pass_fail(pattern_counts: Dict, age: float, num_recommendations: int) -> Dict:
    """Đánh giá pass/fail với logic linh hoạt hơn."""
    mandatory_patterns = ['gender_style', 'age_price', 'region_city']
    optional_patterns = ['age_star'] if age >= 30 else ['age_score']
    
    # Tính điểm cho mỗi pattern với threshold
    pattern_scores = {}
    
    for pattern_key in mandatory_patterns:
        count = pattern_counts.get(pattern_key, 0)
        # Threshold: ≥ 20% HOẶC ≥ 2 items
        threshold = max(2, int(num_recommendations * 0.2))
        pattern_scores[pattern_key] = {
            'count': count,
            'threshold': threshold,
            'passed': count >= threshold,
            'is_mandatory': True
        }
    
    for pattern_key in optional_patterns:
        count = pattern_counts.get(pattern_key, 0)
        # Threshold: ≥ 30% HOẶC ≥ 2 items
        threshold = max(2, int(num_recommendations * 0.3))
        pattern_scores[pattern_key] = {
            'count': count,
            'threshold': threshold,
            'passed': count >= threshold,
            'is_mandatory': False
        }
    
    # Mandatory: ít nhất 2/3 phải pass
    mandatory_passed_count = sum(1 for p in mandatory_patterns if pattern_scores[p]['passed'])
    mandatory_passed = mandatory_passed_count >= 2
    
    # Optional: bonus nếu pass
    optional_passed = any(pattern_scores[p]['passed'] for p in optional_patterns if p in pattern_scores)
    
    # Tính điểm
    mandatory_score = mandatory_passed_count
    optional_score = 1 if optional_passed else 0
    total_score = mandatory_score + optional_score
    max_score = len(mandatory_patterns) + len(optional_patterns)
    
    # Pass conditions (2 mức):
    # - STRICT: Tất cả mandatory pass + total_score >= 3
    # - FLEXIBLE: 2/3 mandatory pass + total_score >= 3
    passed_strict = mandatory_passed_count == 3 and total_score >= 3
    passed_flexible = mandatory_passed and total_score >= 3
    
    return {
        'pattern_scores': pattern_scores,
        'mandatory_passed_count': mandatory_passed_count,
        'mandatory_passed': mandatory_passed,
        'optional_passed': optional_passed,
        'total_score': total_score,
        'max_score': max_score,
        'passed_strict': passed_strict,
        'passed_flexible': passed_flexible,
        'passed': passed_flexible  # Dùng flexible làm default
    }
```

#### Cải thiện 3: Thêm option summary-only
```python
def main():
    parser = argparse.ArgumentParser(...)
    parser.add_argument('--summary-only', action='store_true',
                        help='Chỉ hiển thị tổng kết, không hiển thị chi tiết items')
    parser.add_argument('--verbose', action='store_true',
                        help='Hiển thị chi tiết đầy đủ (default khi test 1 user)')
    # ...
    
    # Trong test_user_detailed:
    if args.summary_only:
        # Chỉ hiển thị summary, skip chi tiết items
        pass
    elif args.verbose or args.user_id:
        # Hiển thị đầy đủ
        pass
    else:
        # Hiển thị tóm tắt (medium detail)
        pass
```

---

## 📋 TÓM TẮT ĐỀ XUẤT

### Priority 1 (QUAN TRỌNG - Cần sửa ngay):
1. ✅ **Sửa logic tính Accuracy trong `test_phase1_with_model.py`**
2. ✅ **Thêm điều kiện Pass/Fail trong `test_phase1_with_model.py`**
3. ✅ **Cải thiện Region → City Matching trong cả 2 files**

### Priority 2 (QUAN TRỌNG - Nên sửa):
4. ✅ **Cải thiện logic Pass/Fail linh hoạt hơn trong `test_phase1_ultra_detailed.py`**
5. ✅ **Cải thiện logic tính điểm với threshold (≥ 20% hoặc ≥ 2 items)**

### Priority 3 (TỐT NHƯNG KHÔNG BẮT BUỘC):
6. ✅ **Thêm option summary-only để giảm output dài**
7. ✅ **Thêm hiển thị tóm tắt items trong `test_phase1_with_model.py`**

---

## 🎯 KẾ HOẠCH THỰC HIỆN

### Bước 1: Sửa `test_phase1_with_model.py`
- [ ] Sửa logic tính Accuracy
- [ ] Thêm hàm `evaluate_test_result()`
- [ ] Thêm hiển thị Pass/Fail
- [ ] Test lại với dataset hiện tại

### Bước 2: Sửa `test_phase1_ultra_detailed.py`
- [ ] Cải thiện `check_region_city_match()`
- [ ] Cải thiện logic Pass/Fail (linh hoạt hơn)
- [ ] Thêm threshold cho pattern matching (≥ 20% hoặc ≥ 2 items)
- [ ] Thêm option `--summary-only`
- [ ] Test lại với dataset hiện tại

### Bước 3: Testing
- [ ] Test cả 2 scripts với nhiều users khác nhau
- [ ] So sánh kết quả trước và sau khi sửa
- [ ] Verify logic pass/fail hợp lý

---

## 💡 GỢI Ý THÊM

### 1. Tạo shared utilities
Có thể tạo file `test_utils.py` chứa các functions chung:
- `check_region_city_match()` - Improved matching
- `evaluate_test_result()` - Evaluation logic
- `calculate_pattern_scores()` - Pattern scoring

### 2. Thêm configuration file
Tạo `test_config.py` để config:
- Pattern thresholds (20%, 30%, etc.)
- Pass/fail criteria
- Expected patterns per user type

### 3. Thêm logging
Thêm option để log kết quả ra file:
```python
parser.add_argument('--log-file', type=str, default=None,
                    help='Ghi kết quả ra file (JSON hoặc CSV)')
```

---

**Tài liệu được tạo ngày 2025-01-14**

