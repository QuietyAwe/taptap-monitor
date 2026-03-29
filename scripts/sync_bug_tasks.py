#!/usr/bin/env python3
"""
同步 Bug 任务状态
从钉钉 API 查询未完成任务的状态并更新 bug_tasks.md
"""

import sys
import os
import re
from datetime import datetime, timezone, timedelta

# 尝试导入钉钉任务模块（可选依赖）
try:
    # 优先从环境变量获取路径
    dingtalk_task_path = os.environ.get('DINGTALK_TASK_PATH')
    if dingtalk_task_path:
        sys.path.insert(0, dingtalk_task_path)
        import task as dingtalk_task
    else:
        dingtalk_task = None
except ImportError:
    dingtalk_task = None

# 文件路径
BUG_TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "bug_tasks.md")

# 状态映射
STATUS_MAP = {
    "待处理": "待处理",
    "进行中": "进行中", 
    "已完成": "已完成"
}

def parse_bug_tasks_table(content):
    """解析 bug_tasks.md 中的表格"""
    lines = content.split('\n')
    tasks = []
    in_table = False
    
    for i, line in enumerate(lines):
        # 检测表头行
        if line.startswith('| 日期') or line.startswith('|日期'):
            in_table = True
            continue
        
        # 跳过分隔行
        if in_table and line.startswith('|:') or line.startswith('| :'):
            continue
        
        # 解析数据行
        if in_table and line.startswith('|'):
            parts = [p.strip() for p in line.split('|')]
            # parts[0] 是空的（行首的 |），所以有效数据从 parts[1] 开始
            if len(parts) >= 7:
                task_id = parts[2].strip()
                # 跳过无效行
                if task_id and task_id != 'taskId':
                    tasks.append({
                        'line_idx': i,
                        'date': parts[1],
                        'task_id': task_id,
                        'desc': parts[3],
                        'severity': parts[4],
                        'status': parts[5] if len(parts) > 5 else '待处理',
                        'progress': parts[6] if len(parts) > 6 else '-',
                        'raw_line': line
                    })
    
    return tasks

def get_task_progress(task_data):
    """从任务数据中提取进展信息"""
    progress = "-"
    
    # 从 customFields 中提取进展备注
    custom_fields = task_data.get('customFields', [])
    for field in custom_fields:
        value = field.get('value', [])
        if value and isinstance(value, list) and len(value) > 0:
            title = value[0].get('title', '')
            # 查找包含评论的字段（通常有用户名前缀）
            if '发表' in title or ':' in title:
                progress = title
                break
    
    return progress

def sync_task_status(task_id):
    """查询单个任务的状态"""
    if task_id == "创建失败":
        return None, None
    
    result = dingtalk_task.get_task(task_id)
    
    if isinstance(result, dict) and 'error' not in result:
        is_done = result.get('isDone', False)
        status = "已完成" if is_done else "进行中"
        progress = get_task_progress(result)
        return status, progress
    
    return None, None

def update_bug_tasks_file(tasks, header_lines, original_content):
    """更新 bug_tasks.md 文件"""
    lines = original_content.split('\n')
    
    for task in tasks:
        if task['status'] != '已完成' and task['task_id'] != '创建失败':
            new_status, new_progress = sync_task_status(task['task_id'])
            
            if new_status:
                task['status'] = new_status
                task['progress'] = new_progress if new_progress else task['progress']
                
                # 更新行
                new_line = f"| {task['date']} | {task['task_id']} | {task['desc']} | {task['severity']} | {task['status']} | {task['progress']} |"
                lines[task['line_idx']] = new_line
    
    return '\n'.join(lines)

def main():
    """主函数"""
    # 读取文件
    if not os.path.exists(BUG_TASKS_FILE):
        print(f"文件不存在: {BUG_TASKS_FILE}")
        return
    
    with open(BUG_TASKS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析表格
    tasks = parse_bug_tasks_table(content)
    
    if not tasks:
        print("未找到任务记录")
        return
    
    # 统计
    total = len(tasks)
    pending = sum(1 for t in tasks if t['status'] == '待处理')
    in_progress = sum(1 for t in tasks if t['status'] == '进行中')
    completed = sum(1 for t in tasks if t['status'] == '已完成')
    
    print(f"任务统计: 总计 {total} | 待处理 {pending} | 进行中 {in_progress} | 已完成 {completed}")
    
    # 同步未完成任务状态
    updated_count = 0
    for task in tasks:
        if task['status'] != '已完成' and task['task_id'] != '创建失败':
            new_status, new_progress = sync_task_status(task['task_id'])
            
            if new_status and new_status != task['status']:
                task['status'] = new_status
                task['progress'] = new_progress if new_progress else task['progress']
                updated_count += 1
                print(f"  更新: {task['task_id'][:8]}... -> {new_status}")
    
    # 写回文件
    lines = content.split('\n')
    for task in tasks:
        new_line = f"| {task['date']} | {task['task_id']} | {task['desc']} | {task['severity']} | {task['status']} | {task['progress']} |"
        lines[task['line_idx']] = new_line
    
    with open(BUG_TASKS_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"同步完成，更新了 {updated_count} 条任务状态")

if __name__ == "__main__":
    main()