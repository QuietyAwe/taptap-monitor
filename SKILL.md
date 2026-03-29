# TapTap Monitor

TapTap 社区舆情监控与智能决策辅助系统。

## 功能概述

- **自动爬取**：定时获取 TapTap 最新帖子和评价
- **智能去重**：基于历史 ID 记录，避免重复处理
- **AI 分析**：自动定级、分类、生成决策建议
- **台账管理**：结构化记录所有舆情数据
- **钉钉推送**：实时告警，支持同类事件合并

## 目录结构

```
skills/taptap-monitor/
├── .venv/                    # Python 虚拟环境
├── scripts/
│   ├── main_sync.py          # 爬虫主脚本（爬取+去重+生成待分析文件）
│   └── update_ledger.py      # 台账更新脚本
├── data/
│   ├── history_ids.txt       # 已处理的 ID 记录
│   ├── monitor_log.csv       # 舆情台账
│   ├── to_analyze.json       # 待分析数据
│   ├── alert_msg.md          # 钉钉告警消息缓存
│   ├── bug_tasks.md          # Bug 任务跟踪表
│   └── daily_reports.md      # 每日舆情日报归档
├── config.json               # 配置文件
└── SKILL.md                  # 本文档
```

## 配置说明

`config.json` 字段：

| 字段    | 说明           | 示例     |
| ------- | -------------- | -------- |
| game_id | TapTap 游戏 ID | "259153" |
| cookie  | 登录凭证       | "..."    |

## 数据文件

### monitor_log.csv

舆情台账，长期存储所有处理过的帖子/评价。

| 字段            | 说明            | 示例                          |
| --------------- | --------------- | ----------------------------- |
| create_time     | 发布时间        | 2026-03-16 17:30:00           |
| source_id       | 来源 ID（主键） | 12345678                      |
| source_type     | 类型            | 帖子/评价                     |
| content         | 内容原文        | 怎么回事？新关卡一直进不去... |
| content_summary | AI 摘要         | 玩家反馈新关卡进不去...       |
| severity        | 定级            | P0/P1/P2                      |
| category        | 分类            | Bug/建议/负面/正面/水贴       |
| ai_suggestion   | AI 建议         | 收集设备信息...               |
| url             | 直达链接        | https://www.taptap.cn/...     |

### history_ids.txt

已处理的帖子/评价 ID 列表，用于去重。

### to_analyze.json

待 AI 分析的精简数据，格式：

```json
[
  {
    "id": "12345678",
    "type": "post",
    "content": "原文内容...",
    "url": "https://www.taptap.cn/moment/...",
    "created_at": "2026-03-16 17:30:00"
  }
]
```

## 定级标准

| 级别 | 触发条件                           | 处理时效 |
| ---- | ---------------------------------- | -------- |
| P0   | 阻断性 Bug、炸服、充值问题         | 立即     |
| P1   | Bug 反馈、有节奏的负面、大规模吐槽 | 3 小时内 |
| P2   | 常规吐槽、好评、水贴               | 当日     |

## 分类与决策

| 分类        | AI 操作                        |
| ----------- | ------------------------------ |
| Bug         | 收集设备信息，给出安抚回复参考 |
| 负面-可转化 | 分析痛点，给出转化回复参考     |
| 负面        | 判定恶意宣泄，给出投诉理由     |
| 正面        | 给暖心致谢回复参考             |
| 中立/建议   | 根据内容决定是否回复           |
| 水贴        | 建议无视                       |

## 触发词

- TapTap监控、舆情监控、获取评价、监控任务

## 使用方式

### 手动执行爬虫

```bash
cd /home/qee/.picoclaw/workspace/skills/taptap-monitor && .venv/bin/python scripts/main_sync.py
```

### 更新台账

```bash
.venv/bin/python scripts/update_ledger.py \
  --create_time "{{时间}}" \
  --content "{{原始评论}}" \
  --content_summary "{{摘要}}" \
  --severity "{{定级}}" \
  --category "{{分类}}" \
  --ai_suggestion "{{回复参考/处理建议}}" \
  --author "{{作者}}" \
  --url "{{url}}"
```

### 定时任务

每 30 分钟自动执行，详见 MEMORY.md 中的「TapTap 舆情监控及决策辅助任务」。

## 依赖

- Python 3.10+
- requests
- beautifulsoup4
- dingtalk-push 技能（推送告警）

## 更新日志

- 2026-03-21：新增 `bug_tasks.md` Bug 任务跟踪、`daily_reports.md` 日报归档；新增每日舆情总结定时任务
- 2026-03-19：迁移至 skills 目录，更新路径，新增 update_ledger.py 说明
- 2026-03-16：v2.0 初始化，重构架构
