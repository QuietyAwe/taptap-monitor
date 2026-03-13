#!/usr/bin/env python3
"""
TapTap 回复管理器
功能：
1. 简单规则生成初版回复
2. 保存待确认列表
3. 支持润色（调用菜汪技能）
4. 支持发布
"""
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional


class ReplyManager:
    """回复管理器"""
    
    def __init__(self, app_id: str = "236096"):
        self.app_id = app_id
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.pending_file = os.path.join(self.data_dir, f"pending_replies_{app_id}.json")
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_pending(self) -> Dict:
        """加载待确认列表"""
        if os.path.exists(self.pending_file):
            try:
                with open(self.pending_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"items": [], "updated_at": None}
    
    def _save_pending(self, data: Dict):
        """保存待确认列表"""
        data["updated_at"] = datetime.now().isoformat()
        with open(self.pending_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _should_skip(self, item: Dict) -> bool:
        """判断是否应该跳过（内置分享帖）"""
        title = item.get("title", "")
        content = item.get("content", "")
        
        # 内置分享帖模式
        skip_patterns = [
            r".+竟然对我说\.\.\.$",
            r"测测你和.+的羁绊$",
            r"和.+聊天竟然这么好玩～$",
            r"开服\d+抽$",
            r"主线送角色$",
        ]
        
        for pattern in skip_patterns:
            if re.match(pattern, title):
                return True
        
        return False
    
    def _generate_simple_reply(self, item: Dict) -> str:
        """用简单规则生成初版回复"""
        item_type = item.get("type", "topic")
        rating = item.get("rating", 0)
        content = item.get("content", "")
        title = item.get("title", "")
        text = content or title
        
        # 差评安抚
        if item_type == "review" and rating <= 2:
            return "非常抱歉给班长带来了不好的体验汪！(；´д｀)ゞ 您的问题我们已经记录，我们会努力改进的！"
        
        # BUG/闪退
        if any(kw in text for kw in ["闪退", "BUG", "bug", "崩溃", "卡死", "黑屏"]):
            return "抱歉给班长带来不好的体验汪！(；´д｀)ゞ 麻烦尝试重启/重装游戏，如果还有问题联系企微帮您处理汪！https://work.weixin.qq.com/kfid/kfc0e845aae7577cc05"
        
        # 建议/期待
        if any(kw in text for kw in ["建议", "希望", "期待", "能不能", "可以不可以"]):
            return "班长的建议本汪记在小本本上了汪！(๑•̀ㅂ•́)و✧"
        
        # 欧皇/抽卡
        if any(kw in text for kw in ["出货", "金光", "欧皇", "十连", "单抽出"]):
            return "(｀・ω・´) 经过本汪专业鉴定，这是标准的欧皇现象！快让菜汪摸摸您的手手~"
        
        # 攻略/二创
        if any(kw in text for kw in ["攻略", "教程", "分享", "二创"]):
            return "班长太厉害了汪！(✪ω✪) 感谢分享！"
        
        # 好评
        if item_type == "review" and rating >= 4:
            return "感谢班长的支持汪！(๑•̀ㅂ•́)و✧ 您的喜欢是我们最大的动力！"
        
        # 默认
        return "感谢班长的反馈汪！(๑•̀ㅂ•́)و✧"
    
    def add_pending_items(self, items: List[Dict]) -> List[Dict]:
        """
        添加待确认项
        
        Args:
            items: 评价/帖子列表
        
        Returns:
            添加的待确认项（带编号）
        """
        pending = self._load_pending()
        existing_ids = {item.get("id") for item in pending.get("items", [])}
        
        new_items = []
        for item in items:
            # 跳过内置分享帖
            if self._should_skip(item):
                continue
            
            # 跳过已存在的
            item_id = item.get("id")
            if item_id and item_id in existing_ids:
                continue
            
            # 生成初版回复
            reply_content = self._generate_simple_reply(item)
            
            pending_item = {
                "id": item_id,
                "type": item.get("type", "topic"),
                "link": item.get("link", ""),
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "author": item.get("author", ""),
                "rating": item.get("rating", 0),
                "reply_content": reply_content,
                "reply_type": "simple",  # simple / caiwang
                "status": "pending",  # pending / published
                "created_at": datetime.now().isoformat(),
            }
            
            new_items.append(pending_item)
            pending["items"].append(pending_item)
        
        if new_items:
            self._save_pending(pending)
        
        return new_items
    
    def get_pending_items(self, status: str = "pending") -> List[Dict]:
        """获取待确认项"""
        pending = self._load_pending()
        return [item for item in pending.get("items", []) if item.get("status") == status]
    
    def polish_items(self, indices: List[int], caiwang_replies: Dict[int, str]) -> bool:
        """
        润色指定项
        
        Args:
            indices: 要润色的编号列表（从1开始）
            caiwang_replies: {index: 菜汪回复内容} 由外部调用菜汪技能生成
        
        Returns:
            是否成功
        """
        pending = self._load_pending()
        items = [item for item in pending.get("items", []) if item.get("status") == "pending"]
        
        success = False
        for idx in indices:
            if 1 <= idx <= len(items):
                item = items[idx - 1]
                if idx in caiwang_replies:
                    item["reply_content"] = caiwang_replies[idx]
                    item["reply_type"] = "caiwang"
                    item["polished_at"] = datetime.now().isoformat()
                    success = True
        
        if success:
            self._save_pending(pending)
        
        return success
    
    def update_reply(self, index: int, new_content: str) -> bool:
        """更新指定项的回复内容"""
        pending = self._load_pending()
        items = [item for item in pending.get("items", []) if item.get("status") == "pending"]
        
        if 1 <= index <= len(items):
            items[index - 1]["reply_content"] = new_content
            self._save_pending(pending)
            return True
        
        return False
    
    def mark_published(self, indices: List[int]) -> bool:
        """标记为已发布"""
        pending = self._load_pending()
        items = [item for item in pending.get("items", []) if item.get("status") == "pending"]
        
        success = False
        for idx in indices:
            if 1 <= idx <= len(items):
                items[idx - 1]["status"] = "published"
                items[idx - 1]["published_at"] = datetime.now().isoformat()
                success = True
        
        if success:
            self._save_pending(pending)
        
        return success
    
    def remove_item(self, index: int) -> bool:
        """删除指定项"""
        pending = self._load_pending()
        items = [item for item in pending.get("items", []) if item.get("status") == "pending"]
        
        if 1 <= index <= len(items):
            # 找到原始列表中的位置
            target_id = items[index - 1].get("id")
            pending["items"] = [item for item in pending.get("items", []) if item.get("id") != target_id]
            self._save_pending(pending)
            return True
        
        return False
    
    def clear_published(self):
        """清理已发布的项"""
        pending = self._load_pending()
        pending["items"] = [item for item in pending.get("items", []) if item.get("status") != "published"]
        self._save_pending(pending)
    
    def format_pending_list(self, max_items: int = 10) -> str:
        """格式化待确认列表为 Markdown"""
        items = self.get_pending_items()[:max_items]
        
        if not items:
            return "📭 当前没有待回复的内容"
        
        lines = ["## 📬 待回复列表\n"]
        
        for i, item in enumerate(items, 1):
            item_type = "评价" if item.get("type") == "review" else "帖子"
            rating = item.get("rating", 0)
            rating_str = f"⭐{rating}" if rating else ""
            
            lines.append(f"### {i}. [{item_type}] {rating_str}")
            
            if item.get("title"):
                lines.append(f"**标题**: {item.get('title', '')[:50]}")
            
            content = item.get("content", "")[:100]
            if content:
                lines.append(f"**内容**: {content}{'...' if len(item.get('content', '')) > 100 else ''}")
            
            lines.append(f"**作者**: {item.get('author', '')}")
            lines.append(f"**链接**: {item.get('link', '')}")
            lines.append(f"**回复**: {item.get('reply_content', '')}")
            lines.append(f"**类型**: {'🌸 菜汪润色' if item.get('reply_type') == 'caiwang' else '📝 简单回复'}")
            lines.append("")
        
        lines.append("---")
        lines.append("💡 **操作指令**:")
        lines.append("- `润色编号1、3` - 用菜汪风格重新生成")
        lines.append("- `发布编号1、3` - 确认并发布")
        lines.append("- `发布全部` - 发布所有待回复")
        lines.append("- `删除编号1` - 从列表中移除")
        
        return "\n".join(lines)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TapTap 回复管理器")
    parser.add_argument("--app-id", type=str, default="236096", help="游戏ID")
    parser.add_argument("--list", action="store_true", help="显示待回复列表")
    parser.add_argument("--clear-published", action="store_true", help="清理已发布的项")
    
    args = parser.parse_args()
    
    manager = ReplyManager(app_id=args.app_id)
    
    if args.list:
        print(manager.format_pending_list())
    elif args.clear_published:
        manager.clear_published()
        print("✅ 已清理已发布的项")
    else:
        print("请指定操作: --list, --clear-published")


if __name__ == "__main__":
    main()