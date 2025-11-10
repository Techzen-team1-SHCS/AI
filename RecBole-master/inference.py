"""
Inference module for RecBole DeepFM model.
Loads trained model and provides recommendation functionality.
"""
import os
import glob
import torch
from typing import List, Optional, Tuple
import numpy as np

from recbole.quick_start import load_data_and_model
from recbole.data import create_dataset
from recbole.data.interaction import Interaction
from recbole.config import Config

# Global variables for caching
_model_cache = None
_config_cache = None
_dataset_cache = None


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


def load_model(model_path: Optional[str] = None, force_reload: bool = False) -> Tuple[Config, torch.nn.Module, any]:
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
    if not force_reload and _model_cache is not None:
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
                return set(item_tokens.tolist())
            else:
                return set(item_tokens)
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
    exclude_interacted: bool = True
) -> List[str]:
    """Lấy recommendations cho user.
    
    Args:
        user_id: ID của user (external token, ví dụ: "user_123")
        top_k: Số lượng recommendations cần trả về
        model_path: Đường dẫn đến checkpoint (None = dùng checkpoint mới nhất)
        exclude_interacted: Nếu True, loại bỏ items user đã tương tác
        
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
    
    # Lấy top-K items (internal IDs)
    top_k_indices = np.argsort(scores)[::-1][:top_k + len(interacted_items)]
    top_k_items = []
    
    # Convert internal IDs to external tokens và filter interacted items
    for idx in top_k_indices:
        item_internal_id = int(all_item_internal_ids[idx].item())
        try:
            item_token = dataset.id2token(dataset.iid_field, item_internal_id)
            
            # Skip nếu đã tương tác
            if exclude_interacted and item_token in interacted_items:
                continue
            
            top_k_items.append(item_token)
            
            if len(top_k_items) >= top_k:
                break
        except (ValueError, IndexError) as e:
            # Skip nếu có lỗi khi convert
            continue
    
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
    global _model_cache, _config_cache, _dataset_cache
    _model_cache = None
    _config_cache = None
    _dataset_cache = None


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

