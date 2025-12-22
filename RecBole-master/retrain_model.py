"""
Retraining Pipeline - Tự động retrain model mỗi ngày 1 lần.

Script này thực hiện quy trình retraining tự động:
1. Kiểm tra số lượng interactions mới (so với lần train trước)
2. Backup checkpoint cũ trước khi retrain (để có thể rollback nếu cần)
3. Train model mới với toàn bộ dữ liệu (cũ + mới)
4. So sánh metrics (RMSE, MAE) với model cũ
5. Lưu model mới (ngay cả khi metrics không tốt hơn - để có dữ liệu mới nhất)
6. Clear model cache để load model mới

Lưu ý: Model mới luôn được lưu, không phụ thuộc vào metrics. 
Điều này đảm bảo model luôn được cập nhật với dữ liệu mới nhất.
"""
import os
import sys
import json
import shutil
import glob
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple
import io

# Fix encoding cho Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Import RecBole
from recbole.quick_start import run
from recbole.quick_start import load_data_and_model
from recbole.config import Config

# Import inference để clear cache
try:
    from inference import clear_cache, _get_latest_checkpoint
except ImportError:
    print("[WARNING] Không thể import inference module, sẽ không clear cache")
    clear_cache = None
    _get_latest_checkpoint = None

# ============================================================================
# CONSTANTS
# ============================================================================

SAVED_DIR = "saved"
DATASET_DIR = "dataset/hotel"
CONFIG_FILE = "deepfm_config.yaml"
RETRAIN_HISTORY_FILE = "retrain_history.json"
MIN_NEW_INTERACTIONS = 100  # Số interactions mới tối thiểu để retrain
BACKUP_DIR = os.path.join(SAVED_DIR, "backups")


