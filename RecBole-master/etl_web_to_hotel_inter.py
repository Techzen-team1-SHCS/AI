#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL Script: Chuyển đổi dữ liệu hành vi từ Web sang hotel.inter
- Extract: Lấy dữ liệu hành vi từ web/database (JSON format)
- Transform: Chuyển đổi hành động thành điểm số và group theo Max strategy
- Load: Append dữ liệu mới vào file hotel.inter (không ghi đè dữ liệu cũ)

Thuật toán xử lý:
1. Map hành động thành điểm số: booking=1.0, share=0.75, like=0.5, click=0.25
2. Group by (user_id, hotel_id) và lấy điểm cao nhất (Max strategy)
3. Append kết quả vào file hotel.inter để tích lũy dữ liệu cho ML
"""

import pandas as pd
import json
import os
from datetime import datetime

def get_action_score(action_type):
    """Chuyển đổi hành động thành điểm số"""
    action_scores = {
        'booking': 1.0,   # Hành động chuyển đổi
        'share': 0.75,    # Mức quan tâm mạnh
        'like': 0.5,      # Ý định chọn
        'click': 0.25     # Quan tâm cơ bản
    }
    return action_scores.get(action_type, 0.0)

def process_web_actions_to_hotel_inter(web_data_file, output_file):
    """
    Xử lý dữ liệu hành vi từ web và tạo hotel.inter
    
    Args:
        web_data_file: File JSON chứa dữ liệu hành vi từ web
        output_file: File hotel.inter output
    """
    
    # 1. Load dữ liệu từ web (JSON format)
    print("Loading web data...")
    with open(web_data_file, 'r', encoding='utf-8') as f:
        web_actions = json.load(f)
    
    print(f"   Found {len(web_actions)} raw actions from web")
    
    # 2. Convert to DataFrame
    df = pd.DataFrame(web_actions)
    print(f"   Columns: {list(df.columns)}")
    
    # 3. Transform: Chuyển action_type thành điểm số
    print("Transforming actions to scores...")
    df['action_score'] = df['action_type'].apply(get_action_score)
    
    # 4. Group by user_id + hotel_id và lấy MAX score
    print("Grouping by user-hotel pairs and taking MAX score...")
    grouped = df.groupby(['user_id', 'hotel_id']).agg({
        'action_score': 'max',  # Lấy điểm cao nhất
        'timestamp': 'max'      # Lấy timestamp của hành động có điểm cao nhất
    }).reset_index()
    
    print(f"   After grouping: {len(grouped)} unique user-hotel pairs")
    
    # 5. Rename columns để phù hợp với hotel.inter format
    grouped = grouped.rename(columns={
        'action_score': 'action_type',
        'timestamp': 'timestamp'
    })
    
    # 6. Sort by timestamp
    grouped = grouped.sort_values('timestamp')
    
    # 7. Append to hotel.inter format (không ghi đè)
    print(f"Appending to {output_file}...")
    
    # Kiểm tra file có tồn tại không
    file_exists = os.path.exists(output_file)
    
    with open(output_file, 'a', encoding='utf-8') as f:
        # Chỉ ghi header nếu file chưa tồn tại
        if not file_exists:
            f.write('user_id:token\titem_id:token\taction_type:float\ttimestamp:float\n')
        
        # Append data mới
        for _, row in grouped.iterrows():
            f.write(f"{row['user_id']}\t{row['hotel_id']}\t{row['action_type']}\t{int(row['timestamp'])}\n")
    
    print("ETL completed successfully!")
    print(f"   Output: {len(grouped)} interactions in {output_file}")
    
    # 8. Show statistics
    print("\nStatistics:")
    print(f"   Users: {grouped['user_id'].nunique()}")
    print(f"   Hotels: {grouped['hotel_id'].nunique()}")
    print(f"   Score distribution:")
    print(f"     Booking (1.0): {(grouped['action_type'] == 1.0).sum()}")
    print(f"     Share (0.75): {(grouped['action_type'] == 0.75).sum()}")
    print(f"     Like (0.5): {(grouped['action_type'] == 0.5).sum()}")
    print(f"     Click (0.25): {(grouped['action_type'] == 0.25).sum()}")

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
    
    with open('sample_web_actions.json', 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)
    
    print("Created sample web data: sample_web_actions.json")
    return 'sample_web_actions.json'

if __name__ == "__main__":
    # Tạo dữ liệu mẫu
    web_file = create_sample_web_data()
    
    # Chạy ETL (append vào cuối file gốc)
    process_web_actions_to_hotel_inter(web_file, 'dataset/hotel/hotel.inter')
    
    print("\nKết quả:")
    print("   - Dữ liệu từ web đã được xử lý")
    print("   - Mỗi user-hotel pair chỉ có 1 dòng (điểm cao nhất)")
    print("   - Sẵn sàng để train AI model")
