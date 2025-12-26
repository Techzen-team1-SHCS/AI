"""
Inference Module cho RecBole DeepFM Model.

Module này cung cấp chức năng:
1. Load model và dataset từ checkpoint
2. Generate recommendations cho users
3. Behavior Boost (Phase 1): Boost items dựa trên hành vi gần đây
4. Similarity Boost (Phase 2): Boost items tương tự items đã tương tác
5. Cache management để tối ưu performance

Sử dụng global cache để tránh load model nhiều lần không cần thiết.
"""
import os
import glob
import json
import time
import math
import torch
from typing import List, Optional, Tuple, Dict
import numpy as np

from recbole.quick_start import load_data_and_model
from recbole.data import create_dataset
from recbole.data.interaction import Interaction
from recbole.config import Config
from typing import TYPE_CHECKING

# Type checking để tránh circular import
if TYPE_CHECKING:
    from recbole.data.dataset import Dataset
else:
    Dataset = object  # Runtime type, sẽ được thay thế bởi Dataset instance thực tế

# ============================================================================
# GLOBAL CACHE - Tránh load model nhiều lần
# ============================================================================

# Cache cho model, config, dataset để tăng tốc inference
_model_cache = None
_config_cache = None
_dataset_cache = None
_similarity_matrix_cache = None  # Cache cho similarity matrix (Phase 2)


def _get_latest_checkpoint(saved_dir: str = "saved") -> Optional[str]:
    """
    Tìm checkpoint mới nhất trong thư mục saved dựa trên thời gian modified.
    
    Args:
        saved_dir: Thư mục chứa checkpoints (default: "saved")
        
    Returns:
        Đường dẫn đến checkpoint mới nhất hoặc None nếu không tìm thấy
    """
    pattern = os.path.join(saved_dir, "DeepFM-*.pth")
    checkpoints = glob.glob(pattern)
    if not checkpoints:
        return None
    
    # Sắp xếp theo thời gian modified, lấy file mới nhất
    latest = max(checkpoints, key=os.path.getmtime)
    return latest


def load_model(model_path: Optional[str] = None, force_reload: bool = False) -> Tuple[Config, torch.nn.Module, Dataset]:
    """
    Load model và dataset từ checkpoint với caching mechanism.
    
    Logic:
    - Nếu đã có trong cache và không force reload → trả về cache
    - Nếu chưa có hoặc force reload → load từ checkpoint
    - Cache kết quả để dùng lại lần sau
    
    Args:
        model_path: Đường dẫn đến checkpoint. Nếu None, tự động tìm checkpoint mới nhất
        force_reload: Nếu True, reload model ngay cả khi đã có trong cache
        
    Returns:
        Tuple (config, model, dataset)
        
    Raises:
        FileNotFoundError: Nếu không tìm thấy checkpoint
        RuntimeError: Nếu load model thất bại
    """
    global _model_cache, _config_cache, _dataset_cache
    
    # Kiểm tra cache: nếu đã có và không force reload, trả về cache
    if not force_reload and _model_cache is not None and _config_cache is not None and _dataset_cache is not None:
        return _config_cache, _model_cache, _dataset_cache
    
    # Tìm checkpoint nếu không được chỉ định
    if model_path is None:
        model_path = _get_latest_checkpoint()
        if model_path is None:
            raise FileNotFoundError("Không tìm thấy checkpoint trong thư mục saved/")
    
    # Kiểm tra file tồn tại
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Checkpoint không tồn tại: {model_path}")
    
    print(f"[INFERENCE] Đang load model từ: {model_path}")
    
    try:
        # Load model và dataset từ checkpoint
        config, model, dataset, train_data, valid_data, test_data = load_data_and_model(model_path)
        
        # Set model về evaluation mode (tắt dropout, batch norm, etc.)
        model.eval()
        
        # Cache kết quả để dùng lại
        _config_cache = config
        _model_cache = model
        _dataset_cache = dataset
        
        print(f"[INFERENCE] Load model thành công!")
        print(f"[INFERENCE] Dataset: {dataset.dataset_name}, Users: {dataset.user_num}, Items: {dataset.item_num}")
        
        return config, model, dataset
        
    except Exception as e:
        raise RuntimeError(f"Lỗi khi load model: {str(e)}") from e


