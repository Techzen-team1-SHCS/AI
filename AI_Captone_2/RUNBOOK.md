## RUNBOOK — Cài môi trường & chạy dự án (từ đầu đến cuối)

### 1) Yêu cầu
- Python 3.12+
- Windows PowerShell (khuyến nghị)

### 2) Tạo virtual environment (khuyến nghị)
```powershell
cd d:\GitHub\AI\AI_Captone_2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 3) Cài thư viện
```powershell
cd d:\GitHub\AI\AI_Captone_2
python -m pip install -r requirements.txt
```

### 4) Chạy Phase 1 (Core Forecast)
#### 4.1 Global (gộp tất cả khách sạn)
```powershell
cd d:\GitHub\AI\AI_Captone_2
python -m ai_service.main --csv Document_code/hotel_booking.csv --horizon 14 --scope global
```

#### 4.2 Per-hotel (theo từng khách sạn)
```powershell
cd d:\GitHub\AI\AI_Captone_2
python -m ai_service.main --csv Document_code/hotel_booking.csv --horizon 14 --scope per_hotel --hotel "City Hotel"
```

### 5) Kết quả mong đợi
Chương trình in ra 1 JSON object duy nhất gồm:
- `forecast` (danh sách ngày dự báo)
- `confidence`, `deviation`, `suggested_action` (Phase 1 đang là giá trị mặc định)
- `explanation` (bắt buộc, tiếng Việt)

### 6) Lưu ý thường gặp
- Nếu terminal không in được tiếng Việt: dùng Windows Terminal hoặc đảm bảo output UTF-8 (code đã cấu hình sẵn).

### 7) Nhật ký file chức năng đã tạo (kèm giải thích ngắn)
- `ai_service/evaluation/comparison.py`: so sánh forecast vs actual theo từng `ds` và (tuỳ chọn) lưu bảng sai lệch để phục vụ drift detection.
