import re
import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

def parse_log_file(log_file_path):
    """解析日志文件，提取关键信息"""
    
    # 存储解析结果的数据结构
    data = {
        'timestamps': [],
        'token_usage': [],
        'throughput': [],
        'running_requests': [],
        'http_responses': [],
        'prefill_batches': [],
        'decode_batches': []
    }
    
    # 正则表达式模式
    timestamp_pattern = r'\[(.*?)\]'
    token_usage_pattern = r'token usage: ([\d.]+)'
    throughput_pattern = r'gen throughput \(token/s\): ([\d.]+)'
    running_req_pattern = r'#running-req: (\d+)'
    http_response_pattern = r'HTTP/1\.1" (\d+) OK'
    
    with open(log_file_path, 'r') as file:
        for line in file:
            # 提取时间戳
            timestamp_match = re.search(timestamp_pattern, line)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                if 'TP0' not in timestamp:  # 只处理主要时间戳，不处理TP0
                    data['timestamps'].append(timestamp)
            
            # 提取token使用量
            token_usage_match = re.search(token_usage_pattern, line)
            if token_usage_match:
                token_usage = float(token_usage_match.group(1))
                data['token_usage'].append(token_usage)
            
            # 提取吞吐量
            throughput_match = re.search(throughput_pattern, line)
            if throughput_match:
                throughput = float(throughput_match.group(1))
                data['throughput'].append(throughput)
            
            # 提取运行中的请求数
            running_req_match = re.search(running_req_pattern, line)
            if running_req_match:
                running_req = int(running_req_match.group(1))
                data['running_requests'].append(running_req)
            
            # 提取HTTP响应
            http_response_match = re.search(http_response_pattern, line)
            if http_response_match:
                status_code = http_response_match.group(1)
                data['http_responses'].append(status_code)
            
            # 记录Prefill批次
            if 'Prefill batch' in line:
                data['prefill_batches'].append(line.strip())
            
            # 记录Decode批次
            if 'Decode batch' in line:
                data['decode_batches'].append(line.strip())
    
    return data

def analyze_data(data):
    """分析提取的数据，生成统计信息"""
    
    analysis = {}
    
    # 计算总请求数
    analysis['total_http_responses'] = len(data['http_responses'])
    
    # 计算最大并发请求数
    if data['running_requests']:
        analysis['max_concurrent_requests'] = max(data['running_requests'])
    else:
        analysis['max_concurrent_requests'] = 0
    
    # 计算平均吞吐量
    if data['throughput']:
        analysis['avg_throughput'] = sum(data['throughput']) / len(data['throughput'])
        analysis['max_throughput'] = max(data['throughput'])
        analysis['min_throughput'] = min(data['throughput'])
    else:
        analysis['avg_throughput'] = 0
        analysis['max_throughput'] = 0
        analysis['min_throughput'] = 0
    
    # 计算最大token使用量
    if data['token_usage']:
        analysis['max_token_usage'] = max(data['token_usage'])
    else:
        analysis['max_token_usage'] = 0
    
    # 计算测试持续时间
    if len(data['timestamps']) >= 2:
        try:
            start_time = datetime.datetime.strptime(data['timestamps'][0], '%Y-%m-%d %H:%M:%S')
            end_time = datetime.datetime.strptime(data['timestamps'][-1], '%Y-%m-%d %H:%M:%S')
            duration = (end_time - start_time).total_seconds()
            analysis['test_duration_seconds'] = duration
        except ValueError:
            analysis['test_duration_seconds'] = 0
    else:
        analysis['test_duration_seconds'] = 0
    
    # 分析Prefill和Decode批次数量
    analysis['prefill_batch_count'] = len(data['prefill_batches'])
    analysis['decode_batch_count'] = len(data['decode_batches'])
    
    return analysis

