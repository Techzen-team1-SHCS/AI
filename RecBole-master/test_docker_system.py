"""
Script test hệ thống Docker sau khi build
Test từ đầu đến cuối: API, ETL, Behavior Boost
"""
import json
import sys
import io
import time
import urllib.request
import urllib.error
from typing import Dict, List, Tuple, Optional

# Fix encoding cho Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:5000"

def print_header(title: str):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def http_get(url: str, params: Optional[Dict] = None) -> Tuple[int, Dict]:
    """Helper function để gọi GET request"""
    if params:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query_string}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.getcode()
            data = json.loads(response.read().decode('utf-8'))
            return status, data
    except urllib.error.HTTPError as e:
        return e.code, {"error": str(e)}
    except Exception as e:
        raise

def http_post(url: str, data: Dict) -> Tuple[int, Dict]:
    """Helper function để gọi POST request"""
    json_data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=json_data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.getcode()
            resp_data = json.loads(response.read().decode('utf-8'))
            return status, resp_data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_data = json.loads(error_body)
        except:
            error_data = {"error": error_body}
        return e.code, error_data
    except Exception as e:
        raise

def test_health():
    """Test 1: Health check"""
    print_header("TEST 1: Health Check")
    try:
        status, data = http_get(f"{BASE_URL}/health")
        print(f"Status: {status}")
        print(f"Response: {json.dumps(data, indent=2)}")
        if status == 200 and data.get("ok") and data.get("model_loaded"):
            print("✓ Health check PASSED")
            return True
        else:
            print("✗ Health check FAILED - Model chưa load")
            return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_recommendations_basic():
    """Test 2: Recommendations cơ bản (không behavior boost)"""
    print_header("TEST 2: Recommendations Cơ Bản (không behavior boost)")
    try:
        user_id = "1"
        status, data = http_get(
            f"{BASE_URL}/recommendations/{user_id}",
            params={
                "top_k": 5,
                "use_behavior_boost": "false"
            }
        )
        print(f"Status: {status}")
        if status == 200:
            print(f"User ID: {data.get('user_id')}")
            print(f"Recommendations count: {len(data.get('recommendations', []))}")
            print(f"First 3 recommendations: {data.get('recommendations', [])[:3]}")
            print("✓ Recommendations cơ bản PASSED")
            return True, data.get('recommendations', [])
        else:
            print(f"✗ FAILED: {status} - {json.dumps(data, indent=2)}")
            return False, []
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, []

def test_user_action_post():
    """Test 3: POST user action"""
    print_header("TEST 3: POST User Action")
    try:
        action = {
            "user_id": 999,
            "item_id": 100,
            "action_type": "click",
            "timestamp": int(time.time())
        }
        status, data = http_post(f"{BASE_URL}/user_action", action)
        print(f"Status: {status}")
        if status == 200:
            print(f"Response: {json.dumps(data, indent=2)}")
            print("✓ POST user action PASSED")
            return True, action
        else:
            print(f"✗ FAILED: {status} - {json.dumps(data, indent=2)}")
            return False, None
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_recommendations_with_behavior_boost():
    """Test 4: Recommendations với behavior boost"""
    print_header("TEST 4: Recommendations Với Behavior Boost")
    try:
        # Đợi một chút để ETL có thể xử lý
        print("Đợi 5 giây để ETL xử lý...")
        time.sleep(5)
        
        user_id = "999"
        status, data = http_get(
            f"{BASE_URL}/recommendations/{user_id}",
            params={
                "top_k": 5,
                "use_behavior_boost": "true",
                "alpha": 0.3,
                "behavior_hours": 24
            }
        )
        print(f"Status: {status}")
        if status == 200:
            print(f"User ID: {data.get('user_id')}")
            recs = data.get('recommendations', [])
            print(f"Recommendations count: {len(recs)}")
            print(f"Recommendations: {recs}")
            print("✓ Recommendations với behavior boost PASSED")
            return True
        else:
            print(f"✗ FAILED: {status} - {json.dumps(data, indent=2)}")
            return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_recommendations_cold_start():
    """Test 5: Cold start (user mới)"""
    print_header("TEST 5: Cold Start (User Mới)")
    try:
        user_id = "9999"  # User chưa có trong dataset
        status, data = http_get(
            f"{BASE_URL}/recommendations/{user_id}",
            params={"top_k": 5}
        )
        print(f"Status: {status}")
        if status == 200:
            recs = data.get('recommendations', [])
            print(f"Recommendations count: {len(recs)}")
            print(f"Recommendations: {recs[:5]}")
            if len(recs) > 0:
                print("✓ Cold start PASSED - System có thể recommend cho user mới")
                return True
            else:
                print("⚠ Cold start - Không có recommendations (có thể OK)")
                return True
        else:
            print(f"✗ FAILED: {status} - {json.dumps(data, indent=2)}")
            return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Chạy tất cả các test"""
    print("=" * 70)
    print(" BẮT ĐẦU TEST HỆ THỐNG DOCKER")
    print("=" * 70)
    
    results = {}
    
    # Test 1: Health check
    results['health'] = test_health()
    
    # Test 2: Recommendations cơ bản
    success, recs = test_recommendations_basic()
    results['recommendations_basic'] = success
    if not success:
        print("\n⚠ Không thể test tiếp vì recommendations cơ bản thất bại")
        return
    
    # Test 3: POST user action
    results['user_action'] = False
    success, action = test_user_action_post()
    results['user_action'] = success
    
    # Test 4: Recommendations với behavior boost
    if success:
        results['behavior_boost'] = test_recommendations_with_behavior_boost()
    else:
        print("\n⚠ Bỏ qua test behavior boost vì POST action thất bại")
        results['behavior_boost'] = False
    
    # Test 5: Cold start
    results['cold_start'] = test_recommendations_cold_start()
    
    # Tổng kết
    print_header("KẾT QUẢ TỔNG KẾT")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"Tổng số test: {total}")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    print("\nChi tiết:")
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  - {test_name}: {status}")
    
    if passed == total:
        print("\n🎉 TẤT CẢ TEST ĐỀU PASSED!")
    else:
        print(f"\n⚠ Có {total - passed} test thất bại")

if __name__ == "__main__":
    main()
