"""
ETL Module: Xử lý dữ liệu hành động người dùng từ web và chuyển đổi sang định dạng RecBole.

Module này thực hiện:
1. Đọc dữ liệu hành động từ web (JSON format)
2. Validate và normalize dữ liệu
3. Group và aggregate các hành động trùng lặp (lấy action có điểm cao nhất)
4. Ghi vào file hotel.inter theo định dạng RecBole
5. Hỗ trợ xử lý incremental từ log file với retry mechanism
"""
import pandas as pd
import json
import os
import sys
import io
from datetime import datetime
from typing import List, Dict

# Fix encoding cho Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Đường dẫn thư mục gốc của project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Danh sách các hành động được phép
ALLOWED_ACTIONS = {'booking', 'share', 'like', 'click'}


def get_action_score(action_type):
    """
    Chuyển đổi loại hành động thành điểm số tương ứng.
    
    Điểm số phản ánh mức độ quan tâm của người dùng:
    - Booking: Quan tâm cao nhất (1.0)
    - Share: Quan tâm cao (0.75)
    - Like: Quan tâm trung bình (0.5)
    - Click: Quan tâm thấp (0.25)
    
    Args:
        action_type: Loại hành động (string)
    
    Returns:
        Điểm số từ 0.0 đến 1.0, hoặc 0.0 nếu không hợp lệ
    """
    action_scores = {
        'booking': 1.0,   # Hành động quan trọng nhất
        'share': 0.75,   # Chia sẻ thể hiện sự quan tâm cao
        'like': 0.5,     # Like thể hiện sự quan tâm trung bình
        'click': 0.25    # Click chỉ là tương tác nhẹ
    }
    return action_scores.get(action_type, 0.0)


def validate_action_data(obj: Dict):
    """
    Validate dữ liệu hành động người dùng trước khi xử lý.
    
    Kiểm tra:
    - Các trường bắt buộc có tồn tại không
    - Định dạng và giá trị hợp lệ
    - Giới hạn độ dài để tránh dữ liệu bất thường
    
    Args:
        obj: Dictionary chứa dữ liệu hành động
    
    Returns:
        Tuple (is_valid: bool, error_message: str)
        - is_valid: True nếu dữ liệu hợp lệ, False nếu không
        - error_message: Thông báo lỗi nếu không hợp lệ, rỗng nếu hợp lệ
    """
    # Kiểm tra các trường bắt buộc
    if 'user_id' not in obj:
        return False, "Missing required field: user_id"
    if 'hotel_id' not in obj and 'item_id' not in obj:
        return False, "Missing required field: hotel_id or item_id"
    if 'action_type' not in obj:
        return False, "Missing required field: action_type"
    if 'timestamp' not in obj:
        return False, "Missing required field: timestamp"
    
    # Validate user_id: không được rỗng và có độ dài hợp lý
    user_id = str(obj['user_id']).strip()
    if not user_id:
        return False, "user_id cannot be empty"
    if len(user_id) > 100:  # Giới hạn hợp lý để tránh dữ liệu bất thường
        return False, f"user_id too long (max 100 chars): {user_id[:50]}..."
    
    # Validate hotel_id/item_id: hỗ trợ cả hai tên trường
    hotel_id = str(obj.get('hotel_id') or obj.get('item_id', '')).strip()
    if not hotel_id:
        return False, "hotel_id/item_id cannot be empty"
    if len(hotel_id) > 100:
        return False, f"hotel_id too long (max 100 chars): {hotel_id[:50]}..."
    
    # Validate action_type: phải nằm trong danh sách cho phép
    action_type = str(obj['action_type']).strip().lower()
    if action_type not in ALLOWED_ACTIONS:
        return False, f"Invalid action_type: {action_type}. Allowed: {sorted(ALLOWED_ACTIONS)}"
    
    # Validate timestamp: phải là số dương và trong khoảng hợp lý
    try:
        timestamp = float(obj['timestamp'])
        if timestamp < 0:
            return False, f"Invalid timestamp: {timestamp} (must be >= 0)"
        # Kiểm tra timestamp trong khoảng hợp lý (từ 2000-01-01 đến 2100-01-01)
        # 946684800 = 2000-01-01 00:00:00 UTC
        # 4102444800 = 2100-01-01 00:00:00 UTC
        if timestamp < 946684800 or timestamp > 4102444800:
            return False, f"Timestamp out of reasonable range: {timestamp}"
    except (ValueError, TypeError):
        return False, f"Invalid timestamp format: {obj['timestamp']}"
    
    return True, ""