def _get_user_interacted_items(dataset, user_id: str) -> set:
    """
    Lấy danh sách items mà user đã tương tác từ dataset.
    
    Sử dụng interaction matrix (sparse matrix) để truy vấn nhanh.
    
    Args:
        dataset: RecBole dataset object
        user_id: ID của user (external token, ví dụ: "123")
        
    Returns:
        Set chứa item IDs (external tokens) mà user đã tương tác
    """
    try:
        # Convert user_id (external token) sang internal ID
        user_internal_id = dataset.token2id(dataset.uid_field, user_id)
        
        # Sử dụng interaction matrix để lấy items user đã tương tác
        # inter_matrix là sparse matrix (CSR format) có shape (user_num, item_num)
        inter_matrix = dataset.inter_matrix(form="csr")
        
        # Lấy row tương ứng với user (chứa tất cả items user đã tương tác)
        user_row = inter_matrix[user_internal_id, :]
        
        # Lấy item indices (internal IDs) mà user đã tương tác
        item_internal_ids = user_row.indices
        
        # Convert internal IDs sang external tokens
        if len(item_internal_ids) > 0:
            item_tokens = dataset.id2token(dataset.iid_field, item_internal_ids.tolist())
            
            # id2token có thể trả về numpy array hoặc list
            if isinstance(item_tokens, np.ndarray):
                tokens_list = item_tokens.tolist()
            else:
                tokens_list = item_tokens
            
            # Convert về int nếu có thể, giữ nguyên nếu không
            result = set()
            for token in tokens_list:
                try:
                    result.add(int(token))
                except (ValueError, TypeError):
                    result.add(token)
            return result
        else:
            return set()
    except ValueError:
        # User không tồn tại trong dataset
        return set()
    except Exception as e:
        print(f"[WARNING] Lỗi khi lấy interacted items: {e}")
        return set()


