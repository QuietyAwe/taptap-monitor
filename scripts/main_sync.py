#!/usr/bin/env python3
"""
TapTap 监控脚本 v2.0
功能：爬取最新帖子/评价，排除已处理 ID并过滤系统分享帖，生成待分析数据
输出：data/to_analyze.json
"""

import json
import time
import re
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 路径配置
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
DATA_DIR = SKILL_DIR / "data"
CONFIG_FILE = SKILL_DIR / "config.json"
HISTORY_FILE = DATA_DIR / "history_ids.txt"
OUTPUT_FILE = DATA_DIR / "to_analyze.json"
LOG_DIR = SKILL_DIR / "logs"
# 过滤规则
SKIP_PATTERNS = [
    r"^.+竟然对我说\.\.\.$",   # 角色互动分享
    r"^测试你和.+的羁绊$",     # 羁绊测试
    r"^和.+聊天竟然这么好玩",   # 聊天分享
    r"主线送角色",              # 福利宣传
    r"快来沾沾好运",            # 福利宣传
    r"入坑即可养成", 
]
# Playwright 导入
try:
    from playwright.sync_api import sync_playwright, Page, Browser
except ImportError:
    print("错误：未安装 playwright，请运行：pip install playwright && playwright install chromium")
    sys.exit(1)


