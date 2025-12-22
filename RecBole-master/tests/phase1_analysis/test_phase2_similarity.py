"""
Script test Phase 2 - Similarity Boost chi tiết.

Script này chứng minh Phase 2 hoạt động đúng bằng cách:
1. Tạo user actions (click hotels cụ thể) vào log file test riêng
2. So sánh recommendations với/không có similarity boost
3. Phân tích items nào được boost do similarity
4. Hiển thị similarity scores và features tương tự giữa clicked items và recommended items

Cơ chế test:
- Tạo file log test riêng (test_phase2_actions.log) để không ảnh hưởng đến hệ thống
- Chạy Phase 1 (không có similarity boost) để có baseline
- Chạy Phase 1 + Phase 2 (có similarity boost) để so sánh
- Phân tích sự khác biệt và items được boost

Usage:
    python test_phase2_similarity.py --user-id 123 --item-id 50     # Test 1 user với 1 item
    python test_phase2_similarity.py --user-id 123 --item-id 50,51  # Test với nhiều items
    python test_phase2_similarity.py --model saved/xxx.pth          # Test với model cụ thể
    python test_phase2_similarity.py --auto                         # Tự động chọn user và item
    # Chạy từ thư mục gốc RecBole-master:
    python tests/phase1_analysis/test_phase2_similarity.py --user-id 123 --item-id 50
"""

import sys
import os
import pandas as pd
import argparse
import json
import time
from typing import List, Dict, Optional, Set, Tuple
import io
import glob
from contextlib import contextmanager
import logging

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Suppress RecBole logging - Phải làm TRƯỚC khi import
logging.basicConfig(level=logging.ERROR)
logging.getLogger('recbole').setLevel(logging.ERROR)
logging.getLogger().setLevel(logging.ERROR)
os.environ['RECBOLE_QUIET'] = '1'
os.environ['RECBOLE_LOG_LEVEL'] = 'ERROR'

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Redirect stdout/stderr để suppress RecBole output
@contextmanager
def suppress_output():
    """Context manager để tạm thời suppress stdout/stderr.
    
    Hữu ích khi cần giảm log output từ RecBole hoặc các thư viện khác
    trong quá trình test để output dễ đọc hơn.
    
    Usage:
        with suppress_output():
            # Code ở đây sẽ không in ra console
            result = some_function()
    
    Note:
        Context manager này redirect stdout/stderr vào /dev/null (hoặc NUL trên Windows)
        trong thời gian thực thi code block.
    """
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    devnull = open(os.devnull, 'w', encoding='utf-8')
    try:
        sys.stdout = devnull
        sys.stderr = devnull
        yield
    finally:
        # Khôi phục stdout/stderr về trạng thái ban đầu
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        devnull.close()

from inference import get_recommendations, load_model, clear_cache, calculate_item_similarity

# Paths - Tìm thư mục gốc của project (chứa inference.py)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # tests/phase1_analysis
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))  # Thư mục gốc RecBole-master

DATASET_DIR = os.path.join(PROJECT_ROOT, 'dataset', 'hotel')
USER_FILE = os.path.join(DATASET_DIR, 'hotel.user')
ITEM_FILE = os.path.join(DATASET_DIR, 'hotel.item')
# LOG_FILE: File log test riêng, tạo trong cùng thư mục với script
# KHÔNG dùng data/user_actions.log vì đó là tài nguyên của hệ thống khác
LOG_FILE = os.path.join(SCRIPT_DIR, 'test_phase2_actions.log')
SAVED_DIR = os.path.join(PROJECT_ROOT, 'saved')


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


def format_currency(amount: float) -> str:
    """Format số tiền."""
    return f"{amount:,.0f} VND"


