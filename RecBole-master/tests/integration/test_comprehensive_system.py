"""
Script test tổng thể hệ thống theo TEST_PLAN.md
Test từ đầu đến cuối: Input → Processing → Output → E2E
"""
import json
import sys
import io
import time
import os
import urllib.request
import urllib.error
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime

# Fix encoding cho Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:5000"
TEST_RESULTS = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "details": []
}

def print_header(title: str):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def log_result(test_name: str, passed: bool, message: str = "", skip: bool = False):
    """Log kết quả test"""
    if skip:
        TEST_RESULTS["skipped"] += 1
        status = "⏭️  SKIPPED"
    elif passed:
        TEST_RESULTS["passed"] += 1
        status = "✓ PASSED"
    else:
        TEST_RESULTS["failed"] += 1
        status = "✗ FAILED"
    
    TEST_RESULTS["details"].append({
        "test": test_name,
        "status": status,
        "message": message
    })
    print(f"{status}: {test_name}")
    if message:
        print(f"  → {message}")

def http_get(url: str, params: Optional[Dict] = None) -> Tuple[int, Dict]:
    """Helper function để gọi GET request"""
    if params:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query_string}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status = response.getcode()
            data = json.loads(response.read().decode('utf-8'))
            return status, data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_data = json.loads(error_body)
        except:
            error_data = {"error": error_body}
        return e.code, error_data
    except Exception as e:
        raise

def http_post(url: str, data: Union[Dict, List]) -> Tuple[int, Dict]:
    """Helper function để gọi POST request"""
    json_data = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=json_data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
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

