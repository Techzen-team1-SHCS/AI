#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để lưu kết quả metrics và thời gian chạy từ RecBole vào file result.txt
"""

import os
import json
import time
from datetime import datetime
from recbole.quick_start import run

def save_results_to_file(result_dict, config_dict, output_file="result.txt"):
    """
    Lưu kết quả metrics và thông tin huấn luyện vào file
    
    Args:
        result_dict: Dictionary chứa kết quả từ RecBole
        config_dict: Dictionary chứa cấu hình
        output_file: Tên file output
    """
    
    # Tạo thông tin header
    header = "=" * 80 + "\n"
    header += f"RECBOLE TRAINING RESULTS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += "=" * 80 + "\n\n"
    
    # Thông tin cấu hình
    config_info = "CONFIGURATION:\n"
    config_info += "-" * 40 + "\n"
    for key, value in config_dict.items():
        config_info += f"{key}: {value}\n"
    config_info += "\n"
    
    # Kết quả validation tốt nhất
    best_valid_info = "BEST VALIDATION RESULTS:\n"
    best_valid_info += "-" * 40 + "\n"
    best_valid_info += f"Best Valid Score: {result_dict['best_valid_score']:.4f}\n"
    best_valid_info += "Best Valid Metrics:\n"
    for metric, value in result_dict['best_valid_result'].items():
        best_valid_info += f"  {metric}: {value:.4f}\n"
    best_valid_info += "\n"
    
    # Kết quả test
    test_info = "TEST RESULTS:\n"
    test_info += "-" * 40 + "\n"
    for metric, value in result_dict['test_result'].items():
        test_info += f"{metric}: {value:.4f}\n"
    test_info += "\n"
    
    # Thông tin bổ sung
    additional_info = "ADDITIONAL INFORMATION:\n"
    additional_info += "-" * 40 + "\n"
    additional_info += f"Valid Score Bigger is Better: {result_dict['valid_score_bigger']}\n"
    additional_info += f"Output File: {output_file}\n"
    additional_info += f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    # Gộp tất cả thông tin
    full_content = header + config_info + best_valid_info + test_info + additional_info
    
    # Ghi vào file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    print(f"✅ Kết quả đã được lưu vào file: {output_file}")
    print(f"📊 Best Valid Score: {result_dict['best_valid_score']:.4f}")
    print(f"🧪 Test AUC: {result_dict['test_result'].get('AUC', 'N/A')}")
    print(f"🧪 Test LogLoss: {result_dict['test_result'].get('LogLoss', 'N/A')}")

def run_with_result_saving(model, dataset, config_file_list=None, config_dict=None, output_file="result.txt"):
    """
    Chạy RecBole và tự động lưu kết quả vào file
    
    Args:
        model: Tên model
        dataset: Tên dataset  
        config_file_list: Danh sách file config
        config_dict: Dictionary cấu hình
        output_file: Tên file output
    """
    
    print(f"🚀 Bắt đầu huấn luyện model {model} trên dataset {dataset}")
    print(f"📝 Kết quả sẽ được lưu vào: {output_file}")
    
    # Ghi lại thời gian bắt đầu
    start_time = time.time()
    
    # Chạy RecBole
    result = run(
        model=model,
        dataset=dataset,
        config_file_list=config_file_list,
        config_dict=config_dict
    )
    
    # Ghi lại thời gian kết thúc
    end_time = time.time()
    total_time = end_time - start_time
    
    # Thêm thông tin thời gian vào config_dict
    if config_dict is None:
        config_dict = {}
    
    config_dict.update({
        'model': model,
        'dataset': dataset,
        'total_training_time': f"{total_time:.2f} seconds",
        'total_training_time_minutes': f"{total_time/60:.2f} minutes",
        'start_time': datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # Lưu kết quả vào file
    save_results_to_file(result, config_dict, output_file)
    
    return result

if __name__ == "__main__":
    # Ví dụ sử dụng
    config_dict = {
        "epochs": 20,
        "learning_rate": 0.001,
        "eval_type": "both",
        "metrics": ["AUC", "LogLoss"],
        "save_result": True,
        "save_log": True,
        "show_progress": True,
    }
    
    result = run_with_result_saving(
        model="NFM",
        dataset="ml-100k", 
        config_dict=config_dict,
        output_file="result.txt"
    )

