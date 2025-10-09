Yêu cầu hệ thống

Python >= 3.8, <= 3.12

pip >= 21.0

GPU (tùy chọn, có thể chạy CPU)

Hệ điều hành: Windows / macOS / Linux

1) Chuẩn bị kiểm tra ban đầu

Mở PowerShell và đổi đến thư mục dự án:

Set-Location G:\AI\RecBole-master


Kiểm tra Python bạn đang dùng (phải ≥ 3.7):


2) Tạo và kích hoạt môi trường ảo (venv) — Tại sao: tách gói của dự án, tránh xung đột

Tạo venv:

python -m venv recbole-env


Kích hoạt (PowerShell):

.\recbole-env\Scripts\Activate.ps1


Nếu PowerShell chặn script, cho phép tạm thời:

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

Sau đó nhập lại lệnh .\recbole-env\Scripts\Activate.ps1

Sau khi kích hoạt, bạn sẽ thấy (recbole-env) tiền tố trên prompt.

3) Cập nhật pip và cài PyTorch (quan trọng)

Lý do: requirements.txt có thể tham chiếu torch; tốt nhất cài PyTorch trước tùy môi trường GPU/CPU.

Nếu máy không có NVIDIA GPU (CPU-only):

python -m pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu


Nếu có GPU và bạn muốn dùng CUDA, vào https://pytorch.org
 chọn phiên bản CUDA tương thích rồi copy lệnh pip install ... --index-url ... tương ứng.

Lưu ý: nếu trong requirements.txt có một dòng torch==... mà không tương thích (ví dụ yêu cầu CUDA), tốt nhất xóa dòng torch trong file hoặc cài torch theo cách bên trên trước rồi pip install -r requirements.txt (không cài torch hai lần).

4) Cài các thư viện từ requirements.txt — Tại sao: đây là tất cả phụ thuộc dự án

Trong venv đã activate:

pip install -r requirements.txt


Nếu lệnh báo lỗi hoặc dừng ở phần torch/cuda thì:

Xem lại file requirements.txt, nếu có torch dòng, xóa dòng đó và cài torch riêng như bước 3 rồi chạy lại pip install -r requirements.txt.

5) Cài thêm (nếu cần) — những library RecBole hay dùng

Bạn đã gặp các lỗi trước (thiếu ray, pyarrow) — để chắc chắn, cài:

pip install "ray[tune]" pyarrow


ray[tune] cho hyperparameter tuning; pyarrow thường là dependency của Ray.

6) Kiểm tra cài đặt RecBole & PyTorch

Trong môi trường đang active:

python -c "import recbole, torch; print('recbole', recbole.__version__); print('torch', torch.__version__, 'cuda_available=', torch.cuda.is_available())"


Nếu lỗi ModuleNotFoundError: recbole thì pip install recbole (thường không cần nếu bạn đã cài theo requirements). Nếu lỗi numpy như np.float_ removed, cài lại numpy tương thích:

pip install numpy==1.26.4

=============================================================================
Chạy dự án:PowerShell
1.Kích hoạt môi trường:

.\recbole-env\Scripts\Activate.ps1

2.lệnh chạy:
python run_recbole.py --model=NFM --dataset=hotel --epochs=10
chú ý:--epochs= : là số lần train. --epochs=10 là train 10 lần