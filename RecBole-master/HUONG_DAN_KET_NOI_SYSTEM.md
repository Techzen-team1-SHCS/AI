# Hướng dẫn kết nối DeepFM với hệ thống đặt khách sạn

## Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────┐
│                  HỆ THỐNG ĐẶT KHÁCH SẠN                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Thu thập dữ liệu hành vi người dùng              │   │
│  │     (click, like, share, booking)                    │   │
│  └─────────────────┬────────────────────────────────────┘   │
│                    │ JSON export                            │
│                    ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  2. ETL Script (etl_web_to_hotel_inter.py)          │   │
│  │     - Convert hành động → điểm số                    │   │
│  │     - Append vào hotel.inter                         │   │
│  └─────────────────┬────────────────────────────────────┘   │
│                    │ hotel.inter                            │
│                    ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  3. Train DeepFM Model                               │   │
│  │     - Học pattern từ hành vi                        │   │
│  │     - Dự đoán khách sạn phù hợp                     │   │
│  └─────────────────┬────────────────────────────────────┘   │
│                    │ Saved Model (.pth)                     │
│                    ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  4. API/Service để recommend                        │   │
│  │     - Load model đã train                           │   │
│  │     - Trả về top K khách sạn cho user               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Bước 1: Thu thập dữ liệu từ hệ thống đặt khách sạn

### 1.1. Export dữ liệu hành vi người dùng

Từ hệ thống web đặt khách sạn, export dữ liệu hành vi theo format JSON:

```json
[
  {
    "user_id": "u1",
    "hotel_id": "h1",
    "action_type": "click",
    "timestamp": 1695400000
  },
  {
    "user_id": "u1",
    "hotel_id": "h1",
    "action_type": "booking",
    "timestamp": 1695403000
  }
]
```

**Các loại hành động:**

- `click`: 0.25 điểm
- `like`: 0.5 điểm
- `share`: 0.75 điểm
- `booking`: 1.0 điểm

### 1.2. Ví dụ query SQL để export (nếu dùng database)

```sql
-- Lấy hành vi người dùng từ bảng hành động
SELECT
    user_id,
    hotel_id,
    action_type,  -- 'click', 'like', 'share', 'booking'
    UNIX_TIMESTAMP(created_at) as timestamp
FROM user_actions
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY user_id, hotel_id, created_at
INTO props_ARRAY_FORMAT '/tmp/web_actions.json';
```

## Bước 2: Chạy ETL để xử lý dữ liệu

### 2.1. Chạy script ETL

```bash
python etl_web_to_hotel_inter.py
```

Script này sẽ:

1. Đọc dữ liệu từ `sample_web_actions.json` (hoặc file dữ liệu thực tế)
2. Chuyển đổi hành động thành điểm số
3. Group by (user_id, hotel_id) và lấy điểm cao nhất
4. Append vào `dataset/hotel/hotel.inter`

### 2.2. Tùy chỉnh để import dữ liệu thực tế

Sửa file `etl_web_to_hotel_inter.py`:

```python
if __name__ == "__main__":
    # Thay vì tạo sample data, đọc từ file thực tế
    web_file = 'path/to/your/web_actions.json'  # <- Sửa đường dẫn này

    # Chạy ETL (append vào cuối file gốc)
    process_web_actions_to_hotel_inter(
        web_file,
        'dataset/hotel/hotel.inter'
    )
```

## Bước 3: Train model DeepFM

### 3.1. Train với dữ liệu mới

```bash
python run_recbole.py \
    --model=DeepFM \
    --dataset=hotel \
    --config_file_list=deepfm_config.yaml \
    --epochs=300
```

### 3.2. Lưu kết quả training

```bash
python run_recbole.py \
    --model=DeepFM \
    --dataset=hotel \
    --config_file_list=deepfm_config.yaml \
    --epochs=300 \
    --save_results \
    --output_file=deepfm_results.txt
```

Model được lưu tại: `saved/DeepFM-YYYY-MM-DD_HH-MM-SS.pth`

## Bước 4: Tạo API để recommend (Integration)

Tạo file `hotel_recommendation_api.py`:

ron job):

Tạo file `daily_retrain.sh`:

