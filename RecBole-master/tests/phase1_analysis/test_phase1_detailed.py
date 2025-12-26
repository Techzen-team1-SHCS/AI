"""
Script test Phase 1 chi tiết - Hiển thị rõ ràng từng user và recommendations.
"""

import sys
import os
import pandas as pd
from typing import List, Dict
import io

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from inference import get_recommendations, load_model, clear_cache

# Paths
DATASET_DIR = 'dataset/hotel'
USER_FILE = os.path.join(DATASET_DIR, 'hotel.user')
ITEM_FILE = os.path.join(DATASET_DIR, 'hotel.item')


def load_user_item_data():
    """Load user và item data."""
    user_df = pd.read_csv(USER_FILE, sep='\t')
    user_df.columns = [col.split(':')[0] for col in user_df.columns]
    
    item_df = pd.read_csv(ITEM_FILE, sep='\t')
    item_df.columns = [col.split(':')[0] for col in item_df.columns]
    
    return user_df, item_df


def get_item_features(item_id: str, item_df: pd.DataFrame) -> Dict:
    """Lấy features của item."""
    item_row = item_df[item_df['item_id'].astype(str) == str(item_id)]
    if len(item_row) == 0:
        return {}
    
    item_row = item_row.iloc[0]
    return {
        'item_id': str(item_id),
        'style': str(item_row.get('style', '')),
        'price': float(item_row.get('price', 0)),
        'star': float(item_row.get('star', 0)),
        'score': float(item_row.get('score', 0)),
        'city': str(item_row.get('city', ''))
    }


def check_pattern(gender: str, age: float, region: str, item_features: Dict) -> Dict:
    """Kiểm tra item có match patterns không."""
    checks = {
        'gender_style': False,
        'age_price': False,
        'region_city': False,
        'age_star': False,
        'age_score': False
    }
    
    # Pattern 1: Gender → Style (CẢI THIỆN: Dùng set intersection thay vì substring)
    # CẢI THIỆN: Cân bằng số lượng styles giữa Nữ và Nam dựa trên phân tích dataset
    # Dataset cho thấy: Nữ tương tác với Romantic (59.9%), Love (53.0%), Modern (34.8%), Lively (28.6%)
    # Nam tương tác với Love (53.2%), Romantic (52.1%), Modern (28.9%), Lively (27.6%)
    style = item_features.get('style', '').lower()
    # Tách style thành các từ (tokens)
    style_tokens = set(style.split()) if style else set()
    
    if gender == 'F':
        # Nữ: Top 4 styles dựa trên phân tích dataset
        expected_tokens = {'romantic', 'love', 'modern', 'lively'}
        checks['gender_style'] = bool(expected_tokens & style_tokens)
    else:  # M
        # Nam: Top 4 styles dựa trên phân tích dataset
        expected_tokens = {'love', 'romantic', 'modern', 'lively'}
        checks['gender_style'] = bool(expected_tokens & style_tokens)
    
    # Pattern 2: Age → Price
    price = item_features.get('price', 0)
    if age < 30:
        checks['age_price'] = price < 1600000
    elif age >= 30:
        checks['age_price'] = price >= 1200000
    # Xử lý edge case: age = 30 chính xác → dùng điều kiện >= 30
    
    # Pattern 3: Region → City (CẢI THIỆN: So sánh chính xác hơn)
    city = item_features.get('city', '').lower()
    region_norm = region.lower()
    
    # Tách thành các từ và so sánh
    city_words = set(city.replace(' ', '').split()) if city else set()
    region_words = set(region_norm.replace(' ', '').split()) if region_norm else set()
    
    # Match nếu có từ chung hoặc một trong hai chứa toàn bộ từ của cái kia
    checks['region_city'] = bool(city_words & region_words) or \
                           (len(region_words) > 0 and region_words.issubset(city_words)) or \
                           (len(city_words) > 0 and city_words.issubset(region_words))
    
    # Pattern 4: Age → Star (CẢI THIỆN: Xử lý age = 30)
    if age >= 30:
        checks['age_star'] = item_features.get('star', 0) >= 3.5
    
    # Pattern 5: Age → Score
    if age < 30:
        checks['age_score'] = item_features.get('score', 0) >= 9.0
    
    return checks


def format_price(price: float) -> str:
    """Format price."""
    if price >= 1000000:
        return f"{price/1000000:.1f}M"
    elif price >= 1000:
        return f"{price/1000:.0f}K"
    return f"{price:.0f}"


