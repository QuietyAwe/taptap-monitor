#!/usr/bin/env python3
"""
执行单条 TapTap 回复
用于卡片回调时调用
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import json

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
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


def main():
    parser = argparse.ArgumentParser(description="执行单条 TapTap 回复")
    parser.add_argument("--url", required=True, help="帖子或评价的 URL")
    parser.add_argument("--content", required=True, help="回复内容")
    parser.add_argument("--id", help="帖子或评价的 ID（用于去重记录）")
    args = parser.parse_args()
    
    print(f"[{datetime.now()}] 开始执行回复...")
    print(f"URL: {args.url}")
    print(f"内容: {args.content[:50]}...")
    
    # 加载已回复记录
    replied_ids, replies_data = load_replies_record()
    
    # 检查是否已回复
    if args.id and args.id in replied_ids:
        print("⚠️ 该内容已回复过，跳过")
        return
    
    # 执行回复
    reply = TapTapReply(app_id="236096", headless=True)
    reply._start_browser()
    
    try:
        result = reply.reply_single(url=args.url, content=args.content)
        
        if result:
            print("✅ 回复成功")
            # 记录已回复
            if args.id:
                replied_ids.add(args.id)
                if "replies" not in replies_data:
                    replies_data["replies"] = []
                replies_data["replies"].append({
                    "url": args.url,
                    "content": args.content,
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                })
                save_replies_record(replied_ids, replies_data)
            sys.exit(0)
        else:
            print("❌ 回复失败")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 回复异常: {e}")
        sys.exit(1)
    finally:
        reply._close_browser()


if __name__ == "__main__":
    main()