# Script tạo Docker package để gửi cho team
# Chạy script này: .\create_docker_package.ps1

Write-Host "===========================================" -ForegroundColor Green
Write-Host "TẠO DOCKER PACKAGE CHO TEAM" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

# Kiểm tra xem đang ở thư mục đúng chưa
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "ERROR: Không tìm thấy docker-compose.yml" -ForegroundColor Red
    Write-Host "Vui lòng chạy script này trong thư mục gốc của dự án" -ForegroundColor Red
    exit 1
}

# Tạo thư mục tạm
$tempDir = "docker_package_temp"
$zipFile = "RecBole-Docker-Package.zip"

Write-Host "Bước 1: Tạo thư mục tạm..." -ForegroundColor Yellow
if (Test-Path $tempDir) {
    Remove-Item -Path $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

Write-Host "Bước 2: Copy các file cần thiết..." -ForegroundColor Yellow

# Danh sách file và thư mục cần copy
$filesToCopy = @(
    "api_server.py",
    "inference.py",
    "etl_web_to_hotel_inter.py",
    "retrain_model.py",
    "retrain_scheduler.py",
    "run_recbole.py",
    "Dockerfile",
    "docker-compose.yml",
    "requirements.txt",
    "deepfm_config.yaml",
    ".env.example",
    ".dockerignore",
    "README_FOR_TEAM.md",
    "HUONG_DAN_BUILD_DOCKER.md"
)

# Copy các file
foreach ($file in $filesToCopy) {
    if (Test-Path $file) {
        Copy-Item -Path $file -Destination $tempDir -Force
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file (không tìm thấy)" -ForegroundColor Red
    }
}

# Copy thư mục dataset
Write-Host "Bước 3: Copy thư mục dataset..." -ForegroundColor Yellow
if (Test-Path "dataset") {
    Copy-Item -Path "dataset" -Destination $tempDir -Recurse -Force
    Write-Host "  ✓ dataset/" -ForegroundColor Green
} else {
    Write-Host "  ✗ dataset/ (không tìm thấy)" -ForegroundColor Red
}

# Copy thư mục saved (model files)
Write-Host "Bước 4: Copy thư mục saved (model files)..." -ForegroundColor Yellow
if (Test-Path "saved") {
    # Tạo thư mục saved trong temp
    New-Item -ItemType Directory -Path "$tempDir\saved" -Force | Out-Null
    
    # Copy các file .pth (không copy backups)
    $pthFiles = Get-ChildItem -Path "saved" -Filter "*.pth" -File
    if ($pthFiles.Count -gt 0) {
        foreach ($file in $pthFiles) {
            Copy-Item -Path $file.FullName -Destination "$tempDir\saved\" -Force
            Write-Host "  ✓ saved/$($file.Name)" -ForegroundColor Green
        }
    } else {
        Write-Host "  ⚠ Không tìm thấy file .pth trong saved/" -ForegroundColor Yellow
        Write-Host "    Lưu ý: Team cần có model file để chạy API" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ saved/ (không tìm thấy)" -ForegroundColor Red
    Write-Host "    CẢNH BÁO: Không có model file! Team sẽ không thể chạy API." -ForegroundColor Red
}

# Copy thư mục recbole (code)
Write-Host "Bước 5: Copy thư mục recbole..." -ForegroundColor Yellow
if (Test-Path "recbole") {
    Copy-Item -Path "recbole" -Destination $tempDir -Recurse -Force
    Write-Host "  ✓ recbole/" -ForegroundColor Green
} else {
    Write-Host "  ✗ recbole/ (không tìm thấy)" -ForegroundColor Red
}

# Tạo thư mục data (trống)
Write-Host "Bước 6: Tạo thư mục data (trống)..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "$tempDir\data" -Force | Out-Null
Write-Host "  ✓ data/ (đã tạo)" -ForegroundColor Green

# Tạo file .gitkeep trong data
New-Item -ItemType File -Path "$tempDir\data\.gitkeep" -Force | Out-Null

# Tạo file ZIP
Write-Host "Bước 7: Tạo file ZIP..." -ForegroundColor Yellow
if (Test-Path $zipFile) {
    Remove-Item -Path $zipFile -Force
    Write-Host "  Đã xóa file ZIP cũ" -ForegroundColor Yellow
}

Compress-Archive -Path "$tempDir\*" -DestinationPath $zipFile -Force
Write-Host "  ✓ Đã tạo file ZIP: $zipFile" -ForegroundColor Green

# Xóa thư mục tạm
Write-Host "Bước 8: Dọn dẹp..." -ForegroundColor Yellow
Remove-Item -Path $tempDir -Recurse -Force
Write-Host "  ✓ Đã xóa thư mục tạm" -ForegroundColor Green

# Hiển thị kết quả
Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host "HOÀN THÀNH!" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""
Write-Host "File ZIP đã được tạo: $zipFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Kích thước file:" -ForegroundColor Yellow
$fileSize = (Get-Item $zipFile).Length / 1MB
Write-Host "  $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
Write-Host ""
Write-Host "Bây giờ bạn có thể gửi file ZIP này cho team." -ForegroundColor Green
Write-Host ""

# Kiểm tra xem có model file không
$pthFiles = Get-ChildItem -Path "saved" -Filter "*.pth" -File -ErrorAction SilentlyContinue
if (-not $pthFiles -or $pthFiles.Count -eq 0) {
    Write-Host "⚠ CẢNH BÁO: Không tìm thấy model file (.pth) trong thư mục saved/" -ForegroundColor Red
    Write-Host "  Team sẽ không thể chạy API mà không có model file." -ForegroundColor Red
    Write-Host "  Vui lòng đảm bảo có ít nhất 1 file .pth trong thư mục saved/ trước khi gửi cho team." -ForegroundColor Red
    Write-Host ""
}

Write-Host "Nhấn phím bất kỳ để thoát..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