def get_recommendations(
    user_id: str,
    top_k: int = 10,
    model_path: Optional[str] = None,
    exclude_interacted: bool = True,
    use_behavior_boost: bool = True,
    use_similarity_boost: bool = True,
    alpha: float = 0.3,
    decay_rate: float = 0.1,
    behavior_hours: int = 24,
    log_file: str = "data/user_actions.log",
    similarity_threshold: float = 0.5,
    similarity_boost_factor: float = 0.5
) -> List[str]:
    """
    Generate recommendations cho user với hỗ trợ Behavior Boost và Similarity Boost.
    
    Quy trình:
    1. Load model và dataset (sử dụng cache nếu có)
    2. Kiểm tra user có tồn tại trong dataset không
    3. Tạo interaction cho user với tất cả items
    4. Predict scores từ model
    5. Áp dụng Behavior Boost (Phase 1) nếu enabled
    6. Áp dụng Similarity Boost (Phase 2) nếu enabled
    7. Combine scores: final_score = base_score * (1 + alpha * boost)
    8. Sort và filter để lấy top-K items
    
    Args:
        user_id: ID của user (external token, ví dụ: "123")
        top_k: Số lượng recommendations cần trả về (default: 10)
        model_path: Đường dẫn đến checkpoint (None = dùng checkpoint mới nhất)
        exclude_interacted: Nếu True, loại bỏ items user đã tương tác (từ hotel.inter)
        use_behavior_boost: Nếu True, áp dụng behavior boost từ user_actions.log (Phase 1)
        use_similarity_boost: Nếu True, áp dụng similarity boost (Phase 2) - chỉ hoạt động nếu use_behavior_boost=True
        alpha: Boost coefficient (0.3 = tối đa 30% boost) (Phase 1)
        decay_rate: Time decay rate (0.1 = giảm ~10% mỗi giờ) (Phase 1)
        behavior_hours: Số giờ gần đây cần lấy actions (default: 24) (Phase 1)
        log_file: Đường dẫn đến log file (default: "data/user_actions.log") (Phase 1)
        similarity_threshold: Chỉ boost items có similarity >= threshold (default: 0.5) (Phase 2)
        similarity_boost_factor: Trọng số cho similarity boost (0.5 = boost 50% của direct boost) (Phase 2)
        
    Returns:
        List of item IDs (external tokens) được recommend, sắp xếp theo điểm số giảm dần
        
    Raises:
        ValueError: Nếu user_id không hợp lệ
        RuntimeError: Nếu inference thất bại
    """
    # Load model (sử dụng cache nếu đã load)
    config, model, dataset = load_model(model_path, force_reload=False)
    
    # Kiểm tra user có tồn tại trong dataset không
    try:
        user_internal_id = dataset.token2id(dataset.uid_field, user_id)
        # Skip padding token (không phải user thật)
        if user_id == "[PAD]" or user_internal_id == 0:
            print(f"[INFERENCE] User '{user_id}' là padding token, skip")
            return []
    except ValueError:
        # User mới (cold start) - không có trong dataset
        print(f"[INFERENCE] User '{user_id}' không tồn tại trong dataset (cold start)")
        return []  # Có thể trả về popular items thay vì empty list
    
    # Lấy items user đã tương tác (để filter ra nếu cần)
    interacted_items = set()
    if exclude_interacted:
        interacted_items = _get_user_interacted_items(dataset, user_id)
        print(f"[INFERENCE] User '{user_id}' đã tương tác với {len(interacted_items)} items")
    
    # Tạo interaction cho user với tất cả items để predict
    # RecBole yêu cầu tạo Interaction object với user_id và item_id
    device = config["device"]
    
    # Tạo tensors: user_id repeat cho tất cả items, và list tất cả item IDs
    all_item_internal_ids = torch.arange(dataset.item_num, dtype=torch.long, device=device)
    user_internal_ids = torch.full((dataset.item_num,), user_internal_id, dtype=torch.long, device=device)
    
    # Tạo interaction dict với user_id và item_id
    interaction_dict = {
        dataset.uid_field: user_internal_ids,
        dataset.iid_field: all_item_internal_ids,
    }
    
    # Thêm user features nếu có (age, gender, region, etc.)
    if dataset.user_feat is not None:
        # Tìm user trong user_feat
        user_mask = dataset.user_feat[dataset.uid_field] == user_internal_id
        user_indices = user_mask.nonzero(as_tuple=True)[0]
        if len(user_indices) > 0:
            user_idx = user_indices[0].item()
            # Thêm tất cả user features vào interaction
            for field in dataset.user_feat.columns:
                if field != dataset.uid_field:
                    feature_value = dataset.user_feat[field][user_idx]
                    if isinstance(feature_value, torch.Tensor):
                        if feature_value.dim() == 0:
                            # Scalar value - repeat cho tất cả items
                            interaction_dict[field] = feature_value.unsqueeze(0).repeat(dataset.item_num).to(device)
                        else:
                            # Sequence hoặc multi-dim - repeat along batch dimension
                            interaction_dict[field] = feature_value.unsqueeze(0).repeat(
                                dataset.item_num, *([1] * (feature_value.dim()))
                            ).to(device)
    
    # Thêm item features nếu có (style, price, star, score, city, etc.)
    if dataset.item_feat is not None:
        # item_feat được sắp xếp theo item_id, nên có thể index trực tiếp
        for field in dataset.item_feat.columns:
            if field != dataset.iid_field:
                # Lấy tất cả values của field này cho tất cả items
                # item_feat có shape (item_num, ...) nên có thể index trực tiếp
                if hasattr(dataset.item_feat[field], '__getitem__'):
                    interaction_dict[field] = dataset.item_feat[field].to(device)
    
    # Tạo Interaction object từ dict
    interaction = Interaction(interaction_dict)
    interaction = interaction.to(device)
    
    # Predict scores sử dụng model (DeepFM sử dụng predict method)
    with torch.no_grad():  # Tắt gradient computation để tăng tốc
        scores = model.predict(interaction)
        scores = scores.cpu().numpy().flatten()
    
    # ============================================================================
    # BEHAVIOR BOOST (Phase 1 + Phase 2)
    # ============================================================================
    behavior_boost_dict = {}
    if use_behavior_boost:
        try:
            current_time = time.time()
            # Lấy actions gần đây của user từ log file
            recent_actions = get_recent_user_actions(user_id, hours=behavior_hours, log_file=log_file)
            
            if use_similarity_boost and len(recent_actions) > 0:
                # Phase 2: Sử dụng similarity boost (boost hotels tương tự)
                behavior_boost_dict = calculate_behavior_boost_with_similarity(
                    recent_actions,
                    current_time,
                    dataset,
                    decay_rate=decay_rate,
                    similarity_threshold=similarity_threshold,
                    similarity_boost_factor=similarity_boost_factor
                )
                if len(recent_actions) > 0:
                    print(f"[INFERENCE] Found {len(recent_actions)} recent actions, boost with similarity for {len(behavior_boost_dict)} items")
            else:
                # Phase 1: Chỉ boost trực tiếp (boost hotels đã tương tác)
                behavior_boost_dict = calculate_behavior_boost(recent_actions, current_time, decay_rate)
                if len(recent_actions) > 0:
                    print(f"[INFERENCE] Found {len(recent_actions)} recent actions, boost for {len(behavior_boost_dict)} items")
        except Exception as e:
            # Nếu có lỗi khi đọc log hoặc tính boost, skip boost nhưng không crash
            # Điều này đảm bảo hệ thống vẫn hoạt động ngay cả khi log file có vấn đề
            print(f"[WARNING] Lỗi khi tính behavior boost: {e}. Skip boost.")
            behavior_boost_dict = {}
    
    # Combine scores: final_score = base_score * (1 + alpha * boost)
    # alpha giới hạn boost tối đa (0.3 = tối đa 30% boost)
    final_scores = {}
    for idx, item_internal_id in enumerate(all_item_internal_ids):
        item_internal_id_int = int(item_internal_id.item())
        base_score = float(scores[idx])
        
        # Convert internal ID sang external token
        try:
            item_token = dataset.id2token(dataset.iid_field, item_internal_id_int)
            try:
                item_id = int(item_token)
            except (ValueError, TypeError):
                item_id = item_token  # Giữ nguyên nếu không convert được
            
            # Áp dụng behavior boost nếu có
            if use_behavior_boost and item_id in behavior_boost_dict:
                boost = behavior_boost_dict[item_id]
                # Công thức: final_score = base_score * (1 + alpha * boost)
                # Ví dụ: base_score=0.6, boost=1.0, alpha=0.3
                # → final_score = 0.6 * (1 + 0.3 * 1.0) = 0.6 * 1.3 = 0.78 (tăng 30%)
                final_score = base_score * (1 + alpha * boost)
            else:
                final_score = base_score
            
            final_scores[item_id] = final_score
        except (ValueError, IndexError):
            # Skip nếu có lỗi khi convert (item không hợp lệ)
            continue
    
    # Sắp xếp theo final_score giảm dần
    # LƯU Ý: sorted() không stable khi có items cùng score → có thể dẫn đến kết quả không nhất quán
    sorted_items = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Filter interacted items và lấy top-K
    top_k_items = []
    for item_id, final_score in sorted_items:
        # Bỏ qua items user đã tương tác nếu exclude_interacted=True
        if exclude_interacted and item_id in interacted_items:
            continue
        top_k_items.append(item_id)
        if len(top_k_items) >= top_k:
            break
    
    print(f"[INFERENCE] Trả về {len(top_k_items)} recommendations cho user '{user_id}'")
    return top_k_items


