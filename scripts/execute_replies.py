#!/usr/bin/env python3
"""
执行待确认的回复
支持：
  - 全部回复：python3 execute_replies.py
  - 选择回复：python3 execute_replies.py 1 3 5
"""

import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent  # skills/taptap-monitor
DATA_FILE = SKILL_DIR / "data" / "pending_replies.json"
REPLIES_FILE = SKILL_DIR / "data" / "replies_236096.json"

sys.path.insert(0, str(SCRIPT_DIR))
from taptap_reply import TapTapReply


def load_replies_record():
    """加载已回复记录"""
    if REPLIES_FILE.exists():
        data = json.loads(REPLIES_FILE.read_text())
        return set(data.get("replied_ids", [])), data
    return set(), {}


def save_replies_record(replied_ids: set, replies_data: dict):
    """保存已回复记录"""
    replies_data["replied_ids"] = list(replied_ids)
    replies_data["last_updated"] = datetime.now().isoformat()
    REPLIES_FILE.write_text(json.dumps(replies_data, ensure_ascii=False, indent=2))


def main(selected_indices=None):
    """
    执行回复
    selected_indices: None = 全部回复, [1, 3, 5] = 只回复指定编号
    """
    if not DATA_FILE.exists():
        print("❌ 没有待确认的回复")
        return None
    
    pending = json.loads(DATA_FILE.read_text())
    all_items = pending.get("items", [])
    
    if not all_items:
        print("❌ 没有待回复的内容")
        return None
    
    # 筛选要回复的内容
    if selected_indices:
        items = [item for item in all_items if item["index"] in selected_indices]
        print(f"筛选回复: {len(items)} 条")
    else:
        items = all_items
        print(f"准备回复全部: {len(items)} 条")
    
    if not items:
        print("❌ 没有匹配的内容")
        return None
    
    # 加载已回复记录
    replied_ids, replies_data = load_replies_record()
    print(f"已有 {len(replied_ids)} 条已回复记录")
    
    # 准备回复
    reply = TapTapReply(app_id="236096", headless=True)
    reply._start_browser()
    
    results = {"success": [], "failed": []}
    newly_replied = []
    
    for item in items:
        idx = item["index"]
        item_type = item["type"]
        type_label = "📋评价" if item_type == "review" else "📣帖子"
        
        try:
            result = reply.reply_single(
                url=item["url"],
                content=item["reply_content"]
            )
            if result:
                results["success"].append(idx)
                print(f"✅ #{idx} {type_label} 回复成功")
                replied_ids.add(item["id"])
                newly_replied.append({
                    "url": item["url"],
                    "content": item["reply_content"],
                    "status": "success",
                    "message": "回复成功",
                    "timestamp": datetime.now().isoformat(),
                    "page_type": "review" if item_type == "review" else "moment"
                })
            else:
                results["failed"].append(idx)
                print(f"❌ #{idx} {type_label} 回复失败")
        except Exception as e:
            results["failed"].append(idx)
            print(f"❌ #{idx} {type_label} 异常: {e}")
    
    reply._close_browser()
    
    # 更新已回复记录
    if newly_replied:
        if "replies" not in replies_data:
            replies_data["replies"] = []
        replies_data["replies"].extend(newly_replied)
        save_replies_record(replied_ids, replies_data)
        print(f"✅ 已更新回复记录，共 {len(replied_ids)} 条")
    
    # 如果是全部回复，清空待确认文件；否则只移除已回复的
    if selected_indices is None:
        DATA_FILE.unlink()
        print("✅ 已清空待确认文件")
    else:
        remaining = [item for item in all_items if item["index"] not in selected_indices]
        if remaining:
            pending["items"] = remaining
            DATA_FILE.write_text(json.dumps(pending, ensure_ascii=False, indent=2))
            print(f"✅ 保留 {len(remaining)} 条待确认")
        else:
            DATA_FILE.unlink()
            print("✅ 已清空待确认文件")
    
    # 输出结果
    print(f"\n📊 回复完成: 成功 {len(results['success'])} 条, 失败 {len(results['failed'])} 条")
    
    return results


if __name__ == "__main__":
    # 解析命令行参数
    args = sys.argv[1:]
    if args:
        # 提取编号
        selected = set()
        for arg in args:
            try:
                selected.add(int(arg))
            except ValueError:
                pass
        if selected:
            print(f"选择性回复编号: {sorted(selected)}")
            main(selected)
        else:
            print("❌ 无效的编号参数")
    else:
        # 全部回复
        main()