"""
Script test Phase 1 với model được chỉ định.

Script này cho phép test Phase 1 (Behavior Boost) với một model cụ thể,
bao gồm cả model mới ngay cả khi metrics thấp hơn model cũ.

Chức năng chính:
- Test Phase 1 cho một số lượng users được chỉ định
- Đánh giá recommendations dựa trên các patterns: Gender→Style, Age→Price, Region→City, Age→Star/Score
- Hiển thị kết quả chi tiết cho từng user và tổng kết

Usage:
    python test_phase1_with_model.py                    # Dùng model mới nhất
    python test_phase1_with_model.py --model saved/DeepFM-2025-01-15_10-30-00.pth  # Dùng model cụ thể
    python test_phase1_with_model.py --latest           # Dùng model mới nhất (explicit)
    python test_phase1_with_model.py --num-users 100   # Test 100 users
"""

import sys
import os
import pandas as pd
import argparse
from typing import List, Dict, Optional
import io
import glob

# Fix encoding cho Windows - xử lý lỗi Unicode khi in ra console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Thêm thư mục gốc vào path để import inference module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from inference import get_recommendations, load_model, clear_cache

# Import shared utilities từ cùng thư mục
sys.path.insert(0, os.path.dirname(__file__))
from test_utils import check_region_city_match, calculate_accuracy, evaluate_test_result

# Đường dẫn đến dataset và model
DATASET_DIR = 'dataset/hotel'
USER_FILE = os.path.join(DATASET_DIR, 'hotel.user')
ITEM_FILE = os.path.join(DATASET_DIR, 'hotel.item')
SAVED_DIR = 'saved'


def find_latest_checkpoint(saved_dir: str = SAVED_DIR) -> Optional[str]:
    """Tìm checkpoint mới nhất dựa trên thời gian chỉnh sửa file.
    
    Hàm này tìm tất cả các file checkpoint (DeepFM-*.pth) trong thư mục saved/
    và trả về file có thời gian chỉnh sửa mới nhất.
    
    Args:
        saved_dir: Đường dẫn đến thư mục chứa checkpoints (mặc định: 'saved')
    
    Returns:
        Đường dẫn đến checkpoint mới nhất, hoặc None nếu không tìm thấy.
    """
    pattern = os.path.join(saved_dir, "DeepFM-*.pth")
    checkpoints = glob.glob(pattern)
    if not checkpoints:
        return None
    # Tìm file có mtime (modification time) lớn nhất
    latest = max(checkpoints, key=os.path.getmtime)
    return latest


def load_user_item_data():
    """Load dữ liệu user và item từ dataset.
    
    Đọc file hotel.user và hotel.item, xử lý format RecBole
    (cột có format "name:type" cần tách lấy phần name).
    
    Returns:
        Tuple (user_df, item_df):
        - user_df: DataFrame chứa thông tin users (user_id, gender, age, region, ...)
        - item_df: DataFrame chứa thông tin items (item_id, style, price, star, score, city, ...)
    
    Note:
        Format RecBole: cột có dạng "column_name:type" (ví dụ: "user_id:token")
        Hàm này tách lấy phần "column_name" làm tên cột.
    """
    # Đọc file user với separator tab
    user_df = pd.read_csv(USER_FILE, sep='\t')
    # Xử lý format RecBole: tách phần tên cột (trước dấu ':')
    user_df.columns = [col.split(':')[0] for col in user_df.columns]
    
    # Đọc file item với separator tab
    item_df = pd.read_csv(ITEM_FILE, sep='\t')
    # Xử lý format RecBole: tách phần tên cột (trước dấu ':')
    item_df.columns = [col.split(':')[0] for col in item_df.columns]
    
    return user_df, item_df