def get_popular_items(dataset, top_k: int = 10) -> List[str]:
    """
    Lấy popular items (items được tương tác nhiều nhất) - dùng cho cold start users.
    
    Args:
        dataset: RecBole dataset object
        top_k: Số lượng items cần trả về (default: 10)
        
    Returns:
        List of item IDs (external tokens) được sắp xếp theo độ phổ biến
    """
    # Đếm số lần tương tác của mỗi item
    item_counter = dataset.item_counter()
    
    # Lấy top-K items phổ biến nhất
    top_items = item_counter.most_common(top_k)
    
    # Convert sang external tokens
    return [item_id for item_id, count in top_items]


def is_model_loaded() -> bool:
    """
    Kiểm tra model đã được load và cache chưa.
    
    Returns:
        True nếu model đã được load, False nếu chưa
    """
    return _model_cache is not None


def clear_cache():
    """
    Xóa cache của model và dataset (dùng khi cần reload model mới).
    
    Nên gọi sau khi retrain model để đảm bảo load model mới thay vì dùng cache cũ.
    """
    global _model_cache, _config_cache, _dataset_cache, _similarity_matrix_cache
    _model_cache = None
    _config_cache = None
    _dataset_cache = None
    _similarity_matrix_cache = None  # Clear similarity cache cũng


# ============================================================================
# BEHAVIOR BOOST FUNCTIONS (Phase 1)
# ============================================================================