def write_test_action(user_id: str, item_id: str, action_type: str = "click", log_file: str = None):
    """Ghi test action vào log file.
    
    Hàm này ghi một action (click) vào log file để simulate user behavior.
    Format: JSON Lines (mỗi dòng là một JSON object).
    
    Args:
        user_id: ID của user thực hiện action
        item_id: ID của item được click
        action_type: Loại action (mặc định: "click")
        log_file: Đường dẫn file log (mặc định: LOG_FILE)
    
    Returns:
        True nếu ghi thành công, False nếu có lỗi.
    
    Note:
        File log được append (mode 'a') để có thể ghi nhiều actions.
        Format timestamp: Unix timestamp (seconds since epoch).
    """
    if log_file is None:
        log_file = LOG_FILE
    
    # Tạo action object với format chuẩn
    action = {
        "user_id": int(user_id) if str(user_id).isdigit() else user_id,
        "item_id": int(item_id) if str(item_id).isdigit() else item_id,
        "action_type": action_type,
        "timestamp": time.time()  # Unix timestamp (seconds)
    }
    
    try:
        # Ghi vào file log (append mode)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(action) + '\n')
        return True
    except Exception as e:
        print(f"❌ Lỗi khi ghi action vào log ({log_file}): {e}")
        return False


def analyze_similarity_items(
    clicked_item_id: str,
    recommendations_with_boost: List[str],
    recommendations_without_boost: List[str],
    item_df: pd.DataFrame,
    dataset,
    similarity_threshold: float = 0.5
) -> Dict:
    """Phân tích items nào được boost do similarity."""
    
    clicked_features = get_item_features(clicked_item_id, item_df)
    if not clicked_features:
        return {}
    
    # Tính similarity matrix (hoặc lấy từ cache)
    try:
        similarity_dict = calculate_item_similarity(dataset, similarity_threshold=similarity_threshold)
    except Exception as e:
        print(f"⚠️ Lỗi khi tính similarity: {e}")
        return {}
    
    # Tìm items được boost lên (có trong với boost nhưng không có trong không boost, hoặc vị trí cao hơn)
    boosted_items = []
    for idx, item_id in enumerate(recommendations_with_boost):
        item_features = get_item_features(item_id, item_df)
        if not item_features:
            continue
        
        # Tìm vị trí trong recommendations không có boost
        try:
            idx_without = recommendations_without_boost.index(item_id)
        except ValueError:
            idx_without = len(recommendations_without_boost)  # Không có trong list
        
        # Kiểm tra similarity với clicked item
        similarity_score = 0.0
        
        # Try different key formats (int or string)
        clicked_keys = [str(clicked_item_id)]
        item_keys = [str(item_id)]
        
        try:
            clicked_keys.append(int(clicked_item_id))
        except (ValueError, TypeError):
            pass
        
        try:
            item_keys.append(int(item_id))
        except (ValueError, TypeError):
            pass
        
        for clicked_key in clicked_keys:
            if clicked_key in similarity_dict:
                for item_key in item_keys:
                    if item_key in similarity_dict[clicked_key]:
                        similarity_score = similarity_dict[clicked_key][item_key]
                        break
                if similarity_score > 0:
                    break
        
        if similarity_score >= similarity_threshold:
            boosted_items.append({
                'item_id': item_id,
                'features': item_features,
                'similarity': similarity_score,
                'rank_with_boost': idx + 1,
                'rank_without_boost': idx_without + 1 if idx_without < len(recommendations_without_boost) else None,
                'boosted': idx_without >= len(recommendations_without_boost) or idx < idx_without
            })
    
    return {
        'clicked_item': clicked_features,
        'similarity_dict': similarity_dict.get(str(clicked_item_id), {}),
        'boosted_items': boosted_items
    }