def generate_report(data, analysis):
    """生成测试报告"""
    
    report = []
    report.append("=" * 50)
    report.append("SGLang 并发请求测试报告")
    report.append("=" * 50)
    report.append("")
    
    report.append(f"测试持续时间: {analysis['test_duration_seconds']:.2f} 秒")
    report.append(f"总HTTP响应数: {analysis['total_http_responses']}")
    report.append(f"最大并发请求数: {analysis['max_concurrent_requests']}")
    report.append("")
    
    report.append("吞吐量统计:")
    report.append(f"  - 平均吞吐量: {analysis['avg_throughput']:.2f} token/s")
    report.append(f"  - 最大吞吐量: {analysis['max_throughput']:.2f} token/s")
    report.append(f"  - 最小吞吐量: {analysis['min_throughput']:.2f} token/s")
    report.append("")
    
    report.append(f"最大Token使用量: {analysis['max_token_usage']:.2f}")
    report.append(f"Prefill批次数量: {analysis['prefill_batch_count']}")
    report.append(f"Decode批次数量: {analysis['decode_batch_count']}")
    report.append("")
    
    # 计算请求完成时间分布
    if data['timestamps']:
        report.append("HTTP响应时间分布:")
        for i, timestamp in enumerate(data['timestamps']):
            if i < analysis['total_http_responses']:
                report.append(f"  - 请求 {i+1}: {timestamp}")
    
    report.append("")
    report.append("=" * 50)
    
    return "\n".join(report)

def analyze_sglang_performance(data):
    """专门分析SGLang的并发请求性能"""
    
    performance = {}
    
    # 分析并发请求处理情况
    if data['running_requests']:
        # 计算并发请求数的变化
        req_changes = []
        for i in range(1, len(data['running_requests'])):
            req_changes.append(data['running_requests'][i] - data['running_requests'][i-1])
        
        # 计算请求增长和减少的次数
        performance['request_increases'] = sum(1 for change in req_changes if change > 0)
        performance['request_decreases'] = sum(1 for change in req_changes if change < 0)
        
        # 计算并发请求数的平均值
        performance['avg_concurrent_requests'] = sum(data['running_requests']) / len(data['running_requests'])
        
        # 计算并发请求数的标准差（衡量稳定性）
        if len(data['running_requests']) > 1:
            performance['request_std_dev'] = np.std(data['running_requests'])
        else:
            performance['request_std_dev'] = 0
    else:
        performance['request_increases'] = 0
        performance['request_decreases'] = 0
        performance['avg_concurrent_requests'] = 0
        performance['request_std_dev'] = 0
    
    # 分析吞吐量的稳定性
    if data['throughput']:
        # 计算吞吐量的标准差
        performance['throughput_std_dev'] = np.std(data['throughput'])
        
        # 计算吞吐量的变化率
        throughput_changes = []
        for i in range(1, len(data['throughput'])):
            if data['throughput'][i-1] > 0:
                change_rate = (data['throughput'][i] - data['throughput'][i-1]) / data['throughput'][i-1]
                throughput_changes.append(change_rate)
        
        if throughput_changes:
            performance['avg_throughput_change_rate'] = sum(throughput_changes) / len(throughput_changes)
            performance['max_throughput_change_rate'] = max(throughput_changes)
            performance['min_throughput_change_rate'] = min(throughput_changes)
        else:
            performance['avg_throughput_change_rate'] = 0
            performance['max_throughput_change_rate'] = 0
            performance['min_throughput_change_rate'] = 0
    else:
        performance['throughput_std_dev'] = 0
        performance['avg_throughput_change_rate'] = 0
        performance['max_throughput_change_rate'] = 0
        performance['min_throughput_change_rate'] = 0
    
    # 分析Prefill和Decode批次的比例
    total_batches = len(data['prefill_batches']) + len(data['decode_batches'])
    if total_batches > 0:
        performance['prefill_ratio'] = len(data['prefill_batches']) / total_batches
        performance['decode_ratio'] = len(data['decode_batches']) / total_batches
    else:
        performance['prefill_ratio'] = 0
        performance['decode_ratio'] = 0
    
    # 分析HTTP响应的分布
    if data['timestamps']:
        # 计算响应时间间隔
        response_intervals = []
        for i in range(1, min(len(data['timestamps']), len(data['http_responses']))):
            try:
                time1 = datetime.datetime.strptime(data['timestamps'][i-1], '%Y-%m-%d %H:%M:%S')
                time2 = datetime.datetime.strptime(data['timestamps'][i], '%Y-%m-%d %H:%M:%S')
                interval = (time2 - time1).total_seconds()
                response_intervals.append(interval)
            except ValueError:
                continue
        
        if response_intervals:
            performance['avg_response_interval'] = sum(response_intervals) / len(response_intervals)
            performance['max_response_interval'] = max(response_intervals)
            performance['min_response_interval'] = min(response_intervals)
        else:
            performance['avg_response_interval'] = 0
            performance['max_response_interval'] = 0
            performance['min_response_interval'] = 0
    else:
        performance['avg_response_interval'] = 0
        performance['max_response_interval'] = 0
        performance['min_response_interval'] = 0
    
    return performance