def _ensure_parent_dir(path: str) -> None:
    """
    Đảm bảo thư mục cha của file tồn tại, tạo mới nếu chưa có.
    
    Args:
        path: Đường dẫn file cần kiểm tra
    """
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)


def _group_and_append(rows: List[Dict], output_file: str) -> int:
    """
    Nhóm các hành động theo (user_id, hotel_id) và ghi vào file output.
    
    Logic xử lý:
    1. Normalize dữ liệu (hotel_id/item_id, lowercase action_type)
    2. Tính điểm số cho mỗi hành động
    3. Group theo (user_id, hotel_id) và lấy hành động có điểm cao nhất
    4. Nếu có nhiều hành động cùng điểm, lấy timestamp mới nhất
    5. Ghi vào file theo định dạng RecBole (TSV với header)
    
    Args:
        rows: Danh sách các dictionary chứa dữ liệu hành động
        output_file: Đường dẫn file output (hotel.inter)
    
    Returns:
        Số lượng bản ghi đã ghi vào file
    
    Raises:
        ValueError: Nếu dữ liệu không hợp lệ
        IOError: Nếu không thể ghi file
    """
    if not rows:
        return 0
    
    try:
        # Chuyển đổi list dicts thành DataFrame để xử lý dễ dàng
        df = pd.DataFrame(rows)
        if df.empty:
            return 0
        
        # Normalize: hỗ trợ cả hotel_id và item_id
        if 'hotel_id' not in df.columns and 'item_id' in df.columns:
            df['hotel_id'] = df['item_id']
        elif 'hotel_id' not in df.columns:
            raise ValueError("No hotel_id or item_id found in data")
        
        # Convert về string trước để tránh pandas tự động convert thành float
        # (sẽ convert về int khi ghi file)
        df['user_id'] = df['user_id'].astype(str).str.strip()
        df['hotel_id'] = df['hotel_id'].astype(str).str.strip()
        
        # Normalize action_type: lowercase và trim whitespace
        df['action_type'] = df['action_type'].str.strip().str.lower()
        
        # Tính điểm số cho mỗi hành động
        df['action_score'] = df['action_type'].apply(get_action_score)
        
        # Hàm helper để lấy điểm cao nhất và timestamp tương ứng
        def get_max_score_and_timestamp(group):
            """
            Lấy điểm số cao nhất trong group và timestamp của hành động đó.
            Nếu có nhiều hành động cùng điểm, lấy timestamp mới nhất.
            """
            max_score = group['action_score'].max()
            # Lọc các hành động có điểm cao nhất
            max_score_rows = group[group['action_score'] == max_score]
            # Lấy timestamp mới nhất trong số đó
            max_timestamp = max_score_rows['timestamp'].max()
            return pd.Series({
                'action_score': max_score,
                'timestamp': max_timestamp
            })
        
        # Group theo (user_id, hotel_id) và áp dụng hàm trên
        # group_keys=False để tương thích với pandas < 2.0
        grouped = df.groupby(['user_id', 'hotel_id'], group_keys=False).apply(
            get_max_score_and_timestamp
        ).reset_index()
        
        # Đổi tên cột action_score thành action_type (vì sẽ ghi điểm số vào cột này)
        grouped = grouped.rename(columns={'action_score': 'action_type'})
        
        # Sắp xếp theo timestamp để đảm bảo thứ tự thời gian
        grouped = grouped.sort_values('timestamp')
        
        # Đảm bảo thư mục output tồn tại
        _ensure_parent_dir(output_file)
        file_exists = os.path.exists(output_file)
        
        # Ghi dữ liệu vào file với error handling
        try:
            with open(output_file, 'a', encoding='utf-8') as f:
                # Ghi header nếu file mới
                if not file_exists:
                    f.write('user_id:token\titem_id:token\taction_type:float\ttimestamp:float\n')
                
                # Ghi từng dòng dữ liệu
                for _, row in grouped.iterrows():
                    # Convert user_id về int (xử lý trường hợp pandas tạo .0)
                    try:
                        user_id_str = str(row['user_id']).strip()
                        # Loại bỏ .0 nếu có (từ float khi pandas groupby)
                        if user_id_str.endswith('.0'):
                            user_id_str = user_id_str[:-2]
                        user_id = int(float(user_id_str))
                    except (ValueError, TypeError):
                        # Fallback: giữ nguyên string nếu không convert được
                        user_id = str(row['user_id']).strip()
                    
                    # Convert hotel_id về int (tương tự user_id)
                    try:
                        hotel_id_str = str(row['hotel_id']).strip()
                        if hotel_id_str.endswith('.0'):
                            hotel_id_str = hotel_id_str[:-2]
                        hotel_id = int(float(hotel_id_str))
                    except (ValueError, TypeError):
                        hotel_id = str(row['hotel_id']).strip()
                    
                    # Convert action_type (điểm số) và timestamp
                    action_type = float(row['action_type'])
                    timestamp = int(float(row['timestamp']))
                    
                    # Ghi ra file theo định dạng TSV (Tab-Separated Values)
                    # Format: user_id \t hotel_id \t action_score \t timestamp
                    f.write(f"{user_id}\t{hotel_id}\t{action_type}\t{timestamp}\n")
            
            return len(grouped)
        except IOError as e:
            print(f"ERROR: Không thể ghi vào file {output_file}: {e}")
            raise
        except Exception as e:
            print(f"ERROR: Lỗi khi ghi dữ liệu: {e}")
            raise
            
    except Exception as e:
        print(f"ERROR: Lỗi khi xử lý dữ liệu: {e}")
        raise