def print_explanations():
    """In phần giải thích các thuật ngữ."""
    print("=" * 100)
    print("GIẢI THÍCH THUẬT NGỮ")
    print("=" * 100)
    print()
    print("📚 CÁC KHÁI NIỆM:")
    print("   1. PHASE 1: Gợi ý dựa trên pattern học được từ dataset (Gender→Style, Age→Price, Region→City)")
    print("   2. PHASE 2: Boost thêm các hotels tương tự với hotels user đã click gần đây")
    print("   3. SIMILARITY: Độ tương đồng giữa 2 hotels (0.0-1.0), tính dựa trên:")
    print("      - Style: Jaccard similarity (có chung từ khóa style)")
    print("      - City: Giống nhau = 1.0, khác = 0.0")
    print("      - Price/Star/Score: Khoảng cách chuẩn hóa (càng gần nhau càng cao)")
    print("   4. BOOST: Tăng điểm/ưu tiên cho hotels tương tự, đẩy chúng lên top recommendations")
    print()
    print("📊 KÝ HIỆU:")
    print("   ✅ = Giống nhau / Phù hợp")
    print("   ❌ = Khác nhau / Không phù hợp")
    print("   ↑ = Tăng thứ hạng (tốt hơn)")
    print("   ↓ = Giảm thứ hạng (tệ hơn)")
    print("   → = Thay đổi")
    print()
    print("=" * 100)
    print()


