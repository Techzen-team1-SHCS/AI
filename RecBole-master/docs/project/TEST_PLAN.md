# Kế Hoạch Test Tổng Thể - Hệ Thống Recommendation AI

## Tổng Quan

Kế hoạch test này bao gồm toàn bộ các test từ đầu vào đến đầu ra, đảm bảo tất cả chức năng của hệ thống hoạt động đúng. Test được thực hiện theo luồng từ đầu đến cuối.

---

## 1. TEST ĐẦU VÀO (Input Testing)

### 1.1. Test API Endpoints - Nhận User Actions

#### Test 1.1.1: POST /user_action - Single Action
**Mục đích**: Kiểm tra API nhận được user action đơn lẻ từ web

**Input**:
```json
{
  "user_id": 123,
  "item_id": 456,
  "action_type": "click",
  "timestamp": 1234567890
}
```

**Expected Output**:
- Status: 200 OK
- Response: `{"status": "success", "data": {...}}`
- File `data/user_actions.log` được cập nhật với 1 dòng JSON

**Các trường hợp test**:
- [x] ✓ Valid action (click)
- [ ] ✓ Valid action (like)
- [ ] ✓ Valid action (share)
- [ ] ✓ Valid action (booking)
- [ ] ✗ Invalid action_type
- [ ] ✗ Missing required fields
- [ ] ✗ Invalid user_id format
- [ ] ✗ Invalid item_id format

#### Test 1.1.2: POST /user_actions_batch - Batch Actions
**Mục đích**: Kiểm tra API nhận được nhiều actions cùng lúc

**Input**:
```json
{
  "actions": [
    {"user_id": 123, "item_id": 456, "action_type": "click", "timestamp": 1234567890},
    {"user_id": 123, "item_id": 789, "action_type": "like", "timestamp": 1234567891}
  ]
}
```

**Expected Output**:
- Status: 200 OK
- File log được cập nhật với 2 dòng

**Các trường hợp test**:
- [ ] ✓ Valid batch (2 actions)
- [ ] ✓ Valid batch (10 actions)
- [ ] ✗ Empty batch
- [ ] ✗ Mixed valid/invalid actions

---

### 1.2. Test Data Validation

#### Test 1.2.1: Validation Rules
**Kiểm tra**:
- [ ] user_id phải là số nguyên dương hoặc string số
- [ ] item_id phải là số nguyên dương hoặc string số
- [ ] action_type phải trong ["click", "like", "share", "booking"]
- [ ] timestamp phải là số nguyên dương (Unix timestamp)

#### Test 1.2.2: File Log Format
**Kiểm tra**:
- [ ] Mỗi dòng là valid JSON
- [ ] Encoding UTF-8
- [ ] Line ending đúng format
- [ ] Không có duplicate entries

---

## 2. TEST XỬ LÝ (Processing Testing)

### 2.1. Test ETL Process

#### Test 2.1.1: ETL Đọc Log File
**Mục đích**: Kiểm tra ETL có đọc được file `data/user_actions.log`

**Steps**:
1. Gửi user actions qua API (Test 1.1.1)
2. Đợi ETL chạy (mỗi 3 phút hoặc trigger thủ công)
3. Kiểm tra log file được đọc

**Expected**:
- [ ] ETL đọc được log file
- [ ] Parse được JSON từng dòng
- [ ] Xử lý được các action types
- [ ] Lưu processed data vào archive log

#### Test 2.1.2: ETL Cập Nhật Dataset
**Mục đích**: Kiểm tra ETL cập nhật `dataset/hotel/hotel.inter`

**Steps**:
1. Ghi 5 user actions vào log
2. Đợi ETL chạy
3. Kiểm tra `hotel.inter` được cập nhật

**Expected**:
- [ ] File `hotel.inter` được cập nhật
- [ ] Format TSV đúng (tab-separated)
- [ ] Không có duplicate entries
- [ ] Dữ liệu đúng format: `user_id\titem_id\taction_type\ttimestamp\t...`

**Validation**:
```python
# Kiểm tra số dòng tăng
before_count = count_lines("dataset/hotel/hotel.inter")
# ... ETL chạy ...
after_count = count_lines("dataset/hotel/hotel.inter")
assert after_count > before_count
```

#### Test 2.1.3: ETL Archive Log
**Mục đích**: Kiểm tra processed actions được archive

**Expected**:
- [ ] Processed actions được move sang `user_actions.archive.log`
- [ ] Log file gốc được clear
- [ ] Archive log format đúng

#### Test 2.1.4: ETL Error Handling
**Kiểm tra**:
- [ ] Invalid JSON trong log → skip và log error
- [ ] File locked → retry sau
- [ ] Disk full → log error, không crash

