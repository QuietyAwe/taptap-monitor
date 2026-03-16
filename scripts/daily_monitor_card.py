#!/usr/bin/env python3
"""
TapTap 每日监控任务（数据抓取与初筛版）
1. 获取最新帖子和评价
2. 生成默认占位回复，存入待处理队列
3. 推送数据汇总通知（不发单条卡片）
"""

import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# 路径配置
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
WORKSPACE_DIR = SKILL_DIR.parent.parent
DATA_FILE = SKILL_DIR / "data" / "236096_data.json"
PENDING_FILE = SKILL_DIR / "data" / "pending_replies.json"

sys.path.insert(0, str(SKILL_DIR / "scripts"))
from taptap_monitor import TapTapMonitor
from caiwang_reply import generate_reply, should_skip

MODERATORS = {"homie"}

def extract_id(url):
    return url.rstrip("/").split("/")[-1]

def get_latest_data():
    monitor = TapTapMonitor(app_id="236096", data_file=str(DATA_FILE))
    raw_topics = monitor.fetch_topics(10)
    raw_reviews = monitor.fetch_reviews(10)
    
    new_topics = monitor._add_new_topics(raw_topics)
    new_reviews = monitor._add_new_reviews(raw_reviews)
    monitor._save_data()
    return new_topics, new_reviews

def main():
    print(f"[{datetime.now()}] 开始 TapTap 监控与抓取...")
    topics, reviews = get_latest_data()
    
    if not topics and not reviews:
        print("无新内容，结束")
        return
    
    pending_items = []
    index = 1
    
    for r in reviews:
        rid = str(r.get("id", extract_id(r.get("link", ""))))
        reply_content = generate_reply(r, "review")
        pending_items.append({
            "index": index,
            "type": "review",
            "id": rid,
            "url": r.get("link", f"https://www.taptap.cn/review/{rid}"),
            "rating": r.get("rating", ""),
            "author": r.get("author", ""),
            "content": r.get("content", "")[:100] + "..." if len(r.get("content", "")) > 100 else r.get("content", ""),
            "played_hours": r.get("played_hours", ""),
            "reply_content": reply_content,
            "create_time": r.get("create_time", datetime.now().strftime('%m-%d %H:%M'))
        })
        index += 1
    
    for t in topics:
        title = t.get("title", "")
        author = t.get("author", "")
        if author in MODERATORS or should_skip(title):
            continue
            
        reply_content = generate_reply(t, "topic")
        if not reply_content:
            continue
            
        pending_items.append({
            "index": index,
            "type": "topic",
            "id": extract_id(t.get("link", "")),
            "url": t.get("link", ""),
            "title": title,
            "author": author,
            "content": title,
            "reply_content": reply_content,
            "create_time": t.get("create_time", datetime.now().strftime('%m-%d %H:%M'))
        })
        index += 1
    
    if not pending_items:
        return
        
    pending_items = pending_items[:15]
    
    # 保存待办，供后续 AI 节点读取
    PENDING_FILE.write_text(json.dumps({
        "created_at": datetime.now().isoformat(),
        "items": pending_items
    }, ensure_ascii=False, indent=2))
    
    # 统计并发送汇总消息
    positive = sum(1 for r in reviews if "5星" in r.get("rating", "") or "4星" in r.get("rating", ""))
    negative = sum(1 for r in reviews if "1星" in r.get("rating", "") or "2星" in r.get("rating", ""))
    neutral = len(reviews) - positive - negative
    
    summary = f"📢 **《盲盒派对》TapTap 每日监控** ({datetime.now().strftime('%m-%d %H:%M')})\n\n"
    summary += f"📊 本次新增: **{len(topics)}** 条帖子, **{len(reviews)}** 条评价\n"
    summary += f"📝 需回复: **{len(pending_items)}** 条（已存入队列，等待菜汪 AI 润色）"
    
    dingtalk_script = WORKSPACE_DIR / "skills" / "dingtalk-push" / "notify.py"
    try:
        subprocess.run(["python3", str(dingtalk_script)], input=summary, capture_output=True, text=True, timeout=30)
        print("汇总消息已发送，等待 AI 技能处理...")
    except Exception as e:
        print(f"汇总消息发送失败: {e}")

if __name__ == "__main__":
    main()