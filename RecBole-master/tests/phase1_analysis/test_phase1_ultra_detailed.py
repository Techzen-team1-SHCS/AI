"""
Script test Phase 1 chi tiết cực kỳ - Hiển thị đầy đủ thông tin.

Script này cung cấp output chi tiết nhất cho Phase 1 testing, bao gồm:
- Thông tin đầy đủ về user (gender, age, region)
- Danh sách items được gợi ý với đầy đủ features (style, price, star, score, city)
- Phân tích từng pattern cho mỗi item (match/không match và lý do)
- Điều kiện đạt/thất bại rõ ràng với threshold
- Tổng kết chi tiết với điểm số và accuracy

Khác biệt với test_phase1_with_model.py:
- Output chi tiết hơn nhiều (hiển thị từng item và pattern analysis)
- Phù hợp cho debug và hiểu rõ cách Phase 1 hoạt động
- Không phù hợp cho batch testing (chỉ test ít users)

Usage:
    python test_phase1_ultra_detailed.py                    # Test với model mới nhất, 5 users
    python test_phase1_ultra_detailed.py --num-users 10     # Test 10 users
    python test_phase1_ultra_detailed.py --model saved/xxx.pth  # Test với model cụ thể 
    python tests/phase1_analysis/test_phase1_ultra_detailed.py --user-id 100 # Test 1 user cụ thể
"""

import sys
import os
import pandas as pd
import argparse
from typing import List, Dict, Optional
import io
import glob

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from inference import get_recommendations, load_model, clear_cache

# Import shared utilities
sys.path.insert(0, os.path.dirname(__file__))
from test_utils import check_region_city_match, evaluate_test_result

# Paths
DATASET_DIR = 'dataset/hotel'
USER_FILE = os.path.join(DATASET_DIR, 'hotel.user')
ITEM_FILE = os.path.join(DATASET_DIR, 'hotel.item')
SAVED_DIR = 'saved'


def find_latest_checkpoint(saved_dir: str = SAVED_DIR) -> Optional[str]:
    """Tìm checkpoint mới nhất."""
    pattern = os.path.join(saved_dir, "DeepFM-*.pth")
    checkpoints = glob.glob(pattern)
    if not checkpoints:
        return None
    latest = max(checkpoints, key=os.path.getmtime)
    return latest


def load_user_item_data():
    """Load user và item data."""
    user_df = pd.read_csv(USER_FILE, sep='\t')
    user_df.columns = [col.split(':')[0] for col in user_df.columns]
    
    item_df = pd.read_csv(ITEM_FILE, sep='\t')
    item_df.columns = [col.split(':')[0] for col in item_df.columns]
    
    return user_df, item_df


