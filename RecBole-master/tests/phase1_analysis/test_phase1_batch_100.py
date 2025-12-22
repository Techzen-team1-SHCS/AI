"""
Script test Phase 1 cho nhiều users - Batch testing với output cho báo cáo.

Script này được thiết kế để test Phase 1 trên một số lượng lớn users (mặc định 100),
tạo ra kết quả JSON phù hợp cho việc tạo báo cáo chi tiết.

Chức năng chính:
- Test Phase 1 cho nhiều users (batch processing)
- Tính toán thống kê tổng hợp (pass rate, accuracy, pattern stats)
- Xuất kết quả ra file JSON để generate report
- Hỗ trợ quiet mode để giảm output khi chạy batch lớn

Usage:
    python test_phase1_batch_100.py                    # Test 100 users, dùng model mới nhất
    python test_phase1_batch_100.py --num-users 50     # Test 50 users
    python test_phase1_batch_100.py --output results.json  # Lưu kết quả vào file JSON
    python test_phase1_batch_100.py --quiet            # Chỉ in kết quả tổng hợp
"""

import sys
import os
import pandas as pd
import argparse
import json
from typing import List, Dict, Optional
import io
import glob
from datetime import datetime

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
    
    # Pattern 1: Gender → Style
    style = item_features.get('style', '').lower()
    style_tokens = set(style.split()) if style else set()
    
    if gender == 'F':
        expected_tokens = {'romantic', 'love', 'modern', 'lively'}
        checks['gender_style'] = bool(expected_tokens & style_tokens)
    else:  # M
        expected_tokens = {'love', 'romantic', 'modern', 'lively'}
        checks['gender_style'] = bool(expected_tokens & style_tokens)
    
    # Pattern 2: Age → Price
    price = item_features.get('price', 0)
    if age < 30:
        checks['age_price'] = price < 1600000
    else:  # >= 30
        checks['age_price'] = price >= 1200000
    
    # Pattern 3: Region → City
    city = item_features.get('city', '')
    checks['region_city'] = check_region_city_match(city, region)
    
    # Pattern 4: Age → Star
    if age >= 30:
        checks['age_star'] = item_features.get('star', 0) >= 3.5
    
    # Pattern 5: Age → Score
    if age < 30:
        checks['age_score'] = item_features.get('score', 0) >= 9.0
    
    return checks


def test_user(user_id: str, user_row: pd.Series, item_df: pd.DataFrame, top_k: int = 10) -> Dict:
    """Test Phase 1 cho một user và trả về kết quả chi tiết.
    
    Hàm này tương tự test_user trong test_phase1_with_model.py nhưng được tối ưu
    cho batch processing (không in output, trả về error nếu có).
    
    Args:
        user_id: ID của user cần test
        user_row: Series chứa thông tin user (gender, age, region)
        item_df: DataFrame chứa thông tin items
        top_k: Số lượng recommendations cần lấy (mặc định: 10)
    
    Returns:
        Dict chứa kết quả test, bao gồm:
        - Thông tin user (user_id, gender, age, region)
        - Recommendations (danh sách item IDs)
        - Pattern counts (số lượng items match mỗi pattern)
        - Evaluation (kết quả đánh giá)
        - Error (nếu có lỗi khi lấy recommendations)
    """
    gender = user_row['gender']
    age = float(user_row['age'])
    region = user_row['region']
    
    # Lấy recommendations từ inference module (chỉ Phase 1)
    try:
        recommendations = get_recommendations(
            user_id=user_id,
            top_k=top_k,
            use_behavior_boost=True,
            use_similarity_boost=False  # Phase 1 chỉ test behavior boost
        )
    except Exception as e:
        # Trả về kết quả với error nếu có lỗi
        return {
            'user_id': user_id,
            'gender': gender,
            'age': age,
            'region': region,
            'recommendations': [],
            'num_recommendations': 0,
            'pattern_counts': {},
            'evaluation': None,
            'error': str(e)
        }
    
    # Kiểm tra patterns cho từng item
    pattern_counts = {
        'gender_style': 0,
        'age_price': 0,
        'region_city': 0,
        'age_star': 0,
        'age_score': 0
    }
    
    for item_id in recommendations:
        item_features = get_item_features(item_id, item_df)
        if not item_features:
            continue  # Bỏ qua nếu không tìm thấy features
        
        checks = check_pattern(gender, age, region, item_features)
        for pattern, matched in checks.items():
            if matched:
                pattern_counts[pattern] += 1
    
    # Đánh giá kết quả
    evaluation = evaluate_test_result(pattern_counts, age, len(recommendations))
    
    return {
        'user_id': user_id,
        'gender': gender,
        'age': age,
        'region': region,
        'recommendations': recommendations,
        'num_recommendations': len(recommendations),
        'pattern_counts': pattern_counts,
        'evaluation': evaluation,
        'error': None
    }


