#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script đơn giản để chạy RecBole và tự động lưu kết quả vào file result.txt
"""

import subprocess
import sys
import os

def run_recbole_with_results(model="NFM", dataset="ml-100k", config_file=None, output_file="result.txt"):
    """
    Chạy RecBole với model và dataset được chỉ định, tự động lưu kết quả
    
    Args:
        model: Tên model (mặc định: NFM)
        dataset: Tên dataset (mặc định: ml-100k)
        config_file: File config (tùy chọn)
        output_file: Tên file kết quả (mặc định: result.txt)
    """
    
    print(f"[START] Chay RecBole voi model {model} tren dataset {dataset}")
    print(f"[SAVE] Ket qua se duoc luu vao: {output_file}")
    
    # Tạo command
    cmd = [sys.executable, "run_recbole.py", 
           "--model", model, 
           "--dataset", dataset,
           "--save_results",
           "--output_file", output_file]
    
    # Thêm config file nếu có
    if config_file and os.path.exists(config_file):
        cmd.extend(["--config_files", config_file])
        print(f"[CONFIG] Su dung config file: {config_file}")
    
    print(f"[CMD] Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        # Chạy command
        result = subprocess.run(cmd, check=True, capture_output=False)
        
        if result.returncode == 0:
            print("-" * 60)
            print("[SUCCESS] Hoan thanh thanh cong!")
            if os.path.exists(output_file):
                print(f"[FILE] File ket qua da duoc tao: {output_file}")
                print("[CONTENT] Noi dung file:")
                print("-" * 40)
                with open(output_file, 'r', encoding='utf-8') as f:
                    print(f.read())
            else:
                print("[WARNING] File ket qua khong duoc tao")
        else:
            print("[ERROR] Co loi xay ra trong qua trinh chay")
            
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Loi: {e}")
    except FileNotFoundError:
        print("[ERROR] Khong tim thay file run_recbole.py")
        print("[TIP] Hay dam bao ban dang chay script nay trong thu muc goc cua RecBole")

if __name__ == "__main__":
    # Có thể thay đổi các tham số ở đây
    model = "NFM"
    dataset = "ml-100k"
    config_file = "nfm_config.yaml"  # Có thể để None nếu không cần
    output_file = "result.txt"
    
    # Kiểm tra xem config file có tồn tại không
    if config_file and not os.path.exists(config_file):
        print(f"[WARNING] Config file {config_file} khong ton tai, se chay voi config mac dinh")
        config_file = None
    
    run_recbole_with_results(model, dataset, config_file, output_file)
