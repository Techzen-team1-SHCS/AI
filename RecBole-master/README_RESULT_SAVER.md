# Giải pháp lưu kết quả RecBole vào file result.txt

## Vấn đề

RecBole mặc định chỉ lưu kết quả vào log file và hiển thị trên console, không tự động tạo file `result.txt` để lưu metrics và thời gian chạy.

## Giải pháp đã triển khai

### 1. File `run_recbole.py` (Đã được sửa đổi)

- Thêm chức năng lưu kết quả vào file với tùy chọn `--save_results`
- Tự động tính toán thời gian huấn luyện
- Lưu tất cả metrics và cấu hình vào file có định dạng đẹp

### 2. File `run_with_results.py` (Script đơn giản)

- Script wrapper để chạy RecBole và tự động lưu kết quả
- Không cần nhớ các tham số phức tạp

### 3. File `save_results.py` (Script tùy chỉnh)

- Cho phép tùy chỉnh hoàn toàn quá trình chạy và lưu kết quả
- Có thể import và sử dụng trong code khác

## Cách sử dụng

### Cách 1: Sử dụng script đã sửa đổi (Khuyến nghị)

```bash
# Chạy và lưu kết quả
python run_recbole.py --model NFM --dataset ml-100k --save_results

# Chỉ định tên file output
python run_recbole.py --model NFM --dataset ml-100k --save_results --output_file my_results.txt

# Sử dụng với config file
python run_recbole.py --model NFM --dataset ml-100k --config_files nfm_config.yaml --save_results
```

### Cách 2: Sử dụng script đơn giản

```bash
# Chạy trực tiếp (sử dụng các tham số mặc định)
python run_with_results.py
```

### Cách 3: Sử dụng script tùy chỉnh

```python
from save_results import run_with_result_saving

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

File sẽ chứa:

- **CONFIGURATION**: Tất cả tham số cấu hình
- **BEST VALIDATION RESULTS**: Kết quả validation tốt nhất
- **TEST RESULTS**: Kết quả trên test set
- **ADDITIONAL INFORMATION**: Thông tin bổ sung (thời gian, file output, etc.)

## Lưu ý quan trọng

1. **Encoding**: File được lưu với UTF-8 để hỗ trợ tiếng Việt
2. **Tương thích**: Đã loại bỏ emoji để tương thích với Windows console
3. **Không ảnh hưởng**: Các file log và model vẫn được lưu như bình thường
4. **Tùy chọn**: Có thể chạy bình thường mà không lưu file result.txt

## Test

Đã test thành công với:

- ✅ Tạo file result.txt với định dạng đẹp
- ✅ Lưu tất cả metrics (AUC, LogLoss, etc.)
- ✅ Ghi lại thời gian huấn luyện
- ✅ Tương thích với Windows console
- ✅ Encoding UTF-8

## Troubleshooting

1. **Lỗi "File not found"**: Đảm bảo chạy script trong thư mục gốc của RecBole
2. **Lỗi encoding**: File được lưu UTF-8, mở bằng Notepad++ hoặc VS Code
3. **Không có kết quả test**: Kiểm tra cấu hình evaluation

## Kết luận

Giải pháp này hoàn toàn giải quyết vấn đề ban đầu của bạn:

- ✅ Tự động tạo file result.txt
- ✅ Lưu tất cả metrics quan trọng
- ✅ Ghi lại thời gian huấn luyện
- ✅ Định dạng dễ đọc và chuyên nghiệp
- ✅ Không ảnh hưởng đến chức năng hiện có của RecBole