def extend_report_with_performance(report, performance):
    """使用性能分析结果扩展报告"""
    
    extended_report = report.split("\n")
    
    # 在报告末尾添加性能分析结果
    extended_report.append("")
    extended_report.append("SGLang 并发性能分析")
    extended_report.append("-" * 30)
    extended_report.append("")
    
    extended_report.append("并发请求分析:")
    extended_report.append(f"  - 平均并发请求数: {performance['avg_concurrent_requests']:.2f}")
    extended_report.append(f"  - 并发请求数标准差: {performance['request_std_dev']:.2f}")
    extended_report.append(f"  - 请求增加次数: {performance['request_increases']}")
    extended_report.append(f"  - 请求减少次数: {performance['request_decreases']}")
    extended_report.append("")
    
    extended_report.append("吞吐量稳定性分析:")
    extended_report.append(f"  - 吞吐量标准差: {performance['throughput_std_dev']:.2f}")
    extended_report.append(f"  - 平均吞吐量变化率: {performance['avg_throughput_change_rate']*100:.2f}%")
    extended_report.append(f"  - 最大吞吐量变化率: {performance['max_throughput_change_rate']*100:.2f}%")
    extended_report.append(f"  - 最小吞吐量变化率: {performance['min_throughput_change_rate']*100:.2f}%")
    extended_report.append("")
    
    extended_report.append("批次处理分析:")
    extended_report.append(f"  - Prefill批次比例: {performance['prefill_ratio']*100:.2f}%")
    extended_report.append(f"  - Decode批次比例: {performance['decode_ratio']*100:.2f}%")
    extended_report.append("")
    
    extended_report.append("响应时间分析:")
    extended_report.append(f"  - 平均响应间隔: {performance['avg_response_interval']:.2f} 秒")
    extended_report.append(f"  - 最大响应间隔: {performance['max_response_interval']:.2f} 秒")
    extended_report.append(f"  - 最小响应间隔: {performance['min_response_interval']:.2f} 秒")
    extended_report.append("")
    
    extended_report.append("=" * 50)
    
    return "\n".join(extended_report)

