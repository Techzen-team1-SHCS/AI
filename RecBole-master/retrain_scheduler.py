"""
Retraining Scheduler - Chạy retraining tự động mỗi ngày 1 lần.

Script này chạy retrain_model.py vào thời gian được cấu hình (mặc định: 2h sáng).
Scheduler sẽ:
1. Kiểm tra thời gian hiện tại
2. Chạy retraining khi đến giờ đã cấu hình
3. Chỉ chạy 1 lần mỗi ngày
4. Tiếp tục chạy và chờ đến ngày hôm sau

Có thể cấu hình thời gian retraining qua environment variables:
- RETRAIN_HOUR: Giờ chạy (0-23), mặc định: 2
- RETRAIN_MINUTE: Phút chạy (0-59), mặc định: 0
- RETRAIN_CHECK_INTERVAL: Khoảng thời gian kiểm tra (giây), mặc định: 3600 (1 giờ)
"""
import os
import sys
import time
from datetime import datetime, time as dt_time, timedelta
import io

# Fix encoding cho Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Import retrain script
from retrain_model import main as retrain_main


def should_run_retrain(retrain_hour: int = 2, retrain_minute: int = 0) -> bool:
    """
    Kiểm tra xem có nên chạy retraining không dựa trên thời gian.
    
    Logic:
    - Lấy thời gian retraining hôm nay
    - Nếu thời gian hiện tại >= thời gian retraining hôm nay → chạy
    
    Args:
        retrain_hour: Giờ chạy retraining (0-23), mặc định: 2
        retrain_minute: Phút chạy retraining (0-59), mặc định: 0
    
    Returns:
        True nếu đã đến giờ retraining, False nếu chưa
    """
    now = datetime.now()
    retrain_time = dt_time(retrain_hour, retrain_minute)
    
    # Lấy thời gian retraining hôm nay
    today_retrain = datetime.combine(now.date(), retrain_time)
    
    # Nếu đã qua giờ retraining hôm nay, chạy ngay
    if now >= today_retrain:
        return True
    
    return False


def run_scheduler(retrain_hour: int = 2, retrain_minute: int = 0, check_interval: int = 3600):
    """
    Chạy scheduler để retrain model định kỳ.
    
    Scheduler chạy trong vòng lặp vô hạn:
    1. Kiểm tra thời gian hiện tại
    2. Nếu đến giờ retraining và chưa chạy hôm nay → chạy retraining
    3. Nếu chưa đến giờ → chờ đến lần kiểm tra tiếp theo
    4. Lặp lại
    
    Args:
        retrain_hour: Giờ chạy retraining (0-23), mặc định 2h sáng
        retrain_minute: Phút chạy retraining (0-59), mặc định 0
        check_interval: Khoảng thời gian kiểm tra (giây), mặc định 1 giờ (3600s)
    """
    print("=" * 80)
    print("RETRAINING SCHEDULER - DEEPFM HOTEL RECOMMENDATION")
    print("=" * 80)
    print(f"[INFO] Scheduler khởi động lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[INFO] Thời gian retraining: {retrain_hour:02d}:{retrain_minute:02d} mỗi ngày")
    print(f"[INFO] Kiểm tra mỗi {check_interval} giây")
    print()
    
    # Lưu ngày retrain cuối cùng để đảm bảo chỉ chạy 1 lần mỗi ngày
    last_retrain_date = None
    
    # Vòng lặp chính của scheduler
    while True:
        try:
            now = datetime.now()
            current_date = now.date()
            
            # Kiểm tra xem có nên chạy retraining không
            if should_run_retrain(retrain_hour, retrain_minute):
                # Chỉ chạy 1 lần mỗi ngày (kiểm tra ngày để tránh chạy nhiều lần)
                if last_retrain_date != current_date:
                    print(f"[INFO] Đã đến giờ retraining: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                    print()
                    
                    try:
                        # Chạy retraining pipeline
                        retrain_main()
                        # Cập nhật ngày retrain cuối cùng
                        last_retrain_date = current_date
                        print(f"[SUCCESS] Retraining hoàn thành lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    except Exception as e:
                        print(f"[ERROR] Lỗi khi chạy retraining: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    print()
                    print(f"[INFO] Scheduler tiếp tục chạy, chờ đến ngày mai...")
                    print()
            else:
                # Chưa đến giờ retraining
                # Tính thời gian retraining tiếp theo
                next_retrain = datetime.combine(current_date, dt_time(retrain_hour, retrain_minute))
                if now > next_retrain:
                    # Đã qua giờ retraining hôm nay, chờ đến ngày mai
                    next_retrain = datetime.combine(
                        (current_date + timedelta(days=1)), 
                        dt_time(retrain_hour, retrain_minute)
                    )
                
                # Tính số giây cần chờ
                wait_seconds = (next_retrain - now).total_seconds()
                # Giới hạn wait_seconds không quá check_interval
                if wait_seconds > check_interval:
                    wait_seconds = check_interval
                
                # Chờ đến lần kiểm tra tiếp theo
                if wait_seconds > 0:
                    time.sleep(min(wait_seconds, check_interval))
            
            # Sleep một chút trước khi kiểm tra lại
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            # Người dùng nhấn Ctrl+C → dừng scheduler
            print("\n[INFO] Scheduler dừng bởi người dùng")
            break
        except Exception as e:
            # Xử lý lỗi không mong đợi
            print(f"[ERROR] Lỗi trong scheduler: {e}")
            import traceback
            traceback.print_exc()
            # Chờ một chút trước khi thử lại (tránh loop lỗi liên tục)
            time.sleep(60)


if __name__ == "__main__":
    # Lấy thời gian retraining từ environment variable (mặc định: 2h sáng)
    retrain_hour = int(os.getenv("RETRAIN_HOUR", "2"))
    retrain_minute = int(os.getenv("RETRAIN_MINUTE", "0"))
    check_interval = int(os.getenv("RETRAIN_CHECK_INTERVAL", "3600"))  # 1 giờ
    
    # Chạy scheduler
    run_scheduler(retrain_hour, retrain_minute, check_interval)