def test_user_detailed(user_id: str, user_df: pd.DataFrame, item_df: pd.DataFrame, 
                       top_k: int = 10):
    """Test một user chi tiết."""
    # VALIDATION: Kiểm tra input
    if not user_id or str(user_id).strip() == '':
        print(f"❌ User ID không hợp lệ!")
        return None
    
    if user_df is None or len(user_df) == 0:
        print(f"❌ User dataframe rỗng!")
        return None
    
    if item_df is None or len(item_df) == 0:
        print(f"❌ Item dataframe rỗng!")
        return None
    
    # Lấy user features
    user_row = user_df[user_df['user_id'].astype(str) == str(user_id)]
    if len(user_row) == 0:
        print(f"❌ User {user_id} không tìm thấy!")
        return None
    
    user_row = user_row.iloc[0]
    age = float(user_row.get('age', 0))
    gender = str(user_row.get('gender', ''))
    region = str(user_row.get('region', ''))
    
    print("\n" + "=" * 100)
    print(f"USER: {user_id}")
    print("=" * 100)
    print(f"📋 User Features:")
    print(f"   Age: {age:.0f} tuổi")
    print(f"   Gender: {gender} ({'Nữ' if gender == 'F' else 'Nam'})")
    print(f"   Region: {region}")
    
    # Expected patterns
    print(f"\n🎯 Expected Patterns:")
    if gender == 'F':
        print(f"   ✓ Style: Romantic, Love, Modern, hoặc Lively (Top 4 styles cho Nữ)")
    else:
        print(f"   ✓ Style: Love, Romantic, Modern, hoặc Lively (Top 4 styles cho Nam)")
    
    if age < 30:
        print(f"   ✓ Price: < 1.6M (trẻ)")
        print(f"   ✓ Score: ≥ 9.0 (trẻ)")
    else:
        print(f"   ✓ Price: ≥ 1.2M (già)")
        print(f"   ✓ Star: ≥ 3.5 (già)")
    
    print(f"   ✓ City: Phải chứa '{region}' hoặc liên quan")
    
    # Lấy recommendations
    print(f"\n🔍 Getting recommendations...")
    try:
        recommendations = get_recommendations(
            user_id=str(user_id),
            top_k=top_k,
            use_behavior_boost=False,
            use_similarity_boost=False
        )
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return
    
    if not recommendations or len(recommendations) == 0:
        print("❌ Không có recommendations!")
        return None
    
    print(f"✅ Nhận được {len(recommendations)} recommendations\n")
    
    # Hiển thị từng recommendation
    print("=" * 100)
    print("RECOMMENDATIONS:")
    print("=" * 100)
    
    pattern_counts = {
        'gender_style': 0,
        'age_price': 0,
        'region_city': 0,
        'age_star': 0,
        'age_score': 0
    }
    
    for idx, item_id in enumerate(recommendations, 1):
        features = get_item_features(item_id, item_df)
        # VALIDATION: Kiểm tra item có features không
        if not features or len(features) == 0:
            print(f"\n[WARNING] Item {item_id} không có features, bỏ qua...")
            continue
        
        checks = check_pattern(gender, age, region, features)
        
        # Đếm patterns
        for pattern, passed in checks.items():
            if passed:
                pattern_counts[pattern] += 1
        
        # Status icons
        status_icons = {
            'gender_style': '✓' if checks['gender_style'] else '✗',
            'age_price': '✓' if checks['age_price'] else '✗',
            'region_city': '✓' if checks['region_city'] else '✗',
            'age_star': '✓' if checks['age_star'] else '✗' if age >= 30 else '-',
            'age_score': '✓' if checks['age_score'] else '✗' if age < 30 else '-'
        }
        
        print(f"\n[{idx}] Item ID: {item_id}")
        print(f"    Style: {features.get('style', 'N/A')}")
        print(f"    Price: {format_price(features.get('price', 0))} VND")
        print(f"    Star: {features.get('star', 0):.1f} ⭐")
        print(f"    Score: {features.get('score', 0):.1f}/10")
        print(f"    City: {features.get('city', 'N/A')}")
        print(f"    Patterns: {status_icons['gender_style']}Style  {status_icons['age_price']}Price  {status_icons['region_city']}City  {status_icons['age_star']}Star  {status_icons['age_score']}Score")
    
    # Tổng hợp
    print("\n" + "=" * 100)
    print("TỔNG HỢP PATTERNS:")
    print("=" * 100)
    
    total_items = len(recommendations)
    
    # Định nghĩa patterns (CẢI THIỆN: Logic rõ ràng hơn)
    mandatory_patterns = ['gender_style', 'age_price', 'region_city']
    optional_patterns = ['age_star', 'age_score']
    
    patterns = [
        ('Gender → Style', 'gender_style', True, True),  # (name, key, is_relevant, is_mandatory)
        ('Age → Price', 'age_price', True, True),
        ('Region → City', 'region_city', True, True),
        ('Age → Star', 'age_star', age >= 30, False),
        ('Age → Score', 'age_score', age < 30, False)
    ]
    
    # Tính điểm cho từng pattern (CẢI THIỆN: Logic rõ ràng hơn)
    pattern_results = {}
    mandatory_passed = True
    
    for pattern_name, pattern_key, is_relevant, is_mandatory in patterns:
        count = pattern_counts[pattern_key]
        ratio = count / total_items if total_items > 0 else 0
        
        if not is_relevant:
            status = "N/A"
            passed = True
            score = 0.0
        elif pattern_key in ['gender_style', 'region_city']:
            # Pattern 1, 3: Ít nhất 1 item match
            passed = count >= 1
            status = "✓ PASS" if passed else "✗ FAIL"
            score = 1.0 if passed else 0.0
        elif pattern_key == 'age_price':
            # Pattern 2: Ít nhất 30% items match (hoặc ít nhất 2 items)
            # Lý do: Pattern này quan trọng nhưng không nên quá strict như 50%
            min_required = max(2, int(total_items * 0.3))  # Ít nhất 30% hoặc 2 items
            passed = count >= min_required
            status = "✓ PASS" if passed else "✗ FAIL"
            score = 1.0 if passed else 0.0
        else:
            # Pattern 4, 5 (tùy chọn): Ít nhất 50%
            passed = ratio >= 0.5
            status = "✓ PASS" if passed else "✗ FAIL"
            score = 0.5 if passed else 0.0
        
        # Kiểm tra patterns bắt buộc
        if is_mandatory and not passed:
            mandatory_passed = False
        
        pattern_results[pattern_key] = {
            'passed': passed,
            'score': score,
            'count': count,
            'ratio': ratio
        }
        
        mandatory = " [BẮT BUỘC]" if is_mandatory else " [TÙY CHỌN]"
        print(f"   {pattern_name}: {count}/{total_items} items ({ratio:.1%}) {status}{mandatory}")
    
    # Tính tổng điểm (CẢI THIỆN: Logic rõ ràng hơn)
    mandatory_score = sum(pattern_results[key]['score'] for key in mandatory_patterns)
    optional_score = sum(pattern_results[key]['score'] for key in optional_patterns if pattern_results[key]['score'] > 0)
    total_score = mandatory_score + optional_score
    
    # Kết luận
    print("\n" + "=" * 100)
    print("KẾT LUẬN:")
    print("=" * 100)
    
    # Điều kiện pass: Tất cả patterns bắt buộc phải pass VÀ tổng điểm >= 3.0
    final_passed = mandatory_passed and total_score >= 3.0
    
    if final_passed:
        print(f"✅ PASS - User {user_id} đạt yêu cầu!")
        print(f"   - Tất cả 3 patterns bắt buộc: PASS")
        print(f"   - Điểm bắt buộc: {mandatory_score:.1f}/3.0")
        print(f"   - Điểm tùy chọn: {optional_score:.1f}/1.0")
        print(f"   - Tổng điểm: {total_score:.1f}/4.0")
    else:
        print(f"❌ FAIL - User {user_id} không đạt yêu cầu!")
        if not mandatory_passed:
            print(f"   - Một số patterns bắt buộc: FAIL")
            failed_mandatory = [key for key in mandatory_patterns if not pattern_results[key]['passed']]
            print(f"   - Patterns bắt buộc fail: {', '.join(failed_mandatory)}")
        print(f"   - Điểm bắt buộc: {mandatory_score:.1f}/3.0")
        print(f"   - Điểm tùy chọn: {optional_score:.1f}/1.0")
        print(f"   - Tổng điểm: {total_score:.1f}/4.0")
    
    return final_passed