---

### 2.2. Test Behavior Boost Processing

#### Test 2.2.1: Đọc Recent Actions
**Mục đích**: Kiểm tra system đọc được recent actions từ log

**Steps**:
1. Gửi user action với timestamp hiện tại
2. Gọi API recommendations với `use_behavior_boost=true`
3. Kiểm tra log có được đọc

**Expected**:
- [ ] System đọc được actions trong time window (24h default)
- [ ] Filter đúng theo user_id
- [ ] Tính toán time weight đúng

#### Test 2.2.2: Tính Toán Boost Scores
**Mục đích**: Kiểm tra công thức boost đúng

**Test Cases**:
- [ ] Action mới (< 1h) → weight cao
- [ ] Action cũ (> 12h) → weight thấp
- [ ] Multiple actions cùng item → boost cộng dồn
- [ ] Different action types → scores khác nhau (booking > share > like > click)

**Expected Formula**:
```
action_score = get_action_score(action_type)
time_weight = exp(-decay_rate * hours_ago)
boost = action_score * time_weight
final_score = base_score * (1 + alpha * boost)
```

#### Test 2.2.3: Similarity Boost
**Mục đích**: Kiểm tra similarity boost hoạt động (Phase 2)

**Steps**:
1. User click vào item có style="luxury", price="high"
2. Gọi recommendations với `use_similarity_boost=true`
3. Kiểm tra items tương tự được boost

**Expected**:
- [ ] Items có style tương tự được boost
- [ ] Items có price range tương tự được boost
- [ ] Similarity threshold hoạt động đúng
- [ ] Boost factor được áp dụng đúng

**Test Cases**:
- [ ] Similarity >= threshold → boost
- [ ] Similarity < threshold → không boost
- [ ] Multiple similar items → boost tổng hợp

---

### 2.3. Test Model Inference

#### Test 2.3.1: Load Model
**Kiểm tra**:
- [ ] Model load thành công từ `saved/*.pth`
- [ ] Dataset load thành công
- [ ] Cache model hoạt động (không reload mỗi request)

#### Test 2.3.2: Generate Base Scores
**Mục đích**: Kiểm tra model tạo được base scores

**Expected**:
- [ ] Model predict được scores cho tất cả items
- [ ] Scores trong khoảng hợp lý
- [ ] User có history → scores khác user không có history

---

## 3. TEST ĐẦU RA (Output Testing)

### 3.1. Test API Recommendations

#### Test 3.1.1: GET /recommendations/{user_id} - Basic
**Mục đích**: Test recommendations cơ bản (không behavior boost)

**Input**: `GET /recommendations/1?top_k=10&use_behavior_boost=false`

**Expected Output**:
```json
{
  "user_id": "1",
  "recommendations": [473, 582, 92, ...],
  "model_version": "..."
}
```

**Validation**:
- [ ] Status: 200 OK
- [ ] Recommendations là list of integers/strings
- [ ] Số lượng recommendations = top_k (nếu đủ)
- [ ] Recommendations không trùng với interacted items (nếu exclude_interacted=true)
- [ ] Recommendations được sort theo score giảm dần

#### Test 3.1.2: GET /recommendations/{user_id} - With Behavior Boost
**Mục đích**: Test recommendations với behavior boost

**Steps**:
1. Gửi user action: user 999 click item 100
2. Đợi 5 giây (để ETL xử lý)
3. Gọi recommendations với `use_behavior_boost=true`

**Expected**:
- [ ] Item 100 xuất hiện trong recommendations hoặc items tương tự
- [ ] Scores khác với recommendations không có boost
- [ ] Recent actions ảnh hưởng đến kết quả

#### Test 3.1.3: GET /recommendations/{user_id} - With Similarity Boost
**Mục đích**: Test recommendations với similarity boost (Phase 2)

**Steps**:
1. User click item có features cụ thể (style, price, star, etc.)
2. Gọi recommendations với `use_similarity_boost=true`

**Expected**:
- [ ] Items có features tương tự được boost
- [ ] Recommendations đa dạng hơn
- [ ] Không chỉ recommend items đã tương tác

#### Test 3.1.4: Cold Start - New User
**Mục đích**: Test recommendations cho user mới (không có history)

**Input**: `GET /recommendations/9999` (user chưa có trong dataset)

**Expected**:
- [ ] Status: 200 OK
- [ ] Có recommendations (popular items hoặc random)
- [ ] Không crash với user mới

