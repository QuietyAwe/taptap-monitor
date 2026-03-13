#!/usr/bin/env python3
"""
菜汪风格回复生成器
基于 caiwang-reply skill 的人设和规则
"""

import re

# 企微客服链接
QIWEI_LINK = "https://work.weixin.qq.com/kfid/kfc0e845aae7577cc05"

# 过滤规则：不需要回复的帖子标题模式
SKIP_PATTERNS = [
    r"^.+竟然对我说\.\.\.$",  # 角色互动分享
    r"^测测你和.+的羁绊$",    # 羁绊测试
    r"^和.+聊天竟然这么好玩",  # 聊天分享
    r"^开服\d+抽$",           # 福利宣传
    r"^主线送角色$",           # 福利宣传
]

def should_skip(title: str) -> bool:
    """判断是否应该跳过该帖子"""
    for pattern in SKIP_PATTERNS:
        if re.match(pattern, title):
            return True
    return False


def generate_reply(item: dict, item_type: str = "review") -> str:
    """
    生成菜汪风格回复
    item: 评价或帖子的数据
    item_type: "review" 或 "topic"
    """
    if item_type == "review":
        return _generate_review_reply(item)
    else:
        return _generate_topic_reply(item)


def _generate_review_reply(review: dict) -> str:
    """生成评价回复"""
    rating = review.get("rating", 0)
    # 兼容整数和字符串格式
    if isinstance(rating, str):
        rating_num = int(rating.replace("星", "").strip()) if rating else 0
    else:
        rating_num = int(rating) if rating else 0
    
    content = review.get("content", "")
    played_hours = review.get("played_hours", "")
    
    # 提取关键信息
    has_bug = any(kw in content for kw in ["BUG", "bug", "闪退", "崩溃", "卡死", "闪退了", "进不去"])
    has_suggestion = any(kw in content for kw in ["建议", "希望", "能不能", "可以不可以", "为什么不"])
    has_complaint = any(kw in content for kw in ["差评", "垃圾", "退钱", "卸载", "恶心", "骗氪"])
    is_lucky = any(kw in content for kw in ["金光", "欧皇", "十连双黄", "单抽出金", "双黄", "三黄"])
    is_unlucky = any(kw in content for kw in ["非酋", "歪了", "保底", "吃井", "沉船", "没出"])
    has_praise = any(kw in content for kw in ["好玩", "有趣", "喜欢", "可爱", "赞", "好评", "良心"])
    
    # 5星好评
    if rating_num == 5:
        if is_lucky:
            return f"(｀・ω・´) 经过本汪专业鉴定，这是标准的欧皇现象！虽然我们出货率确实比较高...但班长这运气也太犯规啦！快让菜汪摸摸您的手手~"
        elif has_praise:
            return f"哇！感谢班长的五星好评！(๑•̀ㅂ•́)و✧ 您的认可是我们最大的动力汪~"
        else:
            return f"感谢班长的五星支持汪！(๑•̀ㅂ•́)و✧ {played_hours}小时的陪伴太暖心了~"
    
    # 4星好评
    elif rating_num == 4:
        if has_suggestion:
            return f"班长的建议本汪记在小本本上了汪！(๑•̀ㅂ•́)و✧ 我们会认真考虑的~"
        else:
            return f"感谢班长的支持汪！{played_hours}小时的陪伴太暖心了~ 有任何建议随时告诉我们！"
    
    # 3星中评
    elif rating_num == 3:
        if has_bug:
            return f"抱歉给班长带来不好的体验汪！(；´д｀)ゞ 麻烦尝试重启/重装游戏，如果还有问题联系企微帮您处理汪！{QIWEI_LINK}"
        elif has_suggestion:
            return f"感谢班长的中肯评价和建议汪！我们会继续努力，争取下次能拿到更多星星~ (๑•̀ㅂ•́)و✧"
        else:
            return f"感谢班长的中肯评价汪！我们会继续加油的~"
    
    # 1-2星差评
    elif rating_num <= 2:
        if has_bug:
            return f"非常抱歉给班长带来不好的体验汪！(；´д｀)ゞ 麻烦班长尝试重启/重装游戏，如果还有问题联系企微为您处理汪！{QIWEI_LINK}"
        elif has_complaint:
            return f"抱歉让班长失望了汪...(´;ω;`) 您的反馈我们都记下了，会努力改进的！如果需要帮助可以联系企微汪~ {QIWEI_LINK}"
        else:
            return f"抱歉给班长带来不好的体验汪(´;ω;`) 您的反馈我们都记下了，会努力改进的！"
    
    # 默认
    else:
        return f"感谢班长的反馈汪！我们会继续加油的~"


