"""
Script tạo báo cáo chuyên nghiệp từ kết quả test Phase 1.
Báo cáo dạng bảng, minh bạch, chứng minh độ tin cậy của AI Phase 1.

Usage:
    python generate_report.py phase1_results_100.json report.md
"""

import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List
import math

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def format_percentage(value: float) -> str:
    """Format percentage."""
    return f"{value:.1%}"


def format_float(value: float, decimals: int = 2) -> str:
    """Format float."""
    return f"{value:.{decimals}f}"


def calculate_confidence_interval(p: float, n: int, confidence: float = 0.95) -> tuple:
    """Tính confidence interval cho tỷ lệ (proportion).
    
    Args:
        p: Tỷ lệ mẫu (sample proportion)
        n: Kích thước mẫu (sample size)
        confidence: Mức độ tin cậy (default: 0.95 = 95%)
    
    Returns:
        (lower_bound, upper_bound)
    """
    if n == 0:
        return (0.0, 0.0)
    
    z = 1.96 if confidence == 0.95 else 2.576  # 95% hoặc 99%
    margin = z * math.sqrt((p * (1 - p)) / n)
    lower = max(0.0, p - margin)
    upper = min(1.0, p + margin)
    return (lower, upper)


def generate_markdown_report(summary: Dict, output_file: str):
    """Generate markdown report chuyên nghiệp từ summary."""
    
    test_info = summary['test_info']
    overall_stats = summary['overall_stats']
    pattern_stats = summary['pattern_stats']
    results = summary['results']
    
    # Tính confidence interval cho pass rate
    ci_lower, ci_upper = calculate_confidence_interval(
        overall_stats['pass_rate'],
        overall_stats['total_users'] - test_info['num_errors']
    )
    
    # Header
    report = f"""# BÁO CÁO ĐÁNH GIÁ ĐỘ TIN CẬY AI PHASE 1 - BEHAVIOR BOOST

**Ngày test:** {datetime.fromisoformat(test_info['test_date']).strftime('%d/%m/%Y %H:%M:%S')}  
**Model sử dụng:** `{test_info['model_path']}`  
**Số lượng users tested:** {test_info['num_users_tested']}  
**Top-K recommendations:** {test_info['top_k']}  

---

## 1. THÔNG TIN TEST VÀ ĐIỀU KIỆN

### 1.1. Mục đích test

Test này được thiết kế để **đánh giá độ tin cậy và hiệu quả của AI Phase 1 (Behavior Boost)** trong việc recommend items phù hợp với user profiles dựa trên các patterns:
- Gender → Style matching
- Age → Price matching  
- Region → City matching
- Age → Star/Score matching (tùy chọn)

### 1.2. Điều kiện test

| Thông số | Giá trị | Mô tả |
|----------|---------|-------|
| **Số lượng users** | {test_info['num_users_tested']} | Số users được test để đảm bảo tính đại diện |
| **Top-K** | {test_info['top_k']} | Số lượng recommendations cho mỗi user |
| **Model** | DeepFM | Model recommendation được sử dụng |
| **Behavior Boost** | Enabled | Phase 1 boost dựa trên user actions gần đây |
| **Similarity Boost** | Disabled | Phase 2 tắt để test riêng Phase 1 |
| **Valid results** | {overall_stats['total_users'] - test_info['num_errors']} | Số kết quả hợp lệ |
| **Errors** | {test_info['num_errors']} | Số lỗi trong quá trình test |

### 1.3. Tiêu chí đánh giá (Evaluation Criteria)

#### Patterns Bắt Buộc (Mandatory - Phải đạt ít nhất 2/3)

| Pattern | Điều kiện Pass | Threshold | Mô tả |
|---------|----------------|-----------|-------|
| **Gender → Style** | ≥ 30% items HOẶC ≥ 3 items | max(3, 30% × Top-K) | Items có style phù hợp với gender của user |
| **Age → Price** | ≥ 30% items HOẶC ≥ 3 items | max(3, 30% × Top-K) | Items có price phù hợp với age của user |
| **Region → City** | ≥ 20% items HOẶC ≥ 2 items | max(2, 20% × Top-K) | Items có city khớp với region của user |

#### Patterns Tùy Chọn (Optional - Bonus)

| Pattern | Điều kiện Pass | Threshold | Mô tả |
|---------|----------------|-----------|-------|
| **Age → Star (≥30)** | ≥ 30% items HOẶC ≥ 2 items | max(2, 30% × Top-K) | Items có star ≥ 3.5 cho users age ≥ 30 |
| **Age → Score (<30)** | ≥ 30% items HOẶC ≥ 2 items | max(2, 30% × Top-K) | Items có score ≥ 9.0 cho users age < 30 |

#### Điều kiện Pass tổng thể

- **Mandatory patterns**: Ít nhất **2/3 patterns bắt buộc** phải pass
- **Total score**: Tổng điểm ≥ 3.0/4.0
  - Mandatory score: 0-3 điểm (mỗi pattern = 1 điểm)
  - Optional score: 0-1 điểm (nếu pass = 1 điểm)

---

## 2. KẾT QUẢ TỔNG QUAN

### 2.1. Thống kê tổng thể

| Chỉ số | Giá trị | Ghi chú |
|--------|---------|---------|
| **Tổng số users tested** | {overall_stats['total_users']} | - |
| **Valid results** | {overall_stats['total_users'] - test_info['num_errors']} | Kết quả hợp lệ để đánh giá |
| **Errors** | {test_info['num_errors']} | Lỗi trong quá trình test |
| **Passed** | {overall_stats['passed']} | Số users đạt yêu cầu |
| **Failed** | {overall_stats['failed']} | Số users không đạt yêu cầu |
| **Pass Rate** | {format_percentage(overall_stats['pass_rate'])} | Tỷ lệ users pass |
| **95% Confidence Interval** | [{format_percentage(ci_lower)}, {format_percentage(ci_upper)}] | Khoảng tin cậy 95% cho pass rate |
| **Average Accuracy** | {format_percentage(overall_stats['avg_accuracy'])} | Độ chính xác trung bình (0-100%) |
| **Average Score** | {format_float(overall_stats['avg_score'])}/4.0 | Điểm trung bình |
| **Average Mandatory Passed** | {format_float(overall_stats['avg_mandatory_passed'])}/3.0 | Số patterns bắt buộc pass trung bình |

### 2.2. Đánh giá độ tin cậy

| Metric | Giá trị | Đánh giá |
|--------|---------|----------|
| **Pass Rate** | {format_percentage(overall_stats['pass_rate'])} | {'✅ Đạt yêu cầu (≥80%)' if overall_stats['pass_rate'] >= 0.8 else '⚠️ Cần cải thiện (<80%)'} |
| **Confidence Level** | 95% | Mức độ tin cậy của kết quả |
| **Sample Size** | {overall_stats['total_users'] - test_info['num_errors']} | Kích thước mẫu đủ lớn để đánh giá |
| **Error Rate** | {format_percentage(test_info['num_errors'] / test_info['num_users_tested'])} | Tỷ lệ lỗi trong quá trình test |

**Kết luận sơ bộ:** {'✅ Hệ thống AI Phase 1 đạt độ tin cậy cao' if overall_stats['pass_rate'] >= 0.8 else '⚠️ Hệ thống AI Phase 1 cần cải thiện để đạt độ tin cậy cao hơn'}

---

## 3. PHÂN TÍCH CHI TIẾT TỪNG PATTERN

### 3.1. Patterns Bắt Buộc (Mandatory Patterns)

| Pattern | Passed | Total | Pass Rate | 95% CI | Đánh giá | Mô tả |
|---------|--------|-------|-----------|--------|----------|-------|
"""
    
    mandatory_patterns = {
        'gender_style': ('Gender → Style', 'Items có style phù hợp với gender (Nữ: Romantic/Love/Modern/Lively, Nam: Love/Romantic/Modern/Lively)'),
        'age_price': ('Age → Price', 'Items có price phù hợp với age (Age < 30: Price < 1.6M, Age >= 30: Price >= 1.2M)'),
        'region_city': ('Region → City', 'Items có city khớp với region của user')
    }
    
    for pattern_key, (pattern_name, description) in mandatory_patterns.items():
        stats = pattern_stats[pattern_key]
        if stats['total'] > 0:
            ci_lower_p, ci_upper_p = calculate_confidence_interval(stats['pass_rate'], stats['total'])
            evaluation = '✅ Tốt' if stats['pass_rate'] >= 0.7 else '⚠️ Cần cải thiện' if stats['pass_rate'] >= 0.5 else '❌ Yếu'
            report += f"| **{pattern_name}** | {stats['passed']} | {stats['total']} | {format_percentage(stats['pass_rate'])} | [{format_percentage(ci_lower_p)}, {format_percentage(ci_upper_p)}] | {evaluation} | {description} |\n"
        else:
            report += f"| **{pattern_name}** | 0 | 0 | - | - | - | {description} |\n"
    
    report += "\n### 3.2. Patterns Tùy Chọn (Optional Patterns)\n\n"
    report += "| Pattern | Passed | Total | Pass Rate | 95% CI | Đánh giá | Mô tả |\n"
    report += "|---------|--------|-------|-----------|--------|----------|-------|\n"
    
    optional_patterns = {
        'age_star': ('Age → Star (≥30)', 'Items có star >= 3.5 cho users age >= 30'),
        'age_score': ('Age → Score (<30)', 'Items có score >= 9.0 cho users age < 30')
    }
    
    for pattern_key, (pattern_name, description) in optional_patterns.items():
        stats = pattern_stats[pattern_key]
        if stats['total'] > 0:
            ci_lower_p, ci_upper_p = calculate_confidence_interval(stats['pass_rate'], stats['total'])
            evaluation = '✅ Tốt' if stats['pass_rate'] >= 0.6 else '⚠️ Cần cải thiện' if stats['pass_rate'] >= 0.4 else '❌ Yếu'
            report += f"| **{pattern_name}** | {stats['passed']} | {stats['total']} | {format_percentage(stats['pass_rate'])} | [{format_percentage(ci_lower_p)}, {format_percentage(ci_upper_p)}] | {evaluation} | {description} |\n"
        else:
            report += f"| **{pattern_name}** | - | 0 | - | - | N/A | {description} (Không áp dụng) |\n"
    
    report += "\n---\n\n"
    
    # Phân tích theo nhóm
    report += "## 4. PHÂN TÍCH THEO NHÓM USER\n\n"
    
    # Phân tích theo gender
    gender_stats = {'F': {'total': 0, 'passed': 0, 'scores': []}, 'M': {'total': 0, 'passed': 0, 'scores': []}}
    for r in results:
        if r.get('evaluation'):
            gender = r['gender']
            gender_stats[gender]['total'] += 1
            if r['evaluation']['passed']:
                gender_stats[gender]['passed'] += 1
            gender_stats[gender]['scores'].append(r['evaluation']['total_score'])
    
    report += "### 4.1. Phân tích theo Gender\n\n"
    report += "| Gender | Total | Passed | Pass Rate | 95% CI | Avg Score | Avg Accuracy | Đánh giá |\n"
    report += "|--------|-------|--------|-----------|--------|-----------|--------------|----------|\n"
    
    for gender, stats in gender_stats.items():
        if stats['total'] > 0:
            pass_rate = stats['passed'] / stats['total']
            ci_lower_g, ci_upper_g = calculate_confidence_interval(pass_rate, stats['total'])
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0.0
            # Tính avg accuracy cho gender này
            gender_results = [r for r in results if r.get('evaluation') and r['gender'] == gender]
            avg_accuracy = sum(r['evaluation']['accuracy'] for r in gender_results) / len(gender_results) if gender_results else 0.0
            evaluation = '✅ Tốt' if pass_rate >= 0.8 else '⚠️ Cần cải thiện' if pass_rate >= 0.6 else '❌ Yếu'
            report += f"| **{'Nữ' if gender == 'F' else 'Nam'}** | {stats['total']} | {stats['passed']} | {format_percentage(pass_rate)} | [{format_percentage(ci_lower_g)}, {format_percentage(ci_upper_g)}] | {format_float(avg_score)}/4.0 | {format_percentage(avg_accuracy)} | {evaluation} |\n"
    
    report += "\n### 4.2. Phân tích theo Age Group\n\n"
    
    # Phân tích theo age group
    age_groups = {
        '< 30': {'total': 0, 'passed': 0, 'age_range': (0, 30), 'scores': []},
        '30-40': {'total': 0, 'passed': 0, 'age_range': (30, 40), 'scores': []},
        '40-50': {'total': 0, 'passed': 0, 'age_range': (40, 50), 'scores': []},
        '>= 50': {'total': 0, 'passed': 0, 'age_range': (50, 200), 'scores': []}
    }
    
    for r in results:
        if r.get('evaluation'):
            age = r['age']
            for group_name, group_stats in age_groups.items():
                min_age, max_age = group_stats['age_range']
                if min_age <= age < max_age:
                    group_stats['total'] += 1
                    if r['evaluation']['passed']:
                        group_stats['passed'] += 1
                    group_stats['scores'].append(r['evaluation']['total_score'])
                    break
    
    report += "| Age Group | Total | Passed | Pass Rate | 95% CI | Avg Score | Avg Accuracy | Đánh giá |\n"
    report += "|-----------|-------|--------|-----------|--------|-----------|--------------|----------|\n"
    
    for group_name, stats in age_groups.items():
        if stats['total'] > 0:
            pass_rate = stats['passed'] / stats['total']
            ci_lower_a, ci_upper_a = calculate_confidence_interval(pass_rate, stats['total'])
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0.0
            # Tính avg accuracy cho age group này
            age_results = [r for r in results if r.get('evaluation') and stats['age_range'][0] <= r['age'] < stats['age_range'][1]]
            avg_accuracy = sum(r['evaluation']['accuracy'] for r in age_results) / len(age_results) if age_results else 0.0
            evaluation = '✅ Tốt' if pass_rate >= 0.8 else '⚠️ Cần cải thiện' if pass_rate >= 0.6 else '❌ Yếu'
            report += f"| **{group_name}** | {stats['total']} | {stats['passed']} | {format_percentage(pass_rate)} | [{format_percentage(ci_lower_a)}, {format_percentage(ci_upper_a)}] | {format_float(avg_score)}/4.0 | {format_percentage(avg_accuracy)} | {evaluation} |\n"
    
    report += "\n---\n\n"
    
    # Chi tiết từng user
    report += "## 5. CHI TIẾT KẾT QUẢ THEO USER\n\n"
    
    valid_results = [r for r in results if r.get('evaluation')]
    failed_results = [r for r in valid_results if not r['evaluation']['passed']]
    passed_results = [r for r in valid_results if r['evaluation']['passed']]
    
    report += f"### 5.1. Tất cả Users Failed (Cần cải thiện) - Tổng: {len(failed_results)} users\n\n"
    report += "| STT | User ID | Gender | Age | Region | Mandatory Passed | Total Score | Accuracy | Pattern Details |\n"
    report += "|-----|---------|--------|-----|--------|------------------|-------------|----------|----------------|\n"
    
    failed_results_sorted = sorted(failed_results, key=lambda x: x['evaluation']['total_score'])
    
    for idx, r in enumerate(failed_results_sorted, 1):
        eval_result = r['evaluation']
        pattern_details = []
        for pattern_key, score_info in eval_result['pattern_scores'].items():
            if score_info.get('is_mandatory', False):
                status = '✓' if score_info['passed'] else '✗'
                pattern_details.append(f"{status}")
        pattern_str = ' '.join(pattern_details)
        report += f"| {idx} | {r['user_id']} | {r['gender']} | {int(r['age'])} | {r['region']} | {eval_result['mandatory_passed_count']}/3 | {eval_result['total_score']}/4 | {format_percentage(eval_result['accuracy'])} | {pattern_str} |\n"
    
    report += f"\n### 5.2. Tất cả Users Passed (Thành công) - Tổng: {len(passed_results)} users\n\n"
    report += "| STT | User ID | Gender | Age | Region | Mandatory Passed | Total Score | Accuracy | Pattern Details |\n"
    report += "|-----|---------|--------|-----|--------|------------------|-------------|----------|----------------|\n"
    
    passed_results_sorted = sorted(passed_results, key=lambda x: x['evaluation']['total_score'], reverse=True)
    
    for idx, r in enumerate(passed_results_sorted, 1):
        eval_result = r['evaluation']
        pattern_details = []
        for pattern_key, score_info in eval_result['pattern_scores'].items():
            if score_info.get('is_mandatory', False):
                status = '✓' if score_info['passed'] else '✗'
                pattern_details.append(f"{status}")
        pattern_str = ' '.join(pattern_details)
        report += f"| {idx} | {r['user_id']} | {r['gender']} | {int(r['age'])} | {r['region']} | {eval_result['mandatory_passed_count']}/3 | {eval_result['total_score']}/4 | {format_percentage(eval_result['accuracy'])} | {pattern_str} |\n"
    
    report += "\n---\n\n"
    
    # Đánh giá độ tin cậy chi tiết
    report += "## 6. ĐÁNH GIÁ ĐỘ TIN CẬY CHI TIẾT\n\n"
    
    report += "### 6.1. Metrics Độ Tin Cậy\n\n"
    report += "| Metric | Giá trị | Ngưỡng | Đánh giá |\n"
    report += "|--------|---------|--------|----------|\n"
    
    metrics = [
        ('Pass Rate', overall_stats['pass_rate'], 0.8, 'Tỷ lệ users pass test'),
        ('Average Accuracy', overall_stats['avg_accuracy'], 0.7, 'Độ chính xác trung bình'),
        ('Average Score', overall_stats['avg_score'] / 4.0, 0.75, 'Điểm trung bình (normalized)'),
        ('Mandatory Patterns Pass Rate', overall_stats['avg_mandatory_passed'] / 3.0, 0.67, 'Tỷ lệ patterns bắt buộc pass')
    ]
    
    for metric_name, value, threshold, description in metrics:
        passed = '✅ Đạt' if value >= threshold else '⚠️ Chưa đạt'
        report += f"| **{metric_name}** | {format_percentage(value)} | {format_percentage(threshold)} | {passed} |\n"
        report += f"| *({description})* | | | |\n"
    
    report += "\n### 6.2. Phân tích Độ Tin Cậy theo Pattern\n\n"
    report += "| Pattern | Pass Rate | 95% CI | Độ tin cậy | Kết luận |\n"
    report += "|---------|-----------|--------|------------|----------|\n"
    
    all_patterns = {**mandatory_patterns, **optional_patterns}
    for pattern_key, (pattern_name, _) in all_patterns.items():
        stats = pattern_stats[pattern_key]
        if stats['total'] > 0:
            ci_lower_p, ci_upper_p = calculate_confidence_interval(stats['pass_rate'], stats['total'])
            ci_width = ci_upper_p - ci_lower_p
            reliability = 'Cao' if ci_width < 0.15 else 'Trung bình' if ci_width < 0.25 else 'Thấp'
            conclusion = '✅ Đáng tin cậy' if stats['pass_rate'] >= 0.7 else '⚠️ Cần cải thiện' if stats['pass_rate'] >= 0.5 else '❌ Không đáng tin cậy'
            report += f"| {pattern_name} | {format_percentage(stats['pass_rate'])} | [{format_percentage(ci_lower_p)}, {format_percentage(ci_upper_p)}] | {reliability} | {conclusion} |\n"
    
    report += "\n---\n\n"
    
    # Kết luận và khuyến nghị
    report += "## 7. KẾT LUẬN VÀ KHUYẾN NGHỊ\n\n"
    
    report += "### 7.1. Tóm tắt Độ Tin Cậy\n\n"
    
    if overall_stats['pass_rate'] >= 0.8:
        report += "✅ **Hệ thống AI Phase 1 đạt độ tin cậy CAO**\n\n"
        report += f"- Pass rate: {format_percentage(overall_stats['pass_rate'])} (≥ 80% - Đạt yêu cầu)\n"
        report += f"- Confidence interval 95%: [{format_percentage(ci_lower)}, {format_percentage(ci_upper)}]\n"
        report += f"- Average accuracy: {format_percentage(overall_stats['avg_accuracy'])}\n"
        report += f"- Hệ thống có thể được triển khai vào production với độ tin cậy cao.\n\n"
    elif overall_stats['pass_rate'] >= 0.6:
        report += "⚠️ **Hệ thống AI Phase 1 đạt độ tin cậy TRUNG BÌNH**\n\n"
        report += f"- Pass rate: {format_percentage(overall_stats['pass_rate'])} (60-80% - Cần cải thiện)\n"
        report += f"- Confidence interval 95%: [{format_percentage(ci_lower)}, {format_percentage(ci_upper)}]\n"
        report += f"- Average accuracy: {format_percentage(overall_stats['avg_accuracy'])}\n"
        report += f"- Hệ thống cần được cải thiện trước khi triển khai vào production.\n\n"
    else:
        report += "❌ **Hệ thống AI Phase 1 có độ tin cậy THẤP**\n\n"
        report += f"- Pass rate: {format_percentage(overall_stats['pass_rate'])} (< 60% - Không đạt yêu cầu)\n"
        report += f"- Confidence interval 95%: [{format_percentage(ci_lower)}, {format_percentage(ci_upper)}]\n"
        report += f"- Average accuracy: {format_percentage(overall_stats['avg_accuracy'])}\n"
        report += f"- Hệ thống cần được cải thiện đáng kể trước khi triển khai.\n\n"
    
    report += "### 7.2. Điểm Mạnh\n\n"
    
    # Tìm patterns tốt
    good_patterns = [k for k, v in pattern_stats.items() if v['total'] > 0 and v['pass_rate'] >= 0.7]
    if good_patterns:
        report += "- **Patterns hoạt động tốt:**\n"
        for pattern_key in good_patterns:
            pattern_name = all_patterns.get(pattern_key, (pattern_key, ''))[0]
            stats = pattern_stats[pattern_key]
            report += f"  - {pattern_name}: Pass rate {format_percentage(stats['pass_rate'])} ({stats['passed']}/{stats['total']})\n"
        report += "\n"
    
    if overall_stats['avg_accuracy'] >= 0.7:
        report += f"- **Average accuracy cao:** {format_percentage(overall_stats['avg_accuracy'])} - Hệ thống đang recommend items phù hợp với user profiles.\n\n"
    
    report += "### 7.3. Điểm Cần Cải Thiện\n\n"
    
    # Tìm patterns yếu
    weak_patterns = [k for k, v in pattern_stats.items() if v['total'] > 0 and v['pass_rate'] < 0.6]
    if weak_patterns:
        report += "- **Patterns cần cải thiện:**\n"
        for pattern_key in weak_patterns:
            pattern_name = all_patterns.get(pattern_key, (pattern_key, ''))[0]
            stats = pattern_stats[pattern_key]
            report += f"  - {pattern_name}: Pass rate {format_percentage(stats['pass_rate'])} ({stats['passed']}/{stats['total']}) - Cần cải thiện logic matching hoặc tăng số lượng items phù hợp trong dataset.\n"
        report += "\n"
    
    if overall_stats['pass_rate'] < 0.8:
        report += f"- **Pass rate tổng thể:** {format_percentage(overall_stats['pass_rate'])} chưa đạt mục tiêu 80% - Cần điều chỉnh thresholds hoặc cải thiện model.\n\n"
    
    report += "### 7.4. Khuyến Nghị\n\n"
    
    if overall_stats['pass_rate'] >= 0.8:
        report += "1. ✅ **Triển khai vào production:** Hệ thống đã đạt độ tin cậy cao, có thể triển khai.\n"
        report += "2. 📊 **Monitor liên tục:** Theo dõi pass rate và accuracy trong production để đảm bảo chất lượng.\n"
        report += "3. 🔄 **Retrain định kỳ:** Retrain model định kỳ với dữ liệu mới để duy trì chất lượng.\n"
        report += "4. 📈 **Mở rộng test:** Test với nhiều users hơn để đảm bảo tính nhất quán.\n"
    else:
        report += "1. ⚙️ **Điều chỉnh thresholds:** Có thể giảm threshold cho các patterns bắt buộc (từ 20% xuống 15%) để tăng pass rate.\n"
        report += "2. 📦 **Cải thiện dataset:** Thêm nhiều items phù hợp với các patterns (đặc biệt là items có style phù hợp với gender và items có city khớp với region).\n"
        report += "3. 🤖 **Tối ưu model:** Retrain model với hyperparameters khác hoặc thử các models khác (không chỉ DeepFM).\n"
        report += "4. 🔍 **Phân tích sâu hơn:** Xem xét các users failed để tìm pattern chung và cải thiện.\n"
        report += "5. ⏳ **Test lại:** Sau khi cải thiện, test lại với cùng điều kiện để so sánh kết quả.\n"
    
    report += "\n---\n\n"
    report += f"**Báo cáo được tạo tự động vào:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
    report += f"**Bởi:** AI Test Report Generator\n"
    
    # Ghi file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ Đã tạo báo cáo chuyên nghiệp: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Generate markdown report chuyên nghiệp từ kết quả test')
    parser.add_argument('input_json', type=str, help='File JSON chứa kết quả test')
    parser.add_argument('output_md', type=str, help='File markdown output')
    
    args = parser.parse_args()
    
    # Đọc JSON
    with open(args.input_json, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    # Generate report
    generate_markdown_report(summary, args.output_md)


if __name__ == '__main__':
    main()
