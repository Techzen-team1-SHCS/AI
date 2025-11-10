import pandas as pd
import json
import os
import sys
import io
from datetime import datetime
from typing import List, Dict

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


ALLOWED_ACTIONS = {'booking', 'share', 'like', 'click'}

def get_action_score(action_type):
    """Chuyển đổi hành động thành điểm số"""
    action_scores = {
        'booking': 1.0,   
        'share': 0.75,    
        'like': 0.5,      
        'click': 0.25     
    }
    return action_scores.get(action_type, 0.0)


def validate_action_data(obj: Dict):
    """Validate dữ liệu hành động người dùng.
    
    Returns:
        (is_valid, error_message)
    """
    # Kiểm tra required fields
    if 'user_id' not in obj:
        return False, "Missing required field: user_id"
    if 'hotel_id' not in obj and 'item_id' not in obj:
        return False, "Missing required field: hotel_id or item_id"
    if 'action_type' not in obj:
        return False, "Missing required field: action_type"
    if 'timestamp' not in obj:
        return False, "Missing required field: timestamp"
    
    # Validate user_id
    user_id = str(obj['user_id']).strip()
    if not user_id:
        return False, "user_id cannot be empty"
    if len(user_id) > 100:  # Reasonable limit
        return False, f"user_id too long (max 100 chars): {user_id[:50]}..."
    
    # Validate hotel_id/item_id
    hotel_id = str(obj.get('hotel_id') or obj.get('item_id', '')).strip()
    if not hotel_id:
        return False, "hotel_id/item_id cannot be empty"
    if len(hotel_id) > 100:
        return False, f"hotel_id too long (max 100 chars): {hotel_id[:50]}..."
    
    # Validate action_type
    action_type = str(obj['action_type']).strip().lower()
    if action_type not in ALLOWED_ACTIONS:
        return False, f"Invalid action_type: {action_type}. Allowed: {sorted(ALLOWED_ACTIONS)}"
    
    # Validate timestamp
    try:
        timestamp = float(obj['timestamp'])
        if timestamp < 0:
            return False, f"Invalid timestamp: {timestamp} (must be >= 0)"
        # Check reasonable range (từ 2000-01-01 đến 2100-01-01)
        if timestamp < 946684800 or timestamp > 4102444800:
            return False, f"Timestamp out of reasonable range: {timestamp}"
    except (ValueError, TypeError):
        return False, f"Invalid timestamp format: {obj['timestamp']}"
    
    return True, ""


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)


def _group_and_append(rows: List[Dict], output_file: str) -> int:
    """Group Max theo (user_id, hotel_id) và append vào output_file. Trả về số bản ghi ghi thêm."""
    if not rows:
        return 0
    
    try:
        df = pd.DataFrame(rows)
        if df.empty:
            return 0
        
        # Normalize hotel_id/item_id
        if 'hotel_id' not in df.columns and 'item_id' in df.columns:
            df['hotel_id'] = df['item_id']
        elif 'hotel_id' not in df.columns:
            raise ValueError("No hotel_id or item_id found in data")
        
        # Normalize action_type to lowercase
        df['action_type'] = df['action_type'].str.strip().str.lower()
        
        df['action_score'] = df['action_type'].apply(get_action_score)
        
        # Group by user_id and hotel_id
        # Lấy action_score cao nhất, và timestamp của hành động có điểm cao nhất đó
        # (nếu có nhiều hành động cùng điểm cao nhất, lấy timestamp mới nhất)
        def get_max_score_and_timestamp(group):
            max_score = group['action_score'].max()
            # Lấy timestamp của hành động có điểm cao nhất
            max_score_rows = group[group['action_score'] == max_score]
            max_timestamp = max_score_rows['timestamp'].max()
            return pd.Series({
                'action_score': max_score,
                'timestamp': max_timestamp
            })
        
        grouped = df.groupby(['user_id', 'hotel_id']).apply(get_max_score_and_timestamp).reset_index()
        grouped = grouped.rename(columns={'action_score': 'action_type'})
        grouped = grouped.sort_values('timestamp')

        _ensure_parent_dir(output_file)
        file_exists = os.path.exists(output_file)
        
        # Write với error handling
        try:
            with open(output_file, 'a', encoding='utf-8') as f:
                if not file_exists:
                    f.write('user_id:token\titem_id:token\taction_type:float\ttimestamp:float\n')
                for _, row in grouped.iterrows():
                    # Validate before writing
                    user_id = str(row['user_id']).strip()
                    hotel_id = str(row['hotel_id']).strip()
                    action_type = float(row['action_type'])
                    timestamp = int(float(row['timestamp']))
                    
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
    print("Loading web data (JSON array)...")
    with open(web_data_file, 'r', encoding='utf-8') as f:
        web_actions = json.load(f)
    print(f"   Found {len(web_actions)} raw actions from web")

    written = _group_and_append(web_actions, output_file)
    print("ETL completed successfully!")
    print(f"   Output: {written} interactions in {output_file}")


