#!/usr/bin/env python3
"""
追加 Bug 任务记录到 bug_tasks.md
确保格式正确，避免损坏表格
"""

import sys
import os
from datetime import datetime

BUG_TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "bug_tasks.md")

def append_task(date: str, task_id: str, desc: str, severity: str, status: str = "待处理", progress: str = "-"):
    """
    追加一条任务记录
    
    Args:
        date: 日期 (YYYY-MM-DD)
        task_id: 钉钉任务ID
        desc: 任务描述
        severity: 定级 (P0/P1/P2)
        status: 状态 (待处理/进行中/已完成)
        progress: 最新进展
    """
    # 读取现有内容
    if os.path.exists(BUG_TASKS_FILE):
        with open(BUG_TASKS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = ""
    
    # 确保文件末尾有换行
    if content and not content.endswith('\n'):
        content += '\n'
    
    # 构建新行
    new_line = f"| {date} | {task_id} | {desc} | {severity} | {status} | {progress} |"
    
    # 追加
    content += new_line + '\n'
    
    # 写回
    with open(BUG_TASKS_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已追加任务: {task_id} - {desc}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="追加 Bug 任务记录")
    parser.add_argument("--date", "-d", required=True, help="日期 (YYYY-MM-DD)")
    parser.add_argument("--task-id", "-t", required=True, help="任务ID")
    parser.add_argument("--desc", required=True, help="任务描述")
    parser.add_argument("--severity", "-s", required=True, choices=["P0", "P1", "P2"], help="定级")
    parser.add_argument("--status", default="待处理", help="状态")
    parser.add_argument("--progress", "-p", default="-", help="进展")
    
    args = parser.parse_args()
    
    append_task(
        date=args.date,
        task_id=args.task_id,
        desc=args.desc,
        severity=args.severity,
        status=args.status,
        progress=args.progress
    )

if __name__ == "__main__":
    main()