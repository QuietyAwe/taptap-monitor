#!/usr/bin/env python3
"""
TapTap 自动回复脚本
功能：
1. 回复帖子 (moment)
2. 回复评价 (review)
3. 支持自定义回复内容
4. 支持动态生成回复（传入生成函数）
"""
import json
import time
import os
import re
import random
from datetime import datetime
from typing import List, Dict, Optional, Callable, Union
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext


class TapTapReply:
    """TapTap 自动回复类"""
    
    def __init__(
        self, 
        app_id: str = "236096",
        headless: bool = True,
        cookie_file: str = None,
        data_dir: str = None
    ):
        self.app_id = app_id
        self.base_url = "https://www.taptap.cn"
        self.headless = headless
        self.cookie_file = cookie_file or os.path.join(
            os.path.dirname(__file__), "..", "data", f"state_{app_id}.json"
        )
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), "..", "data")
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None
        
        # 回复记录
        self.reply_log_file = os.path.join(self.data_dir, f"replies_{app_id}.json")
        self.reply_log = self._load_reply_log()
    
    def _load_reply_log(self) -> Dict:
        """加载回复记录"""
        if os.path.exists(self.reply_log_file):
            try:
                with open(self.reply_log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data.get("replied_ids"), list):
                        data["replied_ids"] = set(data["replied_ids"])
                    return data
            except:
                pass
        return {"replies": [], "replied_ids": set()}
    
    def _save_reply_log(self):
        """保存回复记录"""
        os.makedirs(os.path.dirname(self.reply_log_file), exist_ok=True)
        log_data = {
            "last_updated": datetime.now().isoformat(),
            "replies": self.reply_log.get("replies", []),
            "replied_ids": list(self.reply_log.get("replied_ids", set()))
        }
        with open(self.reply_log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
    
    def _start_browser(self):
        """启动浏览器"""
        if self.browser is None:
            print("🔧 启动浏览器...")
            self._playwright = sync_playwright().start()
            self.browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )
            
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
            )
            
            # 先加载 cookies
            self._load_cookies_to_context()
            
            # 创建主页面
            self.page = self.context.new_page()
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            
            # 设置 storage 到主页面
            self._setup_storage_on_page()
            
            print("✅ 浏览器已启动")
    
    def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """随机延时，模拟人类行为"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def _load_cookies_to_context(self):
        """加载 Cookies 到 context"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                if "cookies" in state:
                    self.context.add_cookies(state["cookies"])
                    print(f"✅ 已加载 {len(state['cookies'])} 个 Cookies")
                # 保存 state 供后续使用
                self._state_data = state
            except Exception as e:
                print(f"⚠️ 加载 Cookies 失败: {e}")
                self._state_data = {}
    
    def _setup_storage_on_page(self):
        """在页面上设置 LocalStorage 和 SessionStorage"""
        state = getattr(self, '_state_data', {})
        if not state or "origins" not in state:
            return
        
        # 先访问网站以设置 storage
        self.page.goto(self.base_url, wait_until='domcontentloaded')
        time.sleep(1)
        
        for origin in state.get("origins", []):
            origin_url = origin.get("origin", "")
            if origin_url and origin_url in self.base_url:
                # 设置 localStorage
                if "localStorage" in origin:
                    for item in origin["localStorage"]:
                        try:
                            # 转义特殊字符
                            value = item['value'].replace("\\", "\\\\").replace("'", "\\'")
                            self.page.evaluate(f"localStorage.setItem('{item['name']}', '{value}')")
                        except Exception as e:
                            print(f"⚠️ 设置 localStorage 失败: {item['name']} - {e}")
                # 设置 sessionStorage
                if "sessionStorage" in origin:
                    for item in origin["sessionStorage"]:
                        try:
                            value = item['value'].replace("\\", "\\\\").replace("'", "\\'")
                            self.page.evaluate(f"sessionStorage.setItem('{item['name']}', '{value}')")
                        except Exception as e:
                            print(f"⚠️ 设置 sessionStorage 失败: {item['name']} - {e}")
        
        print(f"✅ 已加载完整登录态（Cookie + Storage）")
    
    def _load_cookies(self):
        """加载保存的浏览器状态（Cookie + LocalStorage + SessionStorage）"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                # 使用 context.add_cookies() 加载 cookies
                if "cookies" in state:
                    self.context.add_cookies(state["cookies"])
                # 加载 localStorage 和 sessionStorage
                if "origins" in state:
                    for origin in state["origins"]:
                        origin_url = origin.get("origin", "")
                        if origin_url:
                            # 在对应域名下设置 storage
                            page = self.context.new_page()
                            page.goto(origin_url, wait_until='domcontentloaded')
                            # 设置 localStorage
                            if "localStorage" in origin:
                                for item in origin["localStorage"]:
                                    page.evaluate(
                                        f"localStorage.setItem('{item['name']}', '{item['value']}')"
                                    )
                            # 设置 sessionStorage
                            if "sessionStorage" in origin:
                                for item in origin["sessionStorage"]:
                                    page.evaluate(
                                        f"sessionStorage.setItem('{item['name']}', '{item['value']}')"
                                    )
                            page.close()
                print(f"✅ 已加载完整登录态（Cookie + Storage）")
            except Exception as e:
                print(f"⚠️ 加载浏览器状态失败: {e}")
    
    def _save_cookies(self):
        """保存浏览器状态（Cookie + LocalStorage + SessionStorage）"""
        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
        # 使用 Playwright 原生的 storage_state() 方法
        state = self.context.storage_state()
        with open(self.cookie_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存完整登录态（Cookie + Storage）")
    
    def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
    
    def check_login(self) -> bool:
        """检查是否已登录"""
        try:
            print(f"🌐 访问 {self.base_url} ...")
            self.page.goto(f"{self.base_url}", wait_until='domcontentloaded', timeout=30000)
            print("✅ 页面加载完成")
            self._random_delay(2, 4)
            
            # 检查登录状态
            login_indicators = [
                '.header-user-avatar',
                '.user-avatar',
                '[class*="user-avatar"]',
                '[class*="header-user"]',
            ]
            
            for selector in login_indicators:
                elem = self.page.query_selector(selector)
                if elem:
                    print("✅ 已登录")
                    return True
            
            login_btn = self.page.query_selector('text=登录')
            if login_btn:
                print("❌ 未登录")
                return False
            
            return False
            
        except Exception as e:
            print(f"检查登录状态失败: {e}")
            return False
    
    def manual_login(self):
        """手动登录（等待用户扫码）"""
        print("\n" + "="*50)
        print("请手动登录 TapTap")
        print("1. 浏览器窗口已打开")
        print("2. 请扫码或输入账号密码登录")
        print("3. 登录成功后按回车继续...")
        print("="*50 + "\n")
        
        if self.browser:
            self._close_browser()
        
        self.headless = False
        self._start_browser()
        
        self.page.goto(f"{self.base_url}", wait_until='networkidle')
        
        input("登录成功后按回车继续...")
        
        self._save_cookies()
        print("✅ 登录态已保存")
    
    def _get_page_type_and_id(self, url: str) -> tuple:
        """
        从 URL 判断页面类型和 ID
        
        Returns:
            (page_type, page_id) - page_type: 'moment' | 'review' | 'unknown'
        """
        # 帖子: https://www.taptap.cn/moment/123456
        moment_match = re.search(r'/moment/(\d+)', url)
        if moment_match:
            return ('moment', moment_match.group(1))
        
        # 评价: https://www.taptap.cn/review/123456 或 /app/236096/review/123456
        review_match = re.search(r'/review/(\d+)', url)
        if review_match:
            return ('review', review_match.group(1))
        
        return ('unknown', None)
    
    def send_reply(
        self, 
        url_or_id: str,
        content: str,
        page_type: str = "auto",
        dry_run: bool = False
    ) -> Dict:
        """
        发送回复
        
        Args:
            url_or_id: 帖子/评价的 URL 或 ID
            content: 回复内容
            page_type: 页面类型 'moment' | 'review' | 'auto'（自动判断）
            dry_run: 仅模拟，不实际发送
        
        Returns:
            回复结果
        """
        result = {
            "url": url_or_id,
            "content": content,
            "status": "pending",
            "message": "",
            "timestamp": datetime.now().isoformat()
        }
        
        # 构建完整 URL
        if url_or_id.startswith('http'):
            url = url_or_id
        else:
            # 只有 ID，默认为帖子
            url = f"{self.base_url}/moment/{url_or_id}"
        
        # 判断页面类型
        if page_type == "auto":
            page_type, page_id = self._get_page_type_and_id(url)
        else:
            _, page_id = self._get_page_type_and_id(url)
        
        result["page_type"] = page_type
        
        # 检查是否已回复过
        replied_ids = self.reply_log.get("replied_ids", set())
        if page_id and page_id in replied_ids:
            result["status"] = "skipped"
            result["message"] = "已回复过，跳过"
            return result
        
        if dry_run:
            result["status"] = "dry_run"
            result["message"] = "模拟回复，未实际发送"
            return result
        
        try:
            print(f"🌐 访问: {url}")
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            print("✅ 页面加载完成")
            self._random_delay(2, 4)
            
            # 根据页面类型选择不同的回复方式
            if page_type == "review":
                success = self._reply_to_review(content)
            else:
                success = self._reply_to_moment(content)
            
            if success:
                result["status"] = "success"
                result["message"] = "回复成功"
                
                # 记录已回复
                if "replied_ids" not in self.reply_log:
                    self.reply_log["replied_ids"] = set()
                if page_id:
                    self.reply_log["replied_ids"].add(page_id)
                
                if "replies" not in self.reply_log:
                    self.reply_log["replies"] = []
                self.reply_log["replies"].append(result)
                
                self._save_reply_log()
            else:
                result["status"] = "failed"
                result["message"] = "回复失败"
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
        
        return result
    
    def _reply_to_moment(self, content: str) -> bool:
        """回复帖子"""
        try:
            # 查找评论输入框
            print("查找评论输入框...")
            editor_selectors = [
                '.tap-editor',
                '[contenteditable="true"][role="textbox"]',
                '.comment-editor .tap-editor',
                '.editor-content[contenteditable="true"]',
            ]
            
            input_elem = None
            for selector in editor_selectors:
                try:
                    input_elem = self.page.wait_for_selector(selector, timeout=5000)
                    if input_elem:
                        print(f"✅ 找到输入框: {selector}")
                        break
                except:
                    continue
            
            if not input_elem:
                print("❌ 未找到评论输入框")
                return False
            
            # 输入内容
            input_elem.click()
            self._random_delay(0.3, 0.8)
            input_elem.fill(content)
            print(f"✅ 已输入回复内容")
            self._random_delay(0.5, 1.0)
            
            # 查找发送按钮
            print("查找发送按钮...")
            send_selectors = [
                '.comment-editor__comment-editor-toolbar button:has-text("发送")',
                'button.tap-button:has-text("发送")',
                '.comment-editor button:has-text("发送")',
                'button:has-text("发送")',
            ]
            
            send_btn = None
            for selector in send_selectors:
                try:
                    send_btn = self.page.query_selector(selector)
                    if send_btn:
                        print(f"✅ 找到发送按钮")
                        break
                except:
                    continue
            
            if not send_btn:
                print("❌ 未找到发送按钮")
                return False
            
            # 点击发送
            send_btn.click()
            
            # 智能检测发送成功：检查输入框是否被清空
            max_wait = 5  # 最多等待 5 秒
            start_time = time.time()
            while time.time() - start_time < max_wait:
                try:
                    current_value = input_elem.inner_text()
                    if not current_value or current_value.strip() == "":
                        print("✅ 回复已发送（输入框已清空）")
                        return True
                except:
                    pass
                time.sleep(0.3)
            
            # 检查是否有成功提示
            try:
                self.page.wait_for_selector('text=发送成功', timeout=2000)
                print("✅ 发送成功（检测到成功提示）")
                return True
            except:
                pass
            
            # 检查是否有错误提示
            error_selectors = [
                '.toast-error',
                '.error-message',
                '[class*="error"]',
            ]
            for selector in error_selectors:
                try:
                    error_elem = self.page.query_selector(selector)
                    if error_elem and error_elem.is_visible():
                        print(f"❌ 发送失败: {error_elem.inner_text()}")
                        return False
                except:
                    pass
            
            print("⚠️ 发送状态未知，假设成功")
            return True
            
        except Exception as e:
            print(f"回复帖子失败: {e}")
            return False
    
    def _reply_to_review(self, content: str) -> bool:
        """回复评价"""
        try:
            # 评价页面的评论输入框可能有不同的选择器
            print("查找评价评论输入框...")
            
            # 先尝试找到评论区域
            comment_selectors = [
                '.review-comment-editor',
                '.comment-input-wrapper',
                '[class*="comment-editor"]',
            ]
            
            for selector in comment_selectors:
                try:
                    comment_area = self.page.query_selector(selector)
                    if comment_area:
                        print(f"✅ 找到评论区域: {selector}")
                        break
                except:
                    continue
            
            # 查找输入框
            editor_selectors = [
                '.review-comment-editor__textarea',
                '.tap-editor',
                '[contenteditable="true"]',
                'textarea[placeholder*="评论"]',
                'textarea[placeholder*="回复"]',
                'textarea',
            ]
            
            input_elem = None
            for selector in editor_selectors:
                try:
                    input_elem = self.page.wait_for_selector(selector, timeout=5000)
                    if input_elem:
                        print(f"✅ 找到输入框: {selector}")
                        break
                except:
                    continue
            
            if not input_elem:
                print("❌ 未找到评价评论输入框")
                return False
            
            # 点击输入框
            input_elem.click()
            self._random_delay(0.3, 0.8)
            
            # 判断是 textarea 还是 contenteditable
            tag = input_elem.evaluate('el => el.tagName.toLowerCase()')
            if tag == 'textarea':
                input_elem.fill(content)
            else:
                input_elem.fill(content)
            
            print(f"✅ 已输入回复内容")
            self._random_delay(0.5, 1.0)
            
            # 查找发送按钮
            print("查找发送按钮...")
            send_selectors = [
                '.review-comment-editor__post-wrap button',
                'button:has-text("发布")',
                'button:has-text("发送")',
                'button:has-text("提交")',
                '.btn-send',
                '[class*="submit"]',
            ]
            
            send_btn = None
            for selector in send_selectors:
                try:
                    send_btn = self.page.query_selector(selector)
                    if send_btn:
                        print(f"✅ 找到发送按钮")
                        break
                except:
                    continue
            
            if not send_btn:
                print("❌ 未找到发送按钮")
                return False
            
            # 点击发送
            send_btn.click()
            
            # 智能检测发送成功：检查输入框是否被清空
            max_wait = 5  # 最多等待 5 秒
            start_time = time.time()
            while time.time() - start_time < max_wait:
                try:
                    current_value = input_elem.inner_text() if tag != 'textarea' else input_elem.input_value()
                    if not current_value or current_value.strip() == "":
                        print("✅ 回复已发送（输入框已清空）")
                        return True
                except:
                    pass
                time.sleep(0.3)
            
            # 超时后检查是否有错误提示
            error_selectors = [
                '.toast-error',
                '.error-message',
                '[class*="error"]',
            ]
            for selector in error_selectors:
                try:
                    error_elem = self.page.query_selector(selector)
                    if error_elem and error_elem.is_visible():
                        print(f"❌ 发送失败: {error_elem.inner_text()}")
                        return False
                except:
                    pass
            
            print("⚠️ 发送状态未知，假设成功")
            return True
            
        except Exception as e:
            print(f"回复评价失败: {e}")
            return False
    
    def scan_and_reply(
        self,
        items: List[Dict],
        reply_content: Union[str, Callable[[Dict], str]] = "666",
        dry_run: bool = False,
        auto_confirm: bool = False,
        max_replies: int = 10,
        item_type: str = "auto"
    ) -> List[Dict]:
        """
        扫描并自动回复
        
        Args:
            items: 帖子/评价列表
            reply_content: 回复内容（字符串或生成函数）
            dry_run: 仅模拟
            auto_confirm: 自动确认
            max_replies: 最大回复数量
            item_type: 'topic' | 'review' | 'auto'
        
        Returns:
            回复结果列表
        """
        results = []
        reply_count = 0
        
        for item in items:
            if reply_count >= max_replies:
                print(f"\n已达到最大回复数量 {max_replies}，停止")
                break
            
            # 获取 URL
            link = item.get("link", "") or item.get("url", "")
            if not link:
                # 尝试构建 URL
                item_id = item.get("id", "")
                if item_id:
                    itype = item.get("type", item_type)
                    if itype == "review":
                        link = f"{self.base_url}/review/{item_id}"
                    else:
                        link = f"{self.base_url}/moment/{item_id}"
            
            if not link:
                print(f"跳过无链接项: {item.get('title', item.get('content', '')[:30])}")
                continue
            
            # 检查是否已回复
            _, page_id = self._get_page_type_and_id(link)
            replied_ids = self.reply_log.get("replied_ids", set())
            if page_id and page_id in replied_ids:
                print(f"跳过已回复: {item.get('title', item.get('content', '')[:30])}")
                continue
            
            # 生成回复内容
            # 优先使用 item 中的自定义回复内容
            if item.get("reply_content"):
                content = item.get("reply_content")
            elif callable(reply_content):
                content = reply_content(item)
                if not content:
                    print(f"跳过（未生成回复内容）: {item.get('title', item.get('content', '')[:30])}")
                    continue
            else:
                content = reply_content
            
            # 显示信息
            print(f"\n{'='*50}")
            if item.get("type") == "review" or "rating" in item:
                print(f"评价: {item.get('rating', '')} | {item.get('author', '')}")
                print(f"内容: {item.get('content', '')[:50]}...")
            else:
                print(f"帖子: {item.get('title', '')[:50]}...")
                print(f"作者: {item.get('author', '')} | 👍 {item.get('likes', '0')} | 💬 {item.get('comments', '0')}")
            print(f"链接: {link}")
            print(f"回复: {content[:50]}{'...' if len(content) > 50 else ''}")
            print(f"{'='*50}")
            
            # 确认
            if not auto_confirm:
                confirm = input("\n是否回复? (y/n/a=全部自动/s=跳过): ").strip().lower()
                if confirm == 'a':
                    auto_confirm = True
                elif confirm == 's':
                    continue
                elif confirm != 'y':
                    continue
            
            # 发送回复
            result = self.send_reply(
                url_or_id=link,
                content=content,
                page_type="auto",
                dry_run=dry_run
            )
            
            print(f"结果: {result['status']} - {result['message']}")
            results.append(result)
            
            if result["status"] in ["success", "submitted"]:
                reply_count += 1
            
            self._random_delay(2, 4)
        
        return results
    
    def reply_single(
        self,
        url: str,
        content: str,
        dry_run: bool = False
    ) -> Dict:
        """
        回复单个帖子/评价
        
        Args:
            url: 帖子/评价 URL
            content: 回复内容
            dry_run: 仅模拟
        
        Returns:
            回复结果
        """
        return self.send_reply(url, content, page_type="auto", dry_run=dry_run)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TapTap 自动回复工具")
    parser.add_argument("--app-id", type=str, default="236096", help="游戏ID")
    parser.add_argument("--login", action="store_true", help="手动登录保存登录态")
    parser.add_argument("--check-login", action="store_true", help="检查登录状态")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际发送")
    parser.add_argument("--auto", action="store_true", help="自动确认所有回复")
    parser.add_argument("--visible", action="store_true", help="显示浏览器窗口")
    
    # 回复相关
    parser.add_argument("--url", type=str, help="直接回复指定 URL")
    parser.add_argument("--content", type=str, default="666", help="回复内容")
    parser.add_argument("--content-file", type=str, help="从文件读取回复内容")
    parser.add_argument("--max", type=int, default=10, help="最大回复数量")
    
    # 数据源
    parser.add_argument("--data-file", type=str, help="帖子/评价数据文件 (JSON)")
    parser.add_argument("--fetch", action="store_true", help="先获取最新帖子")
    
    args = parser.parse_args()
    
    # 读取回复内容
    reply_content = args.content
    if args.content_file:
        try:
            with open(args.content_file, 'r', encoding='utf-8') as f:
                reply_content = f.read().strip()
        except Exception as e:
            print(f"读取回复内容文件失败: {e}")
            return
    
    reply = TapTapReply(
        app_id=args.app_id,
        headless=not args.visible
    )
    
    try:
        reply._start_browser()
        
        if args.login:
            reply.manual_login()
            return
        
        if args.check_login:
            is_logged_in = reply.check_login()
            print(f"登录状态: {'已登录' if is_logged_in else '未登录'}")
            return
        
        # 检查登录状态
        if not reply.check_login():
            print("请先运行 --login 进行登录")
            return
        
        # 直接回复指定 URL
        if args.url:
            result = reply.reply_single(
                url=args.url,
                content=reply_content,
                dry_run=args.dry_run
            )
            print(f"\n回复结果: {result}")
            return
        
        # 从数据文件读取
        items = []
        if args.data_file:
            try:
                with open(args.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = data.get("topics", []) + data.get("reviews", [])
            except Exception as e:
                print(f"读取数据文件失败: {e}")
                return
        
        if not items:
            print("请提供数据源:")
            print("  --url URL        直接回复指定 URL")
            print("  --data-file FILE 从 JSON 文件读取帖子/评价")
            return
        
        # 扫描并回复
        results = reply.scan_and_reply(
            items=items,
            reply_content=reply_content,
            dry_run=args.dry_run,
            auto_confirm=args.auto,
            max_replies=args.max
        )
        
        # 统计
        success_count = sum(1 for r in results if r["status"] in ["success", "submitted"])
        print(f"\n{'='*50}")
        print(f"回复完成: 成功 {success_count} / 总计 {len(results)}")
        print(f"{'='*50}")
        
    finally:
        reply._close_browser()


if __name__ == "__main__":
    main()