def process_log_incremental(log_file: str, archive_file: str, output_file: str, max_retries: int = 3):
    #Đọc user_actions.log (mỗi dòng 1 JSON), append vào archive, xử lý và append vào hotel.inter, rồi truncate log.    
    import time
    
    if not os.path.exists(log_file):
        print(f"No log file found at {log_file}. Nothing to process.")
        return

    # Check if file is empty or only whitespace
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
    
    # Đọc file với retry logic
    for attempt in range(max_retries):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            break
        except IOError as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.5  # Exponential backoff
                print(f"WARNING: File bị lock, đợi {wait_time}s và retry... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"ERROR: Không thể đọc file {log_file} sau {max_retries} lần thử: {e}")
                return
    
    if not lines:
        print("Log is empty. Nothing to process.")
        return

    # Parse JSON lines với validation
    for line_num, ln in enumerate(lines, 1):
        ln_stripped = ln.strip()
        if not ln_stripped:
            continue
        
        # Remove literal \n characters that might be in the string
        ln_stripped = ln_stripped.replace('\\n', '').replace('\n', '')
        
        try:
            obj = json.loads(ln_stripped)
            
            # Normalize keys (hotel_id vs item_id)
            if 'hotel_id' not in obj and 'item_id' in obj:
                obj['hotel_id'] = obj['item_id']
            
            # Validate dữ liệu
            is_valid, error_msg = validate_action_data(obj)
            if not is_valid:
                print(f"WARNING: Line {line_num} invalid - {error_msg}: {ln_stripped[:80]}...")
                invalid_count += 1
                # Vẫn lưu vào archive để audit
                processed_lines.append(ln)
                continue
            
            rows.append(obj)
            processed_lines.append(ln)  # Keep original line for archive
            
        except json.JSONDecodeError as e:
            print(f"WARNING: Line {line_num} - Malformed JSON: {e}: {ln_stripped[:80]}...")
            invalid_count += 1
            # Vẫn lưu vào archive để audit
            processed_lines.append(ln)
            continue
        except Exception as e:
            print(f"WARNING: Line {line_num} - Error processing: {e}: {ln_stripped[:80]}...")
            invalid_count += 1
            processed_lines.append(ln)
            continue

    if not rows:
        print("No valid JSON lines found in log file. Nothing to process.")
        if invalid_count > 0:
            print(f"   Skipped {invalid_count} invalid lines")
        return

    # Append raw lines to archive (for audit) before truncating
    try:
        _ensure_parent_dir(archive_file)
        with open(archive_file, 'a', encoding='utf-8') as af:
            for ln in processed_lines:
                af.write(ln if ln.endswith("\n") else (ln + "\n"))
    except IOError as e:
        print(f"ERROR: Không thể ghi vào archive file {archive_file}: {e}")
        # Không nên tiếp tục nếu không archive được
        return

    # Process and write interactions
    try:
        written = _group_and_append(rows, output_file)
    except Exception as e:
        print(f"ERROR: Không thể xử lý và ghi dữ liệu: {e}")
        # Không truncate log nếu xử lý thất bại
        return

    # Truncate original log (clear all content) - chỉ khi đã xử lý thành công
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.truncate(0)
    except IOError as e:
        print(f"WARNING: Không thể truncate log file {log_file}: {e}")
        print("   Dữ liệu đã được xử lý nhưng log file chưa được xóa. Có thể bị xử lý trùng lặp lần sau.")

    print("ETL (incremental) completed!")
    print(f"   Processed: {len(rows)} valid actions from {len(processed_lines)} lines")
    if invalid_count > 0:
        print(f"   Skipped: {invalid_count} invalid lines")
    print(f"   Archived: {len(processed_lines)} lines -> {archive_file}")
    print(f"   Output: {written} interactions -> {output_file}")


def create_sample_web_data():
    """Tạo dữ liệu mẫu từ web để test"""
    sample_data = [
        # User u1 với hotel h1 - có nhiều hành động
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

        # User u3 với hotel h2 - có share
        {"user_id": "u3", "hotel_id": "h2", "action_type": "click", "timestamp": 1695408000},
        {"user_id": "u3", "hotel_id": "h2", "action_type": "share", "timestamp": 1695409000},
    ]

    path = os.path.join(BASE_DIR, 'sample_web_actions.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)

    print("Created sample web data:", path)
    return path


if __name__ == "__main__":
    # Resolve defaults relative to repo dir
    default_log = os.path.join(BASE_DIR, 'user_actions.log')
    default_archive = os.path.join(BASE_DIR, 'user_actions.archive.log')
    default_inter = os.path.join(BASE_DIR, 'dataset', 'hotel', 'hotel.inter')

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

    # Always try to process log file first (this is the main workflow)
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
