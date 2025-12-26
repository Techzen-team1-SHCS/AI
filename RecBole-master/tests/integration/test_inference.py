"""
Script test inference endpoint và inference module.
Test với user có trong dataset và user mới (cold start).
"""
import sys
import os
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add root directory to path (go up 2 levels from tests/integration/)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# Check if dependencies are available
try:
    import torch
    import recbole
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    MISSING_DEPENDENCY = str(e)

if DEPENDENCIES_AVAILABLE:
    from inference import load_model, get_recommendations, is_model_loaded
    from recbole.data import create_dataset
    from recbole.config import Config
else:
    # Dummy functions để test không crash
    def load_model(*args, **kwargs):
        raise ImportError(f"Dependencies không có sẵn: {MISSING_DEPENDENCY}. Vui lòng chạy trong Docker hoặc virtualenv có đầy đủ dependencies.")
    def get_recommendations(*args, **kwargs):
        raise ImportError(f"Dependencies không có sẵn: {MISSING_DEPENDENCY}")
    def is_model_loaded():
        return False

def test_load_model():
    """Test load model."""
    print("=" * 70)
    print("TEST 1: Load Model")
    print("=" * 70)
    
    try:
        config, model, dataset = load_model()
        print(f"✅ Load model thành công!")
        print(f"   Model: {config['model']}")
        print(f"   Dataset: {dataset.dataset_name}")
        print(f"   Users: {dataset.user_num}")
        print(f"   Items: {dataset.item_num}")
        return config, model, dataset
    except Exception as e:
        print(f"❌ Lỗi khi load model: {e}")
        return None, None, None


def test_get_recommendations_with_existing_user(dataset):
    """Test get recommendations với user có trong dataset."""
    print("\n" + "=" * 70)
    print("TEST 2: Get Recommendations - User có trong dataset")
    print("=" * 70)
    
    if dataset is None:
        print("❌ Dataset không có, skip test này")
        return
    
    # Lấy user đầu tiên trong dataset (skip [PAD] token)
    try:
        # Start from 1 to skip [PAD] token
        test_user = dataset.id2token(dataset.uid_field, 1)
        print(f"Test với user: {test_user}")
        
        # Test với top_k=5
        recommendations = get_recommendations(test_user, top_k=5, exclude_interacted=True)
        print(f"✅ Recommendations thành công!")
        print(f"   User: {test_user}")
        print(f"   Recommendations ({len(recommendations)}): {recommendations[:5]}")
        
        # Test với top_k=10
        recommendations = get_recommendations(test_user, top_k=10, exclude_interacted=True)
        print(f"   Recommendations ({len(recommendations)}): {recommendations}")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()


def test_get_recommendations_with_new_user():
    """Test get recommendations với user mới (cold start)."""
    print("\n" + "=" * 70)
    print("TEST 3: Get Recommendations - User mới (Cold Start)")
    print("=" * 70)
    
    try:
        new_user = "new_user_999"
        recommendations = get_recommendations(new_user, top_k=10, exclude_interacted=True)
        print(f"✅ Cold start xử lý thành công!")
        print(f"   User: {new_user}")
        print(f"   Recommendations: {recommendations}")
        print(f"   (Trả về empty list - backend sẽ xử lý)")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()


def test_model_cache():
    """Test model cache."""
    print("\n" + "=" * 70)
    print("TEST 4: Model Cache")
    print("=" * 70)
    
    # Kiểm tra model đã load chưa
    loaded_before = is_model_loaded()
    print(f"Model loaded trước khi test: {loaded_before}")
    
    # Load model lần đầu
    print("\nLoad model lần đầu...")
    import time
    start = time.time()
    config, model, dataset = load_model()
    time1 = time.time() - start
    print(f"   Thời gian load lần 1: {time1:.2f} giây")
    
    # Load model lần 2 (should use cache)
    print("\nLoad model lần 2 (should use cache)...")
    start = time.time()
    config2, model2, dataset2 = load_model()
    time2 = time.time() - start
    print(f"   Thời gian load lần 2: {time2:.2f} giây")
    
    # Verify cache works
    if time2 < time1 / 10:  # Cache should be at least 10x faster
        print(f"✅ Cache hoạt động tốt! (Nhanh hơn {time1/time2:.1f}x)")
    else:
        print(f"⚠️  Cache có vẻ không hoạt động tốt")
    
    # Verify same objects
    if model is model2:
        print(f"✅ Cùng một object trong memory (cache works!)")
    else:
        print(f"⚠️  Không cùng object (cache có vấn đề?)")


def test_multiple_users(dataset):
    """Test với nhiều users khác nhau."""
    print("\n" + "=" * 70)
    print("TEST 5: Test với nhiều users")
    print("=" * 70)
    
    if dataset is None:
        print("❌ Dataset không có, skip test này")
        return
    
    try:
        # Test với 5 users đầu tiên (skip [PAD] token)
        count = 0
        for i in range(1, min(6, dataset.user_num)):  # Start from 1 to skip [PAD]
            user = dataset.id2token(dataset.uid_field, i)
            if user == "[PAD]":
                continue
            recommendations = get_recommendations(user, top_k=5, exclude_interacted=True)
            print(f"User {user}: {len(recommendations)} recommendations")
            if recommendations:
                print(f"   Top 3: {recommendations[:3]}")
            count += 1
            if count >= 3:  # Test với 3 users là đủ
                break
        
        print("✅ Test với nhiều users thành công!")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("BẮT ĐẦU TEST INFERENCE")
    print("=" * 70 + "\n")
    
    # Check dependencies
    if not DEPENDENCIES_AVAILABLE:
        print("⚠️  WARNING: Không tìm thấy dependencies (torch, recbole)")
        print(f"   Lỗi: {MISSING_DEPENDENCY}")
        print("\n💡 HƯỚNG DẪN:")
        print("   1. Chạy trong Docker container:")
        print("      docker-compose exec recbole-api python tests/integration/test_inference.py")
        print("   2. Hoặc kích hoạt virtualenv:")
        print("      recbole-env\\Scripts\\activate (Windows)")
        print("      source recbole-env/bin/activate (Linux/Mac)")
        print("   3. Hoặc cài đặt dependencies:")
        print("      pip install torch recbole")
        print("\n⏭️  Skip tất cả tests...")
        sys.exit(0)
    
    # Test 1: Load model
    config, model, dataset = test_load_model()
    
    if dataset is None:
        print("\n❌ Không thể load model, dừng test.")
        sys.exit(1)
    
    # Test 2: Get recommendations với user có trong dataset
    test_get_recommendations_with_existing_user(dataset)
    
    # Test 3: Cold start
    test_get_recommendations_with_new_user()
    
    # Test 4: Model cache
    test_model_cache()
    
    # Test 5: Multiple users
    test_multiple_users(dataset)
    
    print("\n" + "=" * 70)
    print("KẾT THÚC TEST")
    print("=" * 70)
    print("\n✅ Tất cả tests đã chạy xong!")

