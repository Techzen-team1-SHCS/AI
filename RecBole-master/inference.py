"""
Inference module for RecBole DeepFM model.
Loads trained model and provides recommendation functionality.
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

if TYPE_CHECKING:
    from recbole.data.dataset import Dataset
else:
    Dataset = object  # Runtime type, will be replaced by actual Dataset instance

# Global variables for caching
_model_cache = None
_config_cache = None
_dataset_cache = None
_similarity_matrix_cache = None  # NEW: Cache for similarity matrix


def _get_latest_checkpoint(saved_dir: str = "saved") -> Optional[str]:
    """Tìm checkpoint mới nhất trong thư mục saved.
    
    Args:
        saved_dir: Thư mục chứa checkpoints
        
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
    """Load model và dataset từ checkpoint.
    
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
    
    # Nếu đã có trong cache và không force reload, trả về cache
    if not force_reload and _model_cache is not None and _config_cache is not None and _dataset_cache is not None:
        return _config_cache, _model_cache, _dataset_cache
    
    # Tìm checkpoint
    if model_path is None:
        model_path = _get_latest_checkpoint()
        if model_path is None:
            raise FileNotFoundError("Không tìm thấy checkpoint trong thư mục saved/")
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Checkpoint không tồn tại: {model_path}")
    
    print(f"[INFERENCE] Đang load model từ: {model_path}")
    
    try:
        # Load model và dataset
        config, model, dataset, train_data, valid_data, test_data = load_data_and_model(model_path)
        
        # Set model to eval mode
        model.eval()
        
        # Cache kết quả
        _config_cache = config
        _model_cache = model
        _dataset_cache = dataset
        
        print(f"[INFERENCE] Load model thành công!")
        print(f"[INFERENCE] Dataset: {dataset.dataset_name}, Users: {dataset.user_num}, Items: {dataset.item_num}")
        
        return config, model, dataset
        
    except Exception as e:
        raise RuntimeError(f"Lỗi khi load model: {str(e)}") from e


def _get_user_interacted_items(dataset, user_id: str) -> set:
    """Lấy danh sách items mà user đã tương tác.
    
    Args:
        dataset: RecBole dataset
        user_id: ID của user (external token)
        
    Returns:
        Set của item IDs (external tokens) mà user đã tương tác
    """
    try:
        # Convert user_id (external token) to internal id
        user_internal_id = dataset.token2id(dataset.uid_field, user_id)
        
        # Sử dụng inter_matrix để lấy items user đã tương tác
        # inter_matrix là sparse matrix có shape (user_num, item_num)
        inter_matrix = dataset.inter_matrix(form="csr")
        
        # Lấy row tương ứng với user
        user_row = inter_matrix[user_internal_id, :]
        
        # Lấy item indices (internal IDs) mà user đã tương tác
        item_internal_ids = user_row.indices
        
        # Convert internal ids to external tokens
        if len(item_internal_ids) > 0:
            item_tokens = dataset.id2token(dataset.iid_field, item_internal_ids.tolist())
            # id2token có thể trả về numpy array hoặc list
            if isinstance(item_tokens, np.ndarray):
                tokens_list = item_tokens.tolist()
            else:
                tokens_list = item_tokens
            
            # Convert về int nếu có thể
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
    use_similarity_boost: bool = True,  # NEW: Phase 2
    alpha: float = 0.3,
    decay_rate: float = 0.1,
    behavior_hours: int = 24,
    log_file: str = "data/user_actions.log",
    similarity_threshold: float = 0.5,  # NEW: Phase 2
    similarity_boost_factor: float = 0.5  # NEW: Phase 2
) -> List[str]:
    """Lấy recommendations cho user.
    
    NEW (Phase 1): Hỗ trợ behavior boost từ user_actions.log để recommendations real-time và personalized.
    NEW (Phase 2): Hỗ trợ similarity boost - boost hotels tương tự hotels đã tương tác.
    
    Args:
        user_id: ID của user (external token, ví dụ: "123")
        top_k: Số lượng recommendations cần trả về
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
        # Skip padding token
        if user_id == "[PAD]" or user_internal_id == 0:
            print(f"[INFERENCE] User '{user_id}' là padding token, skip")
            return []
    except ValueError:
        # User mới (cold start) - trả về empty list hoặc popular items
        print(f"[INFERENCE] User '{user_id}' không tồn tại trong dataset (cold start)")
        return []  # Hoặc có thể trả về popular items
    
    # Lấy items user đã tương tác (để filter ra nếu cần)
    interacted_items = set()
    if exclude_interacted:
        interacted_items = _get_user_interacted_items(dataset, user_id)
        print(f"[INFERENCE] User '{user_id}' đã tương tác với {len(interacted_items)} items")
    
    # Sử dụng dataset để tạo interaction cho user với tất cả items
    # RecBole có method để tạo interaction cho full sort prediction
    # Tạo interaction với user và tất cả items
    device = config["device"]
    
    # Tạo user tensor (chỉ 1 user, nhưng repeat cho tất cả items)
    all_item_internal_ids = torch.arange(dataset.item_num, dtype=torch.long, device=device)
    user_internal_ids = torch.full((dataset.item_num,), user_internal_id, dtype=torch.long, device=device)
    
    # Tạo interaction dict với user_id và item_id
    interaction_dict = {
        dataset.uid_field: user_internal_ids,
        dataset.iid_field: all_item_internal_ids,
    }
    
    # Thêm user features nếu có (dataset.user_feat là Interaction object)
    if dataset.user_feat is not None:
        # Tìm user trong user_feat
        user_mask = dataset.user_feat[dataset.uid_field] == user_internal_id
        user_indices = user_mask.nonzero(as_tuple=True)[0]
        if len(user_indices) > 0:
            user_idx = user_indices[0].item()
            for field in dataset.user_feat.columns:
                if field != dataset.uid_field:
                    feature_value = dataset.user_feat[field][user_idx]
                    if isinstance(feature_value, torch.Tensor):
                        if feature_value.dim() == 0:
                            # Scalar value - repeat for all items
                            interaction_dict[field] = feature_value.unsqueeze(0).repeat(dataset.item_num).to(device)
                        else:
                            # Sequence or multi-dim - repeat along batch
                            interaction_dict[field] = feature_value.unsqueeze(0).repeat(dataset.item_num, *([1] * (feature_value.dim()))).to(device)
    
    # Thêm item features nếu có (dataset.item_feat là Interaction object)
    if dataset.item_feat is not None:
        # item_feat được sắp xếp theo item_id, nên có thể index trực tiếp
        for field in dataset.item_feat.columns:
            if field != dataset.iid_field:
                # Lấy tất cả values của field này cho tất cả items
                # item_feat có shape (item_num, ...) nên có thể index trực tiếp
                if hasattr(dataset.item_feat[field], '__getitem__'):
                    interaction_dict[field] = dataset.item_feat[field].to(device)
    
    # Tạo Interaction object
    interaction = Interaction(interaction_dict)
    interaction = interaction.to(device)
    
    # Predict sử dụng predict (DeepFM không có full_sort_predict)
    with torch.no_grad():
        # DeepFM sử dụng predict method
        scores = model.predict(interaction)
        scores = scores.cpu().numpy().flatten()
    
    # ========== NEW: Behavior Boost (Phase 1 + Phase 2) ==========
    behavior_boost_dict = {}
    if use_behavior_boost:
        try:
            current_time = time.time()
            recent_actions = get_recent_user_actions(user_id, hours=behavior_hours, log_file=log_file)
            
            if use_similarity_boost and len(recent_actions) > 0:
                # Phase 2: Use similarity boost (boost hotels tương tự)
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
                # Phase 1: Only direct boost (boost hotels đã tương tác)
                behavior_boost_dict = calculate_behavior_boost(recent_actions, current_time, decay_rate)
                if len(recent_actions) > 0:
                    print(f"[INFERENCE] Found {len(recent_actions)} recent actions, boost for {len(behavior_boost_dict)} items")
        except Exception as e:
            # Nếu có lỗi khi đọc log hoặc tính boost, skip boost nhưng không crash
            print(f"[WARNING] Lỗi khi tính behavior boost: {e}. Skip boost.")
            behavior_boost_dict = {}
    # ========== END Behavior Boost ==========
    
    # Combine scores: final_score = base_score * (1 + alpha * boost)
    final_scores = {}
    for idx, item_internal_id in enumerate(all_item_internal_ids):
        item_internal_id_int = int(item_internal_id.item())
        base_score = float(scores[idx])
        
        # Convert internal ID to external token
        try:
            item_token = dataset.id2token(dataset.iid_field, item_internal_id_int)
            try:
                item_id = int(item_token)
            except (ValueError, TypeError):
                item_id = item_token  # Giữ nguyên nếu không convert được
            
            # Apply behavior boost
            if use_behavior_boost and item_id in behavior_boost_dict:
                boost = behavior_boost_dict[item_id]
                final_score = base_score * (1 + alpha * boost)
            else:
                final_score = base_score
            
            final_scores[item_id] = final_score
        except (ValueError, IndexError):
            # Skip nếu có lỗi khi convert
            continue
    
    # Sort by final_score (descending)
    sorted_items = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Filter interacted items và lấy top-K
    top_k_items = []
    for item_id, final_score in sorted_items:
        if exclude_interacted and item_id in interacted_items:
            continue
        top_k_items.append(item_id)
        if len(top_k_items) >= top_k:
            break
    
    print(f"[INFERENCE] Trả về {len(top_k_items)} recommendations cho user '{user_id}'")
    return top_k_items


