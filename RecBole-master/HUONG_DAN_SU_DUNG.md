# Hướng dẫn lưu kết quả RecBole vào file result.txt

## Vấn đề

RecBole mặc định chỉ lưu kết quả vào log file và hiển thị trên console, không tự động tạo file `result.txt` để lưu metrics và thời gian chạy.

## Giải pháp

Tôi đã tạo 3 cách để lưu kết quả vào file `result.txt`:

### Cách 1: Sử dụng script đã được sửa đổi `run_recbole.py`

```bash
# Chạy với tùy chọn --save_results để tự động lưu kết quả
python run_recbole.py --model NFM --dataset ml-100k --save_results

# Hoặc chỉ định tên file output
python run_recbole.py --model NFM --dataset ml-100k --save_results --output_file my_results.txt

# Sử dụng với config file
python run_recbole.py --model NFM --dataset ml-100k --config_files nfm_config.yaml --save_results
```

### Cách 2: Sử dụng script `run_with_results.py` (Đơn giản nhất)

```bash
# Chạy trực tiếp (sử dụng các tham số mặc định)
python run_with_results.py

# Script sẽ tự động:
# - Chạy model NFM trên dataset ml-100k
# - Sử dụng config file nfm_config.yaml nếu có
# - Lưu kết quả vào result.txt
```

### Cách 3: Sử dụng script `save_results.py` (Tùy chỉnh)

```python
from save_results import run_with_result_saving

# Chạy với cấu hình tùy chỉnh
config_dict = {
    "epochs": 20,
    "learning_rate": 0.001,
    "eval_type": "both",
    "metrics": ["AUC", "LogLoss"],
}

result = run_with_result_saving(
    model="NFM",
    dataset="ml-100k",
    config_dict=config_dict,
    output_file="result.txt"
)
```

## Nội dung file result.txt

File `result.txt` sẽ chứa:

```
================================================================================
RECBOLE TRAINING RESULTS - 2025-01-08 15:30:45
================================================================================

CONFIGURATION:
----------------------------------------
model: NFM
dataset: ml-100k
epochs: 20
learning_rate: 0.001
total_training_time: 45.67 seconds
total_training_time_minutes: 0.76 minutes
start_time: 2025-01-08 15:29:59
end_time: 2025-01-08 15:30:45

BEST VALIDATION RESULTS:
----------------------------------------
Best Valid Score: 0.7721
Best Valid Metrics:
  AUC: 0.7721
  LogLoss: 0.5714

TEST RESULTS:
----------------------------------------
AUC: 0.7654
LogLoss: 0.5832

ADDITIONAL INFORMATION:
----------------------------------------
Valid Score Bigger is Better: True
Output File: result.txt
Generated at: 2025-01-08 15:30:45
```

## Lưu ý

1. **File log**: RecBole vẫn tạo file log trong thư mục `log/` như bình thường
2. **File model**: Model được lưu trong thư mục `saved/` như bình thường
3. **File result.txt**: Là file bổ sung chứa tóm tắt kết quả cuối cùng
4. **Encoding**: File được lưu với encoding UTF-8 để hỗ trợ tiếng Việt

## Ví dụ sử dụng

```bash
# Chạy nhanh với script đơn giản
python run_with_results.py

# Hoặc chạy với tùy chọn đầy đủ
python run_recbole.py --model NFM --dataset ml-100k --save_results --output_file nfm_results.txt
```

## Troubleshooting

1. **Lỗi "File not found"**: Đảm bảo bạn đang chạy script trong thư mục gốc của RecBole
2. **Lỗi encoding**: File được lưu với UTF-8, mở bằng Notepad++ hoặc VS Code
3. **Không có kết quả test**: Kiểm tra xem model có được evaluate trên test set không