def get_recent_user_actions(user_id: str, hours: int = 24, log_file: str = "data/user_actions.log") -> List[Dict]:
    """
    Đọc user_actions.log và lấy actions gần đây của user.
    
    File log có format: mỗi dòng là 1 JSON object chứa thông tin hành động.
    
    Args:
        user_id: ID của user (external token, có thể là string hoặc int)
        hours: Số giờ gần đây cần lấy (default: 24)
        log_file: Đường dẫn đến log file
    
    Returns:
        List of actions: [{"user_id": ..., "item_id": ..., "action_type": ..., "timestamp": ...}, ...]
        Trả về empty list nếu không tìm thấy hoặc có lỗi
    """
    if not os.path.exists(log_file):
        return []
    
    # Tính thời gian cutoff (chỉ lấy actions sau thời điểm này)
    current_time = time.time()
    cutoff_time = current_time - (hours * 3600)
    
    actions = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    # Parse JSON từ mỗi dòng
                    action = json.loads(line)
                    # Filter theo user_id (so sánh dạng string để đảm bảo match)
                    if str(action.get('user_id')) != str(user_id):
                        continue
                    # Filter theo timestamp (chỉ lấy actions trong khoảng thời gian gần đây)
                    if action.get('timestamp', 0) < cutoff_time:
                        continue
                    actions.append(action)
                except json.JSONDecodeError:
                    # Skip dòng không phải JSON hợp lệ
                    continue
    except IOError:
        # Log file đang bị lock (ETL đang xử lý) → skip boost, không crash
        # Điều này đảm bảo hệ thống vẫn hoạt động ngay cả khi ETL đang chạy
        pass
    except Exception as e:
        print(f"[WARNING] Lỗi khi đọc log file: {e}")
    
    return actions


def get_action_score(action_type: str) -> float:
    """
    Map loại hành động thành điểm số tương ứng.
    
    Điểm số phản ánh mức độ quan tâm:
    - Booking: Quan tâm cao nhất (1.0)
    - Share: Quan tâm cao (0.75)
    - Like: Quan tâm trung bình (0.5)
    - Click: Quan tâm thấp (0.25)
    
    Args:
        action_type: Loại hành động ("click" | "like" | "share" | "booking")
    
    Returns:
        Điểm số từ 0.0 đến 1.0, hoặc 0.0 nếu không hợp lệ
    """
    action_scores = {
        'booking': 1.0,
        'share': 0.75,
        'like': 0.5,
        'click': 0.25
    }
    return action_scores.get(action_type.lower(), 0.0)


def calculate_time_weight(timestamp: float, current_time: float, decay_rate: float = 0.1) -> float:
    """
    Tính trọng số theo thời gian sử dụng exponential decay.
    
    Hành động càng gần hiện tại càng có trọng số cao.
    Công thức: weight = exp(-decay_rate * hours_ago)
    
    Args:
        timestamp: Unix timestamp của action
        current_time: Unix timestamp hiện tại
        decay_rate: Decay rate (default: 0.1 = giảm ~10% mỗi giờ)
    
    Returns:
        Time weight từ 0 đến 1, càng gần hiện tại càng cao
    
    Example:
        Action 1 giờ trước với decay_rate=0.1:
        weight = exp(-0.1 * 1) = 0.905 (90.5%)
        
        Action 24 giờ trước:
        weight = exp(-0.1 * 24) = 0.091 (9.1%)
    """
    hours_ago = (current_time - timestamp) / 3600
    return math.exp(-decay_rate * hours_ago)


def calculate_behavior_boost(actions: List[Dict], current_time: float, decay_rate: float = 0.1) -> Dict[int, float]:
    """
    Tính boost cho từng item dựa trên hành vi gần đây của user (Phase 1).
    
    QUAN TRỌNG: Nếu nhiều actions cùng hotel, boost được CỘNG LẠI (không lấy max).
    
    Lý do:
    - Mỗi action thể hiện sự quan tâm khác nhau (click < like < booking)
    - Trọng số thời gian đã giảm dần tự động (actions cũ có weight thấp hơn)
    - Tổng boost có giới hạn bởi alpha (0.3) → boost tối đa 30%
    
    Example:
        Hotel 501 có 3 actions:
        - Click lúc 7:00 AM: boost = 0.25 * 0.967 = 0.242
        - Like lúc 7:10 AM: boost = 0.5 * 0.985 = 0.493
        - Booking lúc 7:20 AM: boost = 1.0 * 1.0 = 1.0
        Total boost = 0.242 + 0.493 + 1.0 = 1.735
        
        Với base_score = 0.60, alpha = 0.3:
        Final = 0.60 * (1 + 0.3 * 1.735) = 0.60 * 1.521 = 0.913 (tăng 52%)
        → Vẫn hợp lý vì user đã booking (quan tâm rất cao)
    
    Args:
        actions: List of actions từ get_recent_user_actions()
        current_time: Unix timestamp hiện tại
        decay_rate: Decay rate cho time weight (default: 0.1)
    
    Returns:
        Dict: {item_id: boost_score, ...}
    """
    boost = {}
    for action in actions:
        try:
            item_id = int(action['item_id'])
            action_type = action['action_type']
            timestamp = float(action['timestamp'])
            
            # Tính điểm số và trọng số thời gian
            action_score = get_action_score(action_type)
            weight = calculate_time_weight(timestamp, current_time, decay_rate)
            boosted_score = action_score * weight
            
            # CỘNG LẠI (không lấy max) - nhiều actions = quan tâm cao hơn
            boost[item_id] = boost.get(item_id, 0) + boosted_score
        except (ValueError, KeyError, TypeError) as e:
            # Skip nếu có lỗi (item_id không phải int, thiếu field, ...)
            continue
    
    return boost


