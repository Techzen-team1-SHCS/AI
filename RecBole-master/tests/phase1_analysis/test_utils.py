"""
Module chứa các utility functions dùng chung cho Phase 1 testing.

Các functions chính:
- check_region_city_match: Kiểm tra matching giữa region và city
- calculate_accuracy: Tính độ chính xác của recommendations
- evaluate_test_result: Đánh giá kết quả test với logic linh hoạt
"""

from typing import Dict, Tuple


def check_region_city_match(city: str, region: str) -> bool:
    """Kiểm tra region và city có khớp với nhau không.
    
    Hàm này xử lý các trường hợp:
    - Tên thành phố có thể viết khác nhau (có/không dấu cách, có/không dấu gạch nối)
    - Tên viết tắt (HCM, Hà Nội)
    - Các biến thể phổ biến (Sài Gòn/Ho Chi Minh, Đà Nẵng/Da Nang)
    
    Thuật toán matching theo thứ tự ưu tiên:
    1. Exact match sau khi normalize (loại bỏ spaces, dashes, lowercase)
    2. Substring match (một trong hai chứa cái kia)
    3. Common word match (có từ chung)
    4. Manual mapping cho các trường hợp đặc biệt
    
    Args:
        city: Tên city từ dataset (ví dụ: "HoChiMinh", "DaNang")
        region: Tên region từ user profile (ví dụ: "Ho Chi Minh", "Da Nang")
    
    Returns:
        True nếu city và region khớp với nhau, False nếu không.
    
    Examples:
        >>> check_region_city_match("HoChiMinh", "Ho Chi Minh")
        True
        >>> check_region_city_match("DaNang", "Da Nang")
        True
        >>> check_region_city_match("Hanoi", "Ha Noi")
        True
    """
    # Bước 1: Normalize - loại bỏ spaces, dashes, chuyển lowercase
    city_norm = city.replace(' ', '').replace('-', '').lower()
    region_norm = region.replace(' ', '').replace('-', '').lower()
    
    # Bước 2: Exact match sau khi normalize
    if city_norm == region_norm:
        return True
    
    # Bước 3: Substring match - một trong hai chứa cái kia
    if city_norm in region_norm or region_norm in city_norm:
        return True
    
    # Bước 4: Common word match - nếu có từ chung
    city_words = set(city_norm.split())
    region_words = set(region_norm.split())
    if city_words & region_words:
        return True
    
    # Bước 5: Manual mapping cho các trường hợp đặc biệt
    # Xử lý các tên thành phố có nhiều cách viết khác nhau
    mappings = {
        'hochiminh': ['ho chi minh', 'hcm', 'saigon', 'hochiminh'],
        'danang': ['da nang', 'danang'],
        'nhatrang': ['nha trang', 'nhatrang'],
        'hue': ['hue'],
        'haiphong': ['hai phong', 'haiphong'],
        'dalat': ['da lat', 'dalat'],
        'phuquoc': ['phu quoc', 'phuquoc'],
        'hanoi': ['ha noi', 'hanoi', 'hoi an']  # Thêm HoiAn nếu cần
    }
    
    # Kiểm tra trong mapping
    for key, variants in mappings.items():
        if key in city_norm and any(v in region_norm for v in variants):
            return True
        if key in region_norm and any(v in city_norm for v in variants):
            return True
    
    return False


def calculate_accuracy(pattern_counts: Dict[str, int], age: float) -> float:
    """Tính độ chính xác (accuracy) của recommendations.
    
    Accuracy được tính dựa trên số lượng patterns được match:
    - Patterns bắt buộc: Gender→Style, Age→Price, Region→City
    - Patterns tùy chọn: Age→Star (nếu age >= 30) hoặc Age→Score (nếu age < 30)
    
    Công thức: accuracy = số_patterns_matched / tổng_số_patterns_áp_dụng
    
    Args:
        pattern_counts: Dict chứa số lượng items match mỗi pattern.
            Keys: 'gender_style', 'age_price', 'region_city', 'age_star', 'age_score'
            Values: Số lượng items match pattern đó
        age: Tuổi của user (dùng để xác định pattern tùy chọn)
    
    Returns:
        Accuracy từ 0.0 đến 1.0:
        - 0.0: Không có pattern nào được match
        - 1.0: Tất cả patterns đều được match
        - Giá trị trung gian: Tỷ lệ patterns được match
    
    Examples:
        >>> pattern_counts = {'gender_style': 3, 'age_price': 2, 'region_city': 1, 'age_star': 0}
        >>> calculate_accuracy(pattern_counts, 35.0)
        0.75  # 3/4 patterns matched (age >= 30 nên dùng age_star)
    """
    # Xác định patterns bắt buộc (luôn áp dụng)
    mandatory_patterns = ['gender_style', 'age_price', 'region_city']
    
    # Xác định patterns tùy chọn dựa trên age
    # - age >= 30: kiểm tra age_star
    # - age < 30: kiểm tra age_score
    optional_patterns = ['age_star'] if age >= 30 else ['age_score']
    
    # Tổng số patterns áp dụng (luôn = 4)
    applicable_patterns = mandatory_patterns + optional_patterns
    max_patterns = len(applicable_patterns)  # = 4
    
    # Đếm số patterns có ít nhất 1 item match (count > 0)
    matched_patterns = sum(1 for p in applicable_patterns if pattern_counts.get(p, 0) > 0)
    
    # Tính accuracy
    return matched_patterns / max_patterns if max_patterns > 0 else 0.0