def get_item_features(item_id: str, item_df: pd.DataFrame) -> Dict:
    """Lấy features đầy đủ của item."""
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
    """Kiểm tra item có match patterns không và trả về chi tiết.
    
    Hàm này tương tự check_pattern trong test_phase1_with_model.py nhưng
    trả về thêm thông tin chi tiết (reason) cho mỗi pattern để hiển thị
    trong output ultra-detailed.
    
    Args:
        gender: Giới tính của user ('F' hoặc 'M')
        age: Tuổi của user
        region: Region của user
        item_features: Dict chứa features của item
    
    Returns:
        Tuple (checks, details):
        - checks: Dict[bool] - Kết quả match/không match cho mỗi pattern
        - details: Dict[Dict] - Chi tiết với lý do match/không match
    """
    checks = {
        'gender_style': False,
        'age_price': False,
        'region_city': False,
        'age_star': False,
        'age_score': False
    }
    
    # Dict chứa chi tiết và lý do cho mỗi pattern
    details = {
        'gender_style': {'matched': False, 'reason': ''},
        'age_price': {'matched': False, 'reason': ''},
        'region_city': {'matched': False, 'reason': ''},
        'age_star': {'matched': False, 'reason': ''},
        'age_score': {'matched': False, 'reason': ''}
    }
    
    # Pattern 1: Gender → Style
    style = item_features.get('style', '').lower()
    style_tokens = set(style.split()) if style else set()
    
    if gender == 'F':
        expected_tokens = {'romantic', 'love', 'modern', 'lively'}
        matched_tokens = expected_tokens & style_tokens
        checks['gender_style'] = bool(matched_tokens)
        if matched_tokens:
            details['gender_style'] = {
                'matched': True,
                'reason': f"Style chứa: {', '.join(matched_tokens)} (phù hợp với Nữ)"
            }
        else:
            details['gender_style'] = {
                'matched': False,
                'reason': f"Style: '{item_features.get('style', '')}' không chứa các từ phù hợp với Nữ (romantic, love, modern, lively)"
            }
    else:  # M
        expected_tokens = {'love', 'romantic', 'modern', 'lively'}
        matched_tokens = expected_tokens & style_tokens
        checks['gender_style'] = bool(matched_tokens)
        if matched_tokens:
            details['gender_style'] = {
                'matched': True,
                'reason': f"Style chứa: {', '.join(matched_tokens)} (phù hợp với Nam)"
            }
        else:
            details['gender_style'] = {
                'matched': False,
                'reason': f"Style: '{item_features.get('style', '')}' không chứa các từ phù hợp với Nam (love, romantic, modern, lively)"
            }
    
    # Pattern 2: Age → Price
    price = item_features.get('price', 0)
    if age < 30:
        checks['age_price'] = price < 1600000
        if checks['age_price']:
            details['age_price'] = {
                'matched': True,
                'reason': f"Price: {price:,.0f} VND < 1,600,000 VND (phù hợp với age < 30)"
            }
        else:
            details['age_price'] = {
                'matched': False,
                'reason': f"Price: {price:,.0f} VND >= 1,600,000 VND (KHÔNG phù hợp với age < 30)"
            }
    else:  # >= 30
        checks['age_price'] = price >= 1200000
        if checks['age_price']:
            details['age_price'] = {
                'matched': True,
                'reason': f"Price: {price:,.0f} VND >= 1,200,000 VND (phù hợp với age >= 30)"
            }
        else:
            details['age_price'] = {
                'matched': False,
                'reason': f"Price: {price:,.0f} VND < 1,200,000 VND (KHÔNG phù hợp với age >= 30)"
            }
    
    # Pattern 3: Region → City (improved matching)
    city = item_features.get('city', '')
    checks['region_city'] = check_region_city_match(city, region)
    
    if checks['region_city']:
        details['region_city'] = {
            'matched': True,
            'reason': f"City: '{city}' khớp với Region: '{region}'"
        }
    else:
        details['region_city'] = {
            'matched': False,
            'reason': f"City: '{city}' KHÔNG khớp với Region: '{region}'"
        }
    
    # Pattern 4: Age → Star (chỉ áp dụng nếu age >= 30)
    if age >= 30:
        star = item_features.get('star', 0)
        checks['age_star'] = star >= 3.5
        if checks['age_star']:
            details['age_star'] = {
                'matched': True,
                'reason': f"Star: {star:.1f} >= 3.5 (phù hợp với age >= 30)"
            }
        else:
            details['age_star'] = {
                'matched': False,
                'reason': f"Star: {star:.1f} < 3.5 (KHÔNG phù hợp với age >= 30)"
            }
    else:
        details['age_star'] = {
            'matched': None,
            'reason': "Không áp dụng (age < 30)"
        }
    
    # Pattern 5: Age → Score (chỉ áp dụng nếu age < 30)
    if age < 30:
        score = item_features.get('score', 0)
        checks['age_score'] = score >= 9.0
        if checks['age_score']:
            details['age_score'] = {
                'matched': True,
                'reason': f"Score: {score:.1f} >= 9.0 (phù hợp với age < 30)"
            }
        else:
            details['age_score'] = {
                'matched': False,
                'reason': f"Score: {score:.1f} < 9.0 (KHÔNG phù hợp với age < 30)"
            }
    else:
        details['age_score'] = {
            'matched': None,
            'reason': "Không áp dụng (age >= 30)"
        }
    
    return checks, details