# ============================================================================
# SIMILARITY BOOST FUNCTIONS (Phase 2)
# ============================================================================

def calculate_item_similarity(
    dataset,
    item_features: List[str] = ['style', 'price', 'star', 'score', 'city'],
    similarity_threshold: float = 0.5
) -> Dict[int, Dict[int, float]]:
    """
    Tính similarity matrix giữa các items dựa trên features (pre-compute và cache).
    
    Similarity được tính dựa trên:
    - style, city: Jaccard similarity (set overlap)
    - price, star, score: Normalized distance similarity
    
    Matrix được cache để tránh tính lại nhiều lần (tốn thời gian).
    
    Args:
        dataset: RecBole dataset object
        item_features: List of feature names để tính similarity (default: ['style', 'price', 'star', 'score', 'city'])
        similarity_threshold: Chỉ giữ similarities >= threshold để giảm memory (default: 0.5)
    
    Returns:
        Dict: {item_id: {similar_item_id: similarity_score, ...}, ...}
        Chỉ chứa similarities >= threshold
    """
    global _similarity_matrix_cache
    
    # Kiểm tra cache: nếu đã tính rồi, trả về cache
    if _similarity_matrix_cache is not None:
        return _similarity_matrix_cache
    
    print("[INFERENCE] Tính similarity matrix giữa items (lần đầu, sẽ cache)...")
    
    similarity_dict = {}
    
    # Kiểm tra dataset có item features không
    if dataset.item_feat is None:
        print("[WARNING] Dataset không có item features, skip similarity calculation")
        return similarity_dict
    
    # Lấy tất cả items và convert internal IDs → external tokens
    all_items = {}
    for idx in range(dataset.item_num):
        try:
            item_token = dataset.id2token(dataset.iid_field, idx)
            try:
                item_id = int(item_token)
            except (ValueError, TypeError):
                item_id = item_token
            all_items[item_id] = idx
        except (ValueError, IndexError):
            continue
    
    print(f"[INFERENCE] Tính similarity cho {len(all_items)} items...")
    
    # Tính similarity cho từng cặp items
    total_pairs = len(all_items) * (len(all_items) - 1) // 2
    processed = 0
    
    for item_id1, internal_id1 in all_items.items():
        similarity_dict[item_id1] = {}
        
        # Chỉ tính với items sau item_id1 (tránh duplicate, similarity(A,B) = similarity(B,A))
        for item_id2, internal_id2 in all_items.items():
            try:
                # So sánh item IDs để chỉ tính một nửa matrix (đối xứng)
                id1_int = int(item_id1) if not isinstance(item_id1, int) else item_id1
                id2_int = int(item_id2) if not isinstance(item_id2, int) else item_id2
                if id1_int >= id2_int:
                    continue
            except (ValueError, TypeError):
                # Fallback: so sánh string
                if str(item_id1) >= str(item_id2):
                    continue
            
            # Tính similarity giữa 2 items
            similarity = _calculate_item_pair_similarity(
                dataset, internal_id1, internal_id2, item_features
            )
            
            # Chỉ lưu nếu similarity >= threshold (để giảm memory)
            try:
                similarity_float = float(similarity) if not isinstance(similarity, (int, float)) else similarity
                if similarity_float >= similarity_threshold:
                    similarity_dict[item_id1][item_id2] = similarity_float
                    # Đối xứng: similarity(A,B) = similarity(B,A)
                    if item_id2 not in similarity_dict:
                        similarity_dict[item_id2] = {}
                    similarity_dict[item_id2][item_id1] = similarity_float
            except (ValueError, TypeError) as e:
                # Skip nếu không convert được similarity
                continue
            
            processed += 1
            if processed % 10000 == 0:
                print(f"[INFERENCE] Đã xử lý {processed}/{total_pairs} cặp items...")
    
    print(f"[INFERENCE] Tính similarity hoàn tất! Tìm thấy similarities cho {len(similarity_dict)} items")
    
    # Cache kết quả để dùng lại
    _similarity_matrix_cache = similarity_dict
    
    return similarity_dict