#### Test 3.1.5: Edge Cases
**Kiểm tra**:
- [ ] top_k=1 → trả về 1 item
- [ ] top_k=100 → trả về tối đa có thể
- [ ] top_k > số items → trả về tất cả items
- [ ] user_id không tồn tại → vẫn có recommendations
- [ ] Invalid user_id format → 400 Bad Request

---

### 3.2. Test Response Format

#### Test 3.2.1: JSON Structure
**Kiểm tra**:
- [ ] Response là valid JSON
- [ ] Encoding UTF-8
- [ ] Content-Type: application/json
- [ ] CORS headers đúng (nếu có)

#### Test 3.2.2: Data Types
**Kiểm tra**:
- [ ] user_id là string hoặc int
- [ ] recommendations là list of integers hoặc strings
- [ ] Không có NaN, Infinity, null

---

## 4. TEST END-TO-END (E2E Testing)

### 4.1. E2E Test: User Journey Hoàn Chỉnh

#### Test 4.1.1: Full Flow - User Tương Tác và Nhận Recommendations
**Mục đích**: Test toàn bộ luồng từ user action đến recommendations

**Steps**:
1. **User Action**: Web gửi POST /user_action
   - User 100 click item 200
   - Timestamp: current time
2. **ETL Processing**: Đợi ETL xử lý (hoặc trigger thủ công)
   - Kiểm tra log được đọc
   - Kiểm tra hotel.inter được cập nhật
3. **Get Recommendations**: Web gọi GET /recommendations/100
   - Với behavior boost = true
   - Kiểm tra item 200 hoặc items tương tự xuất hiện
4. **User Action tiếp**: User 100 like item 201
5. **Get Recommendations lại**: Kiểm tra recommendations thay đổi

**Expected Results**:
- [ ] User actions được ghi vào log
- [ ] ETL xử lý và cập nhật dataset
- [ ] Recommendations phản ánh recent actions
- [ ] Recommendations cập nhật theo thời gian thực

---

#### Test 4.1.2: E2E Test - Multiple Users
**Mục đích**: Test system xử lý được nhiều users cùng lúc

**Steps**:
1. Gửi actions từ 5 users khác nhau
2. Mỗi user có 3-5 actions
3. Gọi recommendations cho từng user
4. Kiểm tra mỗi user nhận recommendations riêng

**Expected**:
- [ ] Mỗi user có recommendations khác nhau
- [ ] Recommendations phù hợp với actions của từng user
- [ ] Không có conflict giữa các users

---

#### Test 4.1.3: E2E Test - Time Decay
**Mục đích**: Kiểm tra recommendations thay đổi theo thời gian

**Steps**:
1. User click item A (t=0)
2. Get recommendations → Item A có boost cao
3. Đợi 2 giờ
4. Get recommendations lại → Item A boost giảm
5. User click item B (t=2h)
6. Get recommendations → Item B boost cao hơn A

**Expected**:
- [ ] Recent actions có weight cao hơn old actions
- [ ] Boost giảm theo time decay
- [ ] Recommendations cập nhật real-time

---

### 4.2. Performance Testing

#### Test 4.2.1: API Response Time
**Kiểm tra**:
- [ ] Health check: < 100ms
- [ ] Recommendations (basic): < 2s
- [ ] Recommendations (with boost): < 3s
- [ ] POST user_action: < 200ms

#### Test 4.2.2: Concurrent Requests
**Kiểm tra**:
- [ ] 10 concurrent requests → tất cả thành công
- [ ] 50 concurrent requests → không crash
- [ ] Response time không tăng đáng kể

#### Test 4.2.3: Large Log File
**Kiểm tra**:
- [ ] ETL xử lý được log file lớn (10k+ lines)
- [ ] Không bị memory leak
- [ ] Processing time hợp lý

---

### 4.3. Integration Testing

#### Test 4.3.1: Docker Containers
**Kiểm tra**:
- [ ] Container recbole-api chạy và healthy
- [ ] Container recbole-etl chạy và xử lý định kỳ
- [ ] Container recbole-retrain chạy và schedule đúng
- [ ] Containers restart được sau khi stop

#### Test 4.3.2: Volume Mounts
**Kiểm tra**:
- [ ] Volume ./data được mount đúng
- [ ] Volume ./dataset được mount đúng
- [ ] Volume ./saved được mount đúng
- [ ] File changes từ host reflect trong container

#### Test 4.3.3: Environment Variables
**Kiểm tra**:
- [ ] API_KEY được đọc từ .env
- [ ] ALLOWED_ORIGINS được đọc từ .env
- [ ] RETRAIN_HOUR/MINUTE được đọc từ .env

---

## 5. TEST RETRAIN SCHEDULER

### 5.1. Test Retrain Schedule