def format_currency(amount: float) -> str:
    """Format số tiền."""
    return f"{amount:,.0f} VND"


def test_user_detailed(user_id: str, user_row: pd.Series, item_df: pd.DataFrame, top_k: int = 10) -> Dict:
    """Test một user với thông tin chi tiết."""
    gender = user_row['gender']
    age = float(user_row['age'])
    region = user_row['region']
    
    print("=" * 100)
    print(f"USER ID: {user_id}")
    print("=" * 100)
    print(f"📋 Thông tin User:")
    print(f"   - Gender: {gender} ({'Nữ' if gender == 'F' else 'Nam'})")
    print(f"   - Age: {age:.0f}")
    print(f"   - Region: {region}")
    print()
    
    # Get recommendations
    print(f"🔍 Đang lấy recommendations (Top-{top_k})...")
    try:
        recommendations = get_recommendations(
            user_id=user_id,
            top_k=top_k,
            use_behavior_boost=True,
            use_similarity_boost=False  # Phase 1 chỉ test behavior boost
        )
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
        return {
            'user_id': user_id,
            'gender': gender,
            'age': age,
            'region': region,
            'recommendations': [],
            'pattern_counts': {},
            'passed': False,
            'accuracy': 0.0
        }
    
    print(f"   ✅ Đã nhận được {len(recommendations)} recommendations")
    print()
    
    # Phân tích từng item
    print("📦 CHI TIẾT CÁC ITEMS ĐƯỢC GỢI Ý:")
    print("-" * 100)
    
    pattern_counts = {
        'gender_style': 0,
        'age_price': 0,
        'region_city': 0,
        'age_star': 0,
        'age_score': 0
    }
    
    item_details = []
    
    for idx, item_id in enumerate(recommendations, 1):
        item_features = get_item_features(item_id, item_df)
        if not item_features:
            print(f"   {idx}. Item {item_id}: ❌ Không tìm thấy thông tin")
            continue
        
        checks, details = check_pattern(gender, age, region, item_features)
        
        # Đếm patterns
        for pattern, matched in checks.items():
            if matched:
                pattern_counts[pattern] += 1
        
        item_details.append({
            'item_id': item_id,
            'features': item_features,
            'checks': checks,
            'details': details
        })
        
        # Hiển thị thông tin item
        print(f"\n   {idx}. Item ID: {item_id}")
        print(f"      📍 City: {item_features['city']}")
        print(f"      🎨 Style: {item_features['style']}")
        print(f"      💰 Price: {format_currency(item_features['price'])}")
        print(f"      ⭐ Star: {item_features['star']:.1f}")
        print(f"      📊 Score: {item_features['score']:.1f}")
        print(f"      📋 Pattern Analysis:")
        
        # Pattern 1: Gender → Style
        detail = details['gender_style']
        status = "✅" if detail['matched'] else "❌"
        print(f"         {status} Gender → Style: {detail['reason']}")
        
        # Pattern 2: Age → Price
        detail = details['age_price']
        status = "✅" if detail['matched'] else "❌"
        print(f"         {status} Age → Price: {detail['reason']}")
        
        # Pattern 3: Region → City
        detail = details['region_city']
        status = "✅" if detail['matched'] else "❌"
        print(f"         {status} Region → City: {detail['reason']}")
        
        # Pattern 4: Age → Star (nếu áp dụng)
        detail = details['age_star']
        if detail['matched'] is not None:
            status = "✅" if detail['matched'] else "❌"
            print(f"         {status} Age → Star: {detail['reason']}")
        
        # Pattern 5: Age → Score (nếu áp dụng)
        detail = details['age_score']
        if detail['matched'] is not None:
            status = "✅" if detail['matched'] else "❌"
            print(f"         {status} Age → Score: {detail['reason']}")
    
    print()
    print("-" * 100)
    
    # Điều kiện pass/fail
    print("\n📊 KẾT QUẢ PHÂN TÍCH:")
    print("-" * 100)
    
    # Evaluate với logic mới
    evaluation = evaluate_test_result(pattern_counts, age, len(recommendations))
    pattern_scores = evaluation['pattern_scores']
    
    mandatory_patterns = ['gender_style', 'age_price', 'region_city']
    optional_patterns = ['age_star'] if age >= 30 else ['age_score']
    
    print("\n🔴 PATTERNS BẮT BUỘC (threshold: ≥20% hoặc ≥2 items):")
    for pattern_key in mandatory_patterns:
        score_info = pattern_scores[pattern_key]
        count = score_info['count']
        threshold = score_info['threshold']
        passed = score_info['passed']
        status = "✅ PASS" if passed else "❌ FAIL"
        pattern_name = {
            'gender_style': 'Gender → Style',
            'age_price': 'Age → Price',
            'region_city': 'Region → City'
        }[pattern_key]
        print(f"   {status} {pattern_name}: {count}/{len(recommendations)} items (threshold: {threshold})")
    
    print("\n🟡 PATTERNS TÙY CHỌN (threshold: ≥30% hoặc ≥2 items):")
    for pattern_key in optional_patterns:
        if pattern_key in pattern_scores:
            score_info = pattern_scores[pattern_key]
            count = score_info['count']
            threshold = score_info['threshold']
            passed = score_info['passed']
            status = "✅ PASS" if passed else "❌ FAIL"
            pattern_name = 'Age → Star (≥30)' if pattern_key == 'age_star' else 'Age → Score (<30)'
            print(f"   {status} {pattern_name}: {count}/{len(recommendations)} items (threshold: {threshold})")
        else:
            print(f"   ⏭️  {pattern_key}: Không áp dụng")
    
    print(f"\n📈 ĐIỂM SỐ:")
    print(f"   - Điểm bắt buộc: {evaluation['mandatory_passed_count']}/{len(mandatory_patterns)}")
    print(f"   - Điểm tùy chọn: {1 if evaluation['optional_passed'] else 0}/1")
    print(f"   - Tổng điểm: {evaluation['total_score']}/{evaluation['max_score']}")
    
    # Kết luận
    final_passed = evaluation['passed']
    print(f"\n{'='*100}")
    if final_passed:
        print(f"✅ KẾT LUẬN: USER {user_id} ĐẠT YÊU CẦU!")
        print(f"   - Patterns bắt buộc passed: {evaluation['mandatory_passed_count']}/3")
        print(f"   - Tổng điểm: {evaluation['total_score']}/{evaluation['max_score']} >= 3")
        print(f"   - Accuracy: {evaluation['accuracy']:.2%}")
    else:
        print(f"❌ KẾT LUẬN: USER {user_id} KHÔNG ĐẠT YÊU CẦU!")
        if not evaluation['mandatory_passed']:
            print(f"   - Patterns bắt buộc passed: {evaluation['mandatory_passed_count']}/3 (cần >= 2)")
        if evaluation['total_score'] < 3:
            print(f"   - Tổng điểm: {evaluation['total_score']}/{evaluation['max_score']} < 3")
        print(f"   - Accuracy: {evaluation['accuracy']:.2%}")
    print(f"{'='*100}\n")
    
    return {
        'user_id': user_id,
        'gender': gender,
        'age': age,
        'region': region,
        'recommendations': recommendations,
        'pattern_counts': pattern_counts,
        'evaluation': evaluation,
        'passed': final_passed,
        'accuracy': evaluation['accuracy']
    }


