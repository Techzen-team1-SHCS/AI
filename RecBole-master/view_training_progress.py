import os
import re
import sys
import io
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def find_latest_log_file():
    """Tìm file log mới nhất có dữ liệu training"""
    log_dir = Path("log/DeepFM")
    if not log_dir.exists():
        return None
    
    log_files = list(log_dir.glob("*.log"))
    if not log_files:
        return None
    
    # Sắp xếp theo thời gian tạo (mới nhất trước)
    log_files_sorted = sorted(log_files, key=os.path.getctime, reverse=True)
    
    # Tìm file đầu tiên có dữ liệu training
    for log_file in log_files_sorted:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Kiểm tra xem có epoch training không (phải có pattern "epoch X training")
                if re.search(r'epoch \d+ training', content, re.IGNORECASE):
                    return log_file
        except:
            continue
    
    # Nếu không tìm thấy, trả về file mới nhất
    return log_files_sorted[0]


def parse_training_log(log_path):
    """Parse log file và trích xuất thông tin training"""
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tìm tất cả các epoch (case insensitive)
    epoch_pattern = r'epoch (\d+) training.*?train loss: ([0-9.]+)'
    epochs = re.findall(epoch_pattern, content, re.IGNORECASE)
    
    # Tìm tất cả các valid result
    valid_pattern = r'epoch (\d+) evaluating.*?valid_score: ([0-9.]+).*?valid result:\s*(.*?)(?=\n\n|\n[A-Z]|\Z)'
    valid_results = re.findall(valid_pattern, content, re.DOTALL)
    
    # Tìm best valid result
    best_valid_match = re.search(r'best valid[^\n]*\n(.*?)(?=\n\n|\n[A-Z]|\Z)', content, re.DOTALL)
    best_valid = None
    if best_valid_match:
        best_valid = best_valid_match.group(1).strip()
    
    # Tìm test result
    test_result_match = re.search(r'test result[^\n]*\n(.*?)(?=\n\n|\n[A-Z]|\Z)', content, re.DOTALL)
    test_result = None
    if test_result_match:
        test_result = test_result_match.group(1).strip()
    
    # Tìm finished training
    finished_match = re.search(r'Finished training.*?epoch (\d+)', content)
    finished_epoch = finished_match.group(1) if finished_match else None
    
    return {
        'epochs': epochs,
        'valid_results': valid_results,
        'best_valid': best_valid,
        'test_result': test_result,
        'finished_epoch': finished_epoch
    }


def extract_metrics(text):
    """Trích xuất metrics từ text"""
    metrics = {}
    # Tìm các metrics phổ biến
    metric_patterns = {
        'RMSE': r'rmse\s*:\s*([0-9.]+)',
        'MAE': r'mae\s*:\s*([0-9.]+)',
        'AUC': r'auc\s*:\s*([0-9.]+)',
        'LogLoss': r'logloss\s*:\s*([0-9.]+)',
        'Recall': r'recall@(\d+)\s*:\s*([0-9.]+)',
        'NDCG': r'ndcg@(\d+)\s*:\s*([0-9.]+)',
        'Hit': r'hit@(\d+)\s*:\s*([0-9.]+)',
        'Precision': r'precision@(\d+)\s*:\s*([0-9.]+)',
    }
    
    for metric_name, pattern in metric_patterns.items():
        matches = re.findall(pattern, text.lower())
        if matches:
            if metric_name in ['Recall', 'NDCG', 'Hit', 'Precision']:
                # Top-k metrics
                for k, value in matches:
                    key = f"{metric_name}@{k}"
                    metrics[key] = float(value)
            else:
                metrics[metric_name] = float(matches[0])
    
    return metrics


