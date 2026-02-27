# TapTap 监控技能

## 页面结构说明

### 《盲盒派对》社区页面
- 游戏ID: 236096
- 社区帖子页面: https://www.taptap.cn/app/236096/topic
- 评价页面: https://www.taptap.cn/app/236096/review

### 页面结构分析（基于2026-02-26的页面）

#### 帖子页面结构
```html
<!-- 大致结构 -->
<div class="topic-list">
  <div class="topic-item">
    <h3 class="title"><a href="/topic/123456">帖子标题</a></h3>
    <div class="meta">
      <span class="author">作者名</span>
      <span class="time">发布时间</span>
    </div>
    <div class="stats">
      <span class="like-count">点赞数</span>
      <span class="comment-count">评论数</span>
    </div>
  </div>
  <!-- 更多帖子 -->
</div>
```

#### 评价页面结构
```html
<!-- 大致结构 -->
<div class="review-list">
  <div class="review-item">
    <div class="rating">评分</div>
    <div class="content">评价内容...</div>
    <div class="meta">
      <span class="author">评价者</span>
      <span class="time">评价时间</span>
    </div>
    <div class="helpful-count">有用数</div>
  </div>
  <!-- 更多评价 -->
</div>
```

### CSS 选择器参考

**帖子选择器**:
- `div.topic-item` - 帖子项
- `h3.title a` - 标题链接
- `.author` - 作者
- `.time` - 发布时间
- `.like-count` - 点赞数
- `.comment-count` - 评论数

**评价选择器**:
- `div.review-item` - 评价项
- `.rating` - 评分
- `.content` - 评价内容
- `.author` - 评价者
- `.time` - 评价时间
- `.helpful-count` - 有用数

## 注意事项

1. **页面结构可能变化**：TapTap 会定期更新页面结构，需要定期检查和更新选择器
2. **反爬虫机制**：TapTap 可能有反爬虫措施，建议：
   - 设置合理的请求间隔
   - 使用随机 User-Agent
   - 避免高频请求
3. **数据格式**：返回的数据为 JSON 格式，便于后续处理和分析
4. **错误处理**：脚本包含基本的错误处理，但网络异常时可能需要重试机制

## 扩展建议

1. **数据库存储**：可添加数据库支持（SQLite/MySQL）存储历史数据
2. **通知功能**：集成钉钉/微信推送新内容通知
3. **关键词过滤**：监控特定关键词的帖子或评价
4. **趋势分析**：分析帖子/评价的数量、评分变化趋势
5. **情感分析**：对评价内容进行情感分析