class TapTapMonitor:
    """TapTap 监控器"""
    
    def __init__(self, app_id: str = "236096", headless: bool = True):
        self.app_id = app_id
        self.base_url = "https://www.taptap.cn"
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._playwright = None
        
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
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            
    def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.page = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
                
    def _wait_for_content(self, timeout: int = 15000):
        """等待页面内容加载"""
        try:
            self.page.wait_for_selector('.moment-card, .moment-list-item, [class*="moment"]', timeout=timeout)
        except:
            pass
        time.sleep(2)
        
    def _scroll_page(self, scrolls: int = 3):
        """模拟滚动加载更多内容"""
        for _ in range(scrolls):
            self.page.evaluate('window.scrollBy(0, 800)')
            time.sleep(0.5)
        self.page.evaluate('window.scrollTo(0, 0)')
        time.sleep(0.5)
        
    def _format_timestamp(self, ts) -> str:
        """格式化时间戳"""
        if not ts:
            return ''
        try:
            if isinstance(ts, (int, float)):
                if ts > 1e12:
                    ts = ts / 1000
                return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
            return str(ts)
        except:
            return str(ts)
            
    def fetch_topics(self, max_posts: int = 20) -> List[Dict]:
        """获取最新帖子"""
        url = f"{self.base_url}/app/{self.app_id}/topic?sort=created"
        
        try:
            self._start_browser()
            print(f"正在访问帖子页: {url}")
            self.page.goto(url, wait_until='networkidle', timeout=30000)
            self._wait_for_content()
            self._scroll_page(2)
            
            # 尝试从 NUXT 数据提取
            nuxt_data = self.page.evaluate('''() => {
                if (window.__NUXT__) return JSON.stringify(window.__NUXT__);
                return null;
            }''')
            
            if nuxt_data:
                try:
                    data = json.loads(nuxt_data)
                    topics = self._parse_nuxt_topics(data, max_posts)
                    if topics:
                        print(f"从 NUXT 解析到 {len(topics)} 个帖子")
                        return topics
                except Exception as e:
                    print(f"解析 NUXT 帖子失败: {e}")
                    
            # 从 DOM 提取
            print("从 DOM 提取帖子...")
            return self._extract_topics_from_dom(max_posts)
            
        except Exception as e:
            print(f"获取帖子失败: {e}")
            return []
            
    def _parse_nuxt_topics(self, data: dict, max_posts: int) -> List[Dict]:
        """从 NUXT 数据解析帖子"""
        topics = []
        
        def find_moment_lists(obj, depth=0):
            if depth > 15:
                return []
            results = []
            if isinstance(obj, dict):
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
                    
                    post_id = moment.get('id_str') or moment.get('id')
                    topic_data = moment.get('topic', {})
                    title = topic_data.get('title', '')
                    summary = topic_data.get('summary', '')
                    content = summary or title
                    
                    author_data = moment.get('author', {}).get('user', {})
                    author = author_data.get('name', '未知')
                    
                    created_time = moment.get('created_time') or moment.get('publish_time', 0)
                    post_time = self._format_timestamp(created_time)
                    
                    stat = moment.get('stat', {})
                    likes = str(stat.get('ups', 0))
                    comments = str(stat.get('comments', 0))
                    
                    link = f"{self.base_url}/moment/{post_id}" if post_id else ''
                    
                    topic = {
                        "id": str(post_id) if post_id else '',
                        "type": "topic",
                        "title": title[:150] if title else content[:150] or "（无标题）",
                        "link": link,
                        "author": author[:50],
                        "time": post_time,
                        "likes": likes,
                        "comments": comments,
                        "content": content[:500] if content else '',
                        "fetched_at": datetime.now().isoformat()
                    }
                    
                    if topic['title'] != "（无标题）":
                        topics.append(topic)
                        
                except Exception as e:
                    continue
        
        # 去重
        seen = set()
        unique = []
        for t in topics:
            if t['id'] and t['id'] not in seen:
                seen.add(t['id'])
                unique.append(t)
        
        return unique[:max_posts]
        
    def _extract_topics_from_dom(self, max_posts: int) -> List[Dict]:
        """从 DOM 提取帖子（备用方案）"""
        topics = []
        selectors = ['.moment-card', '.moment-list-item', '[class*="moment-card"]']
        
        elements = []
        for selector in selectors:
            try:
                found = self.page.query_selector_all(selector)
                if found:
                    elements = found
                    break
            except:
                continue
                
        for elem in elements[:max_posts * 2]:
            try:
                topic = self._parse_topic_element(elem)
                if topic and topic.get('title'):
                    topics.append(topic)
                    if len(topics) >= max_posts:
                        break
            except:
                continue
                
        return topics
        
    def _parse_topic_element(self, elem) -> Optional[Dict]:
        """解析单个帖子元素"""
        try:
            text = elem.inner_text()
            if not text or len(text) < 10:
                return None
                
            # 提取标题
            title = ''
            for sel in ['h2', 'h3', '.title', '[class*="title"]', 'p']:
                title_elem = elem.query_selector(sel)
                if title_elem:
                    candidate = title_elem.inner_text().strip()
                    if candidate and len(candidate) > 5:
                        title = candidate[:150]
                        break
                        
            # 提取链接
            link = ''
            link_elem = elem.query_selector('a[href*="/moment/"]')
            if link_elem:
                href = link_elem.get_attribute('href')
                if href:
                    link = href if href.startswith('http') else self.base_url + href
                    
            # 提取 ID
            post_id = ''
            if link:
                match = re.search(r'/moment/(\d+)', link)
                if match:
                    post_id = match.group(1)
                    
            # 提取作者
            author = '未知'
            for sel in ['.author', '.user-name', '[class*="author"]']:
                author_elem = elem.query_selector(sel)
                if author_elem:
                    author = author_elem.inner_text().strip().split('\n')[0][:50]
                    break
                    
            # 提取时间
            time_text = ''
            for pattern in [r'\d+\s*(?:天|小时|分钟|秒)前', r'刚刚', r'\d{4}/\d{1,2}/\d{1,2}']:
                match = re.search(pattern, text)
                if match:
                    time_text = match.group()
                    break
                    
            return {
                "id": post_id,
                "type": "topic",
                "title": title or "（无标题）",
                "link": link,
                "author": author,
                "time": time_text,
                "content": text[:500],
                "fetched_at": datetime.now().isoformat()
            }
        except:
            return None
            
    def fetch_reviews(self, max_reviews: int = 20) -> List[Dict]:
        """获取最新评价"""
        url = f"{self.base_url}/app/{self.app_id}/review?sort=new"
        
        try:
            self._start_browser()
            print(f"正在访问评价页: {url}")
            self.page.goto(url, wait_until='networkidle', timeout=30000)
            self._wait_for_content()
            self._scroll_page(2)
            
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
                        print(f"从 NUXT 解析到 {len(reviews)} 条评价")
                        return reviews
                except Exception as e:
                    print(f"解析 NUXT 评价失败: {e}")
                    
            # 从 DOM 提取
            print("从 DOM 提取评价...")
            return self._extract_reviews_from_dom(max_reviews)
            
        except Exception as e:
            print(f"获取评价失败: {e}")
            return []
            
    def _parse_nuxt_reviews(self, data: dict, max_reviews: int) -> List[Dict]:
        """从 NUXT 数据解析评价"""
        reviews = []
        
        def find_review_list(obj, depth=0):
            if depth > 20:
                return None
            if isinstance(obj, dict):
                if 'list' in obj and isinstance(obj['list'], list):
                    for item in obj['list']:
                        if isinstance(item, dict) and 'moment' in item:
                            return obj['list']
                for v in obj.values():
                    result = find_review_list(v, depth + 1)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = find_review_list(item, depth + 1)
                    if result:
                        return result
            return None
            
        items = find_review_list(data)
        
        if items:
            for item in items[:max_reviews]:
                try:
                    moment = item.get('moment', {})
                    review_data = moment.get('review', {})
                    author_data = moment.get('author', {}).get('user', {})
                    
                    # 评价短 ID
                    review_id = review_data.get('id')
                    
                    # 评分
                    score = review_data.get('score', '')
                    rating = f"{score}星" if score else "未评分"
                    
                    # 游戏时长
                    played_spent = review_data.get('played_spent') or review_data.get('total_played_spent')
                    played_hours = round(played_spent / 3600, 1) if played_spent else 0
                    
                    # 内容
                    contents = review_data.get('contents', {})
                    content = contents.get('text', '') if isinstance(contents, dict) else str(contents)
                    content = re.sub(r'<br\s*/?>', '\n', content)
                    content = re.sub(r'<[^>]+>', '', content)
                    
                    # 作者
                    author = author_data.get('name', '未知')
                    
                    # 时间
                    created_time = moment.get('created_time')
                    post_time = self._format_timestamp(created_time) if created_time else ''
                    
                    # 链接
                    link = f"{self.base_url}/review/{review_id}" if review_id else ''
                    
                    review = {
                        "id": str(review_id) if review_id else '',
                        "type": "review",
                        "link": link,
                        "rating": rating,
                        "score": str(score) if score else '',
                        "played_hours": str(played_hours) if played_hours else '',
                        "content": content[:500] if content else '',
                        "author": author,
                        "time": post_time,
                        "likes": str(review_data.get('ups', 0)),
                        "fetched_at": datetime.now().isoformat()
                    }
                    
                    if review['content'] and review['id']:
                        reviews.append(review)
                except Exception as e:
                    continue
                    
        return reviews
        
    def _extract_reviews_from_dom(self, max_reviews: int) -> List[Dict]:
        """从 DOM 提取评价（备用方案）"""
        reviews = []
        selectors = ['.review-item', '.review-card', '[class*="review"]']
        
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
            for sel in ['[class*="rating"]', '[class*="score"]', '[class*="star"]']:
                rating_elem = elem.query_selector(sel)
                if rating_elem:
                    match = re.search(r'(\d)', rating_elem.inner_text())
                    if match:
                        rating = f"{match.group(1)}星"
                        break
                        
            # 提取内容
            content = ''
            for sel in ['[class*="content"]', '[class*="text"]', 'p']:
                content_elem = elem.query_selector(sel)
                if content_elem:
                    content = content_elem.inner_text().strip()[:500]
                    break
            if not content:
                content = text[:500]
                
            # 提取链接和 ID
            link = ''
            review_id = ''
            link_elem = elem.query_selector('a[href*="/review/"]')
            if link_elem:
                href = link_elem.get_attribute('href')
                if href:
                    link = href if href.startswith('http') else self.base_url + href
                    match = re.search(r'/review/(\d+)', link)
                    if match:
                        review_id = match.group(1)
                        
            # 提取作者
            author = '未知'
            for sel in ['[class*="author"]', '[class*="user"]']:
                author_elem = elem.query_selector(sel)
                if author_elem:
                    author = author_elem.inner_text().strip().split('\n')[0][:50]
                    break
                    
            # 提取时间
            time_text = ''
            for pattern in [r'\d+\s*(?:天|小时|分钟|秒)前', r'刚刚', r'\d{4}/\d{1,2}/\d{1,2}']:
                match = re.search(pattern, text)
                if match:
                    time_text = match.group()
                    break
                    
            return {
                "id": review_id,
                "type": "review",
                "link": link,
                "rating": rating,
                "content": content,
                "author": author,
                "time": time_text,
                "fetched_at": datetime.now().isoformat()
            }
        except:
            return None