```bash
#!/bin/bash
# Daily retrain script

echo "[$(date)] Starting d```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hotel Recommendation API
Load trained DeepFM model and provide recommendations
"""

import os
import glob
from flask import Flask, jsonify, request
from recbole.quick_start import load_data_and_model
from recbole.utils.case_study import full_sort_topk
import numpy as np

app = Flask(__name__)

# Global variables
model = None
config = None
dataset = None
model_loaded = False

def load_latest_model():
    """Load the most recent trained model"""
    global model, config, dataset, model_loaded

    try:
        # Tìm file model mới nhất
        model_files = glob.glob("saved/DeepFM-*.pth")
        if not model_files:
            print("ERROR: Không tìm thấy model nào trong thư mục saved/")
            return False

        latest_model = max(model_files, key=os.path.getctime)
        print(f"Loading model from: {latest_model}")

        # Load model
        config, model, dataset, _, _, _ = load_data_and_model(model_file=latest_model)

        model_loaded = True
        print("Model loaded successfully!")
        return True

    except Exception as e:
        print(f"ERROR loading model: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model_loaded
    })

@app.route('/recommend', methods=['POST'])
def recommend():
    """
    Recommend hotels for users

    Request body:
    {
        "user_ids": ["u1", "u2", "u3"],
        "top_k": 10
    }
    """
    if not model_loaded:
        return jsonify({
            'error': 'Model not loaded',
            'message': 'Please train and load the model first'
        }), 500

    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        top_k = data.get('top_k', 10)

        # Convert external user tokens to internal IDs
        uid_series = dataset.token2id(dataset.uid_field, user_ids)

        # Get top K recommendations
        topk_score, topk_iid_list = full_sort_topk(
            uid_series,
            model,
            None,  # test_data không cần khi predict
            k=top_k,
            device=config["device"]
        )

        # Convert internal item IDs back to external tokens
        external_item_list = dataset.id2token(
            dataset.iid_field,
            topk_iid_list.cpu()
        )

        # Format results
        results = []
        for i, user_id in enumerate(user_ids):
            recommendations = []
            for j in range(top_k):
                recommendations.append({
                    'hotel_id': external_item_list[i][j].item(),
                    'score': float(topk_score[i][j].item())
                })

            results.append({
                'user_id': user_id,
                'recommendations': recommendations
            })

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        return jsonify({
            'error': 'Recommendation failed',
            'message': str(e)
        }), 500

@app.route('/predict_single', methods=['POST'])
def predict_single():
    """
    Predict score for a specific user-hotel pair

    Request body:
    {
        "user_id": "u1",
        "hotel_id": "h1"
    }
    """
    if not model_loaded:
        return jsonify({
            'error': 'Model not loaded'
        }), 500

    try:
        data = request.get_json()
        user_id = data.get('user_id')
        hotel_id = data.get('hotel_id')

        # Convert to internal IDs
        uid = dataset.token2id(dataset.uid_field, [user_id])
        iid = dataset.token2id(dataset.iid_field, [hotel_id])

        # Create interaction
        from torch import tensor
        interaction = {
            dataset.uid_field: tensor(uid),
            dataset.iid_field: tensor(iid)
        }

        # Predict
        model.eval()
        score = model.predict(interaction)

        return jsonify({
            'success': True,
            'user_id': user_id,
            'hotel_id': hotel_id,
            'score': float(score[0].item())
        })

    except Exception as e:
        return jsonify({
            'error': 'Prediction failed',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Loading DeepFM Model for Hotel Recommendation...")
    print("=" * 60)

    if load_latest_model():
        print("\nStarting Flask API server...")
        print("API endpoints:")
        print("  - GET  /health : Check if model is loaded")
        print("  - POST /recommend : Get top K recommendations")
        print("  - POST /predict_single : Predict user-hotel score")
        print("\n")

        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        print("\nERROR: Failed to load model. Please train a model first.")
```

## Bước 5: Sử dụng API trong hệ thống đặt khách sạn

### 5.1. Start API server

```bash
python hotel_recommendation_api.py
```

### 5.2. Gọi API từ backend web

**Python example:**

```python
import requests

# Get recommendations for a user
response = requests.post('http://localhost:5000/recommend', json={
    'user_ids': ['u1', 'u2'],
    'top_k': 10
})

result = response.json()
for user_rec in result['results']:
    print(f"User {user_rec['user_id']}:")
    for rec in user_rec['recommendations']:
        print(f"  - Hotel {rec['hotel_id']}: score {rec['score']:.4f}")
```

**JavaScript/Node.js example:**

```javascript
const axios = require("axios");

// Get recommendations
async function getRecommendations(userIds, topK = 10) {
  const response = await axios.post("http://localhost:5000/recommend", {
    user_ids: userIds,
    top_k: topK,
  });

  return response.data;
}

// Use in Express.js route
app.get("/api/hotels/recommend/:userId", async (req, res) => {
  const userId = req.params.userId;
  const result = await getRecommendations([userId], 10);

  // Extract hotel IDs
  const recommendations = result.results[0].recommendations;
  const hotelIds = recommendations.map((r) => r.hotel_id);

  // Query your database for hotel details
  const hotels = await db.query("SELECT * FROM hotels WHERE hotel_id IN (?)", [
    hotelIds,
  ]);

  res.json(hotels);
});
```

## Luồng hoạt động hàng ngày (Production)

### Quy trình theo chu kỳ:

```
Hàng ngày:
1. Export hành vi người dùng từ database → JSON
2. Chạy ETL: python etl_web_to_hotel_inter.py
3. Re-train model (hoặc incremental training)
4. Reload model trong API (hot reload)

Hàng tuần:
- Đánh giá model performance
- Tune hyperparameters nếu cần
```

### Script tự động hóa (Caily retrain..."

# 1. Export dữ liệu từ database
echo "[1/4] Exporting data from database..."
mysql -u user -ppassword hotel_db < export_query.sql > web_actions.json

# 2. Run ETL
echo "[2/4] Running ETL..."
python etl_web_to_hotel_inter.py

# 3. Train model
echo "[3/4] Training model..."
python run_recbole.py \
    --model=DeepFM \
    --dataset=hotel \
    --config_file_list=deepfm_config.yaml \
    --epochs=50 \
    --save_results

# 4. Reload API (nếu sử dụng gunicorn)
echo "[4/4] Reloading API..."
pkill -HUP -f hotel_recommendation_api.py

echo "[$(date)] Completed!"
```

Thêm vào crontab:

```bash
# Train model mỗi ngày lúc 2 giờ sáng
0 2 * * * /path/to/daily_retrain.sh >> /var/log/retrain.log 2>&1
```

## Ví dụ sử dụng thực tế

### Scenario 1: User truy cập trang chủ

```javascript
// Frontend request
fetch("http://localhost:5000/recommend", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    user_ids: [currentUserId],
    top_k: 20,
  }),
})
  .then((res) => res.json())
  .then((data) => {
    // Hiển thị 20 khách sạn recommend cho user
    displayHotels(data.results[0].recommendations);
  });
```

### Scenario 2: Thêm item vào "Favorites"

```python
# Backend: Khi user click "Like"
@app.route('/hotel/<hotel_id>/like', methods=['POST'])
def like_hotel(hotel_id):
    user_id = get_current_user()

    # Lưu vào database
    db.execute(
        "INSERT INTO user_actions (user_id, hotel_id, action_type) VALUES (?, ?, 'like')",
        (user_id, hotel_id)
    )

    # Trigger immediate re-recommendation
    response = requests.post('http://localhost:5000/recommend', json={
        'user_ids': [user_id],
        'top_k': 10
    })

    return jsonify(response.json())
```

### Scenario 3: A/B Testing

```python
def get_recommendations(user_id, use_ml=False):
    if use_ml:
        # Sử dụng DeepFM
        response = requests.post('http://localhost:5000/recommend', json={
            'user_ids': [user_id],
            'top_k': 10
        })
        return response.json()['results'][0]['recommendations']
    else:
        # Sử dụng rule-based (popular hotels)
        return get_popular_hotels(limit=10)
```

## Cấu hình hiệu năng

### Tối ưu hóa API

Sửa `hotel_recommendation_api.py`:

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'redis'})

@app.route('/recommend', methods=['POST'])
@cache.cached(timeout=300)  # Cache 5 phút
def recommend():
    # ... existing code
```

### Load balancing với Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 hotel_recommendation_api:app
```

### Monitor performance

```python
import time
from functools import wraps

def monitor_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} took {duration:.3f}s")
        return result
    return wrapper

@app.route('/recommend', methods=['POST'])
@monitor_time
def recommend():
    # ... existing code
```

## Troubleshooting

### Lỗi 1: Model không load được

**Triệu chứng:**

```
ERROR: Không tìm thấy model nào trong thư mục saved/
```

**Giải pháp:**

```bash
# Kiểm tra xem có file model không
ls -la saved/

# Train model trước
python run_recbole.py --model=DeepFM --dataset=hotel
```

### Lỗi 2: User ID không tồn tại

**Triệu chứng:**

```
ERROR: User 'u999' not found in dataset
```

**Giải pháp:**

```python
# Thêm user mới vào dataset
# Option 1: Cold start - recommend popular items
if user_id not in dataset:
    return get_popular_hotels()

# Option 2: Retrain với dữ liệu mới
```

### Lỗi 3: Hotel ID không tồn tại

**Giải pháp:**

```python
# Validate hotel_id trước khi predict
if hotel_id not in dataset.field2id_token[dataset.iid_field]:
    return jsonify({'error': 'Hotel not found'}), 404
```

## Metrics và Monitoring

### Thêm logging

```python
import logging

logging.basicConfig(
    filename='api.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json()
    logging.info(f"Request received: user_ids={data.get('user_ids')}")

    # ... existing code

    logging.info(f"Recommendations generated successfully")
    return jsonify(...)
```

### Track API usage

```python
from collections import defaultdict

request_count = defaultdict(int)

@app.before_request
def track_request():
    request_count['total'] += 1
    request_count[str(request.path)] += 1

@app.route('/stats', methods=['GET'])
def get_stats():
    return jsonify(dict(request_count))
```

## Tổng kết

**Quy trình hoàn chỉnh:**

1. ✅ Thu thập dữ liệu hành vi từ hệ thống booking
2. ✅ Chạy ETL để xử lý và format dữ liệu
3. ✅ Train model DeepFM với dữ liệu mới
4. ✅ Deploy API để serve recommendations
5. ✅ Tích hợp API vào hệ thống đặt khách sạn
6. ✅ Monitor và cải thiện liên tục

**Files quan trọng:**

- `etl_web_to_hotel_inter.py` - Xử lý dữ liệu
- `deepfm_config.yaml` - Cấu hình model
- `run_recbole.py` - Train model
- `hotel_recommendation_api.py` - API service
- `dataset/hotel/hotel.inter` - Dữ liệu interactions
- `saved/DeepFM-*.pth` - Model đã train

**Liên hệ hỗ trợ:**

- Xem logs tại `log/`
- Check model performance tại `result.txt`
- API logs tại `api.log`
