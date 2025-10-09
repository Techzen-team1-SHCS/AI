# @Time   : 2020/7/20
# @Author : Shanlei Mu
# @Email  : slmu@ruc.edu.cn

# UPDATE
# @Time   : 2022/7/8, 2020/10/3, 2020/10/1
# @Author : Zhen Tian, Yupeng Hou, Zihan Lin
# @Email  : chenyuwuxinn@gmail.com, houyupeng@ruc.edu.cn, zhlin@ruc.edu.cn

import argparse

from recbole.quick_start import run
import time
from datetime import datetime

def save_results_to_file(result_dict, config_dict, output_file="result.txt"):
    """Lưu kết quả metrics và thông tin huấn luyện vào file"""
    
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
    
    print(f"[SUCCESS] Ket qua da duoc luu vao file: {output_file}")
    print(f"[METRIC] Best Valid Score: {result_dict['best_valid_score']:.4f}")
    if 'test_result' in result_dict:
        test_result = result_dict['test_result']
        print(f"[TEST] Test AUC: {test_result.get('AUC', 'N/A')}")
        print(f"[TEST] Test LogLoss: {test_result.get('LogLoss', 'N/A')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", "-m", type=str, default="BPR", help="name of models")
    parser.add_argument(
        "--dataset", "-d", type=str, default="ml-100k", help="name of datasets"
    )
    parser.add_argument("--config_files", type=str, default=None, help="config files")
    parser.add_argument(
        "--nproc", type=int, default=1, help="the number of process in this group"
    )
    parser.add_argument(
        "--ip", type=str, default="localhost", help="the ip of master node"
    )
    parser.add_argument(
        "--port", type=str, default="5678", help="the port of master node"
    )
    parser.add_argument(
        "--world_size", type=int, default=-1, help="total number of jobs"
    )
    parser.add_argument(
        "--group_offset",
        type=int,
        default=0,
        help="the global rank offset of this group",
    )
    parser.add_argument(
        "--save_results", action="store_true", help="save results to result.txt file"
    )
    parser.add_argument(
        "--output_file", type=str, default="result.txt", help="output file name for results"
    )

    args, _ = parser.parse_known_args()

    config_file_list = (
        args.config_files.strip().split(" ") if args.config_files else None
    )

    # ✅ Thêm config_dict để bật lưu kết quả và log
    config_dict = {
        "save_result": True,         # Lưu result.txt
        "save_log": True,            # Lưu log huấn luyện
        "log_wandb": False,          # Không bật wandb (nếu bạn không dùng)
        "show_progress": True,       # Hiện tiến độ
    }
    
    print(f"[START] Bat dau huan luyen model {args.model} tren dataset {args.dataset}")
    start_time = time.time()
    
    result = run(
        args.model,
        args.dataset,
        config_file_list=config_file_list,
        nproc=args.nproc,
        world_size=args.world_size,
        ip=args.ip,
        port=args.port,
        group_offset=args.group_offset,
        config_dict=config_dict,
    )
    
    # Ghi lại thời gian kết thúc
    end_time = time.time()
    total_time = end_time - start_time
    
    # Thêm thông tin thời gian vào config_dict
    config_dict.update({
        'model': args.model,
        'dataset': args.dataset,
        'total_training_time': f"{total_time:.2f} seconds",
        'total_training_time_minutes': f"{total_time/60:.2f} minutes",
        'start_time': datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # Lưu kết quả vào file nếu được yêu cầu
    if args.save_results:
        save_results_to_file(result, config_dict, args.output_file)
    else:
        print(f"[TIP] De luu ket qua vao file, hay chay voi --save_results")
        print(f"[METRIC] Best Valid Score: {result['best_valid_score']:.4f}")
        if 'test_result' in result:
            test_result = result['test_result']
            print(f"[TEST] Test AUC: {test_result.get('AUC', 'N/A')}")
            print(f"[TEST] Test LogLoss: {test_result.get('LogLoss', 'N/A')}")
