---
name: taptap-monitor
description: TapTap 社区监控与自动回复。功能：(1) 获取最新帖子/评价 (2) 自动回复帖子/评价 (3) 自动投诉违规差评。触发词：TapTap监控、获取评价、回复玩家、投诉差评。
---

# TapTap 监控技能

## 一、每日自动监控（推荐）

**定时任务**：每天 09:00 自动执行

```bash
cd /home/qee/.picoclaw/workspace/skills/taptap-monitor
python3 scripts/daily_monitor.py
```

**自动化流程**：
1. 获取最新帖子 + 评价
2. 过滤版主帖、系统分享帖
3. 对比已回复记录去重
4. 调用菜汪技能生成回复
5. 推送到钉钉待确认

**输出文件**：
- `data/pending_replies.json` - 待回复列表
- `data/push_content.md` - 推送内容

---

## 二、交互审批（收到推送后）

### 查看待回复列表

```bash
cd /home/qee/.picoclaw/workspace/skills/taptap-monitor
python3 scripts/reply_manager.py --list
```

### 执行回复

```bash
# 全部发布
python3 scripts/execute_replies.py --all

# 选择性发布（编号从 1 开始）
python3 scripts/execute_replies.py --indices 1,3,5

# 润色后发布（先更新 pending_replies.json，再执行）
python3 scripts/execute_replies.py --all
```

### 润色回复

告诉 Agent：「润色编号 1、3」，Agent 会：
1. 调用菜汪技能重新生成回复
2. 更新 `pending_replies.json`
3. 推送更新后的内容

### 跳过/删除

```bash
# 从待回复列表中删除指定项
python3 scripts/reply_manager.py --remove 2,4
```

---

## 三、手动获取数据

```bash
cd /home/qee/.picoclaw/workspace/skills/taptap-monitor

# 获取最新数据（帖子+评价各10条）
python3 scripts/taptap_monitor.py --interval 0

# 持续监控（每30分钟）
python3 scripts/taptap_monitor.py --interval 30
```

**数据保存位置**：`data/236096_data.json`

**评价关键字段**：
- `id`: 评价短ID（用于构建链接 `/review/{id}`）
- `link`: 完整链接
- `rating`: 评分（1-5星）
- `content`: 评价内容
- `author`: 作者

**帖子关键字段**：
- `link`: 链接（`/moment/{id}`）
- `title`: 标题
- `author`: 作者

---

## 四、手动回复

### 首次使用：登录

```bash
python3 scripts/taptap_reply.py --login --visible
```

弹出浏览器窗口，扫码登录后按回车保存登录态。

### 回复单条

```bash
python3 scripts/taptap_reply.py --url "https://www.taptap.cn/review/48009027" --content "感谢反馈汪！"
```

### 批量回复（自定义内容）

**步骤 1**：准备 JSON 文件

```json
{
  "reviews": [
    {"url": "https://www.taptap.cn/review/48009027", "reply_content": "感谢支持汪！"},
    {"url": "https://www.taptap.cn/review/48008198", "reply_content": "角色萌萌哒~"}
  ]
}
```

**步骤 2**：执行回复

```bash
python3 scripts/taptap_reply.py --data-file replies.json --auto
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--url` | 回复指定链接 |
| `--content` | 回复内容 |
| `--data-file` | JSON 数据文件（支持 `reply_content` 字段自定义回复） |
| `--auto` | 自动确认，无需手动确认 |
| `--max N` | 最多回复 N 条 |
| `--dry-run` | 模拟运行，不实际发送 |
| `--visible` | 显示浏览器窗口（调试用） |

### 回复记录

- 已回复 ID 保存在 `data/replies_236096.json`
- 自动跳过已回复的内容

---

## 五、投诉违规差评

```bash
# 模拟运行（查看会投诉哪些）
python3 scripts/taptap_complaint.py --dry-run

# 实际投诉（每个需确认）
python3 scripts/taptap_complaint.py --visible

# 全自动投诉
python3 scripts/taptap_complaint.py --auto --visible
```

**违规检测规则**：
- 谩骂：傻逼、垃圾游戏、脑残等
- 拉踩：提及竞品 + 不如/吊打
- 敏感词：代练、外挂、破解版

---

## 六、菜汪回复生成器

```bash
# 独立使用（测试用）
python3 scripts/caiwang_reply.py --content "玩家评论内容" --rating 5
```

菜汪技能会自动调用，一般无需手动执行。

---

## 七、常见问题

**Q: 获取数据失败？**
检查 Playwright：`pip install playwright && playwright install chromium`

**Q: 回复失败？**
1. 先执行 `--login --visible` 重新登录
2. 用 `--check-login` 检查登录状态

**Q: 评价链接格式错误？**
评价链接必须用短 ID 格式：`/review/48009027`（不是长 ID）

---

## 八、文件结构

```
taptap-monitor/
├── SKILL.md              # 本文档
├── login_taptap.py       # 登录脚本
├── scripts/
│   ├── daily_monitor.py      # 每日监控主脚本（定时任务调用）
│   ├── execute_replies.py    # 执行回复
│   ├── caiwang_reply.py      # 菜汪回复生成器
│   ├── reply_manager.py      # 回复列表管理
│   ├── taptap_monitor.py     # 数据获取
│   ├── taptap_reply.py       # 回复执行
│   └── taptap_complaint.py   # 投诉违规
├── data/
│   ├── 236096_data.json      # 历史数据
│   ├── pending_replies.json  # 待回复列表
│   ├── replies_236096.json   # 已回复记录
│   ├── cookies_236096.json   # 登录态
│   └── push_content.md       # 推送内容
└── references/            # 参考资料
```

---

**最后更新**：2026-03-13
**适用游戏**：盲盒派对 (236096)