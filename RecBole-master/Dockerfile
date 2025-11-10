# Multi-stage Dockerfile for RecBole Hotel Recommendation API
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/dataset/hotel /app/data /app/log /app/log_tensorboard /app/saved

# Set Python to not buffer output (for better logging in Docker)
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 5000

# Default command (overridden by docker-compose)
CMD ["python", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "5000"]

