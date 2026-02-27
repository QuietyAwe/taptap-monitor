# TapTap Monitor

监控 TapTap 游戏社区的最新帖子和评价，支持自动化社区内容分析。

## 功能特点

- 📱 获取游戏社区最新帖子
- ⭐ 获取游戏评价和评分
- 🔄 支持定时监控和去重
- 📊 数据导出为 JSON 格式
- 🔔 可集成钉钉推送通知

## 安装

```bash
pip install requests beautifulsoup4
```

## 快速开始

```bash
# 单次抓取
python scripts/taptap_monitor.py --interval 0

# 持续监控（每30分钟）
python scripts/taptap_monitor.py --interval 30

# 指定游戏ID
python scripts/taptap_monitor.py --app-id 236096 --interval 0
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--app-id` | TapTap 游戏 ID | 236096 |
| `--interval` | 监控间隔（分钟），0 表示单次运行 | 30 |
| `--data-file` | 数据保存路径 | data/236096_data.json |
| `--visible` | 显示浏览器窗口（调试用） | False |

## 数据结构

### 帖子
```json
{
  "id": "帖子ID",
  "title": "帖子标题",
  "link": "帖子链接",
  "author": "作者",
  "time": "发布时间",
  "likes": "点赞数",
  "comments": "评论数"
}
```

### 评价
```json
{
  "id": "评价ID",
  "rating": "评分",
  "content": "评价内容",
  "author": "评价者",
  "time": "评价时间",
  "likes": "有用数"
}
```

## 集成钉钉推送

可配合 [dingtalk-push](./dingtalk-push) 技能实现新内容自动推送。

```bash
# 配置环境变量
export DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
export DINGTALK_SECRET="YOUR_SECRET"

# 监控并推送
python scripts/taptap_monitor.py --interval 30 | python dingtalk-push/notify.py
```

## 注意事项

⚠️ 请遵守 TapTap 使用条款，建议监控间隔不低于 30 分钟。

## License

MIT