def _generate_topic_reply(topic: dict) -> str:
    """生成帖子回复"""
    title = topic.get("title", "")
    content = topic.get("content", "")
    
    # 检查是否应该跳过
    if should_skip(title):
        return None  # 返回 None 表示跳过
    
    combined = f"{title} {content}"
    
    # BUG/问题反馈
    if any(kw in combined for kw in ["BUG", "bug", "闪退", "崩溃", "卡死", "进不去", "黑屏", "报错"]):
        return f"抱歉给班长带来不好的体验汪！(；´д｀)ゞ 麻烦尝试重启/重装游戏，如果还有问题联系企微帮您处理汪！{QIWEI_LINK}"
    
    # 攻略/二创
    if any(kw in combined for kw in ["攻略", "教程", "分享", "心得"]):
        return f"班长简直是行走的攻略百科！感谢分享汪~ (๑•̀ㅂ•́)و✧"
    
    if any(kw in combined for kw in ["同人", "二创", "画了", "创作"]):
        return f"被班长的才华闪到睁不开眼！(✪ω✪) 感谢大大的创作汪~"
    
    # 建议/期待
    if any(kw in combined for kw in ["建议", "希望", "能不能", "可以不可以", "为什么不"]):
        return f"班长的建议本汪记在小本本上了汪！(๑•̀ㅂ•́)و✧"
    
    # 询问活动/角色复刻
    if any(kw in combined for kw in ["什么时候", "复刻", "返场", "活动", "更新"]):
        return f"具体的安排班长关注后续公告汪~ 本汪不能剧透太多(；´д｀)ゞ"
    
    # 抽卡/运气
    if any(kw in combined for kw in ["出货", "金光", "欧皇", "十连双黄", "单抽出金"]):
        return f"(｀・ω・´) 经过本汪专业鉴定，这是标准的欧皇现象！快让菜汪摸摸您的手手~"
    
    if any(kw in combined for kw in ["非酋", "歪了", "保底", "吃井", "沉船"]):
        return f"抱抱班长！(っ´▽｀)っ 坏运气用完就只剩好运气啦，下次一定欧！"
    
    # 程序员/加班相关
    if any(kw in combined for kw in ["程序员", "加班", "秃头", "bug"]):
        return f"心疼程序员，谁心疼菜狗，只要菜狗还因为bug被骂，程序猿就休想闭眼(；´д｀)ゞ"
    
    # 默认
    return f"感谢班长的分享汪！期待看到更多精彩内容~"


# 测试
if __name__ == "__main__":
    # 测试评价
    test_reviews = [
        {"rating": "5星", "content": "太好玩了！", "played_hours": "100"},
        {"rating": "5星", "content": "十连双黄，欧皇附体！", "played_hours": "50"},
        {"rating": "4星", "content": "希望能增加更多角色", "played_hours": "80"},
        {"rating": "3星", "content": "有BUG，经常闪退", "played_hours": "30"},
        {"rating": "2星", "content": "垃圾游戏，骗氪", "played_hours": "10"},
        {"rating": "1星", "content": "进不去游戏，一直闪退", "played_hours": "5"},
    ]
    
    print("=== 评价回复测试 ===")
    for r in test_reviews:
        reply = generate_reply(r, "review")
        print(f"\n[{r['rating']}] {r['content'][:30]}...")
        print(f"→ {reply}")
    
    # 测试帖子
    test_topics = [
        {"title": "新手攻略分享", "content": ""},
        {"title": "BUG反馈：闪退", "content": ""},
        {"title": "建议增加跳过功能", "content": ""},
        {"title": "什么时候复刻？", "content": ""},
        {"title": "十连双黄！", "content": ""},
        {"title": "测测你和伊卡的羁绊", "content": ""},  # 应该跳过
    ]
    
    print("\n\n=== 帖子回复测试 ===")
    for t in test_topics:
        reply = generate_reply(t, "topic")
        print(f"\n[{t['title']}]")
        if reply:
            print(f"→ {reply}")
        else:
            print("→ [跳过]")