def get_item_features(item_id: str, item_df: pd.DataFrame) -> Dict:
    """Lấy các features của một item từ DataFrame.
    
    Args:
        item_id: ID của item cần lấy features
        item_df: DataFrame chứa thông tin items
    
    Returns:
        Dict chứa features của item:
        {
            'item_id': str,
            'style': str,
            'price': float,
            'star': float,
            'score': float,
            'city': str
        }
        Nếu không tìm thấy item, trả về dict rỗng {}.
    """
    # Tìm item trong DataFrame (so sánh dạng string để tránh lỗi type)
    item_row = item_df[item_df['item_id'].astype(str) == str(item_id)]
    if len(item_row) == 0:
        return {}
    
    # Lấy dòng đầu tiên (nếu có nhiều kết quả)
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
    """Kiểm tra item có match các patterns Phase 1 không.
    
    Hàm này kiểm tra 5 patterns:
    1. Gender → Style: Style phù hợp với giới tính
    2. Age → Price: Giá phù hợp với độ tuổi
    3. Region → City: City khớp với region của user
    4. Age → Star: Nếu age >= 30, star >= 3.5
    5. Age → Score: Nếu age < 30, score >= 9.0
    
    Args:
        gender: Giới tính của user ('F' hoặc 'M')
        age: Tuổi của user
        region: Region của user (ví dụ: "Ho Chi Minh", "Da Nang")
        item_features: Dict chứa features của item (style, price, star, score, city)
    
    Returns:
        Dict chứa kết quả kiểm tra từng pattern:
        {
            'gender_style': bool,
            'age_price': bool,
            'region_city': bool,
            'age_star': bool (hoặc False nếu age < 30),
            'age_score': bool (hoặc False nếu age >= 30)
        }
    """
    checks = {
        'gender_style': False,
        'age_price': False,
        'region_city': False,
        'age_star': False,
        'age_score': False
    }
    
    # Pattern 1: Gender → Style
    # Kiểm tra style có chứa các từ khóa phù hợp với giới tính
    style = item_features.get('style', '').lower()
    style_tokens = set(style.split()) if style else set()
    
    if gender == 'F':
        # Nữ: ưu tiên romantic, love, modern, lively
        expected_tokens = {'romantic', 'love', 'modern', 'lively'}
        checks['gender_style'] = bool(expected_tokens & style_tokens)
    else:  # M
        # Nam: ưu tiên love, romantic, modern, lively
        expected_tokens = {'love', 'romantic', 'modern', 'lively'}
        checks['gender_style'] = bool(expected_tokens & style_tokens)
    
    # Pattern 2: Age → Price
    # Tuổi < 30: giá < 1,600,000 VND
    # Tuổi >= 30: giá >= 1,200,000 VND
    price = item_features.get('price', 0)
    if age < 30:
        checks['age_price'] = price < 1600000
    else:  # >= 30
        checks['age_price'] = price >= 1200000
    
    # Pattern 3: Region → City
    # Sử dụng hàm check_region_city_match để xử lý các trường hợp đặc biệt
    city = item_features.get('city', '')
    checks['region_city'] = check_region_city_match(city, region)
    
    # Pattern 4: Age → Star (chỉ áp dụng nếu age >= 30)
    if age >= 30:
        checks['age_star'] = item_features.get('star', 0) >= 3.5
    
    # Pattern 5: Age → Score (chỉ áp dụng nếu age < 30)
    if age < 30:
        checks['age_score'] = item_features.get('score', 0) >= 9.0
    
    return checks


def test_user(user_id: str, user_row: pd.Series, item_df: pd.DataFrame, top_k: int = 10) -> Dict:
    """Test Phase 1 cho một user và trả về kết quả chi tiết.
    
    Quy trình:
    1. Lấy recommendations từ inference module (chỉ Phase 1, không có similarity boost)
    2. Kiểm tra từng item có match patterns không
    3. Đếm số lượng items match mỗi pattern
    4. Đánh giá kết quả với logic linh hoạt (threshold động)
    
    Args:
        user_id: ID của user cần test
        user_row: Series chứa thông tin user (gender, age, region)
        item_df: DataFrame chứa thông tin items
        top_k: Số lượng recommendations cần lấy (mặc định: 10)
    
    Returns:
        Dict chứa kết quả test:
        {
            'user_id': str,
            'gender': str,
            'age': float,
            'region': str,
            'recommendations': List[str] - Danh sách item IDs được recommend
            'pattern_counts': Dict[str, int] - Số lượng items match mỗi pattern
            'evaluation': Dict - Kết quả đánh giá (passed, accuracy, scores, ...)
        }
        Nếu có lỗi khi lấy recommendations, trả về dict với recommendations rỗng.
    """
    gender = user_row['gender']
    age = float(user_row['age'])
    region = user_row['region']
    
    # Bước 1: Lấy recommendations từ inference module
    # Chỉ bật behavior boost (Phase 1), tắt similarity boost (Phase 2)
    try:
        recommendations = get_recommendations(
            user_id=user_id,
            top_k=top_k,
            use_behavior_boost=True,
            use_similarity_boost=False  # Phase 1 chỉ test behavior boost
        )
    except Exception as e:
        print(f"      ❌ Lỗi khi get recommendations: {e}")
        return {
            'user_id': user_id,
            'gender': gender,
            'age': age,
            'region': region,
            'recommendations': [],
            'total_patterns': 0,
            'matched_patterns': 0,
            'accuracy': 0.0,
            'pattern_details': {}
        }
    
    # Bước 2: Kiểm tra patterns cho từng item
    pattern_counts = {
        'gender_style': 0,
        'age_price': 0,
        'region_city': 0,
        'age_star': 0,
        'age_score': 0
    }
    
    for item_id in recommendations:
        # Lấy features của item
        item_features = get_item_features(item_id, item_df)
        if not item_features:
            continue  # Bỏ qua nếu không tìm thấy features
        
        # Kiểm tra item có match patterns không
        checks = check_pattern(gender, age, region, item_features)
        
        # Đếm số lượng items match mỗi pattern
        for pattern, matched in checks.items():
            if matched:
                pattern_counts[pattern] += 1
    
    # Bước 3: Đánh giá kết quả với logic linh hoạt
    evaluation = evaluate_test_result(pattern_counts, age, len(recommendations))
    
    return {
        'user_id': user_id,
        'gender': gender,
        'age': age,
        'region': region,
        'recommendations': recommendations,
        'pattern_counts': pattern_counts,
        'evaluation': evaluation
    }


