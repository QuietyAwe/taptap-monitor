---
name: dingtalk-push
description: 将 Markdown 内容和图片推送到钉钉群机器人。
metadata: {"nanobot":{"emoji":"📢","requires":{"bins":["python3"]}}}
---

# 钉钉推送技能

将 Markdown 内容和图片推送到钉钉群机器人。

## 功能
- 发送 Markdown 文本消息
- 发送本地图片（自动上传到图床）
- 发送网络图片 URL
- 发送 Link 链接卡片（带图片预览）

## 使用方法

### 1. 发送 Markdown 文本
```bash
echo "## 标题\n内容" | python notify.py
```

### 2. 发送本地图片
```bash
python notify.py --image /path/to/image.png --caption "图片说明"
```

### 3. 发送网络图片 URL
```bash
python notify.py --image "https://example.com/image.png" --caption "图片说明"
```

### 4. 发送 Link 链接卡片
```bash
python notify.py --link "标题" "描述内容" "https://图片URL" "https://跳转URL"
```

## 参数说明
| 参数 | 说明 |
|------|------|
| --image, -i | 图片路径或 URL |
| --caption, -c | 图片说明文字 |
| --link, -l | 发送 Link 消息（需4个参数） |
| --title, -t | 消息标题 |

## 图片上传说明
- 本地图片会自动上传到 imgbb 免费图床
- 备用图床：敖武的图床（备用）
- 支持 JPG、PNG、GIF 等常见格式
- 单张图片最大 5MB

## 环境变量配置

在使用前，请配置以下环境变量：

```bash
export DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=YOUR_ACCESS_TOKEN"
export DINGTALK_SECRET="YOUR_SECRET_KEY"
export IMGBB_API_KEY="YOUR_IMGBB_API_KEY"  # 可选，用于图片上传
```

或在脚本目录创建 `.env` 文件：

```env
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=YOUR_ACCESS_TOKEN
DINGTALK_SECRET=YOUR_SECRET_KEY
IMGBB_API_KEY=YOUR_IMGBB_API_KEY
```

### 获取方式
- **钉钉机器人**: 在钉钉群设置中添加自定义机器人，获取 Webhook URL 和签名密钥
- **imgbb API**: 访问 https://api.imgbb.com/ 免费注册获取 API 密钥

## 版本
2.2.0 - 移除硬编码敏感信息，改为环境变量配置