def analyze_request_efficiency(data):
    """分析并发请求的响应时间和处理效率"""
    
    efficiency = {}
    
    # 提取HTTP响应时间
    http_response_times = []
    for line in data['prefill_batches'] + data['decode_batches']:
        if 'HTTP/1.1" 200 OK' in line:
            timestamp_match = re.search(r'\[(.*?)\]', line)
            if timestamp_match:
                http_response_times.append(timestamp_match.group(1))
    
    # 计算每秒处理的请求数
    if len(http_response_times) >= 2:
        try:
            start_time = datetime.datetime.strptime(http_response_times[0], '%Y-%m-%d %H:%M:%S')
            end_time = datetime.datetime.strptime(http_response_times[-1], '%Y-%m-%d %H:%M:%S')
            duration = (end_time - start_time).total_seconds()
            if duration > 0:
                efficiency['requests_per_second'] = len(http_response_times) / duration
            else:
                efficiency['requests_per_second'] = 0
        except ValueError:
            efficiency['requests_per_second'] = 0
    else:
        efficiency['requests_per_second'] = 0
    
    # 分析token处理效率
    if data['token_usage'] and data['timestamps']:
        try:
            start_time = datetime.datetime.strptime(data['timestamps'][0], '%Y-%m-%d %H:%M:%S')
            end_time = datetime.datetime.strptime(data['timestamps'][-1], '%Y-%m-%d %H:%M:%S')
            duration = (end_time - start_time).total_seconds()
            
            if duration > 0 and data['token_usage']:
                # 计算每秒处理的token数
                total_tokens = data['token_usage'][-1] * 1000  # 转换为实际token数
                efficiency['tokens_per_second'] = total_tokens / duration
            else:
                efficiency['tokens_per_second'] = 0
        except (ValueError, IndexError):
            efficiency['tokens_per_second'] = 0
    else:
        efficiency['tokens_per_second'] = 0
    
    # 分析并发请求的峰值持续时间
    if data['running_requests']:
        max_requests = max(data['running_requests'])
        max_request_indices = [i for i, req in enumerate(data['running_requests']) if req == max_requests]
        
        if max_request_indices:
            # 计算峰值持续的时间点数量
            efficiency['peak_duration_points'] = len(max_request_indices)
            
            # 估算峰值持续时间（假设每个时间点间隔约为1秒）
            efficiency['estimated_peak_duration'] = efficiency['peak_duration_points']
            
            # 计算达到峰值的时间点
            efficiency['time_to_peak'] = max_request_indices[0]
        else:
            efficiency['peak_duration_points'] = 0
            efficiency['estimated_peak_duration'] = 0
            efficiency['time_to_peak'] = 0
    else:
        efficiency['peak_duration_points'] = 0
        efficiency['estimated_peak_duration'] = 0
        efficiency['time_to_peak'] = 0
    
    # 计算请求完成率
    total_requests = len(data['http_responses'])
    if data['running_requests']:
        max_concurrent = max(data['running_requests'])
        if max_concurrent > 0:
            efficiency['completion_rate'] = total_requests / max_concurrent
        else:
            efficiency['completion_rate'] = 0
    else:
        efficiency['completion_rate'] = 0
    
    return efficiency

def extend_report_with_efficiency(report, efficiency):
    """使用效率分析结果扩展报告"""
    
    extended_report = report.split("\n")
    
    # 在报告末尾添加效率分析结果
    extended_report.append("")
    extended_report.append("并发请求效率分析")
    extended_report.append("-" * 30)
    extended_report.append("")
    
    extended_report.append("请求处理效率:")
    extended_report.append(f"  - 每秒处理请求数: {efficiency['requests_per_second']:.2f} 请求/秒")
    extended_report.append(f"  - 每秒处理Token数: {efficiency['tokens_per_second']:.2f} token/秒")
    extended_report.append("")
    
    extended_report.append("峰值负载分析:")
    extended_report.append(f"  - 达到峰值的时间点: 第 {efficiency['time_to_peak']} 个时间点")
    extended_report.append(f"  - 峰值持续的时间点数量: {efficiency['peak_duration_points']}")
    extended_report.append(f"  - 估计峰值持续时间: 约 {efficiency['estimated_peak_duration']} 秒")
    extended_report.append("")
    
    extended_report.append("请求完成情况:")
    extended_report.append(f"  - 请求完成率: {efficiency['completion_rate']:.2f}")
    extended_report.append("")
    
    extended_report.append("=" * 50)
    
    return "\n".join(extended_report)

def analyze_cached_tokens(data):
    """分析缓存Token的使用情况"""
    cached_token_pattern = r'#cached-token: (\d+)'
    new_token_pattern = r'#new-token: (\d+)'
    batch_cache_hit_rates = []
    
    # 提取每个批次的缓存token和新token数量，并计算每个批次的缓存命中率
    for line in data['prefill_batches'] + data['decode_batches']:
        cached_match = re.search(cached_token_pattern, line)
        new_match = re.search(new_token_pattern, line)
        
        if cached_match and new_match:
            cached_tokens = int(cached_match.group(1))
            new_tokens = int(new_match.group(1))
            total_tokens = cached_tokens + new_tokens
            
            if total_tokens > 0:
                cache_hit_rate = cached_tokens / total_tokens
                batch_info = {
                    'line': line,
                    'cached_tokens': cached_tokens,
                    'new_tokens': new_tokens,
                    'total_tokens': total_tokens,
                    'cache_hit_rate': cache_hit_rate
                }
                batch_cache_hit_rates.append(batch_info)
    
    # 计算整体缓存命中率
    total_cached = sum(batch['cached_tokens'] for batch in batch_cache_hit_rates) if batch_cache_hit_rates else 0
    total_new = sum(batch['new_tokens'] for batch in batch_cache_hit_rates) if batch_cache_hit_rates else 0
    total_tokens = total_cached + total_new
    overall_cache_hit_rate = total_cached / total_tokens if total_tokens > 0 else 0
    
    return {
        'batch_cache_hit_rates': batch_cache_hit_rates,
        'overall_cache_hit_rate': overall_cache_hit_rate,
        'total_batches': len(batch_cache_hit_rates)
    }