def _calculate_item_pair_similarity(
    dataset,
    internal_id1: int,
    internal_id2: int,
    item_features: List[str]
) -> float:
    """
    Tính similarity giữa 2 items dựa trên features.
    
    Similarity được tính bằng weighted average của similarities từ các features:
    - style, city: Jaccard similarity (tokens overlap)
    - price, star, score: Normalized distance similarity
    
    Args:
        dataset: RecBole dataset object
        internal_id1, internal_id2: Internal IDs của 2 items
        item_features: List of feature names để tính similarity
    
    Returns:
        Similarity score từ 0 đến 1, càng cao càng giống nhau
    """
    similarities = []
    weights = []
    
    for field in item_features:
        if field not in dataset.item_feat.columns:
            continue
        
        try:
            # Lấy feature values cho cả 2 items
            feat1 = dataset.item_feat[field][internal_id1]
            feat2 = dataset.item_feat[field][internal_id2]
            
            # Convert tensor sang Python value nếu cần
            if isinstance(feat1, torch.Tensor):
                if feat1.numel() == 1:
                    # Scalar tensor → convert sang Python value
                    feat1 = feat1.item()
                else:
                    # Tensor có nhiều phần tử (TOKEN_SEQ) → convert sang list và join
                    # Loại bỏ padding (0) và convert sang string
                    try:
                        feat1_list = feat1.cpu().numpy().tolist()
                        # Xử lý list hoặc nested list
                        if isinstance(feat1_list, list):
                            # Flatten nếu là nested list
                            flat_list = []
                            for x in feat1_list:
                                if isinstance(x, list):
                                    flat_list.extend([y for y in x if y != 0])
                                else:
                                    if x != 0:
                                        flat_list.append(x)
                            feat1 = ' '.join(str(x) for x in flat_list) if flat_list else ''
                        else:
                            feat1 = str(feat1_list)
                    except Exception:
                        # Fallback: convert to string
                        feat1 = str(feat1.cpu().numpy())
            elif not isinstance(feat1, (str, int, float)):
                # Nếu không phải tensor, string, int, float → convert sang string
                feat1 = str(feat1)
            
            # Xử lý feat2 tương tự
            if isinstance(feat2, torch.Tensor):
                if feat2.numel() == 1:
                    feat2 = feat2.item()
                else:
                    try:
                        feat2_list = feat2.cpu().numpy().tolist()
                        if isinstance(feat2_list, list):
                            flat_list = []
                            for x in feat2_list:
                                if isinstance(x, list):
                                    flat_list.extend([y for y in x if y != 0])
                                else:
                                    if x != 0:
                                        flat_list.append(x)
                            feat2 = ' '.join(str(x) for x in flat_list) if flat_list else ''
                        else:
                            feat2 = str(feat2_list)
                    except Exception:
                        feat2 = str(feat2.cpu().numpy())
            elif not isinstance(feat2, (str, int, float)):
                feat2 = str(feat2)
            
            # Tính similarity tùy theo loại field
            if field in ['style', 'city']:
                # Token_seq fields: Jaccard similarity (set overlap)
                # Chuyển string thành set (split by space)
                set1 = set(str(feat1).split())
                set2 = set(str(feat2).split())
                if len(set1 | set2) == 0:
                    sim = 1.0  # Cả 2 đều empty → giống nhau
                else:
                    # Jaccard similarity = |intersection| / |union|
                    sim = len(set1 & set2) / len(set1 | set2)
                weight = 0.3  # Style và city có trọng số thấp hơn
                
            elif field in ['price', 'star', 'score']:
                # Float fields: Normalized distance similarity
                # Convert về float
                try:
                    val1 = float(feat1) if isinstance(feat1, str) else float(feat1)
                    val2 = float(feat2) if isinstance(feat2, str) else float(feat2)
                    
                    # Normalize: similarity = 1 - |val1 - val2| / max_range
                    # Tìm max range từ dataset (hoặc dùng fixed range)
                    if field == 'price':
                        # Price range: 0 - 10M (estimated)
                        max_range = 10000000.0
                        diff = abs(val1 - val2)
                        sim = max(0.0, 1.0 - (diff / max_range))
                        weight = 0.25  # Price có trọng số trung bình
                    elif field == 'star':
                        # Star range: 0 - 5
                        max_range = 5.0
                        diff = abs(val1 - val2)
                        sim = max(0.0, 1.0 - (diff / max_range))
                        weight = 0.2  # Star có trọng số thấp
                    elif field == 'score':
                        # Score range: 0 - 10
                        max_range = 10.0
                        diff = abs(val1 - val2)
                        sim = max(0.0, 1.0 - (diff / max_range))
                        weight = 0.25  # Score có trọng số trung bình
                except (ValueError, TypeError):
                    sim = 0.0
                    weight = 0.0
            else:
                # Unknown field type → skip
                continue
            
            similarities.append(sim)
            weights.append(weight)
            
        except (IndexError, KeyError, AttributeError) as e:
            # Skip nếu không lấy được feature
            continue
    
    # Weighted average của tất cả similarities
    if len(similarities) == 0:
        return 0.0
    
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    
    weighted_similarity = sum(sim * w for sim, w in zip(similarities, weights)) / total_weight
    return weighted_similarity