def get_popular_items(dataset, top_k: int = 10) -> List[str]:
    """Lấy popular items (cho cold start users).
    
    Args:
        dataset: RecBole dataset
        top_k: Số lượng items cần trả về
        
    Returns:
        List of item IDs (external tokens)
    """
    # Đếm số lần tương tác của mỗi item
    item_counter = dataset.item_counter()
    
    # Lấy top-K items phổ biến nhất
    top_items = item_counter.most_common(top_k)
    
    # Convert to external tokens
    return [item_id for item_id, count in top_items]


def is_model_loaded() -> bool:
    """Kiểm tra model đã được load chưa.
    
    Returns:
        True nếu model đã được load, False nếu chưa
    """
    return _model_cache is not None


def clear_cache():
    """Xóa cache của model (dùng khi cần reload model mới)."""
    global _model_cache, _config_cache, _dataset_cache, _similarity_matrix_cache
    _model_cache = None
    _config_cache = None
    _dataset_cache = None
    _similarity_matrix_cache = None  # Clear similarity cache too


# ============================================================================
# BEHAVIOR BOOST FUNCTIONS (NEW - Phase 1)
# ============================================================================

def get_recent_user_actions(user_id: str, hours: int = 24, log_file: str = "data/user_actions.log") -> List[Dict]:
    """Đọc user_actions.log và lấy actions gần đây của user.
    
    Args:
        user_id: ID của user (external token, có thể là string hoặc int)
        hours: Số giờ gần đây cần lấy (default: 24)
        log_file: Đường dẫn đến log file
    
    Returns:
        List of actions: [{"user_id": ..., "item_id": ..., "action_type": ..., "timestamp": ...}, ...]
    """
    if not os.path.exists(log_file):
        return []
    
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
                    action = json.loads(line)
                    # Filter by user_id (so sánh dạng string để đảm bảo match)
                    if str(action.get('user_id')) != str(user_id):
                        continue
                    # Filter by timestamp (lấy actions trong khoảng thời gian gần đây)
                    if action.get('timestamp', 0) < cutoff_time:
                        continue
                    actions.append(action)
                except json.JSONDecodeError:
                    # Skip invalid JSON lines
                    continue
    except IOError:
        # Log file đang bị lock (ETL đang xử lý) → skip boost, không crash
        pass
    except Exception as e:
        print(f"[WARNING] Lỗi khi đọc log file: {e}")
    
    return actions