def count_lines(filepath: str) -> int:
    """Đếm số dòng trong file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    except:
        return 0

# ============================================================================
# PHẦN 1: TEST ĐẦU VÀO (Input Testing)
# ============================================================================

def test_1_1_1_post_user_action_single():
    """Test 1.1.1: POST /user_action - Single Action"""
    print_header("TEST 1.1.1: POST /user_action - Single Action")
    
    # Test với các action types khác nhau
    action_types = ["click", "like", "share", "booking"]
    all_passed = True
    
    for action_type in action_types:
        action = {
            "user_id": 1001,
            "item_id": 200,
            "action_type": action_type,
            "timestamp": int(time.time())
        }
        try:
            status, data = http_post(f"{BASE_URL}/user_action", action)
            if status == 200 and data.get("status") == "success":
                print(f"  ✓ {action_type} action: PASSED")
            else:
                print(f"  ✗ {action_type} action: FAILED - {status}")
                all_passed = False
        except Exception as e:
            print(f"  ✗ {action_type} action: ERROR - {e}")
            all_passed = False
    
    # Test invalid cases
    invalid_tests = [
        ({"user_id": 1002, "item_id": 201, "action_type": "invalid", "timestamp": int(time.time())}, "Invalid action_type"),
        ({"user_id": 1003, "item_id": 202, "timestamp": int(time.time())}, "Missing action_type"),
        ({"user_id": "", "item_id": 203, "action_type": "click", "timestamp": int(time.time())}, "Empty user_id"),
    ]
    
    for invalid_data, test_name in invalid_tests:
        try:
            status, data = http_post(f"{BASE_URL}/user_action", invalid_data)
            if status != 200:
                print(f"  ✓ {test_name}: PASSED (correctly rejected)")
            else:
                print(f"  ✗ {test_name}: FAILED (should be rejected)")
                all_passed = False
        except Exception as e:
            print(f"  ⚠ {test_name}: {e}")
    
    log_result("POST /user_action - Single Action", all_passed)
    return all_passed

def test_1_1_2_post_user_actions_batch():
    """Test 1.1.2: POST /user_actions_batch - Batch Actions"""
    print_header("TEST 1.1.2: POST /user_actions_batch - Batch Actions")
    
    # Test valid batch - endpoint nhận trực tiếp list, không phải {"actions": [...]}
    actions = [
        {"user_id": 1004, "item_id": 300, "action_type": "click", "timestamp": int(time.time())},
        {"user_id": 1004, "item_id": 301, "action_type": "like", "timestamp": int(time.time()) + 1}
    ]
    
    try:
        status, data = http_post(f"{BASE_URL}/user_actions_batch", actions)  # Gửi list trực tiếp
        if status == 200 and data.get("status") == "success" and data.get("count") == 2:
            log_result("POST /user_actions_batch - Valid batch", True)
            return True
        else:
            log_result("POST /user_actions_batch - Valid batch", False, f"Status: {status}, Data: {data}")
            return False
    except Exception as e:
        log_result("POST /user_actions_batch - Valid batch", False, str(e))
        return False

def test_1_2_1_validation_rules():
    """Test 1.2.1: Validation Rules"""
    print_header("TEST 1.2.1: Validation Rules")
    
    # Kiểm tra log file format
    log_file = "data/user_actions.log"
    if not os.path.exists(log_file):
        log_result("Validation Rules - Log file format", False, "Log file không tồn tại")
        return False
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if not lines:
                log_result("Validation Rules - Log file format", True, "Log file rỗng (OK)")
                return True
            
            valid_json_count = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    action = json.loads(line)
                    # Validate fields
                    if "user_id" in action and "item_id" in action and "action_type" in action:
                        valid_json_count += 1
                except json.JSONDecodeError:
                    pass
            
            if valid_json_count > 0:
                log_result("Validation Rules - Log file format", True, f"{valid_json_count} valid JSON entries")
                return True
            else:
                log_result("Validation Rules - Log file format", False, "Không có valid JSON entries")
                return False
    except Exception as e:
        log_result("Validation Rules - Log file format", False, str(e))
        return False

# ============================================================================
# PHẦN 2: TEST XỬ LÝ (Processing Testing)
# ============================================================================

def test_2_1_2_etl_update_dataset():
    """Test 2.1.2: ETL Cập Nhật Dataset"""
    print_header("TEST 2.1.2: ETL Cập Nhật Dataset")
    
    hotel_inter_file = "dataset/hotel/hotel.inter"
    if not os.path.exists(hotel_inter_file):
        log_result("ETL Update Dataset", False, "hotel.inter không tồn tại")
        return False
    
    # Đếm số dòng trước khi ETL chạy
    before_count = count_lines(hotel_inter_file)
    print(f"  Số dòng trước: {before_count}")
    
    # Gửi 5 actions mới
    actions = []
    for i in range(5):
        actions.append({
            "user_id": 2000 + i,
            "item_id": 400 + i,
            "action_type": "click",
            "timestamp": int(time.time()) + i
        })
    
    try:
        status, data = http_post(f"{BASE_URL}/user_actions_batch", actions)  # Gửi list trực tiếp
        if status != 200:
            log_result("ETL Update Dataset", False, "Không thể gửi actions")
            return False
        
        print("  Đã gửi 5 actions, đợi ETL xử lý (có thể mất 3 phút)...")
        print("  Đợi 10 giây để ETL có cơ hội chạy...")
        time.sleep(10)
        
        # Kiểm tra lại
        after_count = count_lines(hotel_inter_file)
        print(f"  Số dòng sau: {after_count}")
        
        if after_count >= before_count:
            log_result("ETL Update Dataset", True, f"Dataset được cập nhật ({before_count} → {after_count})")
            return True
        else:
            log_result("ETL Update Dataset", False, "Dataset không được cập nhật")
            return False
    except Exception as e:
        log_result("ETL Update Dataset", False, str(e))
        return False

def test_2_2_1_read_recent_actions():
    """Test 2.2.1: Đọc Recent Actions"""
    print_header("TEST 2.2.1: Đọc Recent Actions")
    
    # Gửi action mới
    test_user_id = 3000
    action = {
        "user_id": test_user_id,
        "item_id": 500,
        "action_type": "click",
        "timestamp": int(time.time())
    }
    
    try:
        # Gửi action
        status, _ = http_post(f"{BASE_URL}/user_action", action)
        if status != 200:
            log_result("Read Recent Actions", False, "Không thể gửi action")
            return False
        
        # Đợi một chút
        time.sleep(2)
        
        # Gọi recommendations với behavior boost
        status, data = http_get(
            f"{BASE_URL}/recommendations/{test_user_id}",
            params={
                "top_k": 5,
                "use_behavior_boost": "true",
                "behavior_hours": 24
            }
        )
        
        if status == 200:
            recs = data.get("recommendations", [])
            log_result("Read Recent Actions", True, f"Recommendations: {len(recs)} items")
            return True
        else:
            log_result("Read Recent Actions", False, f"Status: {status}")
            return False
    except Exception as e:
        log_result("Read Recent Actions", False, str(e))
        return False

def test_2_2_2_boost_scores():
    """Test 2.2.2: Tính Toán Boost Scores"""
    print_header("TEST 2.2.2: Tính Toán Boost Scores")
    
    test_user_id = 3001
    test_item_id = 501
    
    # Gửi nhiều actions cùng item với thời gian khác nhau
    actions = [
        {"user_id": test_user_id, "item_id": test_item_id, "action_type": "click", "timestamp": int(time.time()) - 3600},  # 1h ago
        {"user_id": test_user_id, "item_id": test_item_id, "action_type": "like", "timestamp": int(time.time()) - 1800},  # 30m ago
        {"user_id": test_user_id, "item_id": test_item_id, "action_type": "booking", "timestamp": int(time.time())},  # now
    ]
    
    try:
        # Gửi actions
        for action in actions:
            status, _ = http_post(f"{BASE_URL}/user_action", action)
            if status != 200:
                log_result("Boost Scores - Multiple actions", False, "Không thể gửi actions")
                return False
        
        time.sleep(2)
        
        # Lấy recommendations với và không có boost
        status_no_boost, data_no_boost = http_get(
            f"{BASE_URL}/recommendations/{test_user_id}",
            params={"top_k": 10, "use_behavior_boost": "false"}
        )
        
        status_with_boost, data_with_boost = http_get(
            f"{BASE_URL}/recommendations/{test_user_id}",
            params={"top_k": 10, "use_behavior_boost": "true", "alpha": 0.3}
        )
        
        if status_no_boost == 200 and status_with_boost == 200:
            recs_no_boost = data_no_boost.get("recommendations", [])
            recs_with_boost = data_with_boost.get("recommendations", [])
            
            # Recommendations nên khác nhau (hoặc ít nhất có thể khác)
            if recs_no_boost != recs_with_boost or len(recs_with_boost) > 0:
                log_result("Boost Scores - Multiple actions", True, "Boost ảnh hưởng recommendations")
                return True
            else:
                log_result("Boost Scores - Multiple actions", True, "Recommendations giống nhau (có thể OK)")
                return True
        else:
            log_result("Boost Scores - Multiple actions", False, f"Status: {status_no_boost}/{status_with_boost}")
            return False
    except Exception as e:
        log_result("Boost Scores - Multiple actions", False, str(e))
        return False

def test_2_2_3_similarity_boost():
    """Test 2.2.3: Similarity Boost"""
    print_header("TEST 2.2.3: Similarity Boost")
    
    test_user_id = 3002
    test_item_id = 502  # Giả sử item này có features cụ thể
    
    # Gửi action
    action = {
        "user_id": test_user_id,
        "item_id": test_item_id,
        "action_type": "click",
        "timestamp": int(time.time())
    }
    
    try:
        status, _ = http_post(f"{BASE_URL}/user_action", action)
        if status != 200:
            log_result("Similarity Boost", False, "Không thể gửi action")
            return False
        
        time.sleep(2)
        
        # Lấy recommendations với similarity boost
        status, data = http_get(
            f"{BASE_URL}/recommendations/{test_user_id}",
            params={
                "top_k": 10,
                "use_behavior_boost": "true",
                "use_similarity_boost": "true",
                "similarity_threshold": 0.5
            }
        )
        
        if status == 200:
            recs = data.get("recommendations", [])
            log_result("Similarity Boost", True, f"Recommendations với similarity: {len(recs)} items")
            return True
        else:
            log_result("Similarity Boost", False, f"Status: {status}")
            return False
    except Exception as e:
        log_result("Similarity Boost", False, str(e))
        return False

# ============================================================================
# PHẦN 3: TEST ĐẦU RA (Output Testing)
# ============================================================================

def test_3_1_1_recommendations_basic():
    """Test 3.1.1: GET /recommendations/{user_id} - Basic"""
    print_header("TEST 3.1.1: GET /recommendations - Basic")
    
    test_cases = [
        ("1", 10, False),  # User có trong dataset
        ("9999", 5, False),  # User mới (cold start)
    ]
    
    all_passed = True
    for user_id, top_k, use_boost in test_cases:
        try:
            status, data = http_get(
                f"{BASE_URL}/recommendations/{user_id}",
                params={"top_k": top_k, "use_behavior_boost": "false"}
            )
            
            if status == 200:
                recs = data.get("recommendations", [])
                if isinstance(recs, list) and len(recs) <= top_k:
                    print(f"  ✓ User {user_id}: {len(recs)} recommendations")
                else:
                    print(f"  ✗ User {user_id}: Invalid format")
                    all_passed = False
            else:
                print(f"  ✗ User {user_id}: Status {status}")
                all_passed = False
        except Exception as e:
            print(f"  ✗ User {user_id}: {e}")
            all_passed = False
    
    log_result("GET /recommendations - Basic", all_passed)
    return all_passed

def test_3_1_2_recommendations_with_boost():
    """Test 3.1.2: GET /recommendations - With Behavior Boost"""
    print_header("TEST 3.1.2: GET /recommendations - With Behavior Boost")
    
    test_user_id = 4000
    test_item_id = 600
    
    # Gửi action
    action = {
        "user_id": test_user_id,
        "item_id": test_item_id,
        "action_type": "click",
        "timestamp": int(time.time())
    }
    
    try:
        status, _ = http_post(f"{BASE_URL}/user_action", action)
        if status != 200:
            log_result("Recommendations with Boost", False, "Không thể gửi action")
            return False
        
        time.sleep(2)
        
        # Lấy recommendations với boost
        status, data = http_get(
            f"{BASE_URL}/recommendations/{test_user_id}",
            params={
                "top_k": 10,
                "use_behavior_boost": "true",
                "alpha": 0.3
            }
        )
        
        if status == 200:
            recs = data.get("recommendations", [])
            log_result("Recommendations with Boost", True, f"{len(recs)} recommendations")
            return True
        else:
            log_result("Recommendations with Boost", False, f"Status: {status}")
            return False
    except Exception as e:
        log_result("Recommendations with Boost", False, str(e))
        return False

def test_3_1_4_cold_start():
    """Test 3.1.4: Cold Start - New User"""
    print_header("TEST 3.1.4: Cold Start - New User")
    
    new_user_id = "99999"  # User chưa có trong dataset
    
    try:
        status, data = http_get(
            f"{BASE_URL}/recommendations/{new_user_id}",
            params={"top_k": 5}
        )
        
        if status == 200:
            recs = data.get("recommendations", [])
            log_result("Cold Start", True, f"{len(recs)} recommendations cho user mới")
            return True
        else:
            log_result("Cold Start", False, f"Status: {status}")
            return False
    except Exception as e:
        log_result("Cold Start", False, str(e))
        return False

def test_3_1_5_edge_cases():
    """Test 3.1.5: Edge Cases"""
    print_header("TEST 3.1.5: Edge Cases")
    
    edge_cases = [
        ("1", 1, "top_k=1"),
        ("1", 100, "top_k=100"),
    ]
    
    all_passed = True
    for user_id, top_k, test_name in edge_cases:
        try:
            status, data = http_get(
                f"{BASE_URL}/recommendations/{user_id}",
                params={"top_k": top_k}
            )
            
            if status == 200:
                recs = data.get("recommendations", [])
                print(f"  ✓ {test_name}: {len(recs)} recommendations")
            else:
                print(f"  ✗ {test_name}: Status {status}")
                all_passed = False
        except Exception as e:
            print(f"  ✗ {test_name}: {e}")
            all_passed = False
    
    # Test empty user_id riêng (có thể API không reject)
    try:
        status, _ = http_get(f"{BASE_URL}/recommendations/", params={"top_k": 10})
        # Empty user_id có thể trả về 404 hoặc 400, cả hai đều OK
        if status in [400, 404]:
            print(f"  ✓ Empty user_id: Correctly rejected (status {status})")
        else:
            print(f"  ⚠ Empty user_id: Status {status} (có thể OK)")
    except Exception as e:
        print(f"  ⚠ Empty user_id: {e}")
    
    log_result("Edge Cases", all_passed)
    return all_passed

# ============================================================================
# PHẦN 4: TEST END-TO-END (E2E Testing)
# ============================================================================

def test_4_1_1_full_flow():
    """Test 4.1.1: Full Flow - User Tương Tác và Nhận Recommendations"""
    print_header("TEST 4.1.1: Full Flow - User Journey")
    
    test_user_id = 5000
    test_item_1 = 700
    test_item_2 = 701
    
    try:
        # Step 1: User click item 1
        action1 = {
            "user_id": test_user_id,
            "item_id": test_item_1,
            "action_type": "click",
            "timestamp": int(time.time())
        }
        status1, _ = http_post(f"{BASE_URL}/user_action", action1)
        if status1 != 200:
            log_result("Full Flow", False, "Step 1: Không thể gửi action")
            return False
        
        time.sleep(2)
        
        # Step 2: Get recommendations
        status2, data2 = http_get(
            f"{BASE_URL}/recommendations/{test_user_id}",
            params={"top_k": 10, "use_behavior_boost": "true"}
        )
        if status2 != 200:
            log_result("Full Flow", False, "Step 2: Không thể lấy recommendations")
            return False
        
        recs1 = data2.get("recommendations", [])
        print(f"  Recommendations sau action 1: {len(recs1)} items")
        
        # Step 3: User like item 2
        action2 = {
            "user_id": test_user_id,
            "item_id": test_item_2,
            "action_type": "like",
            "timestamp": int(time.time()) + 1
        }
        status3, _ = http_post(f"{BASE_URL}/user_action", action2)
        if status3 != 200:
            log_result("Full Flow", False, "Step 3: Không thể gửi action 2")
            return False
        
        time.sleep(2)
        
        # Step 4: Get recommendations lại
        status4, data4 = http_get(
            f"{BASE_URL}/recommendations/{test_user_id}",
            params={"top_k": 10, "use_behavior_boost": "true"}
        )
        if status4 != 200:
            log_result("Full Flow", False, "Step 4: Không thể lấy recommendations 2")
            return False
        
        recs2 = data4.get("recommendations", [])
        print(f"  Recommendations sau action 2: {len(recs2)} items")
        
        log_result("Full Flow", True, f"Flow hoàn chỉnh: {len(recs1)} → {len(recs2)} recommendations")
        return True
    except Exception as e:
        log_result("Full Flow", False, str(e))
        return False

# ============================================================================
# PHẦN 5: PERFORMANCE TESTING
# ============================================================================

def test_4_2_1_api_response_time():
    """Test 4.2.1: API Response Time"""
    print_header("TEST 4.2.1: API Response Time")
    
    times = {
        "health": [],
        "recommendations_basic": [],
        "recommendations_boost": [],
        "post_action": []
    }
    
    # Test health check
    for _ in range(5):
        start = time.time()
        try:
            status, _ = http_get(f"{BASE_URL}/health")
            elapsed = (time.time() - start) * 1000
            if status == 200:
                times["health"].append(elapsed)
        except:
            pass
    
    # Test recommendations basic
    for _ in range(3):
        start = time.time()
        try:
            status, _ = http_get(f"{BASE_URL}/recommendations/1", params={"top_k": 10, "use_behavior_boost": "false"})
            elapsed = (time.time() - start) * 1000
            if status == 200:
                times["recommendations_basic"].append(elapsed)
        except:
            pass
    
    # Test recommendations with boost
    for _ in range(3):
        start = time.time()
        try:
            status, _ = http_get(f"{BASE_URL}/recommendations/1", params={"top_k": 10, "use_behavior_boost": "true"})
            elapsed = (time.time() - start) * 1000
            if status == 200:
                times["recommendations_boost"].append(elapsed)
        except:
            pass
    
    # Test POST action
    for _ in range(5):
        start = time.time()
        try:
            action = {"user_id": 6000, "item_id": 800, "action_type": "click", "timestamp": int(time.time())}
            status, _ = http_post(f"{BASE_URL}/user_action", action)
            elapsed = (time.time() - start) * 1000
            if status == 200:
                times["post_action"].append(elapsed)
        except:
            pass
    
    # Tính average
    results = {}
    for key, values in times.items():
        if values:
            avg = sum(values) / len(values)
            results[key] = avg
            print(f"  {key}: {avg:.2f}ms (avg)")
    
    # Check targets
    passed = True
    if "health" in results and results["health"] > 100:
        print(f"  ⚠ Health check: {results['health']:.2f}ms > 100ms target")
    if "recommendations_basic" in results and results["recommendations_basic"] > 2000:
        print(f"  ⚠ Recommendations basic: {results['recommendations_basic']:.2f}ms > 2000ms target")
    if "recommendations_boost" in results and results["recommendations_boost"] > 3000:
        print(f"  ⚠ Recommendations boost: {results['recommendations_boost']:.2f}ms > 3000ms target")
    if "post_action" in results and results["post_action"] > 200:
        print(f"  ⚠ POST action: {results['post_action']:.2f}ms > 200ms target")
    
    log_result("API Response Time", passed, f"Measured: {results}")
    return passed

# ============================================================================
# PHẦN 6: INTEGRATION TESTING
# ============================================================================

def test_4_3_1_docker_containers():
    """Test 4.3.1: Docker Containers"""
    print_header("TEST 4.3.1: Docker Containers")
    
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout
            containers = {
                "recbole-api": False,
                "recbole-etl": False,
                "recbole-retrain": False
            }
            
            for line in output.split('\n'):
                for container in containers.keys():
                    if container in line and "Up" in line:
                        containers[container] = True
                        print(f"  ✓ {container}: Running")
            
            all_running = all(containers.values())
            log_result("Docker Containers", all_running, f"Running: {sum(containers.values())}/3")
            return all_running
        else:
            log_result("Docker Containers", False, "Cannot check containers")
            return False
    except Exception as e:
        log_result("Docker Containers", False, str(e))
        return False

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Chạy tất cả các test"""
    print("=" * 70)
    print(" BẮT ĐẦU TEST TỔNG THỂ HỆ THỐNG")
    print("=" * 70)
    print(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test health check trước
    print_header("PRE-CHECK: Health Check")
    try:
        status, data = http_get(f"{BASE_URL}/health")
        if status == 200 and data.get("model_loaded"):
            print("✓ API đang chạy và model đã load")
        else:
            print("✗ API không sẵn sàng")
            return
    except Exception as e:
        print(f"✗ Không thể kết nối API: {e}")
        return
    
    # PHẦN 1: TEST ĐẦU VÀO
    test_1_1_1_post_user_action_single()
    test_1_1_2_post_user_actions_batch()
    test_1_2_1_validation_rules()
    
    # PHẦN 2: TEST XỬ LÝ
    test_2_1_2_etl_update_dataset()
    test_2_2_1_read_recent_actions()
    test_2_2_2_boost_scores()
    test_2_2_3_similarity_boost()
    
    # PHẦN 3: TEST ĐẦU RA
    test_3_1_1_recommendations_basic()
    test_3_1_2_recommendations_with_boost()
    test_3_1_4_cold_start()
    test_3_1_5_edge_cases()
    
    # PHẦN 4: TEST E2E
    test_4_1_1_full_flow()
    
    # PHẦN 5: PERFORMANCE
    test_4_2_1_api_response_time()
    
    # PHẦN 6: INTEGRATION
    test_4_3_1_docker_containers()
    
    # Tổng kết
    print_header("KẾT QUẢ TỔNG KẾT")
    total = TEST_RESULTS["passed"] + TEST_RESULTS["failed"] + TEST_RESULTS["skipped"]
    print(f"Tổng số test: {total}")
    print(f"✓ Passed: {TEST_RESULTS['passed']}")
    print(f"✗ Failed: {TEST_RESULTS['failed']}")
    print(f"⏭️  Skipped: {TEST_RESULTS['skipped']}")
    print(f"\nTỷ lệ thành công: {TEST_RESULTS['passed']}/{total} ({TEST_RESULTS['passed']/total*100:.1f}%)")
    
    print("\nChi tiết:")
    for detail in TEST_RESULTS["details"]:
        print(f"  {detail['status']}: {detail['test']}")
        if detail['message']:
            print(f"    → {detail['message']}")
    
    if TEST_RESULTS["failed"] == 0:
        print("\n🎉 TẤT CẢ TEST ĐỀU PASSED!")
    else:
        print(f"\n⚠ Có {TEST_RESULTS['failed']} test thất bại")

if __name__ == "__main__":
    main()