#### Test 5.1.1: Schedule Configuration
**Kiểm tra**:
- [ ] Retrain scheduler chạy đúng giờ (2h sáng default)
- [ ] Check interval hoạt động (1h default)
- [ ] Có thể thay đổi schedule qua env vars

#### Test 5.1.2: Retrain Process
**Mục đích**: Test retrain model với data mới

**Steps**:
1. Thêm nhiều user actions mới vào dataset
2. Đợi hoặc trigger retrain thủ công
3. Kiểm tra:
   - [ ] Model được train lại
   - [ ] Model mới được save vào saved/
   - [ ] API load model mới
   - [ ] Recommendations cải thiện với data mới

---

## 6. TEST ERROR HANDLING & ROBUSTNESS

### 6.1. Error Scenarios

#### Test 6.1.1: API Errors
**Kiểm tra**:
- [ ] Invalid JSON → 422 Unprocessable Entity
- [ ] Missing fields → 400 Bad Request
- [ ] Model chưa load → 503 Service Unavailable
- [ ] File locked → retry hoặc error message

#### Test 6.1.2: ETL Errors
**Kiểm tra**:
- [ ] Log file không tồn tại → tạo file mới
- [ ] Invalid JSON trong log → skip và log
- [ ] Dataset file locked → retry sau
- [ ] Disk full → log error, không crash

#### Test 6.1.3: Model Errors
**Kiểm tra**:
- [ ] Model file không tồn tại → error message rõ ràng
- [ ] Model corrupt → fallback hoặc error
- [ ] Out of memory → graceful degradation

---

## 7. TEST DATA CONSISTENCY

### 7.1. Data Integrity

#### Test 7.1.1: No Data Loss
**Kiểm tra**:
- [ ] Tất cả user actions được lưu vào log
- [ ] Tất cả processed actions được archive
- [ ] Không có duplicate entries trong hotel.inter

#### Test 7.1.2: Data Format Consistency
**Kiểm tra**:
- [ ] user_id format nhất quán (int hoặc string)
- [ ] item_id format nhất quán
- [ ] Timestamp format nhất quán

---

## 8. CHECKLIST TEST TỔNG THỂ

### Phase 1: Basic Functionality
- [ ] Health check endpoint hoạt động
- [ ] POST user_action thành công
- [ ] GET recommendations (basic) thành công
- [ ] ETL đọc và xử lý log file

### Phase 2: Behavior Boost
- [ ] Behavior boost hoạt động
- [ ] Time decay hoạt động đúng
- [ ] Multiple actions cùng item → boost cộng dồn
- [ ] Recommendations thay đổi theo recent actions

### Phase 3: Similarity Boost (Phase 2)
- [ ] Similarity boost hoạt động
- [ ] Items tương tự được boost
- [ ] Similarity threshold hoạt động
- [ ] Recommendations đa dạng hơn

### Phase 4: End-to-End
- [ ] Full flow từ user action → ETL → recommendations
- [ ] Multiple users hoạt động độc lập
- [ ] Time decay ảnh hưởng recommendations
- [ ] Cold start (user mới) hoạt động

### Phase 5: Robustness
- [ ] Error handling đúng
- [ ] File locking được xử lý
- [ ] Concurrent requests hoạt động
- [ ] System không crash với invalid input

---

## 9. SCRIPTS TEST TỰ ĐỘNG

### 9.1. Scripts Hiện Có
- `test_docker_system.py`: Test cơ bản sau khi build Docker

### 9.2. Scripts Cần Tạo

#### test_full_e2e.py
- Test toàn bộ flow từ đầu đến cuối
- Test multiple users
- Test time decay

#### test_performance.py
- Test response time
- Test concurrent requests
- Test large dataset

#### test_data_integrity.py
- Test data consistency
- Test no data loss
- Test format consistency

---

## 10. KẾT QUẢ TEST MONG ĐỢI

### Success Criteria
- ✅ Tất cả API endpoints hoạt động
- ✅ ETL xử lý được user actions
- ✅ Behavior boost ảnh hưởng recommendations
- ✅ Similarity boost hoạt động (Phase 2)
- ✅ System xử lý được concurrent requests
- ✅ Error handling đúng và graceful
- ✅ End-to-end flow hoạt động mượt mà

### Performance Targets
- API response time < 3s (với behavior boost)
- ETL processing < 30s cho 1000 actions
- System handle được 100+ concurrent users

---

## 11. NOTES

- Test nên được chạy trong Docker environment để giống production
- Cần có test data sẵn trong dataset
- Test scripts nên cleanup sau khi chạy (nếu cần)
- Log all test results để review sau