def main():
    parser = argparse.ArgumentParser(description='Test Phase 1 batch cho nhiều users')
    parser.add_argument('--model', type=str, default=None,
                        help='Đường dẫn đến model checkpoint (nếu không chỉ định sẽ dùng model mới nhất)')
    parser.add_argument('--num-users', type=int, default=100,
                        help='Số lượng users để test (default: 100)')
    parser.add_argument('--top-k', type=int, default=10,
                        help='Số lượng recommendations (default: 10)')
    parser.add_argument('--output', type=str, default=None,
                        help='Đường dẫn file JSON để lưu kết quả (nếu không chỉ định sẽ in ra console)')
    parser.add_argument('--quiet', action='store_true',
                        help='Chỉ in kết quả tổng hợp, không in chi tiết từng user')
    
    args = parser.parse_args()
    
    if not args.quiet:
        print("=" * 100)
        print("TEST PHASE 1 - BATCH TESTING")
        print("=" * 100)
        print()
    
    # Xác định model path
    if args.model:
        model_path = args.model
        if not os.path.exists(model_path):
            print(f"❌ ERROR: Model không tồn tại: {model_path}")
            return
    else:
        model_path = find_latest_checkpoint()
        if not model_path:
            print("❌ ERROR: Không tìm thấy checkpoint nào trong thư mục saved/")
            return
    
    if not args.quiet:
        print(f"📦 Model được sử dụng: {model_path}")
        print(f"📅 Model mtime: {os.path.getmtime(model_path)}")
        print()
    
    # Clear cache và load model
    if not args.quiet:
        print("🔄 Đang clear cache và load model...")
    clear_cache()
    try:
        config, model, dataset = load_model(model_path=model_path, force_reload=True)
        if not args.quiet:
            print(f"✅ Load model thành công!")
            print(f"   Dataset: {dataset.dataset_name}, Users: {dataset.user_num}, Items: {dataset.item_num}")
            print()
    except Exception as e:
        print(f"❌ ERROR: Không thể load model: {e}")
        return
    
    # Load user và item data
    if not args.quiet:
        print("📂 Đang load user và item data...")
    user_df, item_df = load_user_item_data()
    if not args.quiet:
        print(f"✅ Load thành công: {len(user_df)} users, {len(item_df)} items")
        print()
    
    # Chọn users để test
    num_users_to_test = min(args.num_users, len(user_df))
    test_users = user_df.head(num_users_to_test)
    
    if not args.quiet:
        print("=" * 100)
        print(f"BẮT ĐẦU TEST PHASE 1 (Top-{args.top_k}) - {num_users_to_test} users")
        print("=" * 100)
        print()
    
    # Test từng user
    results = []
    for idx, (_, user_row) in enumerate(test_users.iterrows(), 1):
        user_id = str(user_row['user_id'])
        
        if not args.quiet and idx % 10 == 0:
            print(f"Progress: {idx}/{num_users_to_test} users tested...")
        
        result = test_user(user_id, user_row, item_df, top_k=args.top_k)
        results.append(result)
        
        if not args.quiet and not args.quiet:
            eval_result = result.get('evaluation')
            if eval_result:
                status = "✅ PASS" if eval_result['passed'] else "❌ FAIL"
                print(f"User {idx}/{num_users_to_test}: ID={user_id}, {status}")
    
    # Tính tổng kết
    total_users = len(results)
    valid_results = [r for r in results if r.get('evaluation') is not None]
    passed_results = [r for r in valid_results if r['evaluation']['passed']]
    failed_results = [r for r in valid_results if not r['evaluation']['passed']]
    
    # Tính statistics
    if valid_results:
        avg_accuracy = sum(r['evaluation']['accuracy'] for r in valid_results) / len(valid_results)
        avg_score = sum(r['evaluation']['total_score'] for r in valid_results) / len(valid_results)
        avg_mandatory = sum(r['evaluation']['mandatory_passed_count'] for r in valid_results) / len(valid_results)
    else:
        avg_accuracy = 0.0
        avg_score = 0.0
        avg_mandatory = 0.0
    
    # Phân tích từng pattern
    pattern_stats = {
        'gender_style': {'passed': 0, 'total': 0},
        'age_price': {'passed': 0, 'total': 0},
        'region_city': {'passed': 0, 'total': 0},
        'age_star': {'passed': 0, 'total': 0},
        'age_score': {'passed': 0, 'total': 0}
    }
    
    for r in valid_results:
        eval_result = r['evaluation']
        for pattern_key, score_info in eval_result['pattern_scores'].items():
            if pattern_key in pattern_stats:
                pattern_stats[pattern_key]['total'] += 1
                if score_info['passed']:
                    pattern_stats[pattern_key]['passed'] += 1
    
    # Tạo summary
    summary = {
        'test_info': {
            'model_path': model_path,
            'model_mtime': os.path.getmtime(model_path),
            'num_users_tested': total_users,
            'num_valid_results': len(valid_results),
            'num_errors': total_users - len(valid_results),
            'top_k': args.top_k,
            'test_date': datetime.now().isoformat()
        },
        'overall_stats': {
            'total_users': total_users,
            'passed': len(passed_results),
            'failed': len(failed_results),
            'pass_rate': len(passed_results) / len(valid_results) if valid_results else 0.0,
            'avg_accuracy': avg_accuracy,
            'avg_score': avg_score,
            'avg_mandatory_passed': avg_mandatory
        },
        'pattern_stats': {
            k: {
                'passed': v['passed'],
                'total': v['total'],
                'pass_rate': v['passed'] / v['total'] if v['total'] > 0 else 0.0
            }
            for k, v in pattern_stats.items()
        },
        'results': results
    }
    
    # In kết quả
    if not args.quiet:
        print("\n" + "=" * 100)
        print("TỔNG KẾT")
        print("=" * 100)
        print()
        
        print(f"📊 Tổng số users tested: {total_users}")
        print(f"📊 Valid results: {len(valid_results)}")
        print(f"📊 Errors: {total_users - len(valid_results)}")
        print()
        
        print(f"📊 Passed: {len(passed_results)}/{len(valid_results)} ({len(passed_results)/len(valid_results):.1%})")
        print(f"📊 Failed: {len(failed_results)}/{len(valid_results)} ({len(failed_results)/len(valid_results):.1%})")
        print()
        
        print(f"📊 Average accuracy: {avg_accuracy:.2%}")
        print(f"📊 Average score: {avg_score:.2f}/{valid_results[0]['evaluation']['max_score'] if valid_results else 4}")
        print(f"📊 Average mandatory passed: {avg_mandatory:.2f}/3")
        print()
        
        print("📊 Phân tích từng pattern:")
        pattern_names = {
            'gender_style': 'Gender → Style',
            'age_price': 'Age → Price',
            'region_city': 'Region → City',
            'age_star': 'Age → Star (≥30)',
            'age_score': 'Age → Score (<30)'
        }
        for pattern_key, pattern_name in pattern_names.items():
            stats = pattern_stats[pattern_key]
            if stats['total'] > 0:
                pass_rate = stats['passed'] / stats['total']
                print(f"   {pattern_name}: {stats['passed']}/{stats['total']} users passed ({pass_rate:.2%})")
        
        print()
        print("=" * 100)
    
    # Lưu kết quả vào file nếu có chỉ định
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"✅ Đã lưu kết quả vào: {args.output}")
    
    return summary


if __name__ == '__main__':
    main()

