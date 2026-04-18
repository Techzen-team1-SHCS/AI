FROM python:3.11-slim-bullseye

# Đặt thư mục làm việc
WORKDIR /app

# Khai báo timezone
ENV TZ=Asia/Ho_Chi_Minh

# Cài đặt các gói biên dịch môi trường C++ cho cmdstan (Prophet)
# Prophet yêu cầu build-essential và curl để tải pre-built binary
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cài đặt CmdStanPy binary ngầm định cho hệ điều hành
ENV CMDSTAN_DIR=/root/.cmdstan
RUN python -c "import cmdstanpy; cmdstanpy.install_cmdstan()"

# Copy toàn bộ pipeline phân tích AI
COPY ai_service/ ./ai_service/

# Thư mục output cho file csv
RUN mkdir -p outputs

# Lệnh khởi động Container
CMD ["uvicorn", "ai_service.api:app", "--host", "0.0.0.0", "--port", "8000"]
