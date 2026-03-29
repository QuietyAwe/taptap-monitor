# TapTap Monitor

TapTap 社区舆情监控与智能决策辅助系统。

## 功能

- **舆情监控**：自动爬取 TapTap 社区帖子、评价、评论
- **智能分析**：AI 驱动的舆情定级（P0/P1/P2）、分类、决策建议
- **钉钉推送**：实时推送舆情播报到钉钉群聊
- **任务管理**：自动创建钉钉项目任务，追踪 Bug 处理进度
- **日报生成**：每日舆情数据统计与报告

## 安装

```bash
# 克隆仓库
git clone https://github.com/QuietyAwe/taptap-monitor.git
cd taptap-monitor

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 配置

1. 复制示例配置文件：
```bash
cp config.example.json config.json
```

2. 编辑 `config.json`，填入你的 TapTap Cookie 和 App ID：
```json
{
  "taptap_cookie": "your_taptap_cookie_here",
  "app_id": "your_app_id_here"
}
```

## 使用

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行监控
python scripts/main_sync.py
```

## 目录结构

```
taptap-monitor/
├── SKILL.md              # 技能文档
├── README.md             # 本文件
├── config.example.json   # 示例配置
├── .gitignore
└── scripts/
    ├── main_sync.py          # 主爬虫脚本
    ├── update_ledger.py      # 更新监控台账
    ├── append_bug_task.py    # 追加 Bug 任务记录
    ├── sync_bug_tasks.py     # 同步 Bug 任务状态
    └── generate_daily_report.py  # 生成日报
```

## License

MIT