def process_web_actions_to_hotel_inter(web_data_file, output_file):
    """
    Xử lý dữ liệu hành động từ file JSON array và ghi vào hotel.inter.
    
    Hàm này dùng cho batch processing từ file JSON chứa array các hành động.
    
    Args:
        web_data_file: Đường dẫn file JSON chứa array các hành động
        output_file: Đường dẫn file output (hotel.inter)
    """
    print("Loading web data (JSON array)...")
    with open(web_data_file, 'r', encoding='utf-8') as f:
        web_actions = json.load(f)
    print(f"   Found {len(web_actions)} raw actions from web")

    # Xử lý và ghi vào file
    written = _group_and_append(web_actions, output_file)
    print("ETL completed successfully!")
    print(f"   Output: {written} interactions in {output_file}")


def process_log_incremental(log_file: str, archive_file: str, output_file: str, max_retries: int = 3):
    """
    Xử lý incremental từ log file (line-delimited JSON).
    
    Quy trình:
    1. Đọc user_actions.log (mỗi dòng là 1 JSON object)
    2. Validate và parse từng dòng
    3. Append vào archive file (để audit)
    4. Xử lý và append vào hotel.inter
    5. Truncate log file (xóa nội dung đã xử lý)
    
    Hỗ trợ retry mechanism để xử lý trường hợp file bị lock.
    
    Args:
        log_file: Đường dẫn file log (user_actions.log)
        archive_file: Đường dẫn file archive (user_actions.archive.log)
        output_file: Đường dẫn file output (hotel.inter)
        max_retries: Số lần retry tối đa khi file bị lock (default: 3)
    """
    import time
    
    # Kiểm tra file log có tồn tại không
    if not os.path.exists(log_file):
        print(f"No log file found at {log_file}. Nothing to process.")
        return

    # Kiểm tra file có rỗng không
    try:
        file_size = os.path.getsize(log_file)
        if file_size == 0:
            print("Log is empty. Nothing to process.")
            return
    except OSError as e:
        print(f"ERROR: Không thể đọc file {log_file}: {e}")
        return

    print(f"Loading line-delimited JSON from {log_file}...")
    rows: List[Dict] = []
    processed_lines: List[str] = []
    invalid_count = 0
    
    # Đọc file với retry logic (xử lý trường hợp file đang bị lock bởi process khác)
    for attempt in range(max_retries):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            break
        except IOError as e:
            if attempt < max_retries - 1:
                # Exponential backoff: đợi lâu hơn mỗi lần retry
                wait_time = (attempt + 1) * 0.5
                print(f"WARNING: File bị lock, đợi {wait_time}s và retry... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"ERROR: Không thể đọc file {log_file} sau {max_retries} lần thử: {e}")
                return
    
    if not lines:
        print("Log is empty. Nothing to process.")
        return

    # Parse từng dòng JSON với validation
    for line_num, ln in enumerate(lines, 1):
        ln_stripped = ln.strip()
        if not ln_stripped:
            continue
        
        # Loại bỏ ký tự newline literal có thể có trong string
        ln_stripped = ln_stripped.replace('\\n', '').replace('\n', '')
        
        try:
            # Parse JSON từ dòng
            obj = json.loads(ln_stripped)
            
            # Normalize keys: hỗ trợ cả hotel_id và item_id
            if 'hotel_id' not in obj and 'item_id' in obj:
                obj['hotel_id'] = obj['item_id']
            
            # Validate dữ liệu trước khi xử lý
            is_valid, error_msg = validate_action_data(obj)
            if not is_valid:
                print(f"WARNING: Line {line_num} invalid - {error_msg}: {ln_stripped[:80]}...")
                invalid_count += 1
                # Vẫn lưu vào archive để audit (kể cả dữ liệu invalid)
                processed_lines.append(ln)
                continue
            
            # Dữ liệu hợp lệ, thêm vào danh sách xử lý
            rows.append(obj)
            processed_lines.append(ln)  # Lưu dòng gốc để archive
            
        except json.JSONDecodeError as e:
            # Dòng không phải JSON hợp lệ
            print(f"WARNING: Line {line_num} - Malformed JSON: {e}: {ln_stripped[:80]}...")
            invalid_count += 1
            processed_lines.append(ln)  # Vẫn archive để audit
            continue
        except Exception as e:
            # Lỗi khác khi xử lý
            print(f"WARNING: Line {line_num} - Error processing: {e}: {ln_stripped[:80]}...")
            invalid_count += 1
            processed_lines.append(ln)
            continue

    # Kiểm tra có dữ liệu hợp lệ không
    if not rows:
        print("No valid JSON lines found in log file. Nothing to process.")
        if invalid_count > 0:
            print(f"   Skipped {invalid_count} invalid lines")
        return

    # Bước 1: Append tất cả dòng (kể cả invalid) vào archive trước khi truncate
    # Điều này đảm bảo không mất dữ liệu nếu có lỗi xảy ra sau đó
    try:
        _ensure_parent_dir(archive_file)
        with open(archive_file, 'a', encoding='utf-8') as af:
            for ln in processed_lines:
                # Đảm bảo mỗi dòng kết thúc bằng newline
                af.write(ln if ln.endswith("\n") else (ln + "\n"))
    except IOError as e:
        print(f"ERROR: Không thể ghi vào archive file {archive_file}: {e}")
        # Không tiếp tục nếu không archive được (để tránh mất dữ liệu)
        return

    # Bước 2: Xử lý và ghi interactions vào hotel.inter
    try:
        written = _group_and_append(rows, output_file)
    except Exception as e:
        print(f"ERROR: Không thể xử lý và ghi dữ liệu: {e}")
        # Không truncate log nếu xử lý thất bại (để có thể retry sau)
        return

    # Bước 3: Truncate log file (xóa nội dung) - chỉ khi đã xử lý thành công
    # Điều này đảm bảo dữ liệu đã được lưu an toàn trước khi xóa
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.truncate(0)
    except IOError as e:
        print(f"WARNING: Không thể truncate log file {log_file}: {e}")
        print("   Dữ liệu đã được xử lý nhưng log file chưa được xóa. Có thể bị xử lý trùng lặp lần sau.")

    # In kết quả
    print("ETL (incremental) completed!")
    print(f"   Processed: {len(rows)} valid actions from {len(processed_lines)} lines")
    if invalid_count > 0:
        print(f"   Skipped: {invalid_count} invalid lines")
    print(f"   Archived: {len(processed_lines)} lines -> {archive_file}")
    print(f"   Output: {written} interactions -> {output_file}")


def create_sample_web_data():
    """
    Tạo dữ liệu mẫu từ web để test ETL pipeline.
    
    Returns:
        Đường dẫn file JSON chứa dữ liệu mẫu
    """
    # Dữ liệu mẫu với các kịch bản khác nhau
    sample_data = [
        # User u1 với hotel h1 - có nhiều hành động (từ click đến booking)
        {"user_id": "u1", "hotel_id": "h1", "action_type": "click", "timestamp": 1695400000},
        {"user_id": "u1", "hotel_id": "h1", "action_type": "like", "timestamp": 1695401000},
        {"user_id": "u1", "hotel_id": "h1", "action_type": "share", "timestamp": 1695402000},
        {"user_id": "u1", "hotel_id": "h1", "action_type": "booking", "timestamp": 1695403000},

        # User u1 với hotel h2 - chỉ có click
        {"user_id": "u1", "hotel_id": "h2", "action_type": "click", "timestamp": 1695404000},

        # User u2 với hotel h1 - có like và booking
        {"user_id": "u2", "hotel_id": "h1", "action_type": "like", "timestamp": 1695405000},
        {"user_id": "u2", "hotel_id": "h1", "action_type": "booking", "timestamp": 1695406000},

        # User u2 với hotel h3 - chỉ có click
        {"user_id": "u2", "hotel_id": "h3", "action_type": "click", "timestamp": 1695407000},

        # User u3 với hotel h2 - có click và share
        {"user_id": "u3", "hotel_id": "h2", "action_type": "click", "timestamp": 1695408000},
        {"user_id": "u3", "hotel_id": "h2", "action_type": "share", "timestamp": 1695409000},
    ]

    # Ghi vào file
    path = os.path.join(BASE_DIR, 'sample_web_actions.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)

    print("Created sample web data:", path)
    return path


if __name__ == "__main__":
    # Resolve đường dẫn mặc định (relative to repo directory)
    default_log = os.path.join(BASE_DIR, 'data', 'user_actions.log')
    default_archive = os.path.join(BASE_DIR, 'data', 'user_actions.archive.log')
    default_inter = os.path.join(BASE_DIR, 'dataset', 'hotel', 'hotel.inter')

    # Lấy đường dẫn từ environment variable hoặc dùng mặc định
    log_path = os.getenv('USER_ACTION_LOG_FILE', default_log)
    archive_path = os.getenv('USER_ACTION_ARCHIVE_FILE', default_archive)
    inter_path = os.getenv('HOTEL_INTER_FILE', default_inter)

    print("=" * 70)
    print("ETL: Processing user actions from web")
    print("=" * 70)
    print(f"Log file: {log_path}")
    print(f"Archive file: {archive_path}")
    print(f"Output file: {inter_path}")
    print("-" * 70)

    # Luôn ưu tiên xử lý log file (workflow chính)
    if os.path.exists(log_path):
        file_size = os.path.getsize(log_path)
        if file_size > 0:
            print(f"Found log file with {file_size} bytes. Processing...")
            process_log_incremental(log_path, archive_path, inter_path)
        else:
            print("Log file exists but is empty. Waiting for web data...")
    else:
        print("Log file not found. Waiting for web data...")
        print("(Web should write to user_actions.log periodically)")

    print("\n" + "=" * 70)
    print("ETL completed!")
    print("=" * 70)