def get_action_score(action_type: str) -> float:
    """Map action_type thành điểm số.
    
    Args:
        action_type: "click" | "like" | "share" | "booking"
    
    Returns:
        Action score (0.25, 0.5, 0.75, hoặc 1.0)
    """
    action_scores = {
        'booking': 1.0,
        'share': 0.75,
        'like': 0.5,
        'click': 0.25
    }
    return action_scores.get(action_type.lower(), 0.0)


def calculate_time_weight(timestamp: float, current_time: float, decay_rate: float = 0.1) -> float:
    """Tính trọng số theo thời gian (exponential decay).
    
    Args:
        timestamp: Unix timestamp của action
        current_time: Unix timestamp hiện tại
        decay_rate: Decay rate (default: 0.1)
    
    Returns:
        Time weight (0-1), càng gần hiện tại càng cao
    
    Example:
        Action 1 giờ trước với decay_rate=0.1:
        weight = exp(-0.1 * 1) = 0.905 (90.5%)
        
        Action 24 giờ trước:
        weight = exp(-0.1 * 24) = 0.091 (9.1%)
    """
    hours_ago = (current_time - timestamp) / 3600
    return math.exp(-decay_rate * hours_ago)


def calculate_behavior_boost(actions: List[Dict], current_time: float, decay_rate: float = 0.1) -> Dict[int, float]:
    """Tính boost cho từng item dựa trên hành vi gần đây.
    
    IMPORTANT: Nếu nhiều actions cùng hotel, boost được CỘNG LẠI (không lấy max).
    
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
        decay_rate: Decay rate (default: 0.1)
    
    Returns:
        Dict: {item_id: boost_score, ...}
    """
    boost = {}
    for action in actions:
        try:
            item_id = int(action['item_id'])
            action_type = action['action_type']
            timestamp = float(action['timestamp'])
            
            action_score = get_action_score(action_type)
            weight = calculate_time_weight(timestamp, current_time, decay_rate)
            boosted_score = action_score * weight
            
            # CỘNG LẠI (không lấy max)
            boost[item_id] = boost.get(item_id, 0) + boosted_score
        except (ValueError, KeyError, TypeError) as e:
            # Skip nếu có lỗi (item_id không phải int, thiếu field, ...)
            continue
    
    return boost