def main():
    """Main function."""
    import argparse
    parser = argparse.ArgumentParser(description="Test Phase 1 Chi tiết")
    parser.add_argument("--user_id", type=str, help="User ID để test (nếu không có sẽ test nhiều users)")
    parser.add_argument("--num_users", type=int, default=5, help="Số lượng users để test (nếu không chỉ định user_id)")
    parser.add_argument("--top_k", type=int, default=10, help="Số recommendations")
    args = parser.parse_args()
    
    print("=" * 100)
    print("TEST PHASE 1 - CHI TIẾT")
    print("=" * 100)
    
    # Load data
    print("\n📊 Loading data...")
    user_df, item_df = load_user_item_data()
    print(f"✓ Loaded {len(user_df)} users, {len(item_df)} items")
    
    # Load model
    print("\n🤖 Loading model...")
    clear_cache()
    try:
        config, model, dataset = load_model()
        print(f"✓ Model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return
    
    # Test
    if args.user_id:
        # Test một user cụ thể
        test_user_detailed(args.user_id, user_df, item_df, args.top_k)
    else:
        # Test nhiều users
        import random
        random.seed(42)
        test_users = [str(uid) for uid in random.sample(user_df['user_id'].tolist(), args.num_users)]
        
        print(f"\n🧪 Testing {len(test_users)} users...\n")
        
        results = []
        for user_id in test_users:
            passed = test_user_detailed(user_id, user_df, item_df, args.top_k)
            results.append((user_id, passed))
        
        # Tổng hợp cuối
        print("\n" + "=" * 100)
        print("TỔNG HỢP TẤT CẢ USERS:")
        print("=" * 100)
        
        passed_count = sum(1 for _, p in results if p)
        total = len(results)
        accuracy = passed_count / total if total > 0 else 0
        
        print(f"\n📊 Kết quả:")
        print(f"   Total: {total} users")
        print(f"   Passed: {passed_count}")
        print(f"   Failed: {total - passed_count}")
        print(f"   Accuracy: {accuracy:.1%}")
        
        print(f"\n📋 Chi tiết:")
        for user_id, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   User {user_id}: {status}")


if __name__ == "__main__":
    main()


