#!/usr/bin/env python3
"""
TapTap 每日监控任务
1. 获取最新帖子和评价
2. 生成菜汪风格回复建议
3. 保存到待确认文件
4. 推送到钉钉
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# 路径配置
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent  # skills/taptap-monitor
WORKSPACE_DIR = SKILL_DIR.parent.parent  # workspace
DATA_FILE = SKILL_DIR / "data" / "236096_data.json"
PENDING_FILE = SKILL_DIR / "data" / "pending_replies.json"

sys.path.insert(0, str(SKILL_DIR / "scripts"))
from taptap_monitor import TapTapMonitor
from taptap_reply import TapTapReply
from caiwang_reply import generate_reply, should_skip


def get_latest_data():
    """获取最新数据，只返回本次新抓取的内容（去重）"""
    monitor = TapTapMonitor(
        app_id="236096",
        data_file=str(DATA_FILE)
    )
    
    # 抓取原始数据
    raw_topics = monitor.fetch_topics(10)
    raw_reviews = monitor.fetch_reviews(10)
    
    # 筛选出本次新抓取的内容（对比历史记录）
    new_topics = monitor._add_new_topics(raw_topics)
    new_reviews = monitor._add_new_reviews(raw_reviews)
    
    # 保存更新后的历史记录
    monitor._save_data()
    
    return new_topics, new_reviews


def extract_id(url):
    """从 URL 提取 ID"""
    parts = url.rstrip("/").split("/")
    return parts[-1]


# 版主用户名列表（这些用户发的帖子不回复）
MODERATORS = {"homie"}

def main():
    print(f"[{datetime.now()}] 开始获取 TapTap 数据...")
    
    # 1. 获取本次新抓取的数据（已自动去重历史记录）
    topics, reviews = get_latest_data()
    print(f"本次新抓取: {len(topics)} 条帖子, {len(reviews)} 条评价")
    
    # 2. 生成待回复内容（统一编号）
    pending_items = []  # 统一列表，评价在前，帖子在后
    index = 1
    
    # 先处理评价
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
            "reply_content": reply_content
        })
        index += 1
    
    # 再处理帖子
    for t in topics:
        tid = extract_id(t.get("link", ""))
        author = t.get("author", "")
        title = t.get("title", "")
        
        # 过滤版主帖子
        if author in MODERATORS:
            print(f"跳过版主帖子: {title[:30]} (作者: {author})")
            continue
        
        # 过滤系统分享帖
        if should_skip(title):
            print(f"跳过系统分享: {title[:30]}")
            continue
        
        reply_content = generate_reply(t, "topic")
        if not reply_content:  # generate_reply 可能返回 None
            continue
        
        pending_items.append({
            "index": index,
            "type": "topic",
            "id": tid,
            "url": t.get("link", ""),
            "title": title,
            "author": author,
            "reply_content": reply_content
        })
        index += 1
    
    # 3. 保存待确认文件
    pending_data = {
        "created_at": datetime.now().isoformat(),
        "items": pending_items[:15]  # 最多15条
    }
    PENDING_FILE.write_text(json.dumps(pending_data, ensure_ascii=False, indent=2))
    
    # 5. 统计好评/差评/中评
    positive = sum(1 for r in reviews if "5星" in r.get("rating", "") or "4星" in r.get("rating", ""))
    negative = sum(1 for r in reviews if "1星" in r.get("rating", "") or "2星" in r.get("rating", ""))
    neutral = len(reviews) - positive - negative
    
    # 统计评价和帖子数量
    review_count = len([item for item in pending_items if item["type"] == "review"])
    topic_count = len([item for item in pending_items if item["type"] == "topic"])
    
    # 6. 推送到钉钉
    lines = [f"📢 **TapTap 每日监控** ({datetime.now().strftime('%m-%d %H:%M')})"]
    lines.append(f"\n📊 本次新增: **{len(topics)}** 条帖子, **{len(reviews)}** 条评价")
    lines.append(f"   好评 {positive} | 中评 {neutral} | 差评 {negative}")
    
    if pending_items:
        lines.append(f"\n---\n### 📝 待回复内容 ({len(pending_data['items'])} 条)")
        for item in pending_data['items']:
            if item["type"] == "review":
                rating_icon = "🟢" if "5星" in item['rating'] or "4星" in item['rating'] else ("🔴" if "1星" in item['rating'] or "2星" in item['rating'] else "🟡")
                lines.append(f"\n**#{item['index']}** 📋评价 {rating_icon}[{item['rating']}] {item['author']}")
                lines.append(f"> {item['content']}")
                lines.append(f"🔗 [{item['url']}]({item['url']})")
                lines.append(f"💬 回复: {item['reply_content']}")
            else:
                lines.append(f"\n**#{item['index']}** 📣帖子 {item['title']} - {item['author']}")
                lines.append(f"🔗 [{item['url']}]({item['url']})")
                lines.append(f"💬 回复: {item['reply_content']}")
    
    lines.append("\n---\n💡 **回复「确认」全部回复，回复「1 3 5」只回复指定编号**")
    
    # 输出到文件供钉钉推送
    push_file = SKILL_DIR / "data" / "push_content.md"
    push_file.write_text("\n".join(lines))
    
    print(f"待确认文件已保存: {PENDING_FILE}")
    print(f"推送内容已保存: {push_file}")
    
    # 推送到钉钉
    import subprocess
    dingtalk_script = WORKSPACE_DIR / "skills" / "dingtalk-push" / "notify.py"
    try:
        subprocess.run(
            ["python3", str(dingtalk_script)],
            input="\n".join(lines),
            capture_output=True,
            text=True,
            timeout=30
        )
        print("已推送到钉钉")
    except Exception as e:
        print(f"钉钉推送失败: {e}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    result = main()
    print(result)