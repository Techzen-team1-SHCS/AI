import json
import urllib.request
import urllib.error
import sys
import codecs

# Fix encode on Windows terminal output
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# ---------------------------------------------------------------------------
# Dữ liệu lịch sử 180 ngày (đủ để Prophet hoạt động chính xác)
# Mô phỏng số phòng đặt thực tế của City Hotel từ 01/01/2017 → 29/06/2017
# Chu kỳ cuối tuần cao hơn ngày thường, có biến động tự nhiên
# ---------------------------------------------------------------------------
HISTORICAL_DATA = [
    {"ds": "2017-01-01", "rooms_booked": 45}, {"ds": "2017-01-02", "rooms_booked": 50},
    {"ds": "2017-01-03", "rooms_booked": 55}, {"ds": "2017-01-04", "rooms_booked": 48},
    {"ds": "2017-01-05", "rooms_booked": 60}, {"ds": "2017-01-06", "rooms_booked": 75},
    {"ds": "2017-01-07", "rooms_booked": 80}, {"ds": "2017-01-08", "rooms_booked": 52},
    {"ds": "2017-01-09", "rooms_booked": 56}, {"ds": "2017-01-10", "rooms_booked": 61},
    {"ds": "2017-01-11", "rooms_booked": 49}, {"ds": "2017-01-12", "rooms_booked": 58},
    {"ds": "2017-01-13", "rooms_booked": 72}, {"ds": "2017-01-14", "rooms_booked": 79},
    {"ds": "2017-01-15", "rooms_booked": 54}, {"ds": "2017-01-16", "rooms_booked": 57},
    {"ds": "2017-01-17", "rooms_booked": 62}, {"ds": "2017-01-18", "rooms_booked": 50},
    {"ds": "2017-01-19", "rooms_booked": 63}, {"ds": "2017-01-20", "rooms_booked": 78},
    {"ds": "2017-01-21", "rooms_booked": 85}, {"ds": "2017-01-22", "rooms_booked": 55},
    {"ds": "2017-01-23", "rooms_booked": 60}, {"ds": "2017-01-24", "rooms_booked": 65},
    {"ds": "2017-01-25", "rooms_booked": 52}, {"ds": "2017-01-26", "rooms_booked": 67},
    {"ds": "2017-01-27", "rooms_booked": 80}, {"ds": "2017-01-28", "rooms_booked": 88},
    {"ds": "2017-01-29", "rooms_booked": 58}, {"ds": "2017-01-30", "rooms_booked": 62},
    {"ds": "2017-01-31", "rooms_booked": 68},
    {"ds": "2017-02-01", "rooms_booked": 53}, {"ds": "2017-02-02", "rooms_booked": 70},
    {"ds": "2017-02-03", "rooms_booked": 82}, {"ds": "2017-02-04", "rooms_booked": 90},
    {"ds": "2017-02-05", "rooms_booked": 60}, {"ds": "2017-02-06", "rooms_booked": 63},
    {"ds": "2017-02-07", "rooms_booked": 69}, {"ds": "2017-02-08", "rooms_booked": 55},
    {"ds": "2017-02-09", "rooms_booked": 72}, {"ds": "2017-02-10", "rooms_booked": 85},
    {"ds": "2017-02-11", "rooms_booked": 92}, {"ds": "2017-02-12", "rooms_booked": 61},
    {"ds": "2017-02-13", "rooms_booked": 65}, {"ds": "2017-02-14", "rooms_booked": 95},
    {"ds": "2017-02-15", "rooms_booked": 58}, {"ds": "2017-02-16", "rooms_booked": 74},
    {"ds": "2017-02-17", "rooms_booked": 88}, {"ds": "2017-02-18", "rooms_booked": 96},
    {"ds": "2017-02-19", "rooms_booked": 62}, {"ds": "2017-02-20", "rooms_booked": 67},
    {"ds": "2017-02-21", "rooms_booked": 73}, {"ds": "2017-02-22", "rooms_booked": 59},
    {"ds": "2017-02-23", "rooms_booked": 76}, {"ds": "2017-02-24", "rooms_booked": 89},
    {"ds": "2017-02-25", "rooms_booked": 97}, {"ds": "2017-02-26", "rooms_booked": 64},
    {"ds": "2017-02-27", "rooms_booked": 68}, {"ds": "2017-02-28", "rooms_booked": 74},
    {"ds": "2017-03-01", "rooms_booked": 61}, {"ds": "2017-03-02", "rooms_booked": 78},
    {"ds": "2017-03-03", "rooms_booked": 91}, {"ds": "2017-03-04", "rooms_booked": 100},
    {"ds": "2017-03-05", "rooms_booked": 66}, {"ds": "2017-03-06", "rooms_booked": 70},
    {"ds": "2017-03-07", "rooms_booked": 76}, {"ds": "2017-03-08", "rooms_booked": 63},
    {"ds": "2017-03-09", "rooms_booked": 79}, {"ds": "2017-03-10", "rooms_booked": 93},
    {"ds": "2017-03-11", "rooms_booked": 102}, {"ds": "2017-03-12", "rooms_booked": 68},
    {"ds": "2017-03-13", "rooms_booked": 72}, {"ds": "2017-03-14", "rooms_booked": 78},
    {"ds": "2017-03-15", "rooms_booked": 65}, {"ds": "2017-03-16", "rooms_booked": 81},
    {"ds": "2017-03-17", "rooms_booked": 95}, {"ds": "2017-03-18", "rooms_booked": 104},
    {"ds": "2017-03-19", "rooms_booked": 70}, {"ds": "2017-03-20", "rooms_booked": 74},
    {"ds": "2017-03-21", "rooms_booked": 80}, {"ds": "2017-03-22", "rooms_booked": 67},
    {"ds": "2017-03-23", "rooms_booked": 83}, {"ds": "2017-03-24", "rooms_booked": 97},
    {"ds": "2017-03-25", "rooms_booked": 106}, {"ds": "2017-03-26", "rooms_booked": 72},
    {"ds": "2017-03-27", "rooms_booked": 76}, {"ds": "2017-03-28", "rooms_booked": 82},
    {"ds": "2017-03-29", "rooms_booked": 69}, {"ds": "2017-03-30", "rooms_booked": 85},
    {"ds": "2017-03-31", "rooms_booked": 99},
    {"ds": "2017-04-01", "rooms_booked": 108}, {"ds": "2017-04-02", "rooms_booked": 74},
    {"ds": "2017-04-03", "rooms_booked": 78}, {"ds": "2017-04-04", "rooms_booked": 84},
    {"ds": "2017-04-05", "rooms_booked": 71}, {"ds": "2017-04-06", "rooms_booked": 87},
    {"ds": "2017-04-07", "rooms_booked": 101}, {"ds": "2017-04-08", "rooms_booked": 110},
    {"ds": "2017-04-09", "rooms_booked": 76}, {"ds": "2017-04-10", "rooms_booked": 80},
    {"ds": "2017-04-11", "rooms_booked": 86}, {"ds": "2017-04-12", "rooms_booked": 73},
    {"ds": "2017-04-13", "rooms_booked": 89}, {"ds": "2017-04-14", "rooms_booked": 103},
    {"ds": "2017-04-15", "rooms_booked": 112}, {"ds": "2017-04-16", "rooms_booked": 78},
    {"ds": "2017-04-17", "rooms_booked": 82}, {"ds": "2017-04-18", "rooms_booked": 88},
    {"ds": "2017-04-19", "rooms_booked": 75}, {"ds": "2017-04-20", "rooms_booked": 91},
    {"ds": "2017-04-21", "rooms_booked": 105}, {"ds": "2017-04-22", "rooms_booked": 114},
    {"ds": "2017-04-23", "rooms_booked": 80}, {"ds": "2017-04-24", "rooms_booked": 84},
    {"ds": "2017-04-25", "rooms_booked": 90}, {"ds": "2017-04-26", "rooms_booked": 77},
    {"ds": "2017-04-27", "rooms_booked": 93}, {"ds": "2017-04-28", "rooms_booked": 107},
    {"ds": "2017-04-29", "rooms_booked": 116}, {"ds": "2017-04-30", "rooms_booked": 120},
    {"ds": "2017-05-01", "rooms_booked": 82}, {"ds": "2017-05-02", "rooms_booked": 86},
    {"ds": "2017-05-03", "rooms_booked": 92}, {"ds": "2017-05-04", "rooms_booked": 79},
    {"ds": "2017-05-05", "rooms_booked": 95}, {"ds": "2017-05-06", "rooms_booked": 109},
    {"ds": "2017-05-07", "rooms_booked": 118}, {"ds": "2017-05-08", "rooms_booked": 84},
    {"ds": "2017-05-09", "rooms_booked": 88}, {"ds": "2017-05-10", "rooms_booked": 94},
    {"ds": "2017-05-11", "rooms_booked": 81}, {"ds": "2017-05-12", "rooms_booked": 97},
    {"ds": "2017-05-13", "rooms_booked": 111}, {"ds": "2017-05-14", "rooms_booked": 120},
    {"ds": "2017-05-15", "rooms_booked": 86}, {"ds": "2017-05-16", "rooms_booked": 90},
    {"ds": "2017-05-17", "rooms_booked": 96}, {"ds": "2017-05-18", "rooms_booked": 83},
    {"ds": "2017-05-19", "rooms_booked": 99}, {"ds": "2017-05-20", "rooms_booked": 113},
    {"ds": "2017-05-21", "rooms_booked": 122}, {"ds": "2017-05-22", "rooms_booked": 88},
    {"ds": "2017-05-23", "rooms_booked": 92}, {"ds": "2017-05-24", "rooms_booked": 98},
    {"ds": "2017-05-25", "rooms_booked": 85}, {"ds": "2017-05-26", "rooms_booked": 101},
    {"ds": "2017-05-27", "rooms_booked": 115}, {"ds": "2017-05-28", "rooms_booked": 124},
    {"ds": "2017-05-29", "rooms_booked": 90}, {"ds": "2017-05-30", "rooms_booked": 94},
    {"ds": "2017-05-31", "rooms_booked": 100},
    {"ds": "2017-06-01", "rooms_booked": 87}, {"ds": "2017-06-02", "rooms_booked": 103},
    {"ds": "2017-06-03", "rooms_booked": 117}, {"ds": "2017-06-04", "rooms_booked": 126},
    {"ds": "2017-06-05", "rooms_booked": 92}, {"ds": "2017-06-06", "rooms_booked": 96},
    {"ds": "2017-06-07", "rooms_booked": 102}, {"ds": "2017-06-08", "rooms_booked": 89},
    {"ds": "2017-06-09", "rooms_booked": 105}, {"ds": "2017-06-10", "rooms_booked": 119},
    {"ds": "2017-06-11", "rooms_booked": 128}, {"ds": "2017-06-12", "rooms_booked": 94},
    {"ds": "2017-06-13", "rooms_booked": 98}, {"ds": "2017-06-14", "rooms_booked": 104},
    {"ds": "2017-06-15", "rooms_booked": 91}, {"ds": "2017-06-16", "rooms_booked": 107},
    {"ds": "2017-06-17", "rooms_booked": 121}, {"ds": "2017-06-18", "rooms_booked": 130},
    {"ds": "2017-06-19", "rooms_booked": 96}, {"ds": "2017-06-20", "rooms_booked": 100},
    {"ds": "2017-06-21", "rooms_booked": 106}, {"ds": "2017-06-22", "rooms_booked": 93},
    {"ds": "2017-06-23", "rooms_booked": 109}, {"ds": "2017-06-24", "rooms_booked": 123},
    {"ds": "2017-06-25", "rooms_booked": 132}, {"ds": "2017-06-26", "rooms_booked": 98},
    {"ds": "2017-06-27", "rooms_booked": 102}, {"ds": "2017-06-28", "rooms_booked": 108},
    {"ds": "2017-06-29", "rooms_booked": 95},
]


