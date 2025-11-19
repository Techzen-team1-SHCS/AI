"""
Test script de kiem tra API endpoints sau khi doi ID sang int
"""
import requests
import json
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:5000"

def test_health():
    """Test health check endpoint"""
    print("=" * 70)
    print("TEST 1: Health Check")
    print("=" * 70)
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response text: {response.text}")
        else:
            print(f"Response: {response.json()}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("ERROR: Khong the ket noi den API server. Kiem tra xem server da chay chua?")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_user_action_int():
    """Test POST /user_action với int IDs"""
    print("\n" + "=" * 70)
    print("TEST 2: POST /user_action với int IDs")
    print("=" * 70)
    try:
        payload = {
            "user_id": 123,  # int
            "item_id": 456,  # int
            "action_type": "click",
            "timestamp": 1695400000.0
        }
        response = requests.post(
            f"{BASE_URL}/user_action",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response text: {response.text}")
        else:
            print(f"Response: {response.json()}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("ERROR: Khong the ket noi den API server. Kiem tra xem server da chay chua?")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_user_action_string():
    """Test POST /user_action với string IDs"""
    print("\n" + "=" * 70)
    print("TEST 3: POST /user_action với string IDs")
    print("=" * 70)
    try:
        payload = {
            "user_id": "789",  # string
            "item_id": "101",  # string
            "action_type": "like",
            "timestamp": 1695401000.0
        }
        response = requests.post(
            f"{BASE_URL}/user_action",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response text: {response.text}")
        else:
            print(f"Response: {response.json()}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("ERROR: Khong the ket noi den API server. Kiem tra xem server da chay chua?")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_user_actions_batch():
    """Test POST /user_actions_batch với batch data"""
    print("\n" + "=" * 70)
    print("TEST 4: POST /user_actions_batch")
    print("=" * 70)
    try:
        payload = [
            {"user_id": 1, "item_id": 10, "action_type": "click", "timestamp": 1695400000.0},
            {"user_id": 2, "item_id": 20, "action_type": "like", "timestamp": 1695401000.0},
            {"user_id": 3, "item_id": 30, "action_type": "share", "timestamp": 1695402000.0},
        ]
        response = requests.post(
            f"{BASE_URL}/user_actions_batch",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response text: {response.text}")
        else:
            print(f"Response: {response.json()}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("ERROR: Khong the ket noi den API server. Kiem tra xem server da chay chua?")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_recommendations():
    """Test GET /recommendations/{user_id}"""
    print("\n" + "=" * 70)
    print("TEST 5: GET /recommendations/{user_id}")
    print("=" * 70)
    try:
        # Test với user_id có trong dataset (1-600)
        user_id = "1"
        response = requests.get(
            f"{BASE_URL}/recommendations/{user_id}?top_k=5",
            timeout=10
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Kiểm tra format recommendations
        if "recommendations" in data:
            recs = data["recommendations"]
            print(f"\nRecommendations count: {len(recs)}")
            if recs:
                print(f"First recommendation: {recs[0]} (type: {type(recs[0]).__name__})")
                # Recommendations nên là int hoặc string representation của int
                try:
                    int(recs[0])
                    print("✓ Recommendations là số (OK)")
                except (ValueError, TypeError):
                    print("⚠ Recommendations không phải số")
        
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_recommendations_cold_start():
    """Test GET /recommendations với user mới (cold start)"""
    print("\n" + "=" * 70)
    print("TEST 6: GET /recommendations với cold start user")
    print("=" * 70)
    try:
        user_id = "99999"  # User không có trong dataset
        response = requests.get(
            f"{BASE_URL}/recommendations/{user_id}?top_k=5",
            timeout=10
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Cold start nên trả về empty list
        if "recommendations" in data and len(data["recommendations"]) == 0:
            print("✓ Cold start xử lý đúng (empty list)")
        
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("ERROR: Khong the ket noi den API server. Kiem tra xem server da chay chua?")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 70)
    print("TEST API ENDPOINTS SAU KHI DOI ID SANG INT")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print()
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("POST /user_action (int)", test_user_action_int()))
    results.append(("POST /user_action (string)", test_user_action_string()))
    results.append(("POST /user_actions_batch", test_user_actions_batch()))
    results.append(("GET /recommendations", test_recommendations()))
    results.append(("GET /recommendations (cold start)", test_recommendations_cold_start()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ TẤT CẢ TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠ {total - passed} TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())