def extend_report_with_cached_tokens(report, cached_data):
    """使用缓存Token分析结果扩展报告"""
    
    extended_report = report.split("\n")
    
    # 在报告末尾添加缓存Token分析结果
    extended_report.append("")
    extended_report.append("缓存Token命中率分析")
    extended_report.append("-" * 30)
    extended_report.append("")
    
    # 添加整体缓存命中率
    extended_report.append(f"总批次数: {cached_data['total_batches']}")
    extended_report.append(f"整体缓存命中率: {cached_data['overall_cache_hit_rate']*100:.2f}%")
    extended_report.append("")
    
    # 添加每个批次的缓存命中率
    extended_report.append("各批次缓存命中率:")
    
    # 只显示前20个批次，避免报告过长
    max_display = min(20, len(cached_data['batch_cache_hit_rates']))
    for i in range(max_display):
        batch = cached_data['batch_cache_hit_rates'][i]
        extended_report.append(f"  - 批次 {i+1}: 缓存Token: {batch['cached_tokens']}, " +
                              f"新Token: {batch['new_tokens']}, " +
                              f"命中率: {batch['cache_hit_rate']*100:.2f}%")
    
    # 如果批次数量超过显示限制，添加提示信息
    if len(cached_data['batch_cache_hit_rates']) > max_display:
        remaining = len(cached_data['batch_cache_hit_rates']) - max_display
        extended_report.append(f"  ... 还有 {remaining} 个批次未显示")
    
    extended_report.append("")
    extended_report.append("=" * 50)
    
    return "\n".join(extended_report)

def main():
    log_file_path = 'log.txt'
    
    print("开始解析日志文件...")
    # 解析日志文件
    data = parse_log_file(log_file_path)
    print(f"日志解析完成，提取了 {len(data['timestamps'])} 个时间戳，{len(data['running_requests'])} 个并发请求数据点")
    
    print("开始分析数据...")
    # 分析数据
    analysis = analyze_data(data)
    print("基础数据分析完成")
    
    # 生成基础报告
    report = generate_report(data, analysis)
    
    try:
        print("开始分析SGLang性能...")
        # 分析SGLang性能
        performance = analyze_sglang_performance(data)
        print("SGLang性能分析完成")
        
        # 扩展报告
        extended_report = extend_report_with_performance(report, performance)
    except Exception as e:
        print(f"分析SGLang性能时出错: {e}")
        extended_report = report
    
    try:
        print("开始分析请求效率...")
        # 分析请求效率
        efficiency = analyze_request_efficiency(data)
        print("请求效率分析完成")
        
        # 进一步扩展报告
        final_report = extend_report_with_efficiency(extended_report, efficiency)
    except Exception as e:
        print(f"分析请求效率时出错: {e}")
        final_report = extended_report

    try:
        print("开始分析cache token...")
        # 分析缓存Token
        cached_data = analyze_cached_tokens(data)
        print("cache token分析完成")

        # 进一步扩展报告
        final_report = extend_report_with_cached_tokens(final_report, cached_data)
    except Exception as e:
        print(f"分析cache token时出错: {e}")
        # final_report保持不变
    
    # 打印报告
    print("\n" + "="*50)
    print("测试报告生成完成:")
    print("="*50 + "\n")

    # 将报告保存到文件
    try:
        with open('test_report.txt', 'w', encoding='utf-8') as f:
            f.write(final_report)
        print(f"报告已保存到 test_report.txt")
    except Exception as e:
        print(f"保存报告时出错: {e}")
        print("报告内容:")
        print(final_report)
    return


if __name__ == "__main__":
    main() 