import json
import urllib.request
import urllib.error
import sys
import codecs

# Fix encode on Windows terminal output
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def run_e2e_test():
    url = "http://localhost:8000/forecast"
    payload = {
        "hotel_id": "City Hotel Test",
        "hotel_capacity": 150,
        "horizon_days": 7,
        "historical_data": [
            {"ds": "2017-03-01", "rooms_booked": 45},
            {"ds": "2017-03-02", "rooms_booked": 52},
            {"ds": "2017-03-03", "rooms_booked": 65},
            {"ds": "2017-03-04", "rooms_booked": 85},
            {"ds": "2017-03-05", "rooms_booked": 90},
            {"ds": "2017-03-06", "rooms_booked": 45},
            {"ds": "2017-03-07", "rooms_booked": 50},
            {"ds": "2017-03-08", "rooms_booked": 65},
            {"ds": "2017-03-09", "rooms_booked": 85},
            {"ds": "2017-03-10", "rooms_booked": 90},
            {"ds": "2017-03-11", "rooms_booked": 45},
            {"ds": "2017-03-12", "rooms_booked": 50},
            {"ds": "2017-03-13", "rooms_booked": 65},
            {"ds": "2017-03-14", "rooms_booked": 85},
            {"ds": "2017-03-15", "rooms_booked": 90}
        ]
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        print(f"Bắt đầu gửi Request E2E đến: {url}")
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            print(f"HTTP Status: {status_code}")
            
            result = json.loads(response.read().decode("utf-8"))
            print("Response JSON:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            if status_code == 200 and "forecast" in result:
                print("\n[SUCCESS] E2E Test qua mạng thành công! API đã tuân thủ định dạng Phản hồi.")
    except urllib.error.HTTPError as e:
        print(f"[FAILED] Lỗi HTTP: {e.code} - {e.reason}")
        print(e.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"[FAILED] Không thể kết nối. Bạn đã bật Docker Container hoặc Uvicorn chưa?\nChi tiết lỗi: {e.reason}")

if __name__ == "__main__":
    run_e2e_test()
