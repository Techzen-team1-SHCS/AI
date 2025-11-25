# 🔧 SỬA LỖI KẾT NỐI WEB VỚI API

## ❌ LỖI HIỆN TẠI

Web đang gửi dữ liệu **SAI FORMAT**, dẫn đến validation error:

### Lỗi 1: Timestamp sai
```
"timestamp out of reasonable range (2000-01-01 to 2100-01-01), got 2025.0"
```

**Vấn đề:** Web đang gửi `2025.0` (năm 2025) thay vì **Unix timestamp** (seconds từ 1970-01-01).

**Unix timestamp cho năm 2025:**
- 2025-01-01 00:00:00 UTC = `1735689600`
- Hiện tại (2025-11-24) ≈ `1735000000` - `1735100000`

### Lỗi 2: action_type null
```
"Input should be a valid string", "input": null
```

**Vấn đề:** Web đang gửi `action_type: null` thay vì string như `"click"`, `"like"`, `"share"`, `"booking"`.

---

## ✅ CÁCH SỬA

### 1. Sửa Timestamp

**SAI:**
```javascript
{
  "user_id": 123,
  "item_id": 501,
  "action_type": "click",
  "timestamp": 2025.0  // ❌ SAI - đây là năm, không phải Unix timestamp
}
```

**ĐÚNG:**
```javascript
{
  "user_id": 123,
  "item_id": 501,
  "action_type": "click",
  "timestamp": Date.now() / 1000  // ✅ ĐÚNG - Unix timestamp (seconds)
}
// Hoặc
{
  "user_id": 123,
  "item_id": 501,
  "action_type": "click",
  "timestamp": Math.floor(Date.now() / 1000)  // ✅ ĐÚNG - Unix timestamp (seconds, integer)
}
```

**Ví dụ giá trị:**
- Hiện tại (2025-11-24): `1735000000` (khoảng)
- 2025-01-01: `1735689600`
- 2024-01-01: `1704067200`

### 2. Sửa action_type

**SAI:**
```javascript
{
  "action_type": null  // ❌ SAI
}
```

**ĐÚNG:**
```javascript
{
  "action_type": "click"  // ✅ ĐÚNG - phải là một trong: "click", "like", "share", "booking"
}
```

---

## 📝 CODE MẪU ĐÚNG

### JavaScript
```javascript
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
        action_type: actionType,  // Phải là "click", "like", "share", hoặc "booking"
        timestamp: Math.floor(Date.now() / 1000)  // Unix timestamp (seconds)
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      console.error('Error:', error);
      return false;
    }
    
    const data = await response.json();
    return data.status === 'success';
  } catch (error) {
    console.error('Error:', error);
    return false;
  }
}

// Sử dụng
logUserAction(123, 501, 'click');
```

### PHP
```php
<?php
function logUserAction($userId, $itemId, $actionType) {
    $url = "http://localhost:5000/user_action";
    $data = [
        'user_id' => $userId,
        'item_id' => $itemId,
        'action_type' => $actionType,  // Phải là "click", "like", "share", hoặc "booking"
        'timestamp' => time()  // Unix timestamp (seconds)
    ];
    
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode !== 200) {
        error_log("API Error: " . $response);
        return false;
    }
    
    $result = json_decode($response, true);
    return $result['status'] === 'success';
}

// Sử dụng
logUserAction(123, 501, 'click');
?>
```

### Batch Actions
```javascript
// Gửi nhiều actions cùng lúc
async function logUserActionsBatch(actions) {
  try {
    const response = await fetch('http://localhost:5000/user_actions_batch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(
        actions.map(action => ({
          user_id: action.userId,
          item_id: action.itemId,
          action_type: action.actionType,  // Phải là string, không phải null
          timestamp: Math.floor(Date.now() / 1000)  // Unix timestamp (seconds)
        }))
      )
    });
    
    const data = await response.json();
    return data.status === 'success';
  } catch (error) {
    console.error('Error:', error);
    return false;
  }
}

// Sử dụng
logUserActionsBatch([
  { userId: 123, itemId: 501, actionType: 'click' },
  { userId: 123, itemId: 502, actionType: 'like' }
]);
```

---

## 🧪 TEST

### Test bằng curl (PowerShell)
```powershell
# Test với timestamp đúng
$body = @{
    user_id = 123
    item_id = 501
    action_type = "click"
    timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:5000/user_action -Method POST -Body $body -ContentType "application/json"
```

### Test bằng JavaScript
```javascript
// Test trong browser console
fetch('http://localhost:5000/user_action', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 123,
    item_id: 501,
    action_type: 'click',
    timestamp: Math.floor(Date.now() / 1000)
  })
})
.then(res => res.json())
.then(data => console.log('Success:', data))
.catch(err => console.error('Error:', err));
```

---

## 📋 CHECKLIST CHO WEB TEAM

- [ ] Timestamp phải là Unix timestamp (seconds), không phải năm
- [ ] Timestamp phải là số (float hoặc int), ví dụ: `1735000000`
- [ ] action_type phải là string, không phải null
- [ ] action_type phải là một trong: `"click"`, `"like"`, `"share"`, `"booking"`
- [ ] user_id và item_id có thể là string hoặc int
- [ ] Content-Type header phải là `application/json`

---

## 🔍 DEBUG

Nếu vẫn lỗi, kiểm tra:

1. **Xem request thực tế:**
   - Mở DevTools → Network tab
   - Gửi request
   - Xem Request Payload

2. **Kiểm tra response:**
   - Xem Response tab để đọc error message chi tiết

3. **Test trực tiếp:**
   ```javascript
   console.log('Timestamp:', Math.floor(Date.now() / 1000));
   console.log('Action type:', 'click');  // Phải là string
   ```

---

## 📞 LIÊN HỆ

Nếu vẫn gặp vấn đề, gửi:
- Request payload (JSON)
- Response error message
- Code đang dùng

