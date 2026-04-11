## Cursor Internal Context (thoa thuan noi bo)

File nay luu cac quy uoc noi bo de Cursor/AI tham chieu trong qua trinh lam viec.
Khong dung lam runbook van hanh.

### 1) Quy uoc bao cao task (ap dung cho moi task)
- Checklist trong bao cao chi ghi cac kiem tra lien quan **task dang lam**.
- Khong lap lai checklist cua phase truoc neu task hien tai khong yeu cau.
- Mau report copy/paste:

```text
#<task_id>

PR(AI): <link PR>
Mo ta Pull Request
- <mo ta cac thay doi chinh cua task>

Cac file thay doi
- <file_1>
- <file_2>

3. Loai thay doi
- ✨/🐛/♻️ <loai thay doi>

4. Checklist (chi cua task hien tai)
- [x] <kiem tra 1 lien quan truc tiep task>
- [x] <kiem tra 2 lien quan truc tiep task>
```

### 2) Nhat ky file chuc nang da tao (kem giai thich ngan)
- `ai_service/data/loaders/csv_loader.py`: doc CSV theo cau hinh cot dau vao.
- `ai_service/data/adapters/booking_like_adapter.py`: map du lieu booking tho -> chuoi ngay `ds,y` (MVP demand).
- `ai_service/data/preprocessors/continuous_daily_series.py`: reindex chuoi ngay lien tuc, fill missing days.
- `ai_service/models/base.py`: interface model du bao dung chung (`fit/predict`).
- `ai_service/models/prophet_model.py`: trien khai model Prophet cho du bao 7-30 ngay.
- `ai_service/insights/explainer.py`: sinh giai thich ngan dang rule-based.
- `ai_service/services/forecasting_service.py`: dieu phoi pipeline Phase 1 end-to-end.
- `ai_service/main.py`: CLI chay AI module va in output JSON.
- `ai_service/config/dataset_schema.py`: schema mapping raw columns -> chuan noi bo.
- `ai_service/config/settings.py`: cau hinh app/forecast/data/explain.
- `ai_service/evaluation/errors.py`: tinh sai lech forecast-actual (absolute/percentage).
- `ai_service/evaluation/comparison.py`: so sanh forecast vs actual theo `ds` va tao bang sai lech theo thoi gian.
- `ai_service/evaluation/__init__.py`: package marker cho evaluation layer.
- `ai_service/evaluation/large_deviation.py`: danh dau diem co sai lech lon hon nguong (large_deviation).
- `ai_service/tools/task_376_demo.py`: lenh demo in output JSON minh chung cho task #376.
- `ai_service/tools/task_377_demo.py`: lenh demo in output JSON minh chung cho task #377 (co luu CSV).
- `ai_service/tools/task_378_demo.py`: lenh demo minh chung task #378 (large_deviation + dem).
- `ai_service/evaluation/threshold_policy.py`: nguong 3 dai normal/warning/drift + suy ra tu phan vi loi lich su.
- `ai_service/tools/task_379_demo.py`: lenh demo minh chung task #379 (nguong + phan loi).
- `ai_service/evaluation/rolling_window.py`: rolling mean error + dem ngay vuot nguong trong cua so + co persistent.
- `ai_service/tools/task_380_demo.py`: lenh demo minh chung task #380.
- `ai_service/evaluation/error_history_store.py`: luu lich su sai lech theo thoi gian (append CSV) + trang thai hoat dong theo run.
- `ai_service/tools/task_381_demo.py`: lenh demo minh chung task #381 (CSV + operational_status).
- `ai_service/decision/__init__.py`: package marker cho bộ phận hỗ trợ ra quyết định.
- `ai_service/decision/decision_table.py`: bảng quyết định Rule-based phân luồng Trend và Confidence thành văn bản.
- `ai_service/tools/task_395_demo.py`: script tĩnh demo thử nghiệm cho module Decision Table.
- `ai_service/advanced/__init__.py`: marker package hệ thống Khuyến nghị nâng cao.
- `ai_service/advanced/dynamic_pricing.py`: lập trình engine Đề xuất Giá động.
- `ai_service/advanced/staffing_optimizer.py`: bộ tính toán Lượng số phòng quy đổi ra khối lượng nhân sự theo ca làm việc.
- `ai_service/tools/task_418_demo.py`: kịch bản phân nhánh demo toán học của Module Giá động.
- `ai_service/tools/task_419_demo.py`: mô phỏng logic quy đổi Ca nhân sự.
- `Document_code/task_demo_commands.md`: lenh demo theo task (chup man hinh).




### 3) Nguyen tac cap nhat
- Khi tao file chuc nang moi, them 1 dong mo ta ngan vao file nay.
- Neu co quy uoc noi bo moi (khong phai huong dan van hanh), ghi vao day.

### 4) Quy uoc ve thao tac Git va ghi log
- Khong tu dong `commit`/`push` code trong qua trinh lam viec (tru khi ban yeu cau ro).
- Comment code nen tien Viet va de hieu.
- Khi can ghi “nhat ky file / thay doi”, chi ghi vao `Document_code/cursor_internal_context.md`.
- `RUNBOOK.md` chi giu phan “lenh chay / cai dat”, khong dung de ghi nhat ky noi bo.

### 5) Quy uoc khi bat dau moi task
- Truoc khi code:
  - Doc lai cac file quy tac can thiet trong `Document_code/` (toi thieu: `rang_buoc_cursor.md`, va ke hoach/hop dong neu co).
  - Tao nhanh git theo task.
- Quy uoc dat ten nhanh:
  - `task-<id>-<ten_ngan>` (vi du: `task-378-deviation-threshold`)
  - Moi task lam tren 1 nhanh rieng (khong lam chen vao nhanh khac).

### 6) Minh chung (anh) sau khi hoan thanh task
- Moi task sau khi hoan thanh can co anh minh chung (screenshot/anh output) de dan vao bao cao.
- Anh minh chung nen de trong `artifacts/` (khong push len git), va ghi ro ten file theo task (vi du: `artifacts/task_376.png`).
