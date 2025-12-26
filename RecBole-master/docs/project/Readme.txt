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

3) Cập nhật pip và cài PyTorch (quan trọng - BẮT BUỘC)

Lý do: requirements.txt KHÔNG có torch (để tránh tải CUDA packages nặng). Phải cài PyTorch TRƯỚC.

Bước 1: Cài pip vào virtual environment (nếu chưa có):
python -m ensurepip --upgrade

Bước 2: Cài PyTorch CPU-only (khuyến nghị cho Windows, không cần GPU):

python -m pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

Lưu ý: Lệnh trên sẽ cài PyTorch phiên bản mới nhất tương thích với Python của bạn (ví dụ: PyTorch 2.8.0+cpu cho Python 3.12).

Nếu có GPU NVIDIA và muốn dùng CUDA:
Vào https://pytorch.org, chọn phiên bản CUDA tương thích rồi copy lệnh pip install tương ứng.
Ví dụ cho CUDA 11.8:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

4) Cài các thư viện từ requirements.txt

Trong venv đã activate:

pip install -r requirements.txt

Lưu ý về Ray:
- requirements.txt yêu cầu ray<=2.6.3 nhưng version này không còn sẵn có.
- Nếu gặp lỗi "No matching distribution found for ray<=2.6.3", cài ray version mới hơn:
pip install "ray[tune]>=2.31.0" pyarrow>=10.0.0

Sau đó tiếp tục cài các dependencies còn lại:
pip install fastapi==0.115.6 "uvicorn[standard]>=0.34.0,<0.39.0" "numpy>=1.24.0,<2.0.0" scipy>=1.10.0 pandas>=2.0.0 scikit-learn>=1.3.0 PyYAML>=6.0 tqdm>=4.65.0 colorlog==4.7.2 colorama==0.4.4 tensorboard>=2.13.0 thop>=0.1.1 tabulate>=0.9.0 plotly>=5.14.0 texttable>=1.6.0 psutil>=5.9.0 recbole==1.2.0

Hoặc cài từng package một nếu gặp lỗi conflict.

5) Kiểm tra cài đặt

Trong môi trường đang active, kiểm tra từng bước:

Kiểm tra PyTorch:
python -c "import torch; print('PyTorch version:', torch.__version__)"
python -c "import torch.distributed; print('torch.distributed OK')"

Kiểm tra RecBole:
python -c "from recbole.quick_start import run; print('RecBole OK')"

Kiểm tra đầy đủ:
python -c "import recbole, torch; print('recbole', recbole.__version__); print('torch', torch.__version__, 'cuda_available=', torch.cuda.is_available())"

Nếu lỗi ModuleNotFoundError: recbole thì pip install recbole==1.2.0
Nếu lỗi numpy như np.float_ removed, cài lại numpy tương thích:
pip install numpy==1.26.4

Kiểm tra retrain_model.py có chạy được không:
python retrain_model.py --help
Nếu hiển thị help message, môi trường đã sẵn sàng!

=============================================================================
Chạy dự án:PowerShell
1.Kích hoạt môi trường:

.\recbole-env\Scripts\Activate.ps1

2.lệnh chạy:
--NFM
python run_recbole.py --model=NFM --dataset=hotel --epochs=10
chú ý:--epochs= : là số lần train. --epochs=10 là train 10 lần
--DEEPFM
python run_recbole.py --model=DeepFM --dataset=hotel --config_file_list=recbole/properties/overall.yaml,recbole/properties/dataset/hotel.yaml,deepfm_config.yaml --epochs=3

3. Lệnh chạy server
Dev: uvicorn api_server:app --reload --port 5000
Prod: uvicorn api_server:app --host 0.0.0.0 --port 5000

4.Thang điểm 5 mức hành vi người dùng:
click	0.25
like	0.5
share	0.75
booking	1.0

5. lệnh kiểm tra tiến độ và chất lượng train AI
.\recbole-env\Scripts\python.exe view_training_progress.py

6. chạy thủ công retrain model
python retrain_model.py --force

7. chạy retrain tự động
python retrain_scheduler.py

===============================================================================
                  Chạy nội bộ và cho web team kết nối
1. Khởi động các dịch vụ Docker
docker-compose up -d(chỉ cần làm 1 lần, có thì khỏi làm lạilại)
docker-compose ps(kiểm tra trạng tháithái)

-> Bạn cần thấy recbole-api, recbole-etl, recbole-retrain đều “Up”.

2. Lấy địa chỉ IP nội bộ máy bạn
Mở PowerShell:
ipconfig | Select-String "IPv4"
IPv4 Address. . . . . . . . . . . : 192.168.2.70

3. Mở port nếu Windows Firewall chặn
- PowerShell (Run as Administrator), chỉ cần làm một lần:
- New-NetFirewallRule -DisplayName "RecBole API" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow

4. Kiểm tra từ máy khác trong cùng mạng
- Từ máy khác (hoặc nhờ web team):
- Invoke-WebRequest -Uri "http://192.168.2.70:5000/health"
- 192.168.2.70 là IP của bạn. Nếu trả về JSON {"ok": true, ...}, mọi thứ ok.

5. Cung cấp thông tin cho web team
Base URL: http://<IP_MACHINE_BAN>:5000( của tôi: "http://192.168.2.70:5000")
Các endpoint chính:
- GET /health – kiểm tra trạng thái (trả JSON với ok và model_loaded).
- GET /schema – mô tả format request cho team web.
- POST /user_action – gửi 1 hành động (JSON: user_id, item_id, action_type, timestamp).
- POST /user_actions_batch – gửi nhiều hành động cùng lúc (array JSON).
- GET /recommendations/{user_id}?top_k=10 – lấy danh sách gợi ý.
Nếu bạn đặt API_KEY:
Nếu bạn chưa đặt API_KEY trong .env, các endpoint mở sẵn; nếu muốn bật bảo vệ:

Tạo .env (copy từ .env.example)
     API_KEY=dev-secret     ALLOWED_ORIGINS=http://web-team-domain.com     ```  2. Restart Docker (`docker-compose down`, rồi `docker-compose up -d`)  3. Web team gửi thêm header `Authorization: Bearer dev-secret`.### 6. Theo dõi hoạt động```powershelldocker-compose logs -f recbole-apidocker-compose logs -f recbole-etl```Nhấn `Ctrl+C` để thoát khỏi chế độ xem log.### 7. Lưu ý- Máy bạn phải bật và cùng mạng với web team.- Nếu IP đổi (do modem), lặp lại bước 2 & 5.- Khi xong việc, tắt dịch vụ: `docker-compose down`.Cần thêm lệnh mẫu hay test cụ thể cứ nói nhé.
Restart Docker (docker-compose down, rồi docker-compose up -d)
Web team gửi thêm header Authorization: Bearer dev-secret.

6. Theo dõi hoạt động
docker-compose logs -f recbole-apidocker-compose logs -f recbole-etl
Nhấn Ctrl+C để thoát khỏi chế độ xem log.

7. Lưu ý
Máy bạn phải bật và cùng mạng với web team.
Nếu IP đổi (do modem), lặp lại bước 2 & 5.
Khi xong việc, tắt dịch vụ: docker-compose down.