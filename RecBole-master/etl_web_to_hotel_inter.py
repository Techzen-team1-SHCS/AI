"""
ETL Script: Chuyển đổi dữ liệu hành vi từ Web sang hotel.inter
- Extract: Lấy dữ liệu hành vi từ web/database (JSON format)
- Transform: Chuyển đổi hành động thành điểm số và group theo Max strategy
- Load: Append dữ liệu mới vào file hotel.inter (không ghi đè dữ liệu cũ)

Thuật toán xử lý:
1. Map hành động thành điểm số: booking=1.0, share=0.75, like=0.5, click=0.25
2. Group by (user_id, hotel_id) và lấy điểm cao nhất (Max strategy)
3. Append kết quả vào file hotel.inter để tích lũy dữ liệu

Bổ sung (log incremental):
- Đọc user_actions.log (mỗi dòng là 1 JSON)
- Sau khi xử lý: append các dòng đã xử lý vào file lưu trữ (archive) rồi truncate log
"""

import pandas as pd
import json
import os
import sys
import io
from datetime import datetime
from typing import List, Dict

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_action_score(action_type):
    """Chuyển đổi hành động thành điểm số"""
    action_scores = {
        'booking': 1.0,   # Hành động chuyển đổi
        'share': 0.75,    # Mức quan tâm mạnh
        'like': 0.5,      # Ý định chọn
        'click': 0.25     # Quan tâm cơ bản
    }
    return action_scores.get(action_type, 0.0)


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)


def _group_and_append(rows: List[Dict], output_file: str) -> int:
    """Group Max theo (user_id, hotel_id) và append vào output_file. Trả về số bản ghi ghi thêm."""
    if not rows:
        return 0
    df = pd.DataFrame(rows)
    if df.empty:
        return 0
    df['action_score'] = df['action_type'].apply(get_action_score)
    grouped = df.groupby(['user_id', 'hotel_id']).agg({
        'action_score': 'max',
        'timestamp': 'max'
    }).reset_index()
    grouped = grouped.rename(columns={'action_score': 'action_type'})
    grouped = grouped.sort_values('timestamp')

    _ensure_parent_dir(output_file)
    file_exists = os.path.exists(output_file)
    with open(output_file, 'a', encoding='utf-8') as f:
        if not file_exists:
            f.write('user_id:token\titem_id:token\taction_type:float\ttimestamp:float\n')
        for _, row in grouped.iterrows():
            f.write(f"{row['user_id']}\t{row['hotel_id']}\t{row['action_type']}\t{int(row['timestamp'])}\n")
    return len(grouped)


def process_web_actions_to_hotel_inter(web_data_file, output_file):
    print("Loading web data (JSON array)...")
    with open(web_data_file, 'r', encoding='utf-8') as f:
        web_actions = json.load(f)
    print(f"   Found {len(web_actions)} raw actions from web")

    written = _group_and_append(web_actions, output_file)
    print("ETL completed successfully!")
    print(f"   Output: {written} interactions in {output_file}")


def process_log_incremental(log_file: str, archive_file: str, output_file: str):   
    #Đọc user_actions.log (mỗi dòng 1 JSON), append vào archive, xử lý và append vào hotel.inter, rồi truncate log.   
    if not os.path.exists(log_file):
        print(f"No log file found at {log_file}. Nothing to process.")
        return

    # Check if file is empty or only whitespace
    file_size = os.path.getsize(log_file)
    if file_size == 0:
        print("Log is empty. Nothing to process.")
        return

    print(f"Loading line-delimited JSON from {log_file}...")
    rows: List[Dict] = []
    processed_lines: List[str] = []
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        print("Log is empty. Nothing to process.")
        return

    # Parse JSON lines; skip malformed safely
    for ln in lines:
        ln_stripped = ln.strip()
        if not ln_stripped:
            continue
        
        # Remove literal \n characters that might be in the string
        ln_stripped = ln_stripped.replace('\\n', '').replace('\n', '')
        
        try:
            obj = json.loads(ln_stripped)
            # normalize keys (hotel_id vs item_id)
            if 'hotel_id' not in obj and 'item_id' in obj:
                obj['hotel_id'] = obj['item_id']
            # Ensure required fields exist
            if 'user_id' not in obj or 'hotel_id' not in obj or 'action_type' not in obj:
                print(f"Warning: Missing required fields in line: {ln_stripped[:50]}...")
                continue
            rows.append(obj)
            processed_lines.append(ln)  # Keep original line for archive
        except json.JSONDecodeError as e:
            print(f"Warning: Skipping malformed JSON line: {ln_stripped[:50]}... Error: {e}")
            continue
        except Exception as e:
            print(f"Warning: Error processing line: {ln_stripped[:50]}... Error: {e}")
            continue

    if not rows:
        print("No valid JSON lines found in log file. Nothing to process.")
        return

    # Append raw lines to archive (for audit) before truncating
    _ensure_parent_dir(archive_file)
    with open(archive_file, 'a', encoding='utf-8') as af:
        for ln in processed_lines:
            af.write(ln if ln.endswith("\n") else (ln + "\n"))

    # Process and write interactions
    written = _group_and_append(rows, output_file)

    # Truncate original log (clear all content)
    with open(log_file, 'w', encoding='utf-8') as f:
        f.truncate(0)

    print("ETL (incremental) completed!")
    print(f"   Processed: {len(rows)} valid actions from {len(processed_lines)} lines")
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
