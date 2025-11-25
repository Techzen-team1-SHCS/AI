# HƯỚNG DẪN KẾT NỐI WEB VỚI RECBOLE API

## 📡 THÔNG TIN API

### Base URL
```
http://localhost:5000          # Nếu web chạy trên cùng máy
http://<IP_MÁY>:5000          # Nếu web chạy trên máy khác
```

**Lưu ý:** Thay `<IP_MÁY>` bằng IP thực tế của máy chạy Docker (xem phần "Lấy IP máy" bên dưới).

### Endpoints

#### 1. Health Check
```http
GET http://localhost:5000/health
```

**Response:**
```json
{
  "ok": true,
  "model_loaded": true
}
```

#### 2. Lấy Recommendations
```http
GET http://localhost:5000/recommendations/{user_id}?top_k=10
```

**Parameters:**
- `user_id` (path): ID của user (string hoặc int)
- `top_k` (query, optional): Số lượng recommendations (default: 10, max: 100)

**Response:**
```json
{
  "user_id": "123",
  "recommendations": [501, 502, 503, 504, 505, 506, 507, 508, 509, 510],
  "model_version": "DeepFM-Nov-24-2025_08-39-20",
  "top_k": 10
}
```

**Ví dụ:**
```javascript
// JavaScript/Fetch
fetch('http://localhost:5000/recommendations/123?top_k=10')
  .then(response => response.json())
  .then(data => console.log(data.recommendations));
```

#### 3. Gửi User Action (Single)
```http
POST http://localhost:5000/user_action
Content-Type: application/json

{
  "user_id": 123,
  "item_id": 501,
  "action_type": "click",
  "timestamp": 1695400000.0
}
```

**Action Types:** `click`, `like`, `share`, `booking`

**Response:**
```json
{
  "status": "success",
  "data": {
    "user_id": "123",
    "item_id": "501",
    "action_type": "click",
    "timestamp": 1695400000.0
  }
}
```

#### 4. Gửi User Actions (Batch)
```http
POST http://localhost:5000/user_actions_batch
Content-Type: application/json

[
  {
    "user_id": 123,
    "item_id": 501,
    "action_type": "click",
    "timestamp": 1695400000.0
  },
  {
    "user_id": 123,
    "item_id": 502,
    "action_type": "like",
    "timestamp": 1695401000.0
  }
]
```

**Response:**
```json
{
  "status": "success",
  "count": 2
}
```

---

## 🔧 CẤU HÌNH

### 1. CORS (Cross-Origin Resource Sharing)

**Mặc định:** API cho phép tất cả origins (`*`)

**Nếu muốn giới hạn origins:**
1. Tạo file `.env` trong thư mục gốc:
```env
ALLOWED_ORIGINS=http://localhost:3000,http://192.168.1.100:8000
```

2. Restart Docker:
```bash
docker-compose restart recbole-api
```

### 2. API Key (Tùy chọn)

**Mặc định:** Không cần API key

**Nếu muốn bật authentication:**
1. Tạo file `.env`:
```env
API_KEY=your-secret-api-key-here
```

2. Restart Docker:
```bash
docker-compose restart recbole-api
```

3. Thêm header vào requests:
```javascript
fetch('http://localhost:5000/recommendations/123', {
  headers: {
    'Authorization': 'Bearer your-secret-api-key-here'
  }
})
```

---

## 🌐 LẤY IP MÁY

### Windows
```powershell
ipconfig | findstr IPv4
```

### Linux/Mac
```bash
hostname -I
# hoặc
ip addr show | grep "inet "
```

**Ví dụ:** Nếu IP là `192.168.1.100`, web sẽ gọi:
```
http://192.168.1.100:5000/recommendations/123
```

---

## 📝 VÍ DỤ CODE WEB