def calculate_behavior_boost_with_similarity(
    actions: List[Dict],
    current_time: float,
    dataset,
    decay_rate: float = 0.1,
    similarity_threshold: float = 0.5,
    similarity_boost_factor: float = 0.5
) -> Dict[int, float]:
    """
    Tính boost cho từng item, bao gồm cả similarity boost (Phase 2).
    
    Logic:
    1. Tính direct boost từ actions (giống Phase 1)
    2. Tính similarity matrix (pre-compute và cache)
    3. Boost hotels tương tự hotels đã tương tác
    
    Args:
        actions: List of actions từ get_recent_user_actions()
        current_time: Unix timestamp hiện tại
        dataset: RecBole dataset (để tính similarity)
        decay_rate: Decay rate cho time weight (default: 0.1)
        similarity_threshold: Chỉ boost items có similarity >= threshold (default: 0.5)
        similarity_boost_factor: Trọng số cho similarity boost (0.5 = boost 50% của direct boost) (default: 0.5)
    
    Returns:
        Dict: {item_id: boost_score, ...}
    """
    # Bước 1: Tính direct boost (Phase 1) - boost hotels đã tương tác trực tiếp
    direct_boost = calculate_behavior_boost(actions, current_time, decay_rate)
    
    if len(direct_boost) == 0:
        return {}
    
    # Bước 2: Tính similarity matrix (pre-compute và cache)
    try:
        similarity_dict = calculate_item_similarity(dataset, similarity_threshold=similarity_threshold)
    except Exception as e:
        print(f"[WARNING] Lỗi khi tính similarity: {e}. Chỉ dùng direct boost.")
        return direct_boost
    
    # Bước 3: Boost hotels tương tự hotels đã tương tác
    final_boost = direct_boost.copy()
    
    for item_id, direct_boost_value in direct_boost.items():
        # Tìm hotels tương tự với hotel đã tương tác
        similar_items = similarity_dict.get(item_id, {})
        
        for similar_item_id, similarity_score in similar_items.items():
            try:
                # Đảm bảo similarity_score là float
                score_float = float(similarity_score) if not isinstance(similarity_score, (int, float)) else similarity_score
                if score_float >= similarity_threshold and similar_item_id != item_id:
                    # Boost hotels tương tự với trọng số similarity
                    # similarity_boost = direct_boost * similarity_score * similarity_boost_factor
                    # similarity_boost_factor giảm trọng số của similarity boost so với direct boost
                    similarity_boost = direct_boost_value * score_float * similarity_boost_factor
                    
                    # Cộng dồn với boost hiện tại (có thể đã có direct boost hoặc similarity boost từ items khác)
                    final_boost[similar_item_id] = final_boost.get(similar_item_id, 0) + similarity_boost
            except (ValueError, TypeError):
                # Skip nếu không convert được similarity_score
                continue
    
    return final_boost


if __name__ == "__main__":
    # Test inference module
    print("Testing inference...")
    
    # Load model
    config, model, dataset = load_model()
    
    # Test với user có trong dataset
    if dataset.user_num > 0:
        # Lấy user đầu tiên
        test_user = dataset.id2token(dataset.uid_field, 0)
        print(f"\nTest với user: {test_user}")
        
        recommendations = get_recommendations(test_user, top_k=10)
        print(f"Recommendations: {recommendations[:5]}...")
    
    # Test với user mới (cold start)
    print(f"\nTest với user mới: new_user_999")
    recommendations = get_recommendations("new_user_999", top_k=10)
    print(f"Recommendations (cold start): {recommendations}")