def main():
    parser = argparse.ArgumentParser(description='Test Phase 1 với model được chỉ định')
    parser.add_argument('--model', type=str, default=None,
                        help='Đường dẫn đến model checkpoint (nếu không chỉ định sẽ dùng model mới nhất)')
    parser.add_argument('--latest', action='store_true',
                        help='Dùng model mới nhất (explicit)')
    parser.add_argument('--num-users', type=int, default=50,
                        help='Số lượng users để test (default: 50)')
    parser.add_argument('--top-k', type=int, default=10,
                        help='Số lượng recommendations (default: 10)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("TEST PHASE 1 VỚI MODEL ĐƯỢC CHỈ ĐỊNH")
    print("=" * 80)
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
    
    # Clear cache và load model với path cụ thể
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
    print("=" * 80)
    print(f"BẮT ĐẦU TEST PHASE 1 (Top-{args.top_k})")
    print("=" * 80)
    print()
    
    # Chọn users để test
    test_users = user_df.head(args.num_users)
    print(f"📊 Sẽ test {len(test_users)} users")
    print()
    
    results = []
    for idx, (_, user_row) in enumerate(test_users.iterrows(), 1):
        user_id = str(user_row['user_id'])
        gender = user_row['gender']
        age = float(user_row['age'])
        region = user_row['region']
        
        print(f"User {idx}/{len(test_users)}: ID={user_id}, Gender={gender}, Age={age:.0f}, Region={region}")
        
        result = test_user(user_id, user_row, item_df, top_k=args.top_k)
        results.append(result)
        
        # Hiển thị kết quả
        eval_result = result['evaluation']
        pattern_counts = result['pattern_counts']
        
        print(f"   Recommendations: {len(result['recommendations'])} items")
        print(f"   Pattern details:")
        print(f"      Gender→Style: {pattern_counts['gender_style']} items (threshold: {eval_result['pattern_scores']['gender_style']['threshold']}) {'✅' if eval_result['pattern_scores']['gender_style']['passed'] else '❌'}")
        print(f"      Age→Price: {pattern_counts['age_price']} items (threshold: {eval_result['pattern_scores']['age_price']['threshold']}) {'✅' if eval_result['pattern_scores']['age_price']['passed'] else '❌'}")
        print(f"      Region→City: {pattern_counts['region_city']} items (threshold: {eval_result['pattern_scores']['region_city']['threshold']}) {'✅' if eval_result['pattern_scores']['region_city']['passed'] else '❌'}")
        if age >= 30:
            print(f"      Age→Star (≥30): {pattern_counts['age_star']} items (threshold: {eval_result['pattern_scores']['age_star']['threshold']}) {'✅' if eval_result['pattern_scores']['age_star']['passed'] else '❌'}")
        if age < 30:
            print(f"      Age→Score (<30): {pattern_counts['age_score']} items (threshold: {eval_result['pattern_scores']['age_score']['threshold']}) {'✅' if eval_result['pattern_scores']['age_score']['passed'] else '❌'}")
        print(f"   Mandatory patterns passed: {eval_result['mandatory_passed_count']}/3")
        print(f"   Total score: {eval_result['total_score']}/{eval_result['max_score']}")
        print(f"   Accuracy: {eval_result['accuracy']:.2%}")
        print(f"   Status: {'✅ PASS' if eval_result['passed'] else '❌ FAIL'}")
        print()
    
    # Tính tổng kết
    print("=" * 80)
    print("TỔNG KẾT")
    print("=" * 80)
    print()
    
    total_users = len(results)
    passed_count = sum(1 for r in results if r['evaluation']['passed'])
    avg_accuracy = sum(r['evaluation']['accuracy'] for r in results) / total_users if total_users > 0 else 0
    
    print(f"📊 Tổng số users tested: {total_users}")
    print(f"📊 Passed: {passed_count}/{total_users} ({passed_count/total_users:.1%})")
    print(f"📊 Failed: {total_users - passed_count}/{total_users} ({(total_users-passed_count)/total_users:.1%})")
    print(f"📊 Average accuracy: {avg_accuracy:.2%}")
    print()
    
    # Phân tích từng pattern
    pattern_names = {
        'gender_style': 'Gender → Style',
        'age_price': 'Age → Price',
        'region_city': 'Region → City',
        'age_star': 'Age → Star (≥30)',
        'age_score': 'Age → Score (<30)'
    }
    
    print("📊 Phân tích từng pattern (với threshold):")
    for pattern_key, pattern_name in pattern_names.items():
        # Đếm số users có pattern này passed
        passed_users = sum(1 for r in results 
                          if pattern_key in r['evaluation']['pattern_scores'] 
                          and r['evaluation']['pattern_scores'][pattern_key]['passed'])
        pass_rate = passed_users / total_users if total_users > 0 else 0
        print(f"   {pattern_name}: {passed_users}/{total_users} users passed ({pass_rate:.2%})")
    
    print()
    print("=" * 80)
    print("HOÀN TẤT TEST")
    print("=" * 80)


if __name__ == '__main__':
    main()



