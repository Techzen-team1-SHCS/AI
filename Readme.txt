CMD :

1.Cài môi trường
```bash
python -m venv recbole-env
recbole-env\Scripts\activate
pip install -r requirements.txt

2.Kiểm tra Recbole
python -c "import recbole; print(recbole.__version__)"

Hoặc

pip show recbole

TERMINAL(POWERSHELL) :

🧩 Bước 1: Mở PowerShell

Mở thư mục dự án (nơi có requirements.txt), ví dụ:

G:\AI_Project\InstallRecbole


Sau đó Shift + chuột phải → chọn "Open PowerShell window here"
(hoặc gõ đường dẫn này trên thanh địa chỉ của File Explorer và bấm Enter)
⚙️ Bước 2: Kích hoạt môi trường ảo

Nhập lệnh sau:

G:\AI_Project\recbole-env\Scripts\Activate.ps1


Nếu PowerShell báo lỗi như:

running scripts is disabled on this system

thì chạy lệnh này (chỉ cần làm 1 lần):

Set-ExecutionPolicy RemoteSigned -Scope CurrentUser


Sau đó chạy lại lệnh activate phía trên.

Khi thành công, bạn sẽ thấy prompt đổi như sau:

(recobole-env) PS G:\AI_Project\InstallRecbole>

📦 Bước 3: Cài đặt từ requirements.txt

Khi môi trường đã được kích hoạt, chạy:

pip install -r requirements.txt


Python sẽ tự động cài tất cả các thư viện cần thiết cho RecBole (như PyTorch, numpy, pandas, tqdm,...).

✅ Bước 4: Kiểm tra
Sau khi cài xong, kiểm tra RecBole đã sẵn sàng:

python -c "import recbole, torch; print('RecBole:', recbole.__version__, '| Torch:', torch.__version__, '| CUDA:', torch.cuda.is_available())"

Hiển thị là :RecBole: 1.2.1 | Torch: 2.8.0+cpu | CUDA: False 