def explain_metrics(metrics):
    """Giải thích ý nghĩa các metrics"""
    explanations = {
        'RMSE': {
            'name': 'RMSE (Root Mean Squared Error)',
            'meaning': 'Sai so trung binh binh phuong can',
            'interpretation': 'Cang thap cang tot. Do sai so giua du doan va gia tri thuc.',
            'good': '< 0.4',
            'bad': '> 0.6'
        },
        'MAE': {
            'name': 'MAE (Mean Absolute Error)',
            'meaning': 'Sai so tuyet doi trung binh',
            'interpretation': 'Cang thap cang tot. Do sai so tuyet doi giua du doan va gia tri thuc.',
            'good': '< 0.3',
            'bad': '> 0.5'
        },
        'AUC': {
            'name': 'AUC (Area Under Curve)',
            'meaning': 'Dien tich duoi duong cong ROC',
            'interpretation': 'Cang cao cang tot. Do chinh xac phan loai (0.5 = random, 1.0 = hoan hao).',
            'good': '> 0.7',
            'bad': '< 0.6'
        },
        'LogLoss': {
            'name': 'LogLoss (Logarithmic Loss)',
            'meaning': 'Mat mat logarit',
            'interpretation': 'Cang thap cang tot. Do mat mat trong phan loai nhi phan.',
            'good': '< 0.5',
            'bad': '> 0.7'
        },
        'Recall': {
            'name': 'Recall (Do phu)',
            'meaning': 'Ti le tim thay cac item dung',
            'interpretation': 'Cang cao cang tot. Ti le cac item dung duoc tim thay trong top-k.',
            'good': '> 0.1',
            'bad': '< 0.05'
        },
        'NDCG': {
            'name': 'NDCG (Normalized Discounted Cumulative Gain)',
            'meaning': 'Do do chat luong sap xep',
            'interpretation': 'Cang cao cang tot. Do do chat luong sap xep cac item (0-1).',
            'good': '> 0.1',
            'bad': '< 0.05'
        },
        'Hit': {
            'name': 'Hit Rate',
            'meaning': 'Ti le co it nhat 1 item dung trong top-k',
            'interpretation': 'Cang cao cang tot. Ti le co it nhat 1 item dung trong top-k.',
            'good': '> 0.2',
            'bad': '< 0.1'
        },
        'Precision': {
            'name': 'Precision (Do chinh xac)',
            'meaning': 'Ti le item dung trong top-k',
            'interpretation': 'Cang cao cang tot. Ti le item dung trong top-k.',
            'good': '> 0.1',
            'bad': '< 0.05'
        }
    }
    
    return explanations


def analyze_training_progress(epochs, valid_results):
    """Phân tích tiến trình training"""
    if not epochs or not valid_results:
        return None
    
    # Lấy 5 epoch cuối cùng
    recent_epochs = epochs[-5:] if len(epochs) > 5 else epochs
    recent_valids = valid_results[-5:] if len(valid_results) > 5 else valid_results
    
    # Phân tích train loss
    train_losses = [float(loss) for _, loss in recent_epochs]
    train_loss_trend = "giam" if len(train_losses) > 1 and train_losses[-1] < train_losses[0] else "tang"
    train_loss_stable = max(train_losses) - min(train_losses) < 0.1
    
    # Phân tích valid score
    valid_scores = [float(score) for _, score, _ in recent_valids]
    valid_score_trend = "cai thien" if len(valid_scores) > 1 and valid_scores[-1] > valid_scores[0] else "giam"
    valid_score_stable = max(valid_scores) - min(valid_scores) < 0.01
    
    # Phân tích overfitting
    last_train_loss = float(epochs[-1][1]) if epochs else None
    last_valid_score = float(valid_results[-1][1]) if valid_results else None
    
    analysis = {
        'train_loss_trend': train_loss_trend,
        'train_loss_stable': train_loss_stable,
        'valid_score_trend': valid_score_trend,
        'valid_score_stable': valid_score_stable,
        'last_train_loss': last_train_loss,
        'last_valid_score': last_valid_score
    }
    
    return analysis


