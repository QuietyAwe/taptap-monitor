---
name: taptap-monitor
description: 监控TapTap游戏社区的最新帖子和评价，特别针对《盲盒派对》等游戏。使用场景包括：1) 定期监控社区活跃度 2) 获取最新玩家反馈 3) 跟踪游戏讨论热度 4) 收集竞品社区信息 5) 自动化社区内容分析
---

# TapTap 监控技能

## 概述

本技能提供对TapTap游戏社区的自动化监控能力，支持获取最新帖子、评价、玩家反馈等内容。特别针对《盲盒派对》（游戏ID: 236096）进行优化，同时支持其他游戏社区监控。

## 快速开始

### 安装依赖
```bash
pip install requests beautifulsoup4
```

### 基本使用
1. **查看可用脚本**：
   ```bash
   ls scripts/
   ```

2. **运行监控脚本**：
   ```bash
   python scripts/taptap_monitor.py
   ```

3. **带参数运行**：
   ```bash
   python scripts/taptap_monitor.py --interval 60 --output data.json
   ```

### 常用命令
- `--interval 30`：30分钟监控一次（0表示只运行一次）
- `--output data.json`：保存数据到JSON文件
- `--app-id 236096`：指定游戏ID（默认盲盒派对）

## 详细用法

### 1. 一次性获取数据
```bash
# 获取盲盒派对的最新帖子和评价
python scripts/taptap_monitor.py --interval 0
```

### 2. 持续监控并保存数据
```bash
# 每小时监控一次，保存到monitor_data.json
python scripts/taptap_monitor.py --interval 60 --output monitor_data.json
```

### 3. 监控其他游戏
```bash
# 监控其他游戏（需要替换游戏ID）
python scripts/taptap_monitor.py --app-id 123456 --interval 30
```

### 4. 作为后台服务运行
```bash
# 使用nohup或tmux在后台运行
nohup python scripts/taptap_monitor.py --interval 30 --output logs/data.json > logs/monitor.log 2>&1 &
```

## 脚本说明

### `scripts/taptap_monitor.py`
主监控脚本，包含以下功能：

1. **`TapTapMonitor`类**：核心监控类
   - `fetch_topics()`：获取最新帖子
   - `fetch_reviews()`：获取最新评价
   - `monitor()`：持续监控方法

2. **数据结构**：
```python
# 帖子数据格式
{
    "title": "帖子标题",
    "link": "帖子链接",
    "author": "作者",
    "time": "发布时间",
    "likes": "点赞数",
    "comments": "评论数",
    "type": "topic",
    "fetched_at": "获取时间"
}

# 评价数据格式
{
    "rating": "评分",
    "content": "评价内容",
    "author": "评价者",
    "time": "评价时间",
    "likes": "有用数",
    "type": "review",
    "fetched_at": "获取时间"
}
```

## 集成使用

### 在PicoClaw中使用
```python
# 导入监控模块
import sys
sys.path.append('scripts')
from taptap_monitor import TapTapMonitor

# 创建监控实例
monitor = TapTapMonitor(app_id="236096")

# 获取数据
topics = monitor.fetch_topics(10)
reviews = monitor.fetch_reviews(10)

# 处理数据
for topic in topics:
    print(f"新帖子: {topic['title']} - {topic['author']}")
```

### 定时任务
使用cron定时执行：
```bash
# 每小时执行一次
0 * * * * cd /path/to/skill && python scripts/taptap_monitor.py --interval 0 --output /tmp/taptap_$(date +\%Y\%m\%d_\%H).json
```

## 故障排除

### 常见问题
1. **无法获取数据**：检查网络连接，确认页面结构是否变化
2. **返回空数据**：更新页面结构选择器（参考references/page_structure.md）
3. **请求被拒绝**：添加请求头，使用代理，降低请求频率

### 调试方法
```bash
# 启用详细输出
python scripts/taptap_monitor.py --interval 0 --verbose

# 保存原始HTML用于分析
python -c "
import requests
response = requests.get('https://www.taptap.cn/app/236096/topic')
with open('debug.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
print('HTML saved to debug.html')
"
```

## 扩展开发

### 添加新功能
1. **数据库支持**：在scripts/目录下添加database.py
2. **通知推送**：集成dingtalk-push技能
3. **数据分析**：添加analysis.py进行趋势分析

### 页面结构调整
当TapTap页面结构变化时：
1. 查看references/page_structure.md更新选择器
2. 修改scripts/taptap_monitor.py中的CSS选择器
3. 测试新选择器是否有效

## 注意事项

⚠️ **重要提醒**：
1. 遵守TapTap的使用条款，不要过度请求
2. 监控频率建议不低于30分钟一次
3. 数据仅用于个人分析，不得用于商业用途
4. 页面结构可能随时变化，需要定期维护

## 相关资源

- [页面结构文档](references/page_structure.md)：详细的页面结构和选择器说明
- [GitHub示例](https://github.com/Larusyang/TapTap-Forum)：其他TapTap爬虫参考
- [TapTap开发者文档](https://www.taptap.cn/developer)：官方API（如有）

---

**最后更新**：2026-02-26  
**维护状态**：活跃  
**适用游戏**：盲盒派对 (236096) 及其他TapTap游戏