def test_phase2_for_user(
    user_id: str,
    item_ids: List[str],
    item_df: pd.DataFrame,
    dataset,
    model_path: Optional[str] = None,
    top_k: int = 20,
    similarity_threshold: float = 0.5
):
    """Test Phase 2 cho một user với các items cụ thể."""
    
    print("=" * 100)
    print(f"TEST PHASE 2: USER {user_id} - CLICK {len(item_ids)} ITEM(S)")
    print("=" * 100)
    print()
    
    # 1. Hiển thị thông tin items sẽ click
    print("📋 THÔNG TIN ITEMS SẼ CLICK:")
    print("-" * 100)
    clicked_items_info = []
    for item_id in item_ids:
        features = get_item_features(item_id, item_df)
        if features:
            clicked_items_info.append(features)
            print(f"   Item {item_id}:")
            print(f"      - Style: {features['style']}")
            print(f"      - City: {features['city']}")
            print(f"      - Price: {format_currency(features['price'])}")
            print(f"      - Star: {features['star']:.1f}")
            print(f"      - Score: {features['score']:.1f}")
        else:
            print(f"   ⚠️ Item {item_id}: Không tìm thấy")
    print()
    
    # 2. Ghi actions vào log (xóa file cũ trước nếu có để test clean)
    print(f"📝 GHI ACTIONS VÀO LOG: {LOG_FILE}")
    # Xóa file log cũ nếu có để bắt đầu test clean
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
        print(f"   🗑️ Đã xóa file log cũ")
    
    for item_id in item_ids:
        if write_test_action(user_id, item_id, "click", LOG_FILE):
            print(f"   ✅ Đã ghi action: User {user_id} click Item {item_id}")
        else:
            print(f"   ❌ Lỗi khi ghi action: User {user_id} click Item {item_id}")
    print()
    
    # 3. Clear cache và load model
    print("🔄 Loading model...")
    clear_cache()
    try:
        with suppress_output():
            config, model, dataset_loaded = load_model(model_path=model_path, force_reload=True)
        print(f"   ✅ Model loaded: {dataset_loaded.dataset_name}")
    except Exception as e:
        print(f"   ❌ Lỗi khi load model: {e}")
        return
    print()
    
    # 4. Test WITHOUT similarity boost (Phase 1 only)
    print("🔍 ĐANG CHẠY PHASE 1 (chỉ pattern từ dataset, không boost similarity)...")
    try:
        with suppress_output():
            recs_phase1 = get_recommendations(
                user_id=user_id,
                top_k=top_k,
                use_behavior_boost=True,
                use_similarity_boost=False,  # Phase 1 only
                log_file=LOG_FILE  # Dùng file log test riêng
            )
        print(f"   ✅ Hoàn thành! Nhận được {len(recs_phase1)} recommendations")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
        recs_phase1 = []
    print()
    
    # 5. Test WITH similarity boost (Phase 1 + Phase 2)
    print("🔍 ĐANG CHẠY PHASE 1 + PHASE 2 (có boost similarity với hotels đã click)...")
    try:
        with suppress_output():
            recs_phase2 = get_recommendations(
                user_id=user_id,
                top_k=top_k,
                use_behavior_boost=True,
                use_similarity_boost=True,  # Phase 2 enabled
                similarity_threshold=similarity_threshold,
                log_file=LOG_FILE  # Dùng file log test riêng
            )
        print(f"   ✅ Hoàn thành! Nhận được {len(recs_phase2)} recommendations")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
        recs_phase2 = []
    print()
    
    # 6. So sánh và phân tích
    print("=" * 100)
    print("BẢNG SO SÁNH PHASE 1 vs PHASE 2")
    print("=" * 100)
    print()
    
    if not recs_phase1 or not recs_phase2:
        print("   ⚠️ Không thể so sánh (thiếu recommendations)")
        return
    
    # Lấy thông tin clicked items
    clicked_items_features = {}
    for clicked_item_id in item_ids:
        clicked_items_features[clicked_item_id] = get_item_features(clicked_item_id, item_df)
    
    # Tính similarity matrix
    try:
        with suppress_output():
            similarity_dict = calculate_item_similarity(dataset_loaded, similarity_threshold=similarity_threshold)
    except Exception as e:
        print(f"⚠️ Lỗi khi tính similarity: {e}")
        similarity_dict = {}
    
    # Hiển thị bảng so sánh
    print("📋 ITEMS ĐÃ CLICK (user đã tương tác gần đây):")
    print("-" * 100)
    for clicked_item_id, features in clicked_items_features.items():
        print(f"   Item {clicked_item_id}: {features.get('style', 'N/A')} | {features.get('city', 'N/A')} | {format_currency(features.get('price', 0))} | ⭐{features.get('star', 0):.1f} | ⭐⭐⭐⭐⭐ {features.get('score', 0):.1f}")
    print()
    
    print("📊 BẢNG SO SÁNH TOP RECOMMENDATIONS:")
    print("-" * 100)
    print(f"{'Rank (P1)':<12} {'Item ID':<10} {'Style':<20} {'City':<15} {'Price':<15} {'Star':<6} {'Score':<7} {'Similarity':<12} {'Ghi chú'}")
    print(f"{'(P2)':<12} {'':<10} {'':<20} {'':<15} {'':<15} {'':<6} {'':<7} {'(>=0.5=boost)':<12} {'':<20}")
    print("-" * 100)
    
    # Hiển thị top recommendations từ Phase 1 và Phase 2 song song
    max_items = max(len(recs_phase1), len(recs_phase2))
    
    # Tạo dict để tra cứu nhanh
    phase1_ranks = {item: idx + 1 for idx, item in enumerate(recs_phase1)}
    phase2_ranks = {item: idx + 1 for idx, item in enumerate(recs_phase2)}
    
    displayed_items = set()
    
    for rank in range(1, min(max_items + 1, top_k + 1)):
        # Lấy item từ Phase 2 (vì đây là kết quả cuối cùng)
        if rank <= len(recs_phase2):
            item_id_p2 = recs_phase2[rank - 1]
            features_p2 = get_item_features(item_id_p2, item_df)
            
            # Tính similarity với clicked items
            max_similarity = 0.0
            for clicked_item_id in item_ids:
                clicked_key = str(clicked_item_id)
                item_key = str(item_id_p2)
                sim = similarity_dict.get(clicked_key, {}).get(item_key, 0.0)
                if isinstance(sim, (int, float)):
                    max_similarity = max(max_similarity, sim)
                # Thử với int keys
                try:
                    sim_int = similarity_dict.get(int(clicked_item_id), {}).get(int(item_id_p2), 0.0)
                    if isinstance(sim_int, (int, float)):
                        max_similarity = max(max_similarity, sim_int)
                except (ValueError, TypeError):
                    pass
            
            rank_p1 = phase1_ranks.get(item_id_p2, None)
            
            # Xác định ghi chú (đơn giản, không nói tăng/giảm)
            if item_id_p2 not in recs_phase1:
                note = "🆕 MỚI"
            elif max_similarity >= similarity_threshold:
                note = "[SIMILARITY BOOST]"
            else:
                note = ""
            
            style_str = features_p2.get('style', 'N/A')[:18]
            city_str = features_p2.get('city', 'N/A')[:13]
            price_str = format_currency(features_p2.get('price', 0))
            star_str = f"{features_p2.get('star', 0):.1f}"
            score_str = f"{features_p2.get('score', 0):.1f}"
            sim_str = f"{max_similarity:.3f}" if max_similarity > 0 else "-"
            
            # Hiển thị rank Phase 1 bên cạnh
            rank_p1_str = f"({phase1_ranks.get(item_id_p2, 'N/A')})" if phase1_ranks.get(item_id_p2) else "(N/A)"
            rank_display = f"{rank} {rank_p1_str}"
            
            print(f"{rank_display:<12} {item_id_p2:<10} {style_str:<20} {city_str:<15} {price_str:<15} {star_str:<6} {score_str:<7} {sim_str:<12} {note}")
            displayed_items.add(item_id_p2)
    
    print()
    print("📝 GHI CHÚ:")
    print("   - Rank (P2) (P1): Thứ hạng trong Phase 2, trong ngoặc là thứ hạng Phase 1")
    print("   - Similarity: Độ tương đồng với item đã click (>= 0.5 = được boost, '-' = không có similarity hoặc < 0.5)")
    print("   - 🆕 MỚI: Item chỉ có trong Phase 2 (được boost lên từ ngoài top)")
    print("   - ↑/↓: Thay đổi thứ hạng so với Phase 1")
    print("   - [SIMILARITY BOOST]: Item có similarity >= threshold, được boost")
    print()
    
    # 7. Phân tích chi tiết các items được boost
    print("=" * 100)
    print("CHI TIẾT CƠ CHẾ BOOST")
    print("=" * 100)
    print()
    
    set_phase1 = set(recs_phase1)
    set_phase2 = set(recs_phase2)
    new_items = set_phase2 - set_phase1
    
    # Tìm các items được boost (có similarity với clicked items)
    # Dùng set để tránh trùng lặp
    boosted_items_map = {}  # {item_id: item_info}
    
    for item_id in recs_phase2:
        if item_id in boosted_items_map:  # Đã xử lý rồi, skip
            continue
            
        features = get_item_features(item_id, item_df)
        if not features:  # Không tìm thấy features, skip
            continue
            
        max_similarity = 0.0
        matched_clicked_item = None
        
        for clicked_item_id in item_ids:
            clicked_key = str(clicked_item_id)
            item_key = str(item_id)
            sim = similarity_dict.get(clicked_key, {}).get(item_key, 0.0)
            if isinstance(sim, (int, float)) and sim > max_similarity:
                max_similarity = sim
                matched_clicked_item = clicked_item_id
            # Thử với int keys
            try:
                sim_int = similarity_dict.get(int(clicked_item_id), {}).get(int(item_id), 0.0)
                if isinstance(sim_int, (int, float)) and sim_int > max_similarity:
                    max_similarity = sim_int
                    matched_clicked_item = clicked_item_id
            except (ValueError, TypeError):
                pass
        
        if max_similarity >= similarity_threshold:
            rank_p2 = phase2_ranks.get(item_id, 999)
            rank_p1 = phase1_ranks.get(item_id, None)
            boosted_items_map[item_id] = {
                'item_id': item_id,
                'features': features,
                'similarity': max_similarity,
                'clicked_item': matched_clicked_item,
                'rank_p1': rank_p1,
                'rank_p2': rank_p2,
                'is_new': item_id not in recs_phase1
            }
    
    boosted_items_detail = list(boosted_items_map.values())
    
    if boosted_items_detail:
        # Sắp xếp theo thứ hạng Phase 2 (rank_p2) tăng dần
        boosted_items_detail.sort(key=lambda x: x['rank_p2'])
        
        print(f"✅ Tìm thấy {len(boosted_items_detail)} items được boost do similarity (>= {similarity_threshold}):")
        print()
        
        for item_info in boosted_items_detail:
            item_id = item_info['item_id']
            features = item_info['features']
            sim = item_info['similarity']
            clicked_id = item_info['clicked_item']
            rank_p1 = item_info['rank_p1']
            rank_p2 = item_info['rank_p2']
            is_new = item_info['is_new']
            
            clicked_features = clicked_items_features.get(str(clicked_id), {})
            
            print(f"Item {item_id} (Similarity: {sim:.3f} với Item {clicked_id}):")
            print(f"   📍 Thứ hạng: {rank_p2} (Phase 2)", end="")
            if rank_p1:
                print(f" / {rank_p1} (Phase 1)")
            else:
                print(f" / N/A (Phase 1) - 🆕 MỚI")
            
            print(f"   🏨 Style: {features.get('style', 'N/A')}", end="")
            if clicked_features.get('style', '').lower() == features.get('style', '').lower():
                print(" ✅ (giống clicked item)")
            else:
                print(" ❌ (khác clicked item)")
            
            print(f"   📍 City: {features.get('city', 'N/A')}", end="")
            if clicked_features.get('city', '').lower() == features.get('city', '').lower():
                print(" ✅ (giống clicked item)")
            else:
                print(" ❌ (khác clicked item)")
            
            price_diff_pct = 0.0
            if clicked_features.get('price', 0) > 0:
                price_diff_pct = abs(clicked_features.get('price', 0) - features.get('price', 0)) / clicked_features.get('price', 0) * 100
            print(f"   💰 Price: {format_currency(features.get('price', 0))}", end="")
            if price_diff_pct < 30:
                print(f" ✅ (chênh {price_diff_pct:.1f}% - gần với clicked item)")
            else:
                print(f" ❌ (chênh {price_diff_pct:.1f}% - khác nhiều với clicked item)")
            
            print(f"   ⭐ Star: {features.get('star', 0):.1f} (clicked: {clicked_features.get('star', 0):.1f})")
            print(f"   ⭐⭐⭐⭐⭐ Score: {features.get('score', 0):.1f} (clicked: {clicked_features.get('score', 0):.1f})")
            print()
    else:
        print(f"⚠️ Không tìm thấy items nào có similarity >= {similarity_threshold}")
        print()
    
    # 8. Kết luận
    print("=" * 100)
    print("KẾT LUẬN")
    print("=" * 100)
    print()
    
    common_items = set_phase1 & set_phase2
    rank_improved = [item_id for item_id in common_items 
                     if phase2_ranks.get(item_id, 999) < phase1_ranks.get(item_id, 0)]
    
    print(f"📊 Tổng kết:")
    print(f"   - Items mới xuất hiện trong Phase 2: {len(new_items)}")
    print(f"   - Items được boost lên (rank tốt hơn): {len(rank_improved)}")
    print(f"   - Items có similarity >= {similarity_threshold}: {len(boosted_items_detail)}")
    print()
    
    if len(new_items) > 0 or len(rank_improved) > 0:
        print("✅ Phase 2 HOẠT ĐỘNG ĐÚNG!")
        print("   → Similarity boost đã thành công boost các hotels tương tự với hotels user đã click")
        print("   → Các hotels có Style/City/Price/Star/Score tương tự đã được đẩy lên top recommendations")
    else:
        print("⚠️ Phase 2: Chưa thấy sự khác biệt rõ ràng")
        print(f"   → Có thể similarity threshold ({similarity_threshold}) quá cao")
        print("   → Hoặc không có đủ items tương tự trong dataset")
    
    print()
    print("=" * 100)
    print()