def check_training_status(data):
    """Kiểm tra trạng thái training dựa trên dữ liệu"""
    # Nếu có finished_epoch → đã hoàn thành
    if data['finished_epoch']:
        return "completed", data['finished_epoch']
    
    # Nếu có test_result → đã hoàn thành (test chỉ chạy sau khi training xong)
    if data['test_result']:
        # Tìm epoch cuối cùng
        last_epoch = data['epochs'][-1][0] if data['epochs'] else "unknown"
        return "completed", last_epoch
    
    # Nếu có best_valid → có thể đã hoàn thành
    if data['best_valid']:
        # Tìm epoch từ valid_results có score cao nhất
        if data['valid_results']:
            best_epoch = max(data['valid_results'], key=lambda x: float(x[1]))[0]
            return "completed", best_epoch
    
    # Nếu có epochs và valid_results → đã train (có thể đang chạy hoặc đã xong)
    if data['epochs'] and data['valid_results']:
        last_epoch = data['epochs'][-1][0]
        return "trained", last_epoch
    
    # Nếu chỉ có epochs → đang train hoặc chưa có valid
    if data['epochs']:
        return "training", data['epochs'][-1][0]
    
    # Không có gì → chưa train
    return "not_started", None


def print_training_summary(log_path, data):
    """In tóm tắt kết quả training"""
    print("=" * 80)
    print("KET QUA TRAINING - DEEPFM HOTEL RECOMMENDATION")
    print("=" * 80)
    print(f"\nFile log: {log_path}")
    print(f"Thoi gian: {datetime.fromtimestamp(os.path.getctime(log_path)).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Kiểm tra trạng thái
    status, epoch = check_training_status(data)
    
    if status == "completed":
        print(f"\n[STATUS] Training da HOAN THANH")
        print(f"  Best epoch: {epoch}")
    elif status == "trained":
        print(f"\n[STATUS] Training da HOAN THANH (co epochs va valid results)")
        print(f"  Last epoch: {epoch}")
    elif status == "training":
        print(f"\n[STATUS] Training DANG CHAY hoac chua co valid results")
        print(f"  Last epoch: {epoch}")
    else:
        print(f"\n[STATUS] Chua co du lieu training")
    
    # Hiển thị các epoch
    if data['epochs']:
        print(f"\n[EPOCHS] Tong so: {len(data['epochs'])} epochs")
        print("\n5 Epoch cuoi cung:")
        print("-" * 80)
        for epoch_idx, (epoch_num, train_loss) in enumerate(data['epochs'][-5:], 1):
            print(f"  Epoch {epoch_num}: Train Loss = {train_loss}")
    
    # Hiển thị valid results
    if data['valid_results']:
        print(f"\n[VALIDATION] Tong so: {len(data['valid_results'])} lan danh gia")
        print("\n5 Lan danh gia cuoi cung:")
        print("-" * 80)
        for epoch_num, valid_score, valid_text in data['valid_results'][-5:]:
            metrics = extract_metrics(valid_text)
            print(f"  Epoch {epoch_num}: Valid Score = {valid_score}")
            if metrics:
                for metric_name, value in metrics.items():
                    print(f"    - {metric_name}: {value:.4f}")
    
    # Hiển thị best valid result
    if data['best_valid']:
        print(f"\n[BEST VALID RESULT]")
        print("-" * 80)
        best_metrics = extract_metrics(data['best_valid'])
        if best_metrics:
            for metric_name, value in best_metrics.items():
                print(f"  {metric_name}: {value:.4f}")
        else:
            print(f"  {data['best_valid'][:100]}...")
    
    # Hiển thị test result
    if data['test_result']:
        print(f"\n[TEST RESULT]")
        print("-" * 80)
        test_metrics = extract_metrics(data['test_result'])
        if test_metrics:
            for metric_name, value in test_metrics.items():
                print(f"  {metric_name}: {value:.4f}")
        else:
            print(f"  {data['test_result'][:100]}...")
    
    # Nếu không có best valid, lấy từ valid results
    if not data['best_valid'] and data['valid_results']:
        print(f"\n[BEST VALID RESULT] (tu valid results)")
        print("-" * 80)
        # Tìm valid score cao nhất
        best_valid_result = max(data['valid_results'], key=lambda x: float(x[1]))
        epoch_num, valid_score, valid_text = best_valid_result
        print(f"  Epoch {epoch_num}: Valid Score = {valid_score}")
        best_metrics = extract_metrics(valid_text)
        if best_metrics:
            for metric_name, value in best_metrics.items():
                print(f"  {metric_name}: {value:.4f}")
    
    # Giải thích metrics
    all_metrics = {}
    if data['best_valid']:
        all_metrics.update(extract_metrics(data['best_valid']))
    if data['test_result']:
        all_metrics.update(extract_metrics(data['test_result']))
    # Nếu không có, lấy từ valid results cuối cùng
    if not all_metrics and data['valid_results']:
        last_valid_text = data['valid_results'][-1][2]
        all_metrics.update(extract_metrics(last_valid_text))
    
    if all_metrics:
        print(f"\n[GIAI THICH Y NGHIA CAC METRICS]")
        print("-" * 80)
        explanations = explain_metrics(all_metrics)
        for metric_key in sorted(all_metrics.keys()):
            # Tìm metric base name (bỏ @k nếu có)
            base_name = metric_key.split('@')[0]
            if base_name in explanations:
                exp = explanations[base_name]
                value = all_metrics[metric_key]
                print(f"\n{exp['name']}:")
                print(f"  - Y nghia: {exp['meaning']}")
                print(f"  - Giai thich: {exp['interpretation']}")
                print(f"  - Tot: {exp['good']}")
                print(f"  - Kem: {exp['bad']}")
                # Đánh giá giá trị hiện tại
                try:
                    if base_name in ['RMSE', 'MAE', 'LogLoss']:
                        good_threshold = float(exp['good'].split()[1])
                        status = "TOT" if value < good_threshold else "CAN CAI THIEN"
                    else:
                        good_threshold = float(exp['good'].split()[1])
                        status = "TOT" if value > good_threshold else "CAN CAI THIEN"
                    print(f"  - Gia tri hien tai: {value:.4f} ({status})")
                except:
                    print(f"  - Gia tri hien tai: {value:.4f}")
    
    # Phân tích tiến trình
    analysis = analyze_training_progress(data['epochs'], data['valid_results'])
    if analysis:
        print(f"\n[PHAN TICH TIEN TRINH TRAINING]")
        print("-" * 80)
        print(f"Train Loss: {analysis['train_loss_trend']}")
        if analysis['train_loss_stable']:
            print("  -> Train loss on dinh (tot)")
        else:
            print("  -> Train loss chua on dinh (can them epochs)")
        
        print(f"Valid Score: {analysis['valid_score_trend']}")
        if analysis['valid_score_stable']:
            print("  -> Valid score on dinh (tot)")
        else:
            print("  -> Valid score chua on dinh (can them epochs)")
        
        # Đánh giá tổng thể
        print(f"\n[DANH GIA TONG THE]")
        print("-" * 80)
        if analysis['train_loss_trend'] == "giam" and analysis['valid_score_trend'] == "cai thien":
            print("[OK] Model dang CAI THIEN tot")
            print("  - Train loss giam dan")
            print("  - Valid score cai thien")
        elif analysis['train_loss_trend'] == "giam" and analysis['valid_score_trend'] == "giam":
            print("[WARN] Co the bi OVERFITTING")
            print("  - Train loss giam nhung valid score giam")
            print("  - Can dung training som hon hoac them du lieu")
        elif analysis['train_loss_trend'] == "tang":
            print("[WARN] Model chua hoc tot")
            print("  - Train loss tang (bat thuong)")
            print("  - Can kiem tra learning rate hoac model architecture")
        else:
            print("[INFO] Model dang hoc binh thuong")
            print("  - Can theo doi them de danh gia")
    
    print("\n" + "=" * 80)


def main():
    log_file = find_latest_log_file()
    if not log_file:
        print("[ERROR] Khong tim thay log file trong log/DeepFM/")
        return
    
    data = parse_training_log(log_file)
    print_training_summary(log_file, data)


if __name__ == "__main__":
    main()