def main():
    parser = argparse.ArgumentParser(description='Test Phase 1 chi tiết cực kỳ')
    parser.add_argument('--model', type=str, default=None,
                        help='Đường dẫn đến model checkpoint (nếu không chỉ định sẽ dùng model mới nhất)')
    parser.add_argument('--latest', action='store_true',
                        help='Dùng model mới nhất (explicit)')
    parser.add_argument('--num-users', type=int, default=5,
                        help='Số lượng users để test (default: 5)')
    parser.add_argument('--user-id', type=str, default=None,
                        help='Test một user cụ thể (nếu có sẽ bỏ qua --num-users)')
    parser.add_argument('--top-k', type=int, default=10,
                        help='Số lượng recommendations (default: 10)')
    
    args = parser.parse_args()
    
    print("=" * 100)
    print("TEST PHASE 1 - CHI TIẾT CỰC KỲ")
    print("=" * 100)
    print()
    
    # Xác định model path
    if args.model:
        model_path = args.model
        if not os.path.exists(model_path):
            print(f"❌ ERROR: Model không tồn tại: {model_path}")
            return
    elif args.latest or True:  # Mặc định dùng latest
        model_path = find_latest_checkpoint()
        if not model_path:
            print("❌ ERROR: Không tìm thấy checkpoint nào trong thư mục saved/")
            return
    else:
        print("❌ ERROR: Cần chỉ định --model hoặc --latest")
        return
    
    print(f"📦 Model được sử dụng: {model_path}")
    print(f"📅 Model mtime: {os.path.getmtime(model_path)}")
    print()
    
    # Clear cache và load model
    print("🔄 Đang clear cache và load model...")
    clear_cache()
    try:
        config, model, dataset = load_model(model_path=model_path, force_reload=True)
        print(f"✅ Load model thành công!")
        print(f"   Dataset: {dataset.dataset_name}, Users: {dataset.user_num}, Items: {dataset.item_num}")
    except Exception as e:
        print(f"❌ ERROR: Không thể load model: {e}")
        return
    
    print()
    
    # Load user và item data
    print("📂 Đang load user và item data...")
    user_df, item_df = load_user_item_data()
    print(f"✅ Load thành công: {len(user_df)} users, {len(item_df)} items")
    print()
    
    # Test
    if args.user_id:
        # Test một user cụ thể
        user_row = user_df[user_df['user_id'].astype(str) == str(args.user_id)]
        if len(user_row) == 0:
            print(f"❌ ERROR: Không tìm thấy user {args.user_id}")
            return
        user_row = user_row.iloc[0]
        test_user_detailed(str(args.user_id), user_row, item_df, args.top_k)
    else:
        # Test nhiều users
        test_users = user_df.head(args.num_users)
        print(f"📊 Sẽ test {len(test_users)} users\n")
        
        results = []
        for idx, (_, user_row) in enumerate(test_users.iterrows(), 1):
            user_id = str(user_row['user_id'])
            result = test_user_detailed(user_id, user_row, item_df, args.top_k)
            results.append(result)
        
        # Tổng hợp cuối
        print("\n" + "=" * 100)
        print("TỔNG HỢP TẤT CẢ USERS")
        print("=" * 100)
        
        total_users = len(results)
        passed_count = sum(1 for r in results if r['passed'])
        avg_accuracy = sum(r['accuracy'] for r in results) / total_users if total_users > 0 else 0
        
        print(f"\n📊 Kết quả tổng thể:")
        print(f"   - Tổng số users: {total_users}")
        print(f"   - Passed: {passed_count}")
        print(f"   - Failed: {total_users - passed_count}")
        print(f"   - Pass rate: {passed_count/total_users:.1%}")
        print(f"   - Average accuracy: {avg_accuracy:.1%}")
        
        print(f"\n📋 Chi tiết từng user:")
        for r in results:
            status = "✅ PASS" if r['passed'] else "❌ FAIL"
            eval_result = r['evaluation']
            print(f"   User {r['user_id']}: {status} (Score: {eval_result['total_score']}/{eval_result['max_score']}, "
                  f"Mandatory: {eval_result['mandatory_passed_count']}/3, Accuracy: {r['accuracy']:.1%})")
        
        print("\n" + "=" * 100)


if __name__ == '__main__':
    main()



