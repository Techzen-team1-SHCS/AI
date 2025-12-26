# Hướng Dẫn Test Phase 1 - Batch Testing

## Tổng quan

Script này cho phép test Phase 1 (Behavior Boost) với nhiều users cùng lúc và tạo báo cáo chi tiết.

## Yêu cầu

- Python 3.7+
- Đã cài đặt các dependencies: `pandas`, `torch`, `recbole`
- Model đã được train và lưu trong thư mục `saved/`

## Cách sử dụng

### Bước 1: Chạy test

```bash
# Test 100 users (mặc định)
python tests/phase1_analysis/test_phase1_batch_100.py --num-users 100 --output tests/phase1_analysis/phase1_results_100.json

# Test với số lượng users khác
python tests/phase1_analysis/test_phase1_batch_100.py --num-users 50 --output tests/phase1_analysis/phase1_results_50.json

# Chạy im lặng (chỉ in kết quả cuối)
python tests/phase1_analysis/test_phase1_batch_100.py --num-users 100 --output results.json --quiet
```

### Bước 2: Tạo báo cáo

```bash
# Tạo báo cáo markdown từ kết quả JSON
python tests/phase1_analysis/generate_report.py tests/phase1_analysis/phase1_results_100.json tests/phase1_analysis/PHASE1_REPORT.md
```

## Các tham số

### test_phase1_batch_100.py

- `--num-users`: Số lượng users để test (default: 100)
- `--top-k`: Số lượng recommendations (default: 10)
- `--output`: Đường dẫn file JSON để lưu kết quả (optional)
- `--quiet`: Chỉ in kết quả tổng hợp, không in chi tiết từng user
- `--model`: Đường dẫn đến model checkpoint (nếu không chỉ định sẽ dùng model mới nhất)

### generate_report.py

- `input_json`: File JSON chứa kết quả test
- `output_md`: File markdown output

## Cấu trúc kết quả

File JSON output chứa:

```json
{
  "test_info": {
    "model_path": "...",
    "num_users_tested": 100,
    "top_k": 10,
    "test_date": "..."
  },
  "overall_stats": {
    "total_users": 100,
    "passed": 85,
    "failed": 15,
    "pass_rate": 0.85,
    "avg_accuracy": 0.82,
    "avg_score": 3.2,
    "avg_mandatory_passed": 2.8
  },
  "pattern_stats": {
    "gender_style": {"passed": 90, "total": 100, "pass_rate": 0.90},
    ...
  },
  "results": [
    {
      "user_id": "100",
      "gender": "F",
      "age": 25,
      "region": "Ho Chi Minh",
      "recommendations": [...],
      "pattern_counts": {...},
      "evaluation": {...}
    },
    ...
  ]
}
```

## Báo cáo

Báo cáo markdown bao gồm:

1. **Tổng quan kết quả**: Thống kê tổng thể, pass rate, accuracy
2. **Phân tích từng pattern**: Pass rate cho từng pattern (mandatory và optional)
3. **Phân tích theo nhóm**: Theo gender, age group
4. **Chi tiết kết quả**: Top 20 users failed và top 20 users passed
5. **Kết luận và đề xuất**: Điểm mạnh, điểm cần cải thiện, đề xuất

## Lưu ý

- Test có thể mất vài phút tùy vào số lượng users và tốc độ inference
- Đảm bảo model đã được load thành công trước khi test
- Nếu có lỗi, kiểm tra log để xem chi tiết

## Ví dụ

```bash
# Test 100 users và tạo báo cáo
python tests/phase1_analysis/test_phase1_batch_100.py --num-users 100 --output results.json --quiet
python tests/phase1_analysis/generate_report.py results.json PHASE1_REPORT.md

# Xem báo cáo
cat PHASE1_REPORT.md
```