# ============================================================================
# SIMILARITY BOOST FUNCTIONS (NEW - Phase 2)
# ============================================================================

def calculate_item_similarity(
    dataset,
    item_features: List[str] = ['style', 'price', 'star', 'score', 'city'],
    similarity_threshold: float = 0.5
) -> Dict[int, Dict[int, float]]:
    """Tính similarity giữa các items dựa trên features.
    
    Similarity được tính dựa trên:
    - style, city: Jaccard similarity (set overlap)
    - price, star, score: Normalized cosine similarity
    
    Args:
        dataset: RecBole dataset
        item_features: List of feature names để tính similarity
        similarity_threshold: Chỉ giữ similarities >= threshold (default: 0.5)
    
    Returns:
        Dict: {item_id: {similar_item_id: similarity_score, ...}, ...}
        Chỉ chứa similarities >= threshold
    """
    global _similarity_matrix_cache
    
    # Check cache
    if _similarity_matrix_cache is not None:
        return _similarity_matrix_cache
    
    print("[INFERENCE] Tính similarity matrix giữa items (lần đầu, sẽ cache)...")
    
    similarity_dict = {}
    
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
                id1_int = int(item_id1) if not isinstance(item_id1, int) else item_id1
                id2_int = int(item_id2) if not isinstance(item_id2, int) else item_id2
                if id1_int >= id2_int:
                    continue
            except (ValueError, TypeError):
                if str(item_id1) >= str(item_id2):
                    continue
            
            similarity = _calculate_item_pair_similarity(
                dataset, internal_id1, internal_id2, item_features
            )
            
            # Chỉ lưu nếu similarity >= threshold (đảm bảo similarity là float)
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
    
    # Cache kết quả
    _similarity_matrix_cache = similarity_dict
    
    return similarity_dict