def auto_select_user_and_items(user_df: pd.DataFrame, item_df: pd.DataFrame) -> Tuple[str, List[str]]:
    """Tự động chọn user và items phù hợp để test."""
    # Chọn user đầu tiên
    user_id = str(user_df.iloc[0]['user_id'])
    
    # Chọn items có style rõ ràng và features đa dạng
    # Ưu tiên items có style "romantic" hoặc "modern" (dễ tìm similarity)
    item_df_sample = item_df[item_df['style'].str.contains('romantic|modern|love', case=False, na=False)]
    
    if len(item_df_sample) >= 2:
        selected_items = item_df_sample.head(2)['item_id'].astype(str).tolist()
    else:
        # Fallback: chọn 2 items đầu tiên
        selected_items = item_df.head(2)['item_id'].astype(str).tolist()
    
    return user_id, selected_items


def main():
    parser = argparse.ArgumentParser(description='Test Phase 2 - Similarity Boost')
    parser.add_argument('--user-id', type=str, default=None,
                        help='User ID để test')
    parser.add_argument('--item-id', type=str, default=None,
                        help='Item ID(s) để click (có thể nhiều, phân cách bằng dấu phẩy)')
    parser.add_argument('--model', type=str, default=None,
                        help='Đường dẫn đến model checkpoint')
    parser.add_argument('--top-k', type=int, default=20,
                        help='Số lượng recommendations (default: 20)')
    parser.add_argument('--similarity-threshold', type=float, default=0.5,
                        help='Similarity threshold (default: 0.5)')
    parser.add_argument('--auto', action='store_true',
                        help='Tự động chọn user và items')
    
    args = parser.parse_args()
    
    print_explanations()
    
    print("=" * 100)
    print("TEST PHASE 2 - SIMILARITY BOOST")
    print("=" * 100)
    print()
    
    # Load data
    print("📂 Loading user và item data...")
    user_df, item_df = load_user_item_data()
    print(f"   ✅ Load thành công: {len(user_df)} users, {len(item_df)} items")
    print()
    
    # Xác định user và items
    if args.auto:
        user_id, item_ids = auto_select_user_and_items(user_df, item_df)
        print(f"🔍 Auto-select:")
        print(f"   - User ID: {user_id}")
        print(f"   - Item IDs: {', '.join(item_ids)}")
        print()
    elif args.user_id and args.item_id:
        user_id = args.user_id
        item_ids = [x.strip() for x in args.item_id.split(',')]
    else:
        print("❌ ERROR: Cần chỉ định --user-id và --item-id, hoặc dùng --auto")
        return
    
    # Validate user
    user_row = user_df[user_df['user_id'].astype(str) == str(user_id)]
    if len(user_row) == 0:
        print(f"❌ ERROR: Không tìm thấy user {user_id}")
        return
    
    # Validate items
    valid_item_ids = []
    for item_id in item_ids:
        item_row = item_df[item_df['item_id'].astype(str) == str(item_id)]
        if len(item_row) > 0:
            valid_item_ids.append(item_id)
        else:
            print(f"⚠️ WARNING: Không tìm thấy item {item_id}, bỏ qua")
    
    if not valid_item_ids:
        print("❌ ERROR: Không có item hợp lệ nào")
        return
    
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
    
    print(f"📦 Model được sử dụng: {model_path}")
    print()
    
    # Test
    # Load model một lần để lấy dataset
    clear_cache()
    try:
        with suppress_output():
            config, model, dataset = load_model(model_path=model_path, force_reload=True)
    except Exception as e:
        print(f"❌ ERROR: Không thể load model: {e}")
        return
    
    # Chạy test
    test_phase2_for_user(
        user_id=user_id,
        item_ids=valid_item_ids,
        item_df=item_df,
        dataset=dataset,
        model_path=model_path,
        top_k=args.top_k,
        similarity_threshold=args.similarity_threshold
    )


if __name__ == '__main__':
    main()