def run_e2e_test():
    url = "http://localhost:5000/forecast"
    payload = {
        "hotel_id": "City Hotel Test",
        "hotel_capacity": 150,
        # horizon_days không truyền → AI tự dùng mặc định 30 ngày
        "historical_data": HISTORICAL_DATA,
    }

    print(f"Số ngày lịch sử gửi lên: {len(HISTORICAL_DATA)} ngày")
    print(f"Khoảng thời gian: {HISTORICAL_DATA[0]['ds']} → {HISTORICAL_DATA[-1]['ds']}")
    print(f"Bắt đầu gửi Request E2E đến: {url}\n")

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            print(f"HTTP Status: {status_code}")

            result = json.loads(response.read().decode("utf-8"))

            # In gọn: forecast 3 ngày đầu + insights
            print(f"\nDự báo (3 ngày đầu / tổng {len(result.get('forecast', []))} ngày):")
            for item in result.get("forecast", [])[:3]:
                print(f"  {item}")

            print(f"\nConfidence  : {result.get('confidence')}")
            print(f"Deviation   : {result.get('deviation')}")
            print(f"Action      : {result.get('suggested_action')}")
            print(f"Explanation : {result.get('explanation')[:100]}...")

            print("\nAdvanced Insights:")
            ai = result.get("advanced_insights", {})
            print(f"  Pricing  : {ai.get('dynamic_pricing')}")
            print(f"  Staffing : {ai.get('staffing')}")
            print(f"  Holidays : {ai.get('holiday_warnings')}")

            if status_code == 200 and "forecast" in result:
                print("\n[SUCCESS] E2E Test thành công! API tuân thủ định dạng Response.")
    except urllib.error.HTTPError as e:
        print(f"[FAILED] Lỗi HTTP: {e.code} - {e.reason}")
        print(e.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"[FAILED] Không thể kết nối.\nBạn đã bật Docker Container hoặc Uvicorn chưa?\nChi tiết: {e.reason}")


if __name__ == "__main__":
    run_e2e_test()
