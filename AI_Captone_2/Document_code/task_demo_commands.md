## Lệnh demo theo task (để chạy & chụp màn hình minh chứng)

Tài liệu này dùng để lưu các lệnh chạy demo cho từng task (AI module thường minh chứng bằng output JSON/CSV).

### Task #376 — Tính sai lệch forecast vs actual
Chạy lệnh dưới và **chụp màn hình output JSON**:

```powershell
cd d:\GitHub\AI\AI_Captone_2
python -m ai_service.tools.task_376_demo
```

### Task #377 — So sánh forecast vs actual theo `ds` + lưu CSV
Chạy lệnh dưới và **chụp màn hình output JSON**. File CSV được lưu ở `outputs/task_377_errors.csv`.

```powershell
cd d:\GitHub\AI\AI_Captone_2
python -m ai_service.tools.task_377_demo
```

### Task #378 — Phát hiện sai lệch lớn (đánh dấu điểm vượt ngưỡng)
Chạy lệnh dưới và **chụp màn hình output JSON** (có cột `large_deviation` và `count_large_deviations`).

```powershell
cd d:\GitHub\AI\AI_Captone_2
python -m ai_service.tools.task_378_demo
```

### Task #379 — Ngưỡng sai lệch 3 dải (normal / warning / drift)
Chạy lệnh dưới và **chụp màn hình output JSON** (ngưỡng cố định + suy ra từ phân vị chuỗi lỗi).

```powershell
cd d:\GitHub\AI\AI_Captone_2
python -m ai_service.tools.task_379_demo
```

### Task #380 — Rolling window theo dõi sai lệch
Chạy lệnh dưới và **chụp màn hình output JSON** (`rolling_mean_error`, `rolling_exceed_count`, `rolling_persistent_deviation`).

```powershell
cd d:\GitHub\AI\AI_Captone_2
python -m ai_service.tools.task_380_demo
```

### Task #381 — Lưu lịch sử sai lệch theo thời gian + trạng thái hoạt động
Chạy lệnh dưới và **chụp màn hình output JSON**. File CSV append tại `outputs/forecast_error_history.csv` (có `run_id`, `run_at`, `operational_status`).

```powershell
cd d:\GitHub\AI\AI_Captone_2
python -m ai_service.tools.task_381_demo
```

