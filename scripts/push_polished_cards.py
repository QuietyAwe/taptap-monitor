#!/usr/bin/env python3
"""
推送润色后的互动卡片
用于在 AI 润色完成后，读取 pending_replies.json 并发送最终审批卡片
"""

import json
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
WORKSPACE_DIR = SKILL_DIR.parent.parent
PENDING_FILE = SKILL_DIR / "data" / "pending_replies.json"

DINGTALK_DIR = WORKSPACE_DIR / "skills" / "dingtalk-push"
sys.path.insert(0, str(DINGTALK_DIR))
from notify import CLIENT_ID, CLIENT_SECRET, DEFAULT_USER_ID
import dingtalk_stream

CARD_TEMPLATE_ID = "e27c348e-a68a-4c87-b29f-601b39a1cc14.schema"
CARD_DATA_FILE = DINGTALK_DIR / "card_data_store.json"

def convert_json_values_to_string(obj: dict) -> dict:
    result = {}
    for key, value in obj.items():
        result[key] = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return result

def save_card_data(card_instance_id: str, card_data: dict):
    store = {}
    if CARD_DATA_FILE.exists():
        with open(CARD_DATA_FILE, 'r', encoding='utf-8') as f:
            store = json.load(f)
    store[card_instance_id] = card_data
    with open(CARD_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(store, f, ensure_ascii=False, indent=2)

async def send_approval_card_async(user_id, type_, content, reply, url="", create_time="", status="待审批", index=0, item_id=""):
    credential = dingtalk_stream.Credential(CLIENT_ID, CLIENT_SECRET)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    
    fake_incoming_message = dingtalk_stream.ChatbotMessage.from_dict({
        "conversationId": "", "senderNick": "", "senderStaffId": user_id,
        "senderCorpId": "", "conversationType": "1", "senderId": "",
    })
    
    card_data = {
        "lastMessage": f"#{index} {type_}审批",
        "type": type_,
        "createTime": create_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "status": status,
        "url": url,
        "reply": reply,
        "content": content
    }
    
    card_replier = dingtalk_stream.CardReplier(client, fake_incoming_message)
    card_instance_id = await card_replier.async_create_and_deliver_card(
        CARD_TEMPLATE_ID, convert_json_values_to_string(card_data), callback_type="STREAM",
    )
    return card_instance_id, card_data

def send_reply_card(item: dict, index: int):
    item_type = item.get("type", "review")
    type_label = "评价" if item_type == "review" else "帖子"
    
    raw_content = item.get("content", "") or item.get("title", "")
    if len(raw_content) > 150: raw_content = raw_content[:150] + "..."
    reply_content = item.get("reply_content", "")
    
    async def _send():
        return await send_approval_card_async(
            user_id=DEFAULT_USER_ID, type_=type_label, content=raw_content,
            reply=reply_content, url=item.get("url", ""),
            create_time=item.get("create_time", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            status="待审批", index=index, item_id=item.get("id", "")
        )
    
    try:
        card_instance_id, card_data = asyncio.run(_send())
        card_data.update({
            "index": index, "type": item_type, "url": item.get("url", ""),
            "reply_content": reply_content, "id": item.get("id", ""),
            "status": "pending", "created_at": datetime.now().isoformat()
        })
        save_card_data(card_instance_id, card_data)
        print(f"✅ 卡片已发送: #{index} (ID: {card_instance_id[:15]}...)")
        return card_instance_id
    except Exception as e:
        print(f"❌ 卡片发送失败: #{index} - {e}")
        return None

def main():
    if not PENDING_FILE.exists():
        print("未找到润色后的数据文件")
        return
        
    with open(PENDING_FILE, 'r', encoding='utf-8') as f:
        pending_data = json.load(f)
        
    items = pending_data.get("items", [])
    if not items:
        return
        
    print(f"\n开始发送 {len(items)} 张润色后的确认卡片...")
    success_count = 0
    for item in items:
        if send_reply_card(item, item.get("index", 0)):
            success_count += 1
        time.sleep(0.5)
        
    print(f"\n✅ 完成: 成功发送 {success_count}/{len(items)} 张卡片")

if __name__ == "__main__":
    main()