### JavaScript (Fetch API)
```javascript
// Lấy recommendations
async function getRecommendations(userId, topK = 10) {
  try {
    const response = await fetch(
      `http://localhost:5000/recommendations/${userId}?top_k=${topK}`
    );
    const data = await response.json();
    return data.recommendations;
  } catch (error) {
    console.error('Error:', error);
    return [];
  }
}

// Gửi user action
async function logUserAction(userId, itemId, actionType) {
  try {
    const response = await fetch('http://localhost:5000/user_action', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        item_id: itemId,
        action_type: actionType,
        timestamp: Date.now() / 1000  // Unix timestamp (seconds)
      })
    });
    const data = await response.json();
    return data.status === 'success';
  } catch (error) {
    console.error('Error:', error);
    return false;
  }
}

// Sử dụng
const recommendations = await getRecommendations(123, 10);
console.log('Recommendations:', recommendations);

await logUserAction(123, 501, 'click');
```

### PHP (cURL)
```php
<?php
// Lấy recommendations
function getRecommendations($userId, $topK = 10) {
    $url = "http://localhost:5000/recommendations/{$userId}?top_k={$topK}";
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    curl_close($ch);
    $data = json_decode($response, true);
    return $data['recommendations'] ?? [];
}

// Gửi user action
function logUserAction($userId, $itemId, $actionType) {
    $url = "http://localhost:5000/user_action";
    $data = [
        'user_id' => $userId,
        'item_id' => $itemId,
        'action_type' => $actionType,
        'timestamp' => time()
    ];
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    curl_close($ch);
    $result = json_decode($response, true);
    return $result['status'] === 'success';
}

// Sử dụng
$recommendations = getRecommendations(123, 10);
print_r($recommendations);

logUserAction(123, 501, 'click');
?>
```

### Python (requests)
```python
import requests
import time

# Lấy recommendations
def get_recommendations(user_id, top_k=10):
    url = f"http://localhost:5000/recommendations/{user_id}"
    params = {"top_k": top_k}
    response = requests.get(url, params=params)
    data = response.json()
    return data.get("recommendations", [])

# Gửi user action
def log_user_action(user_id, item_id, action_type):
    url = "http://localhost:5000/user_action"
    data = {
        "user_id": user_id,
        "item_id": item_id,
        "action_type": action_type,
        "timestamp": time.time()
    }
    response = requests.post(url, json=data)
    result = response.json()
    return result.get("status") == "success"

# Sử dụng
recommendations = get_recommendations(123, 10)
print("Recommendations:", recommendations)

log_user_action(123, 501, "click")
```

---

## ⚠️ LƯU Ý QUAN TRỌNG

1. **Port 5000:** Đảm bảo port 5000 không bị firewall chặn
2. **CORS:** Nếu web chạy trên domain khác, cần cấu hình `ALLOWED_ORIGINS` trong `.env`
3. **Timestamp:** Phải là Unix timestamp (seconds, không phải milliseconds)
4. **Cold Start:** User mới sẽ nhận `recommendations: []`, backend cần xử lý fallback
5. **Error Handling:** Luôn kiểm tra response status và xử lý lỗi

---

## 🧪 TEST KẾT NỐI

### Test bằng curl (Windows PowerShell)
```powershell
# Health check
Invoke-WebRequest -Uri http://localhost:5000/health

# Get recommendations
Invoke-WebRequest -Uri http://localhost:5000/recommendations/1?top_k=5

# Post user action
$body = @{
    user_id = 123
    item_id = 501
    action_type = "click"
    timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:5000/user_action -Method POST -Body $body -ContentType "application/json"
```

### Test bằng trình duyệt
Mở: `http://localhost:5000/health`

---

## 📞 HỖ TRỢ

Nếu gặp vấn đề:
1. Kiểm tra Docker containers đang chạy: `docker-compose ps`
2. Xem logs: `docker-compose logs recbole-api`
3. Kiểm tra port 5000: `netstat -an | findstr 5000`
4. Test API: `curl http://localhost:5000/health`

