#!/usr/bin/env python3
"""
生成每日舆情日报数据
自动统计昨日 18:00 至今日 18:00 的监控数据
"""

import csv
import json
import os
import re
from datetime import datetime, timedelta
from collections import Counter

# 文件路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
MONITOR_LOG = os.path.join(DATA_DIR, "monitor_log.csv")
BUG_TASKS_FILE = os.path.join(DATA_DIR, "bug_tasks.md")

# 社区情绪分类映射
SENTIMENT_MAP = {
    "正面": "正面",
    "正面/建议": "正面",
    "正面/二创": "正面",
    "负面": "负面",
    "负面-可转化": "负面",
    "中立/建议": "中立",
    "中立/信息分享": "中立",
    "Bug": "负面",
    "[Bug]": "负面",
    "Bug-显示异常": "负面",
    "官方贴": None,  # 官方贴不计入情绪
    "官方贴/水贴": None,
    "水贴": None,
    "水贴/广告": None,
}


def get_time_range():
    """获取统计时间范围：昨日 18:00 至今日 18:00
    
    日报任务在每日 18:00 执行，统计过去 24 小时的数据。
    无论当前时间是 18:00 刚过还是更晚，都应该统计昨日 18:00 到今日 18:00。
    """
    now = datetime.now()
    today_18 = now.replace(hour=18, minute=0, second=0, microsecond=0)
    
    # 统计范围固定为：昨日 18:00 → 今日 18:00
    end_time = today_18
    start_time = end_time - timedelta(days=1)
    
    return start_time, end_time


def parse_csv_datetime(dt_str):
    """解析 CSV 中的时间字符串"""
    try:
        # 格式: "2026-03-19 10:49"
        return datetime.strptime(dt_str.strip('"'), "%Y-%m-%d %H:%M")
    except:
        return None


def read_monitor_log(start_time, end_time):
    """读取监控台账，筛选时间范围内的记录"""
    records = []
    
    if not os.path.exists(MONITOR_LOG):
        return records
    
    with open(MONITOR_LOG, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            create_time = parse_csv_datetime(row.get('create_time', ''))
            if create_time and start_time <= create_time < end_time:
                records.append({
                    'create_time': row.get('create_time', ''),
                    'source_type': row.get('source_type', ''),
                    'content': row.get('content', ''),
                    'content_summary': row.get('content_summary', ''),
                    'severity': row.get('severity', ''),
                    'category': row.get('category', ''),
                    'ai_suggestion': row.get('ai_suggestion', ''),
                    'author': row.get('author', ''),
                    'url': row.get('url', '')
                })
    
    return records


def parse_bug_tasks():
    """解析 bug_tasks.md 获取 Bug 任务状态"""
    tasks = []
    
    if not os.path.exists(BUG_TASKS_FILE):
        return tasks
    
    with open(BUG_TASKS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    for line in lines:
        # 跳过表头和分隔行
        if line.startswith('| 日期') or line.startswith('|:'):
            continue
        if line.startswith('|'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 7:
                # 跳过分隔行（包含 :--- 的行）
                if ':---' in line or ':--' in line:
                    continue
                tasks.append({
                    'date': parts[1],
                    'task_id': parts[2],
                    'desc': parts[3],
                    'severity': parts[4],
                    'status': parts[5] if len(parts) > 5 else '待处理',
                    'progress': parts[6] if len(parts) > 6 else '-'
                })
    
    return tasks


def calculate_statistics(records):
    """计算统计数据"""
    # 总量统计
    total = len(records)
    
    # 定级分布
    severity_counter = Counter(r['severity'] for r in records)
    
    # 分类分布
    category_counter = Counter(r['category'] for r in records)
    
    # 社区情绪统计
    sentiment_counter = Counter()
    for r in records:
        category = r['category']
        sentiment = SENTIMENT_MAP.get(category, '中立')
        if sentiment:
            sentiment_counter[sentiment] += 1
    
    # 计算情绪百分比
    sentiment_total = sum(sentiment_counter.values())
    sentiment_pct = {}
    if sentiment_total > 0:
        for k, v in sentiment_counter.items():
            sentiment_pct[k] = round(v / sentiment_total * 100, 1)
    
    # P0/P1 事件列表
    high_priority = []
    for r in records:
        if r['severity'] in ['P0', 'P1']:
            high_priority.append({
                'summary': r['content_summary'],
                'severity': r['severity'],
                'category': r['category'],
                'content': r['content'][:100] + '...' if len(r['content']) > 100 else r['content'],
                'url': r['url'],
                'author': r['author']
            })
    
    return {
        'total': total,
        'severity': dict(severity_counter),
        'category': dict(category_counter),
        'sentiment': dict(sentiment_counter),
        'sentiment_pct': sentiment_pct,
        'high_priority': high_priority
    }


def generate_report():
    """生成日报数据"""
    start_time, end_time = get_time_range()
    
    # 读取记录
    records = read_monitor_log(start_time, end_time)
    
    # 读取 Bug 任务状态
    bug_tasks = parse_bug_tasks()
    
    # 计算统计
    stats = calculate_statistics(records)
    
    # 生成报告
    report = {
        'time_range': {
            'start': start_time.strftime('%Y-%m-%d %H:%M'),
            'end': end_time.strftime('%Y-%m-%d %H:%M')
        },
        'statistics': stats,
        'bug_tasks': bug_tasks,
        'records': records  # 完整记录，供后续分析使用
    }
    
    return report


def main():
    """主函数"""
    report = generate_report()
    
    # 输出 JSON
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()