def evaluate_test_result(pattern_counts: Dict[str, int], age: float, num_recommendations: int) -> Dict:
    """Đánh giá kết quả test Phase 1 với logic linh hoạt.
    
    Hàm này đánh giá chất lượng recommendations dựa trên:
    1. Số lượng items match từng pattern
    2. Threshold động dựa trên số lượng recommendations
    3. Điểm số cho patterns bắt buộc và tùy chọn
    
    Logic đánh giá:
    - Patterns bắt buộc (3): Gender→Style, Age→Price, Region→City
        + Gender→Style, Age→Price: threshold = max(3, 30% số recommendations)
        + Region→City: threshold = max(2, 20% số recommendations) (khó match hơn)
    - Patterns tùy chọn (1): Age→Star (age >= 30) hoặc Age→Score (age < 30)
        + Threshold = max(2, 30% số recommendations)
    
    Điều kiện PASS (flexible mode):
    - Ít nhất 2/3 patterns bắt buộc phải pass
    - Tổng điểm >= 3 (mandatory_score + optional_score)
    
    Args:
        pattern_counts: Dict chứa số lượng items match mỗi pattern.
            Keys: 'gender_style', 'age_price', 'region_city', 'age_star', 'age_score'
            Values: Số lượng items match pattern đó
        age: Tuổi của user (dùng để xác định pattern tùy chọn)
        num_recommendations: Tổng số recommendations được trả về
    
    Returns:
        Dict chứa kết quả đánh giá:
        {
            'pattern_scores': Dict[str, Dict] - Chi tiết điểm từng pattern
            'mandatory_passed_count': int - Số patterns bắt buộc đã pass (0-3)
            'mandatory_passed': bool - True nếu >= 2/3 patterns bắt buộc pass
            'optional_passed': bool - True nếu pattern tùy chọn pass
            'total_score': int - Tổng điểm (0-4)
            'max_score': int - Điểm tối đa (4)
            'passed_strict': bool - Pass theo chế độ strict (3/3 mandatory + score >= 3)
            'passed_flexible': bool - Pass theo chế độ flexible (2/3 mandatory + score >= 3)
            'passed': bool - Kết quả cuối cùng (dùng flexible)
            'accuracy': float - Độ chính xác (0.0-1.0)
        }
    
    Examples:
        >>> pattern_counts = {'gender_style': 4, 'age_price': 3, 'region_city': 2, 'age_star': 1}
        >>> result = evaluate_test_result(pattern_counts, 35.0, 10)
        >>> result['passed']
        True  # 3/3 mandatory passed, total_score = 4
    """
    # Xác định patterns bắt buộc và tùy chọn
    mandatory_patterns = ['gender_style', 'age_price', 'region_city']
    optional_patterns = ['age_star'] if age >= 30 else ['age_score']
    
    # Tính điểm cho mỗi pattern với threshold động
    pattern_scores = {}
    
    # Đánh giá patterns bắt buộc
    for pattern_key in mandatory_patterns:
        count = pattern_counts.get(pattern_key, 0)
        
        # Threshold động:
        # - Gender→Style và Age→Price: ≥ 30% HOẶC ≥ 3 items (lấy giá trị lớn hơn)
        # - Region→City: ≥ 20% HOẶC ≥ 2 items (pattern này khó match hơn nên threshold thấp hơn)
        if pattern_key in ['gender_style', 'age_price']:
            threshold = max(3, int(num_recommendations * 0.3))
        else:  # region_city
            threshold = max(2, int(num_recommendations * 0.2))
        
        pattern_scores[pattern_key] = {
            'count': count,
            'threshold': threshold,
            'passed': count >= threshold,
            'is_mandatory': True
        }
    
    # Đánh giá patterns tùy chọn
    for pattern_key in optional_patterns:
        count = pattern_counts.get(pattern_key, 0)
        # Threshold: ≥ 30% HOẶC ≥ 2 items (lấy giá trị lớn hơn)
        threshold = max(2, int(num_recommendations * 0.3))
        pattern_scores[pattern_key] = {
            'count': count,
            'threshold': threshold,
            'passed': count >= threshold,
            'is_mandatory': False
        }
    
    # Đếm số patterns bắt buộc đã pass (cần >= 2/3)
    mandatory_passed_count = sum(1 for p in mandatory_patterns if pattern_scores[p]['passed'])
    mandatory_passed = mandatory_passed_count >= 2
    
    # Kiểm tra pattern tùy chọn có pass không
    optional_passed = any(pattern_scores[p]['passed'] for p in optional_patterns if p in pattern_scores)
    
    # Tính điểm:
    # - Mandatory score: số patterns bắt buộc pass (0-3)
    # - Optional score: 1 nếu pattern tùy chọn pass, 0 nếu không
    # - Total score: tổng điểm (0-4)
    mandatory_score = mandatory_passed_count
    optional_score = 1 if optional_passed else 0
    total_score = mandatory_score + optional_score
    max_score = len(mandatory_patterns) + len(optional_patterns)  # = 4
    
    # Điều kiện PASS (2 mức độ):
    # - STRICT: Tất cả 3 patterns bắt buộc pass + total_score >= 3
    # - FLEXIBLE: Ít nhất 2/3 patterns bắt buộc pass + total_score >= 3
    passed_strict = mandatory_passed_count == 3 and total_score >= 3
    passed_flexible = mandatory_passed and total_score >= 3
    
    # Tính accuracy
    accuracy = calculate_accuracy(pattern_counts, age)
    
    return {
        'pattern_scores': pattern_scores,
        'mandatory_passed_count': mandatory_passed_count,
        'mandatory_passed': mandatory_passed,
        'optional_passed': optional_passed,
        'total_score': total_score,
        'max_score': max_score,
        'passed_strict': passed_strict,
        'passed_flexible': passed_flexible,
        'passed': passed_flexible,  # Dùng flexible làm default
        'accuracy': accuracy
    }

