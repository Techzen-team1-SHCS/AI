# TÀI LIỆU HƯỚNG DẪN TRAINING MODEL RECBOLE

## MỤC LỤC

1. [Giới thiệu](#giới-thiệu)
2. [Cách chạy Training](#cách-chạy-training)
3. [Cấu hình Training](#cấu-hình-training)
4. [Các tham số quan trọng](#các-tham-số-quan-trọng)
5. [Metrics và ý nghĩa](#metrics-và-ý-nghĩa)
6. [Early Stopping](#early-stopping)
7. [Cách đọc kết quả Training](#cách-đọc-kết-quả-training)
8. [Kiểm tra tiến trình Training](#kiểm-tra-tiến-trình-training)
9. [Đánh giá Model đã đạt tiêu chuẩn](#đánh-gía-model-đã-đạt-tiêu-chuẩn)
10. [Mối quan hệ giữa Epochs và Dữ liệu](#mối-quan-hệ-giữa-epochs-và-dữ-liệu)
11. [Các vấn đề thường gặp](#các-vấn-đề-thường-gặp)
12. [Scripts hỗ trợ](#scripts-hỗ-trợ)
13. [FAQ - Câu hỏi thường gặp](#faq---câu-hỏi-thường-gặp)

---

## GIỚI THIỆU

Dự án sử dụng **RecBole framework** với model **DeepFM** để xây dựng hệ thống gợi ý khách sạn cá nhân hóa.

- **Model**: DeepFM (Deep Factorization Machine)
- **Dataset**: hotel (hotel.user, hotel.item, hotel.inter)
- **Task**: Regression (dự đoán điểm số quan tâm của người dùng với khách sạn)
- **Output**: Điểm số float từ 0.0 đến 1.0 (từ action_type: click=0.25, like=0.5, share=0.75, booking=1.0)

---

## CÁCH CHẠY TRAINING

### 1. Sử dụng run_recbole.py (Khuyến nghị)

```bash
.\recbole-env\Scripts\python.exe run_recbole.py --model=DeepFM --dataset=hotel --config_file=deepfm_config.yaml
```

### 2. Sử dụng Python script trực tiếp

```python
from recbole.quick_start import run_recbole

run_recbole(
    model='DeepFM',
    dataset='hotel',
    config_file_list=['deepfm_config.yaml']
)
```

### 3. Các tham số dòng lệnh

- `--model`: Tên model (DeepFM)
- `--dataset`: Tên dataset (hotel)
- `--config_file`: Đường dẫn file config (deepfm_config.yaml)
- `--epochs`: Số epochs tối đa (override config)
- `--learning_rate`: Learning rate (override config)

---

## CẤU HÌNH TRAINING

File cấu hình: `deepfm_config.yaml`

```yaml
model: DeepFM
dataset: hotel
eval_type: both
metrics: ["RMSE", "MAE"]
epochs: 300
learning_rate: 0.001
embedding_size: 10
mlp_hidden_size: [64, 64, 64]
dropout_prob: 0.0

# Early stopping settings
stopping_step: 10  # Dừng training nếu valid score không cải thiện trong 10 epochs
valid_metric: RMSE  # Metric để đánh giá (RMSE càng thấp càng tốt)
valid_metric_bigger: False  # False vì RMSE càng thấp càng tốt
eval_step: 1  # Đánh giá sau mỗi epoch
```

---

## CÁC THAM SỐ QUAN TRỌNG

### 1. Model Parameters

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `model` | DeepFM | Tên model sử dụng |
| `dataset` | hotel | Tên dataset |
| `epochs` | 300 | Số epochs tối đa |
| `learning_rate` | 0.001 | Tốc độ học (càng nhỏ học càng chậm nhưng ổn định hơn) |
| `embedding_size` | 10 | Kích thước embedding vector |
| `mlp_hidden_size` | [64, 64, 64] | Kích thước các layer ẩn trong DNN |
| `dropout_prob` | 0.0 | Tỷ lệ dropout (0.0 = không dropout) |

### 2. Training Parameters

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `train_batch_size` | 2048 | Số mẫu trong mỗi batch training |
| `learner` | adam | Optimizer sử dụng (adam, sgd, adagrad, rmsprop) |
| `eval_step` | 1 | Đánh giá sau mỗi N epochs |
| `stopping_step` | 10 | Dừng nếu không cải thiện trong N epochs |

### 3. Evaluation Parameters

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `eval_type` | both | Đánh giá cả valid và test |
| `metrics` | ["RMSE", "MAE"] | Các metrics để đánh giá |
| `valid_metric` | RMSE | Metric chính để đánh giá early stopping |
| `valid_metric_bigger` | False | False = metric càng thấp càng tốt |

---

## METRICS VÀ Ý NGHĨA

### 1. RMSE (Root Mean Squared Error)

- **Ý nghĩa**: Độ sai số trung bình bình phương căn
- **Công thức**: √(Σ(predicted - actual)² / n)
- **Giải thích**: Đo sai số giữa dự đoán và giá trị thực
- **Đánh giá**:
  - **Tốt**: < 0.4
  - **Trung bình**: 0.4 - 0.6
  - **Kém**: > 0.6
- **Đặc điểm**: Phạt nặng các lỗi lớn (vì bình phương)

### 2. MAE (Mean Absolute Error)

- **Ý nghĩa**: Sai số tuyệt đối trung bình
- **Công thức**: Σ|predicted - actual| / n
- **Giải thích**: Đo sai số tuyệt đối giữa dự đoán và giá trị thực
- **Đánh giá**:
  - **Tốt**: < 0.3
  - **Trung bình**: 0.3 - 0.5
  - **Kém**: > 0.5
- **Đặc điểm**: Phạt đều các lỗi (không bình phương)

### 3. So sánh RMSE vs MAE

- **RMSE**: Nhạy cảm với outliers (lỗi lớn)
- **MAE**: Ít nhạy cảm với outliers
- **Khi nào dùng RMSE**: Khi muốn phạt nặng lỗi lớn
- **Khi nào dùng MAE**: Khi muốn đánh giá đều các lỗi

### 4. Metrics cho Regression vs Classification

| Task | Metrics phù hợp | Metrics không phù hợp |
|------|----------------|----------------------|
| **Regression** (DeepFM) | RMSE, MAE | AUC, LogLoss, Recall, Precision |
| **Classification** (NFM) | AUC, LogLoss, Recall, Precision | RMSE, MAE |

**Lưu ý**: Dự án này dùng **Regression** nên chỉ dùng **RMSE** và **MAE**.

---

## EARLY STOPPING

### 1. Cách hoạt động

Early stopping dừng training khi model không còn cải thiện trên validation set.

**Quy trình**:
1. Sau mỗi epoch, đánh giá model trên validation set
2. So sánh với best score hiện tại
3. Nếu **cải thiện** → Reset counter, lưu model mới
4. Nếu **không cải thiện** → Tăng counter
5. Nếu counter > `stopping_step` → **Dừng training**

### 2. Ví dụ cụ thể

```
Epoch 40: RMSE = 0.1829 (BEST) → cur_step = 0, lưu model
Epoch 41: RMSE = 0.1831 (không tốt hơn) → cur_step = 1
Epoch 42: RMSE = 0.1842 (không tốt hơn) → cur_step = 2
...
Epoch 50: RMSE = 0.1854 (không tốt hơn) → cur_step = 10
Epoch 51: RMSE = 0.1847 (không tốt hơn) → cur_step = 11 > 10 → DỪNG!
```

**Kết quả**: Best epoch = 40, Training dừng ở epoch 51

### 3. Các tham số Early Stopping

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `stopping_step` | 10 | Số epochs chờ đợi trước khi dừng |
| `valid_metric` | RMSE | Metric để đánh giá |
| `valid_metric_bigger` | False | False = metric càng thấp càng tốt |
| `eval_step` | 1 | Đánh giá sau mỗi epoch |

### 4. Tại sao cần Early Stopping?

- **Tránh Overfitting**: Model học quá kỹ dữ liệu training
- **Tiết kiệm thời gian**: Dừng khi không còn cải thiện
- **Tự động hóa**: Không cần can thiệp thủ công

### 5. Điều chỉnh Early Stopping

**Muốn chạy nhiều epochs hơn**:
```yaml
stopping_step: 20  # Chờ 20 epochs thay vì 10
```

**Muốn chạy ít epochs hơn**:
```yaml
stopping_step: 5  # Chờ 5 epochs thay vì 10
```

**Tắt Early Stopping** (không khuyến nghị):
```yaml
stopping_step: 0  # Hoặc số rất lớn
```

---

## CÁCH ĐỌC KẾT QUẢ TRAINING

### 1. Output trong Terminal

```
epoch 0 training [time: 0.13s, train loss: 6.1357]
epoch 0 evaluating [time: 0.01s, valid_score: 0.331400]
valid result: 
rmse : 0.3314    mae : 0.2753
Saving current: saved\DeepFM-Nov-06-2025_15-23-44.pth
```

**Giải thích**:
- `train loss`: Loss trên training set (càng thấp càng tốt)
- `valid_score`: Score trên validation set (RMSE trong trường hợp này)
- `valid result`: Chi tiết các metrics
- `Saving current`: Lưu checkpoint khi cải thiện

### 2. Kết quả cuối cùng

```
Finished training, best eval result in epoch 40
Loading model structure and parameters from saved\DeepFM-Nov-06-2025_15-23-44.pth
best valid : OrderedDict({'rmse': 0.1829, 'mae': 0.1148})
test result: OrderedDict({'rmse': 0.1851, 'mae': 0.1156})
```

**Giải thích**:
- `best eval result in epoch 40`: Epoch tốt nhất là 40
- `best valid`: Kết quả tốt nhất trên validation set
- `test result`: Kết quả trên test set (sau khi training xong)

### 3. Files được tạo

| File | Vị trí | Mô tả |
|------|--------|-------|
| **Checkpoint** | `saved/DeepFM-{timestamp}.pth` | Model weights và config |
| **Log file** | `log/DeepFM/DeepFM-hotel-{timestamp}-{hash}.log` | Log chi tiết training |
| **TensorBoard** | `log_tensorboard/` | Logs cho TensorBoard |

---

## KIỂM TRA TIẾN TRÌNH TRAINING

### 1. Sử dụng view_training_progress.py

```bash
.\recbole-env\Scripts\python.exe view_training_progress.py
```

**Output**:
- Tổng số epochs
- Best epoch
- 5 epochs cuối cùng
- 5 lần đánh giá cuối cùng
- Best valid result
- Test result
- Giải thích metrics
- Phân tích tiến trình

### 2. Sử dụng check_training_result.py

```bash
.\recbole-env\Scripts\python.exe check_training_result.py
```

**Output**:
- Thông tin từ log file
- Thông tin từ checkpoint file
- Config của model
- Số lượng parameters

### 3. Đọc Log file trực tiếp

```bash
# Tìm log file mới nhất
dir log\DeepFM\*.log /O-D

# Đọc log file
type log\DeepFM\DeepFM-hotel-{timestamp}-{hash}.log
```

---

## ĐÁNH GIÁ MODEL ĐÃ ĐẠT TIÊU CHUẨN

### 1. Tiêu chuẩn "Tốt"

| Metric | Tiêu chuẩn | Giải thích |
|--------|-----------|------------|
| **RMSE** | < 0.4 | Sai số trung bình thấp |
| **MAE** | < 0.3 | Sai số tuyệt đối thấp |
| **Test vs Valid** | Chênh lệch < 0.05 | Không bị overfitting |

### 2. Ví dụ đánh giá

**Kết quả tốt**:
```
Best valid: RMSE = 0.1829, MAE = 0.1148
Test result: RMSE = 0.1851, MAE = 0.1156
→ ✅ Đạt tiêu chuẩn (RMSE < 0.4, MAE < 0.3)
→ ✅ Không overfitting (test ≈ valid)
```

**Kết quả kém**:
```
Best valid: RMSE = 0.65, MAE = 0.55
Test result: RMSE = 0.80, MAE = 0.70
→ ❌ Không đạt tiêu chuẩn (RMSE > 0.4, MAE > 0.3)
→ ❌ Overfitting (test >> valid)
```

### 3. Khi nào model đã sẵn sàng?

- ✅ RMSE < 0.4 và MAE < 0.3
- ✅ Test result tương đương valid result (không overfitting)
- ✅ Training đã dừng do early stopping (không còn cải thiện)
- ✅ Checkpoint đã được lưu

---

## MỐI QUAN HỆ GIỮA EPOCHS VÀ DỮ LIỆU

### 1. Số epochs KHÔNG phụ thuộc vào số lượng dữ liệu

**Quan niệm sai**:
- "Thêm dữ liệu → chạy nhiều epochs hơn"
- "Ít dữ liệu → chạy ít epochs hơn"

**Sự thật**:
- Số epochs phụ thuộc vào:
  - `epochs` (max epochs) trong config
  - `stopping_step` (early stopping)
- **KHÔNG** phụ thuộc vào số lượng dữ liệu

### 2. Thêm dữ liệu có ảnh hưởng gì?

**Có thể**:
- ✅ Giúp model **học tốt hơn** (nhiều mẫu hơn để học)
- ✅ Giúp model **học nhanh hơn** (nhiều mẫu hơn mỗi epoch)
- ✅ Model có thể **hội tụ sớm hơn** hoặc **muộn hơn** (tùy chất lượng dữ liệu)

**KHÔNG nhất thiết**:
- ❌ Chạy nhiều epochs hơn
- ❌ Metrics tốt hơn (nếu dữ liệu mới không chất lượng)

### 3. Chạy nhiều epochs có cải thiện không?

**KHÔNG!** Nếu model đã hội tụ (converged), chạy thêm epochs sẽ:
- ❌ Không cải thiện model
- ❌ Có thể gây overfitting
- ❌ Lãng phí thời gian và tài nguyên

**Early stopping** được thiết kế để tránh điều này.

### 4. Dữ liệu giống nhau → Kết quả giống nhau?

**CÓ!** Nếu:
- ✅ Dữ liệu giống nhau
- ✅ Config giống nhau
- ✅ Seed cố định (`seed = 2020`, `reproducibility = True`)
- ✅ Cùng version RecBole

**KHÔNG** nếu:
- ❌ Seed khác nhau
- ❌ Config khác nhau
- ❌ Version RecBole khác nhau
- ❌ Có randomness (data shuffle, weight initialization)

---

## CÁC VẤN ĐỀ THƯỜNG GẶP

### 1. Training dừng quá sớm

**Triệu chứng**: Training dừng sau vài epochs

**Nguyên nhân**:
- `stopping_step` quá nhỏ
- Learning rate quá cao
- Model không học được

**Giải pháp**:
```yaml
stopping_step: 20  # Tăng lên
learning_rate: 0.0001  # Giảm xuống
```

### 2. Training chạy quá lâu

**Triệu chứng**: Training chạy đến hết epochs (300)

**Nguyên nhân**:
- `stopping_step` quá lớn
- Model chưa hội tụ

**Giải pháp**:
```yaml
stopping_step: 5  # Giảm xuống
epochs: 100  # Giảm max epochs
```

### 3. Overfitting

**Triệu chứng**: Valid score tốt nhưng test score kém

**Nguyên nhân**:
- Model học quá kỹ training data
- Dữ liệu training quá ít

**Giải pháp**:
```yaml
dropout_prob: 0.2  # Thêm dropout
stopping_step: 5  # Dừng sớm hơn
```

### 4. Underfitting

**Triệu chứng**: Cả train và valid score đều kém

**Nguyên nhân**:
- Model quá đơn giản
- Learning rate quá thấp
- Training chưa đủ

**Giải pháp**:
```yaml
mlp_hidden_size: [128, 128, 128]  # Tăng kích thước
learning_rate: 0.01  # Tăng learning rate
epochs: 500  # Tăng max epochs
```

### 5. Lỗi khi load checkpoint

**Triệu chứng**: `_pickle.UnpicklingError: Weights only load failed`

**Nguyên nhân**: PyTorch 2.6+ thay đổi default `weights_only`

**Giải pháp**: Đã sửa trong `recbole/trainer/trainer.py`:
```python
checkpoint = torch.load(checkpoint_file, map_location=self.device, weights_only=False)
```

### 6. Metrics không cải thiện

**Triệu chứng**: Valid score không giảm sau nhiều epochs

**Nguyên nhân**:
- Model đã hội tụ
- Learning rate quá thấp
- Dữ liệu không đủ

**Giải pháp**:
- Kiểm tra xem có đạt tiêu chuẩn chưa (RMSE < 0.4)
- Nếu đã đạt → Model OK, không cần train thêm
- Nếu chưa đạt → Thử tăng learning rate hoặc thêm dữ liệu

---

## SCRIPTS HỖ TRỢ

### 1. view_training_progress.py

**Mục đích**: Xem kết quả training với phân tích

**Cách dùng**:
```bash
.\recbole-env\Scripts\python.exe view_training_progress.py
```

**Output**:
- Tổng số epochs
- Best epoch
- Metrics cuối cùng
- Giải thích metrics
- Phân tích tiến trình

### 2. check_training_result.py

**Mục đích**: Kiểm tra thông tin từ checkpoint và log

**Cách dùng**:
```bash
.\recbole-env\Scripts\python.exe check_training_result.py
```

**Output**:
- Thông tin từ log file
- Thông tin từ checkpoint
- Config của model
- Số lượng parameters

### 3. explain_epochs_and_data.py

**Mục đích**: Giải thích mối quan hệ giữa epochs và dữ liệu

**Cách dùng**:
```bash
.\recbole-env\Scripts\python.exe explain_epochs_and_data.py
```

---

## FAQ - CÂU HỎI THƯỜNG GẶP

### Q1: Tại sao training dừng ở epoch 51?

**A**: Vì early stopping. Best epoch là 40, sau đó không cải thiện trong 10 epochs (41-50), nên dừng ở epoch 51.

### Q2: Thêm dữ liệu có chạy nhiều epochs hơn không?

**A**: KHÔNG. Số epochs phụ thuộc vào `epochs` và `stopping_step`, không phụ thuộc vào số lượng dữ liệu.

### Q3: Chạy nhiều epochs có cải thiện model không?

**A**: KHÔNG. Nếu model đã hội tụ, chạy thêm epochs sẽ không cải thiện, thậm chí có thể overfitting.

### Q4: Dữ liệu giống nhau thì kết quả giống nhau không?

**A**: CÓ, nếu config và seed giống nhau. Nếu seed khác nhau hoặc có randomness, kết quả có thể khác một chút.

### Q5: Model đã đạt tiêu chuẩn chưa?

**A**: Kiểm tra:
- RMSE < 0.4 và MAE < 0.3 → ✅ Đạt
- Test result ≈ valid result → ✅ Không overfitting

### Q6: Làm sao biết model đã hội tụ?

**A**: Khi:
- Valid score không cải thiện sau nhiều epochs
- Early stopping dừng training
- Train loss giảm chậm hoặc không giảm

### Q7: Nên tăng hay giảm learning rate?

**A**: 
- **Tăng** nếu model học quá chậm (loss giảm chậm)
- **Giảm** nếu model không ổn định (loss dao động nhiều)

### Q8: Checkpoint được lưu ở đâu?

**A**: `saved/DeepFM-{timestamp}.pth`

### Q9: Log file được lưu ở đâu?

**A**: `log/DeepFM/DeepFM-hotel-{timestamp}-{hash}.log`

### Q10: Làm sao xem kết quả training?

**A**: Dùng `view_training_progress.py` hoặc đọc log file trực tiếp.

---

## TÓM TẮT NHANH

### Lệnh chạy training
```bash
.\recbole-env\Scripts\python.exe run_recbole.py --model=DeepFM --dataset=hotel --config_file=deepfm_config.yaml
```

### Tiêu chuẩn "Tốt"
- RMSE < 0.4
- MAE < 0.3
- Test ≈ Valid (không overfitting)

### Early Stopping
- `stopping_step: 10` → Dừng nếu không cải thiện trong 10 epochs
- Best epoch được lưu trong checkpoint

### Kiểm tra kết quả
```bash
.\recbole-env\Scripts\python.exe view_training_progress.py
```

---

**Tài liệu này được tạo ngày**: 2025-11-06  
**Phiên bản**: 1.0  
**Dự án**: Hotel Recommendation System với RecBole

