import json
from ai_service.api import forecast, ForecastRequest

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

print("Running test...")
req = ForecastRequest(**payload)
try:
    resp = forecast(req)
    print("Test SUCCESS! Output:")
    print(json.dumps(resp.model_dump(), ensure_ascii=False, indent=2))
except Exception as e:
    print(f"Test FAILED: {e}")