def load_retrain_history() -> Dict:
    """
    Load lịch sử retraining từ file JSON.
    
    History chứa:
    - last_retrain_time: Thời gian retrain cuối cùng
    - last_dataset_size: Số lượng interactions tại thời điểm retrain cuối
    - last_retrain_metrics: Metrics của model cuối cùng
    - retrain_count: Số lần đã retrain
    - backups: Danh sách các backup đã tạo
    
    Returns:
        Dictionary chứa lịch sử retraining, hoặc empty dict nếu chưa có
    """
    if os.path.exists(RETRAIN_HISTORY_FILE):
        try:
            with open(RETRAIN_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Không thể load retrain history: {e}")
            return {}
    return {}


def save_retrain_history(history: Dict):
    """
    Lưu lịch sử retraining vào file JSON.
    
    Args:
        history: Dictionary chứa lịch sử retraining
    """
    try:
        with open(RETRAIN_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARNING] Không thể save retrain history: {e}")


def get_dataset_size() -> int:
    """
    Đếm số dòng interactions trong dataset (hotel.inter).
    
    Returns:
        Số lượng interactions (không tính header)
    """
    inter_file = os.path.join(DATASET_DIR, "hotel.inter")
    if not os.path.exists(inter_file):
        return 0
    try:
        with open(inter_file, 'r', encoding='utf-8') as f:
            # Đếm số dòng, trừ header
            lines = f.readlines()
            return len(lines) - 1 if lines else 0
    except Exception as e:
        print(f"[ERROR] Không thể đọc dataset: {e}")
        return 0


def get_latest_checkpoint_metrics() -> Optional[Dict]:
    """
    Lấy metrics từ checkpoint mới nhất hoặc từ history.
    
    Ưu tiên lấy từ history (nhanh hơn) vì không cần load checkpoint.
    
    Returns:
        Dictionary chứa metrics (RMSE, MAE, ...) hoặc None nếu không có
    """
    # Ưu tiên lấy từ history (nhanh hơn, không cần load checkpoint)
    history = load_retrain_history()
    if 'last_retrain_metrics' in history:
        return history['last_retrain_metrics']
    
    # Nếu không có trong history, thử load từ checkpoint
    if _get_latest_checkpoint is None:
        return None
    
    checkpoint_path = _get_latest_checkpoint(SAVED_DIR)
    if checkpoint_path is None:
        return None
    
    # Không load checkpoint để lấy metrics (tốn thời gian)
    # Thay vào đó, sẽ lấy từ history sau khi train xong
    return None


def backup_checkpoint(checkpoint_path: str) -> Optional[str]:
    """
    Backup checkpoint cũ vào thư mục backups trước khi retrain.
    
    Backup được đặt tên với timestamp để tránh trùng lặp.
    
    Args:
        checkpoint_path: Đường dẫn đến checkpoint cần backup
    
    Returns:
        Đường dẫn đến file backup, hoặc None nếu backup thất bại
    """
    if not os.path.exists(checkpoint_path):
        return None
    
    # Tạo thư mục backups nếu chưa có
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Tạo tên file backup với timestamp
    checkpoint_name = os.path.basename(checkpoint_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{checkpoint_name}.backup_{timestamp}"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    try:
        # Copy file với metadata (timestamp, permissions, etc.)
        shutil.copy2(checkpoint_path, backup_path)
        print(f"[INFO] Đã backup checkpoint: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"[ERROR] Không thể backup checkpoint: {e}")
        return None


def train_new_model() -> Optional[Dict]:
    """
    Train model mới với dữ liệu hiện tại.
    
    Sử dụng RecBole's run() function để train DeepFM model.
    
    Returns:
        Dictionary chứa kết quả training (metrics, best epoch, ...) hoặc None nếu training thất bại
    """
    print("[INFO] Bắt đầu training model mới...")
    
    try:
        # Chạy training với RecBole
        result = run(
            model="DeepFM",
            dataset="hotel",
            config_file_list=[CONFIG_FILE],
            config_dict={
                "save_result": True,      # Lưu kết quả vào file
                "save_log": True,         # Lưu log training
                "show_progress": True,    # Hiển thị progress bar
            }
        )
        
        # Kiểm tra result (có thể None trong một số edge cases)
        if result is None:
            print("[ERROR] Training trả về None, có thể training thất bại")
            return None
        
        return result
    except Exception as e:
        print(f"[ERROR] Lỗi khi training: {e}")
        raise


def compare_models(old_metrics: Optional[Dict], new_metrics: Dict) -> bool:
    """
    So sánh metrics của model cũ và mới.
    
    So sánh dựa trên RMSE (Root Mean Square Error):
    - RMSE càng thấp càng tốt
    - Model mới tốt hơn nếu RMSE thấp hơn
    
    Args:
        old_metrics: Metrics của model cũ (có thể None nếu không có)
        new_metrics: Metrics của model mới
    
    Returns:
        True nếu model mới tốt hơn, False nếu không
    """
    if old_metrics is None:
        # Không có model cũ, chấp nhận model mới
        return True
    
    # So sánh RMSE (càng thấp càng tốt)
    old_rmse = old_metrics.get('RMSE', float('inf'))
    new_rmse = new_metrics.get('RMSE', float('inf'))
    
    if new_rmse < old_rmse:
        print(f"[INFO] Model mới tốt hơn: RMSE {old_rmse:.4f} -> {new_rmse:.4f}")
        return True
    else:
        print(f"[INFO] Model cũ tốt hơn: RMSE {old_rmse:.4f} < {new_rmse:.4f}")
        return False


def should_retrain() -> Tuple[bool, str]:
    """
    Kiểm tra xem có nên retrain không dựa trên điều kiện.
    
    Điều kiện retrain:
    1. Số lượng interactions mới >= MIN_NEW_INTERACTIONS
    2. Thời gian từ lần retrain cuối >= 12 giờ
    
    Returns:
        Tuple (should_retrain: bool, reason: str)
        - should_retrain: True nếu nên retrain, False nếu không
        - reason: Lý do retrain hoặc lý do skip
    """
    history = load_retrain_history()
    
    # Kiểm tra số lượng interactions mới
    current_size = get_dataset_size()
    last_size = history.get('last_dataset_size', 0)
    new_interactions = current_size - last_size
    
    if new_interactions < MIN_NEW_INTERACTIONS:
        return False, f"Chưa đủ dữ liệu mới ({new_interactions} < {MIN_NEW_INTERACTIONS})"
    
    # Kiểm tra thời gian từ lần retrain cuối
    last_retrain = history.get('last_retrain_time')
    if last_retrain:
        # Parse timestamp từ ISO format
        last_time = datetime.fromisoformat(last_retrain)
        hours_since_last = (datetime.now() - last_time).total_seconds() / 3600
        
        # Nếu retrain gần đây (< 12 giờ), bỏ qua để tránh retrain quá thường xuyên
        if hours_since_last < 12:
            return False, f"Đã retrain gần đây ({hours_since_last:.1f} giờ trước)"
    
    return True, f"Có {new_interactions} interactions mới"


def main(force: bool = False):
    """
    Hàm main để chạy retraining pipeline.
    
    Quy trình:
    1. Kiểm tra điều kiện retrain (trừ khi force=True)
    2. Backup checkpoint cũ
    3. Train model mới
    4. So sánh metrics với model cũ
    5. Lưu model mới và cập nhật history
    6. Clear cache để load model mới
    
    Args:
        force: Nếu True, bỏ qua điều kiện kiểm tra và chạy retraining ngay
    """
    print("=" * 80)
    print("RETRAINING PIPELINE - DEEPFM HOTEL RECOMMENDATION")
    print("=" * 80)
    print(f"[TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if force:
        print("[MODE] FORCE MODE - Bỏ qua điều kiện kiểm tra")
    print()
    
    # Kiểm tra xem có nên retrain không
    if not force:
        should_retrain_flag, reason = should_retrain()
        if not should_retrain_flag:
            print(f"[SKIP] Bỏ qua retraining: {reason}")
            print("[TIP] Chạy với force=True để bỏ qua điều kiện này")
            return
    else:
        reason = "Force mode - bỏ qua điều kiện kiểm tra"
    
    print(f"[INFO] Bắt đầu retraining: {reason}")
    print()
    
    # Load history để lưu thông tin retrain
    history = load_retrain_history()
    
    # Lấy metrics từ model cũ (nếu có) để so sánh
    old_metrics = get_latest_checkpoint_metrics()
    
    # Lấy checkpoint cũ để backup
    old_checkpoint = _get_latest_checkpoint(SAVED_DIR) if _get_latest_checkpoint else None
    
    if old_checkpoint:
        print(f"[INFO] Tìm thấy checkpoint cũ: {old_checkpoint}")
        if old_metrics:
            print(f"[INFO] Metrics model cũ (từ history): RMSE={old_metrics.get('RMSE', 'N/A'):.4f}, MAE={old_metrics.get('MAE', 'N/A'):.4f}")
        else:
            print("[WARNING] Không có metrics trong history, sẽ so sánh với model mới sau khi train")
        
        # Backup checkpoint cũ trước khi retrain
        backup_path = backup_checkpoint(old_checkpoint)
        if backup_path:
            # Lưu thông tin backup vào history
            history.setdefault('backups', []).append({
                'checkpoint': old_checkpoint,
                'backup_path': backup_path,
                'backup_time': datetime.now().isoformat(),
                'metrics': old_metrics
            })
    else:
        print("[INFO] Không tìm thấy checkpoint cũ, sẽ train model mới")
        if old_metrics:
            print("[WARNING] Có metrics trong history nhưng không tìm thấy model file!")
            print("[WARNING] Metrics từ history có thể không tương ứng với model hiện tại.")
            print("[INFO] Sẽ so sánh model mới với metrics từ history (nếu có)")
    
    # Train model mới
    try:
        result = train_new_model()
        
        # Kiểm tra result trước khi sử dụng
        if result is None:
            print("[ERROR] Training thất bại, không thể tiếp tục")
            save_retrain_history(history)
            return
        
        # Lấy metrics từ kết quả training
        new_metrics = result.get('best_valid_result', {})
        # Convert keys to uppercase để so sánh (RecBole có thể trả về lowercase)
        new_metrics = {k.upper(): v for k, v in new_metrics.items()}
        new_rmse = new_metrics.get('RMSE', float('inf'))
        new_mae = new_metrics.get('MAE', float('inf'))
        
        print()
        print("[INFO] Training hoàn thành!")
        print(f"[METRICS] RMSE: {new_rmse:.4f}, MAE: {new_mae:.4f}")
        
        # So sánh với model cũ (nếu có)
        is_better = True  # Mặc định là True nếu không có model cũ
        if old_metrics:
            # Convert keys to uppercase để so sánh
            old_metrics_upper = {k.upper(): v for k, v in old_metrics.items()}
            is_better = compare_models(old_metrics_upper, new_metrics)
            if not is_better:
                print("[WARNING] Model mới không tốt hơn model cũ")
                print("[INFO] Model mới vẫn được lưu, nhưng có thể restore từ backup nếu cần")
        else:
            print("[INFO] Không có model cũ để so sánh, chấp nhận model mới")
        
        # Clear cache để load model mới (quan trọng!)
        if clear_cache:
            clear_cache()
            print("[INFO] Đã clear model cache")
        
        # Cập nhật history với thông tin retrain mới
        history['last_retrain_time'] = datetime.now().isoformat()
        history['last_dataset_size'] = get_dataset_size()
        history['last_retrain_metrics'] = new_metrics
        history.setdefault('retrain_count', 0)
        history['retrain_count'] += 1
        history['last_retrain_result'] = {
            'rmse': new_rmse,
            'mae': new_mae,
            'is_better_than_old': is_better
        }
        
        save_retrain_history(history)
        
        print()
        print("[SUCCESS] Retraining pipeline hoàn thành!")
        print(f"[INFO] Đã retrain {history['retrain_count']} lần")
        
    except Exception as e:
        print(f"[ERROR] Lỗi trong retraining pipeline: {e}")
        import traceback
        traceback.print_exc()
        # Không raise để scheduler có thể tiếp tục chạy
        print("[WARNING] Scheduler sẽ tiếp tục chạy, sẽ thử lại vào lần sau")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Retraining Pipeline")
    parser.add_argument("--force", action="store_true", help="Bỏ qua điều kiện kiểm tra và chạy retraining ngay")
    args = parser.parse_args()
    main(force=args.force)