def load_history_ids() -> set:
    """加载已处理 ID"""
    ids = set()
    if HISTORY_FILE.exists():
        for line in HISTORY_FILE.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                ids.add(line)
    return ids


def save_history_ids(new_ids: List[str]):
    """追加保存新 ID"""
    if not new_ids:
        return
    with HISTORY_FILE.open('a', encoding='utf-8') as f:
        for id_ in new_ids:
            f.write(f"{id_}\n")


def filter_new_items(items: List[Dict], history_ids: set) -> List[Dict]:
    """
    过滤已处理的内容及系统默认分享贴
    """
    new_items = []
    for item in items:
        item_id = item.get('id', '')
        title = item.get('title', '')
        if not item_id or item_id in history_ids:
            continue
        if item.get('type') == 'topic':
            is_skip = False
            for pattern in SKIP_PATTERNS:
                if re.search(pattern, title):
                    is_skip = True
                    break

            if is_skip:
                # print(f"  [系统过滤] 跳过分享贴: {title}")
                continue
                
        new_items.append(item)
        
    return new_items


def main():
    """主函数"""
    print(f"[{datetime.now()}] 开始 TapTap 监控...")
    
    # 加载配置
    config = {}
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        except:
            pass
    
    game_id = config.get('game_id') or '236096'  # 默认盲盒派对
    
    # 加载已处理 ID
    history_ids = load_history_ids()
    print(f"已加载 {len(history_ids)} 个历史 ID")
    
    # 初始化监控器
    monitor = TapTapMonitor(app_id=game_id, headless=True)
    
    try:
        # 获取数据
        topics = monitor.fetch_topics(20)
        reviews = monitor.fetch_reviews(20)
        
        print(f"获取到 {len(topics)} 个帖子, {len(reviews)} 条评价")
        
        # 过滤已处理
        new_topics = filter_new_items(topics, history_ids)
        new_reviews = filter_new_items(reviews, history_ids)
        
        print(f"新内容: {len(new_topics)} 个帖子, {len(new_reviews)} 条评价")
        
        # 合并待分析数据
        to_analyze = new_topics + new_reviews
        
        # 保存待分析数据
        OUTPUT_FILE.write_text(json.dumps(to_analyze, ensure_ascii=False, indent=2))
        print(f"待分析数据已保存: {OUTPUT_FILE}")
        
        # 更新历史 ID（只追加本次新发现的 ID）
        new_ids = [item['id'] for item in to_analyze if item.get('id')]
        save_history_ids(new_ids)
        
        # 输出摘要
        if to_analyze:
            print(f"\n待分析内容预览:")
            for item in to_analyze[:5]:
                if item['type'] == 'topic':
                    print(f"  [帖子] {item.get('title', '')[:50]}")
                else:
                    print(f"  [评价] {item.get('rating', '')} {item.get('content', '')[:50]}")
            if len(to_analyze) > 5:
                print(f"  ... 共 {len(to_analyze)} 条")
        else:
            print("无新内容")
            
    finally:
        monitor._close_browser()
        
    return to_analyze


if __name__ == "__main__":
    result = main()
    print(f"\n完成，共 {len(result)} 条待分析")