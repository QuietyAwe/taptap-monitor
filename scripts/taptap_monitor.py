#!/usr/bin/env python3
"""
TapTap 监控脚本 - 使用 Playwright 模拟真人浏览器获取动态渲染内容
监控《盲盒派对》社区的最新帖子和评价
"""
import json
import time
import re
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Page, Browser

class TapTapMonitor:
    def __init__(self, app_id: str = "236096", headless: bool = True, data_file: str = None):
        """
        初始化 TapTap 监控器
        
        Args:
            app_id: 游戏ID (盲盒派对为236096)
            headless: 是否无头模式运行浏览器
            data_file: 数据存储文件路径
        """
        self.app_id = app_id
        self.base_url = "https://www.taptap.cn"
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.data_file = data_file or f"data/{app_id}_data.json"
        self._load_data()
        
    def _load_data(self):
        """加载已存储的数据"""
        self.existing_topics: Dict[str, Dict] = {}  # link -> topic
        self.existing_reviews: Dict[str, Dict] = {}  # content_hash -> review
        
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for topic in data.get('topics', []):
                        if topic.get('link'):
                            self.existing_topics[topic['link']] = topic
                    for review in data.get('reviews', []):
                        # 用内容前100字符+作者作为唯一标识
                        key = f"{review.get('content', '')[:100]}_{review.get('author', '')}"
                        self.existing_reviews[key] = review
                print(f"已加载 {len(self.existing_topics)} 个帖子, {len(self.existing_reviews)} 条评价")
            except Exception as e:
                print(f"加载数据失败: {e}")
                
    def _save_data(self):
        """保存数据到文件"""
        # 确保目录存在
        os.makedirs(os.path.dirname(self.data_file) if os.path.dirname(self.data_file) else '.', exist_ok=True)
        
        data = {
            "last_updated": datetime.now().isoformat(),
            "app_id": self.app_id,
            "topics": list(self.existing_topics.values()),
            "reviews": list(self.existing_reviews.values())
        }
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到: {self.data_file}")
        
    def _add_new_topics(self, topics: List[Dict]) -> List[Dict]:
        """添加新帖子（去重）"""
        new_topics = []
        for topic in topics:
            link = topic.get('link', '')
            if link and link not in self.existing_topics:
                self.existing_topics[link] = topic
                new_topics.append(topic)
        return new_topics
        
    def _add_new_reviews(self, reviews: List[Dict]) -> List[Dict]:
        """添加新评价（去重）"""
        new_reviews = []
        for review in reviews:
            key = f"{review.get('content', '')[:100]}_{review.get('author', '')}"
            if key not in self.existing_reviews:
                self.existing_reviews[key] = review
                new_reviews.append(review)
        return new_reviews
        
    def _start_browser(self):
        """启动浏览器"""
        if self.browser is None:
            self._playwright = sync_playwright().start()
            self.browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )
            context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
            )
            self.page = context.new_page()
            # 隐藏自动化特征
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            
    def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.page = None
            self._playwright.stop()
            
    def _wait_for_content(self, timeout: int = 15000):
        """等待页面内容加载"""
        try:
            # 等待帖子卡片出现
            self.page.wait_for_selector('.moment-card, .moment-list-item, [class*="moment"]', timeout=timeout)
        except:
            pass
        # 额外等待确保内容渲染完成
        time.sleep(2)
        
    def _scroll_page(self, scrolls: int = 3):
        """模拟滚动加载更多内容"""
        for i in range(scrolls):
            self.page.evaluate('window.scrollBy(0, 800)')
            time.sleep(0.5)
        # 滚回顶部
        self.page.evaluate('window.scrollTo(0, 0)')
        time.sleep(0.5)
        
    def fetch_topics(self, max_posts: int = 20, sort: str = "new") -> List[Dict]:
        """
        获取最新帖子
        
        Args:
            max_posts: 最大帖子数量
            sort: 排序方式 (new=最新, hot=热门)
        
        Returns:
            帖子列表
        """
        url = f"{self.base_url}/app/{self.app_id}/topic?sort={sort}"
        
        try:
            self._start_browser()
            print(f"正在访问: {url}")
            self.page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 等待内容加载
            self._wait_for_content()
            
            # 滚动加载更多
            self._scroll_page(2)
            
            # 提取数据 - 尝试多种选择器
            topics = []
            
            # 方法1: 尝试从 NUXT 数据中提取 (SPA 框架数据)
            nuxt_data = self.page.evaluate('''() => {
                if (window.__NUXT__) return JSON.stringify(window.__NUXT__);
                return null;
            }''')
            
            if nuxt_data:
                try:
                    data = json.loads(nuxt_data)
                    print(f"发现 NUXT 数据，尝试解析...")
                    # 调试：保存 NUXT 数据结构
                    debug_file = '/tmp/taptap_nuxt_debug.json'
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                    print(f"NUXT 数据已保存到: {debug_file}")
                    topics = self._parse_nuxt_topics(data, max_posts)
                    if topics:
                        print(f"从 NUXT 数据解析到 {len(topics)} 个帖子")
                        return topics
                except Exception as e:
                    print(f"解析 NUXT 数据失败: {e}")
            
            # 方法2: 从 DOM 中提取
            print("尝试从 DOM 中提取帖子...")
            topics = self._extract_topics_from_dom(max_posts)
            
            return topics
            
        except Exception as e:
            print(f"获取帖子失败: {e}")
            import traceback
            traceback.print_exc()
            return []
            
    def _parse_nuxt_topics(self, data: dict, max_posts: int) -> List[Dict]:
        """从 NUXT 数据中解析帖子"""
        topics = []
        
        def find_moment_lists(obj, depth=0):
            """递归查找包含 moment 的列表"""
            if depth > 15:
                return []
            results = []
            if isinstance(obj, dict):
                # 检查是否有 list 字段且包含 moment
                if 'list' in obj and isinstance(obj['list'], list):
                    if obj['list'] and isinstance(obj['list'][0], dict) and 'moment' in obj['list'][0]:
                        results.append(obj['list'])
                for v in obj.values():
                    results.extend(find_moment_lists(v, depth + 1))
            elif isinstance(obj, list):
                for item in obj:
                    results.extend(find_moment_lists(item, depth + 1))
            return results
            
        moment_lists = find_moment_lists(data)
        
        for moment_list in moment_lists:
            for item in moment_list[:max_posts]:
                try:
                    moment = item.get('moment', {})
                    if not moment:
                        continue
                    
                    # 提取帖子ID
                    post_id = moment.get('id_str') or moment.get('id')
                    
                    # 提取标题和内容
                    topic_data = moment.get('topic', {})
                    title = topic_data.get('title', '')
                    summary = topic_data.get('summary', '')
                    content = summary or title
                    
                    # 提取作者
                    author_data = moment.get('author', {}).get('user', {})
                    author = author_data.get('name', '未知')
                    
                    # 提取时间
                    created_time = moment.get('created_time') or moment.get('publish_time', 0)
                    post_time = self._format_timestamp(created_time)
                    
                    # 提取统计
                    stat = moment.get('stat', {})
                    likes = str(stat.get('ups', 0))  # 点赞数是 ups
                    comments = str(stat.get('comments', 0))
                    
                    # 生成链接
                    link = f"{self.base_url}/moment/{post_id}" if post_id else ''
                    
                    topic = {
                        "title": title[:150] if title else content[:150] or "（无标题）",
                        "link": link,
                        "author": author[:50],
                        "time": post_time,
                        "likes": likes,
                        "comments": comments,
                        "content_preview": content[:200] if content else '',
                        "type": "topic",
                        "fetched_at": datetime.now().isoformat()
                    }
                    
                    if topic['title'] != "（无标题）":
                        topics.append(topic)
                        
                except Exception as e:
                    print(f"解析帖子项失败: {e}")
                    continue
        
        # 去重
        seen = set()
        unique_topics = []
        for t in topics:
            if t['link'] and t['link'] not in seen:
                seen.add(t['link'])
                unique_topics.append(t)
                    
        return unique_topics[:max_posts]
        
    def _format_timestamp(self, ts) -> str:
        """格式化时间戳"""
        if not ts:
            return ''
        try:
            if isinstance(ts, (int, float)):
                # 毫秒或秒级时间戳
                if ts > 1e12:
                    ts = ts / 1000
                return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
            return str(ts)
        except:
            return str(ts)
            
    def _extract_topics_from_dom(self, max_posts: int) -> List[Dict]:
        """从 DOM 中提取帖子"""
        topics = []
        
        # 尝试多种选择器
        selectors = [
            '.moment-card',
            '.moment-list-item', 
            '[class*="moment-card"]',
            '[class*="topic-item"]',
            'article[class*="card"]',
        ]
        
        elements = []
        for selector in selectors:
            try:
                found = self.page.query_selector_all(selector)
                if found:
                    print(f"选择器 '{selector}' 找到 {len(found)} 个元素")
                    elements = found
                    break
            except:
                continue
                
        if not elements:
            # 最后尝试: 获取所有可能包含帖子的元素
            print("尝试通用方法提取...")
            elements = self.page.query_selector_all('div[class*="card"], div[class*="item"], article')
            
        for elem in elements[:max_posts * 2]:  # 多取一些以防解析失败
            try:
                topic = self._parse_topic_element(elem)
                if topic and topic.get('title'):
                    topics.append(topic)
                    if len(topics) >= max_posts:
                        break
            except Exception as e:
                continue
                
        return topics
        
    def _parse_topic_element(self, elem) -> Optional[Dict]:
        """解析单个帖子元素"""
        try:
            # 获取文本内容
            text = elem.inner_text()
            if not text or len(text) < 10:
                return None
            
            # 提取标题 - 尝试多种方式
            title = ''
            
            # 方法1: 查找特定的标题元素
            title_selectors = [
                'h2', 'h3', 'h4',
                '.title', '[class*="title"]',
                '.moment-card__title', '.moment-card__content',
                '[class*="content"]', '[class*="text"]',
                'p'
            ]
            for sel in title_selectors:
                title_elem = elem.query_selector(sel)
                if title_elem:
                    candidate = title_elem.inner_text().strip()
                    # 标题通常比时间字符串长
                    if candidate and len(candidate) > 5 and not re.match(r'^\d+\s*(天|小时|分钟|秒|刚刚)', candidate):
                        # 排除纯时间格式的文本
                        if not re.match(r'^\d{4}/\d{1,2}/\d{1,2}$', candidate):
                            title = candidate
                            break
                
            # 方法2: 从文本行中提取最可能是标题的行
            if not title:
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                for line in lines:
                    # 跳过时间格式
                    if re.match(r'^\d+\s*(天|小时|分钟|秒|刚刚)前$', line):
                        continue
                    if re.match(r'^\d{4}/\d{1,2}/\d{1,2}$', line):
                        continue
                    # 跳过太短的行
                    if len(line) < 5:
                        continue
                    # 跳过纯数字
                    if line.isdigit():
                        continue
                    # 这行可能是标题
                    if len(line) > len(title):
                        title = line
                        
            # 截断过长的标题
            if len(title) > 150:
                title = title[:150] + '...'
                    
            # 提取作者
            author = '未知'
            author_selectors = ['.author', '.user-name', '[class*="author"]', '[class*="user"]', '[class*="name"]']
            for sel in author_selectors:
                author_elem = elem.query_selector(sel)
                if author_elem:
                    author_text = author_elem.inner_text().strip().split('\n')[0]
                    # 作者名通常较短
                    if author_text and len(author_text) < 30:
                        author = author_text
                        break
                    
            # 如果还没找到作者，尝试从文本中提取
            if author == '未知':
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                for i, line in enumerate(lines):
                    # 作者名通常在时间之前
                    if re.match(r'^\d+\s*(天|小时|分钟|秒|刚刚)前', line) or re.match(r'^\d{4}/\d', line):
                        if i > 0 and len(lines[i-1]) < 30:
                            author = lines[i-1]
                            break
                    
            # 提取链接
            link = ''
            link_elem = elem.query_selector('a[href*="/moment/"], a[href*="/topic/"], a[href]')
            if link_elem:
                href = link_elem.get_attribute('href')
                if href:
                    link = href if href.startswith('http') else self.base_url + href
                    
            # 提取时间
            time_text = ''
            # 从文本中匹配时间格式
            time_patterns = [
                r'\d+\s*(?:天|小时|分钟|秒)前',
                r'刚刚',
                r'\d{4}/\d{1,2}/\d{1,2}',
                r'\d{1,2}/\d{1,2}',
            ]
            for pattern in time_patterns:
                match = re.search(pattern, text)
                if match:
                    time_text = match.group()
                    break
                    
            # 提取互动数据
            likes = '0'
            comments = '0'
            
            # 查找包含数字的元素
            footer = elem.query_selector('[class*="footer"], [class*="action"], [class*="stat"], [class*="interact"]')
            if footer:
                footer_text = footer.inner_text()
                numbers = re.findall(r'\d+', footer_text)
                if len(numbers) >= 1:
                    likes = numbers[0]
                if len(numbers) >= 2:
                    comments = numbers[1]
            else:
                # 从整个文本中提取末尾的数字
                numbers = re.findall(r'\d+', text)
                if len(numbers) >= 2:
                    likes = numbers[-2] if len(numbers) >= 2 else numbers[-1]
                    comments = numbers[-1] if len(numbers) >= 2 else '0'
                    
            return {
                "title": title or "（无标题）",
                "link": link,
                "author": author[:50],
                "time": time_text,
                "likes": likes,
                "comments": comments,
                "content_preview": text[:300],
                "type": "topic",
                "fetched_at": datetime.now().isoformat()
            }
        except Exception as e:
            return None
            
    def fetch_reviews(self, max_reviews: int = 20) -> List[Dict]:
        """
        获取最新评价
        
        Args:
            max_reviews: 最大评价数量
        
        Returns:
            评价列表
        """
        url = f"{self.base_url}/app/{self.app_id}/review"
        
        try:
            self._start_browser()
            print(f"正在访问: {url}")
            self.page.goto(url, wait_until='networkidle', timeout=30000)
            
            self._wait_for_content()
            self._scroll_page(2)
            
            reviews = []
            
            # 尝试从 NUXT 数据提取
            nuxt_data = self.page.evaluate('''() => {
                if (window.__NUXT__) return JSON.stringify(window.__NUXT__);
                return null;
            }''')
            
            if nuxt_data:
                try:
                    data = json.loads(nuxt_data)
                    reviews = self._parse_nuxt_reviews(data, max_reviews)
                    if reviews:
                        print(f"从 NUXT 数据解析到 {len(reviews)} 条评价")
                        return reviews
                except Exception as e:
                    print(f"解析 NUXT 评价数据失败: {e}")
                    
            # 从 DOM 提取
            print("尝试从 DOM 中提取评价...")
            reviews = self._extract_reviews_from_dom(max_reviews)
            
            return reviews
            
        except Exception as e:
            print(f"获取评价失败: {e}")
            return []
            
    def _parse_nuxt_reviews(self, data: dict, max_reviews: int) -> List[Dict]:
        """从 NUXT 数据中解析评价"""
        reviews = []
        
        def find_reviews(obj, depth=0):
            if depth > 10:
                return None
            if isinstance(obj, dict):
                if 'reviews' in obj and isinstance(obj['reviews'], list):
                    return obj['reviews']
                if 'list' in obj and isinstance(obj['list'], list):
                    if obj['list'] and isinstance(obj['list'][0], dict):
                        first = obj['list'][0]
                        if any(k in first for k in ['rating', 'score', 'review']):
                            return obj['list']
                for v in obj.values():
                    result = find_reviews(v, depth + 1)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = find_reviews(item, depth + 1)
                    if result:
                        return result
            return None
            
        items = find_reviews(data)
        
        if items:
            for item in items[:max_reviews]:
                try:
                    review = {
                        "rating": str(item.get('rating') or item.get('score', '')),
                        "content": (item.get('content') or item.get('text', ''))[:300],
                        "author": item.get('user', {}).get('name', '') or item.get('author', {}).get('name', '未知'),
                        "time": self._format_timestamp(item.get('created_time') or item.get('created_at')),
                        "likes": str(item.get('likes_count') or item.get('useful_count') or 0),
                        "type": "review",
                        "fetched_at": datetime.now().isoformat()
                    }
                    if review['content']:
                        reviews.append(review)
                except Exception as e:
                    continue
                    
        return reviews
        
    def _extract_reviews_from_dom(self, max_reviews: int) -> List[Dict]:
        """从 DOM 中提取评价"""
        reviews = []
        
        selectors = [
            '.review-item',
            '.review-card',
            '[class*="review"]',
            'article[class*="review"]',
        ]
        
        elements = []
        for selector in selectors:
            try:
                found = self.page.query_selector_all(selector)
                if found:
                    elements = found
                    break
            except:
                continue
                
        for elem in elements[:max_reviews * 2]:
            try:
                review = self._parse_review_element(elem)
                if review and review.get('content'):
                    reviews.append(review)
                    if len(reviews) >= max_reviews:
                        break
            except:
                continue
                
        return reviews
        
    def _parse_review_element(self, elem) -> Optional[Dict]:
        """解析单个评价元素"""
        try:
            text = elem.inner_text()
            if not text or len(text) < 10:
                return None
                
            # 提取评分
            rating = ''
            rating_elem = elem.query_selector('[class*="rating"], [class*="score"], [class*="star"]')
            if rating_elem:
                rating = rating_elem.inner_text().strip()
                # 尝试提取数字
                match = re.search(r'(\d+)', rating)
                if match:
                    rating = match.group(1)
                    
            # 提取内容
            content = ''
            content_elem = elem.query_selector('[class*="content"], [class*="text"], p')
            if content_elem:
                content = content_elem.inner_text().strip()
            if not content:
                content = text[:300]
                
            # 提取作者
            author = '未知'
            author_elem = elem.query_selector('[class*="author"], [class*="user"]')
            if author_elem:
                author = author_elem.inner_text().strip().split('\n')[0]
                
            # 提取时间
            time_text = ''
            time_elem = elem.query_selector('time, [class*="time"], [class*="date"]')
            if time_elem:
                time_text = time_elem.inner_text().strip()
                
            return {
                "rating": rating,
                "content": content,
                "author": author[:50],
                "time": time_text,
                "likes": "0",
                "type": "review",
                "fetched_at": datetime.now().isoformat()
            }
        except:
            return None
            
    def monitor(self, interval_minutes: int = 30) -> Dict:
        """
        执行监控任务
        
        Args:
            interval_minutes: 监控间隔（分钟）
        
        Returns:
            监控结果
        """
        print(f"开始监控 TapTap 社区 (游戏ID: {self.app_id})，间隔 {interval_minutes} 分钟...")
        
        try:
            while True:
                print(f"\n{'='*20} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {'='*20}")
                
                # 获取数据
                topics = self.fetch_topics(10)
                reviews = self.fetch_reviews(10)
                
                # 添加新数据并去重
                new_topics = self._add_new_topics(topics)
                new_reviews = self._add_new_reviews(reviews)
                
                # 输出结果
                if new_topics:
                    print(f"\n🆕 新帖子 ({len(new_topics)} 个):")
                    for i, topic in enumerate(new_topics, 1):
                        print(f"\n{i}. {topic['title']}")
                        print(f"   作者: {topic['author']} | 时间: {topic['time']}")
                        print(f"   👍 {topic['likes']} | 💬 {topic['comments']}")
                        if topic['link']:
                            print(f"   链接: {topic['link']}")
                else:
                    print(f"\n📱 无新帖子 (已记录 {len(self.existing_topics)} 个)")
                    
                if new_reviews:
                    print(f"\n🆕 新评价 ({len(new_reviews)} 条):")
                    for i, review in enumerate(new_reviews, 1):
                        print(f"\n{i}. 评分: {review['rating']} | {review['author']}")
                        print(f"   {review['content'][:100]}{'...' if len(review['content']) > 100 else ''}")
                else:
                    print(f"\n⭐ 无新评价 (已记录 {len(self.existing_reviews)} 条)")
                    
                # 保存数据
                if new_topics or new_reviews:
                    self._save_data()
                    
                # 等待下一次监控
                if interval_minutes > 0:
                    print(f"\n⏳ 等待 {interval_minutes} 分钟后继续...")
                    time.sleep(interval_minutes * 60)
                else:
                    break
                    
        except KeyboardInterrupt:
            print("\n\n✋ 监控已停止")
        finally:
            self._close_browser()
            # 最后保存一次
            self._save_data()
            
        return {"status": "completed", "last_run": datetime.now().isoformat()}


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TapTap 社区监控 (Playwright版)")
    parser.add_argument("--interval", type=int, default=30, 
                        help="监控间隔（分钟），0表示只运行一次")
    parser.add_argument("--app-id", type=str, default="236096", 
                        help="游戏ID（默认：236096为盲盒派对）")
    parser.add_argument("--data-file", type=str, default=None,
                        help="数据存储文件路径（默认: data/{app_id}_data.json）")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="无头模式运行（默认开启）")
    parser.add_argument("--visible", action="store_true",
                        help="显示浏览器窗口（调试用）")
    
    args = parser.parse_args()
    
    monitor = TapTapMonitor(
        app_id=args.app_id, 
        headless=not args.visible,
        data_file=args.data_file
    )
    monitor.monitor(interval_minutes=args.interval)


if __name__ == "__main__":
    main()