def _calculate_item_pair_similarity(
    dataset,
    internal_id1: int,
    internal_id2: int,
    item_features: List[str]
) -> float:
    """Tính similarity giữa 2 items dựa trên features.
    
    Args:
        dataset: RecBole dataset
        internal_id1, internal_id2: Internal IDs của 2 items
        item_features: List of feature names
    
    Returns:
        Similarity score (0-1), càng cao càng giống nhau
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
            
            # Convert tensor to value nếu cần
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
                
            if isinstance(feat2, torch.Tensor):
                if feat2.numel() == 1:
                    # Scalar tensor → convert sang Python value
                    feat2 = feat2.item()
                else:
                    # Tensor có nhiều phần tử (TOKEN_SEQ) → convert sang list và join
                    try:
                        feat2_list = feat2.cpu().numpy().tolist()
                        if isinstance(feat2_list, list):
                            # Flatten nếu là nested list
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
                        # Fallback: convert to string
                        feat2 = str(feat2.cpu().numpy())
            elif not isinstance(feat2, (str, int, float)):
                # Nếu không phải tensor, string, int, float → convert sang string
                feat2 = str(feat2)
            
            # Tính similarity tùy theo field type
            if field in ['style', 'city']:
                # Token_seq fields: Jaccard similarity
                # Chuyển string thành set (split by space)
                set1 = set(str(feat1).split())
                set2 = set(str(feat2).split())
                if len(set1 | set2) == 0:
                    sim = 1.0  # Cả 2 đều empty → giống nhau
                else:
                    sim = len(set1 & set2) / len(set1 | set2)
                weight = 0.3  # Style và city có trọng số thấp hơn
                
            elif field in ['price', 'star', 'score']:
                # Float fields: Normalized cosine similarity
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
    """Tính boost cho từng item, bao gồm cả similarity boost (Phase 2).
    
    Logic:
    1. Tính direct boost từ actions (giống Phase 1)
    2. Tính similarity matrix (pre-compute và cache)
    3. Boost hotels tương tự hotels đã tương tác
    
    Args:
        actions: List of actions từ get_recent_user_actions()
        current_time: Unix timestamp hiện tại
        dataset: RecBole dataset (để tính similarity)
        decay_rate: Decay rate cho time weight
        similarity_threshold: Chỉ boost items có similarity >= threshold
        similarity_boost_factor: Trọng số cho similarity boost (0.5 = boost 50% của direct boost)
    
    Returns:
        Dict: {item_id: boost_score, ...}
    """
    # Bước 1: Tính direct boost (Phase 1)
    direct_boost = calculate_behavior_boost(actions, current_time, decay_rate)
    
    if len(direct_boost) == 0:
        return {}
    
    # Bước 2: Tính similarity matrix (pre-compute và cache)
    try:
        similarity_dict = calculate_item_similarity(dataset, similarity_threshold=similarity_threshold)
    except Exception as e:
        print(f"[WARNING] Lỗi khi tính similarity: {e}. Chỉ dùng direct boost.")
        return direct_boost
    
    # Bước 3: Boost hotels tương tự
    final_boost = direct_boost.copy()
    
    for item_id, direct_boost_value in direct_boost.items():
        # Tìm hotels tương tự
        similar_items = similarity_dict.get(item_id, {})
        
        for similar_item_id, similarity_score in similar_items.items():
            try:
                # Đảm bảo similarity_score là float
                score_float = float(similarity_score) if not isinstance(similarity_score, (int, float)) else similarity_score
                if score_float >= similarity_threshold and similar_item_id != item_id:
                    # Boost hotels tương tự với trọng số similarity
                    # similarity_boost = direct_boost * similarity_score * similarity_boost_factor
                    similarity_boost = direct_boost_value * score_float * similarity_boost_factor
                    
                    # Cộng dồn với boost hiện tại (có thể đã có direct boost hoặc similarity boost từ items khác)
                    final_boost[similar_item_id] = final_boost.get(similar_item_id, 0) + similarity_boost
            except (ValueError, TypeError):
                # Skip nếu không convert được similarity_score
                continue
    
    return final_boost


if __name__ == "__main__":
    # Test inference
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

