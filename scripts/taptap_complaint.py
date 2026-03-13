#!/usr/bin/env python3
"""
TapTap 差评投诉脚本
功能：监控差评 → 检测违规内容 → 自动投诉
"""
import json
import time
import re
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# 违规检测配置
VIOLATION_CONFIG = {
    # 谩骂/人身攻击关键词
    "abuse_words": [
        "傻逼", "煞笔", "沙比", "sb", "SB", "cnm", "操你", "草你", "妈的", "他妈",
        "狗屎", "垃圾游戏", "烂游戏", "废物", "脑残", "智障", "弱智", "白痴",
        "去死", "死全家", "全家爆炸", "畜生", "狗东西", "杂种", "王八蛋",
        "他妈的", "他娘的", "屁眼", "滚蛋", "滚粗", "恶心", "吐了"
    ],
    # 竞品名称（可自定义）
    "competitor_names": [
        # 示例竞品，需要根据实际游戏填写
        # "原神", "王者荣耀", "和平精英", "崩坏", "明日方舟"
    ],
    # 拉踩关键词
    "compare_words": [
        "不如", "吊打", "秒杀", "完爆", "碾压", "垃圾比", "比这好",
        "还是去玩", "不如去玩", "不如玩", "还是xxx好"
    ],
    # 敏感词
    "sensitive_words": [
        "代练", "代打", "外挂", "脚本", "刷钻", "刷金币", "破解版",
        "私服", "辅助", "透视", "自瞄", "作弊"
    ]
}

# 投诉类型映射
COMPLAINT_TYPES = {
    "abuse": {"label": "人身攻击", "reason_id": 1},
    "spam": {"label": "垃圾广告", "reason_id": 2},
    "irrelevant": {"label": "无关内容", "reason_id": 3},
    "competitor": {"label": "恶意拉踩", "reason_id": 4},
    "cheat": {"label": "作弊相关", "reason_id": 5},
    "other": {"label": "其他违规", "reason_id": 6}
}


class ViolationDetector:
    """违规内容检测器"""
    
    def __init__(self, config: dict = None):
        self.config = config or VIOLATION_CONFIG
    
    def detect(self, content: str) -> Tuple[bool, List[str], str]:
        """
        检测内容是否违规
        
        Returns:
            (是否违规, 违规类型列表, 违规原因描述)
        """
        violations = []
        reasons = []
        
        content_lower = content.lower()
        
        # 1. 检测谩骂/人身攻击
        abuse_found = []
        for word in self.config["abuse_words"]:
            if word.lower() in content_lower:
                abuse_found.append(word)
        if abuse_found:
            violations.append("abuse")
            reasons.append(f"谩骂词汇: {', '.join(abuse_found[:3])}")
        
        # 2. 检测竞品拉踩
        competitor_found = []
        compare_found = []
        for name in self.config["competitor_names"]:
            if name in content:
                competitor_found.append(name)
        for word in self.config["compare_words"]:
            if word in content:
                compare_found.append(word)
        
        if competitor_found and compare_found:
            violations.append("competitor")
            reasons.append(f"提及竞品拉踩: {', '.join(competitor_found)} + {compare_found[0]}")
        elif competitor_found:
            violations.append("competitor")
            reasons.append(f"提及竞品: {', '.join(competitor_found)}")
        
        # 3. 检测敏感词
        sensitive_found = []
        for word in self.config["sensitive_words"]:
            if word in content:
                sensitive_found.append(word)
        if sensitive_found:
            violations.append("cheat")
            reasons.append(f"敏感词: {', '.join(sensitive_found[:3])}")
        
        # 生成原因描述
        reason_text = "; ".join(reasons) if reasons else ""
        
        return len(violations) > 0, violations, reason_text


class TapTapComplaint:
    """TapTap 投诉处理类"""
    
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
            os.path.dirname(__file__), "..", "data", f"cookies_{app_id}.json"
        )
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), "..", "data")
        self.detector = ViolationDetector()
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # 投诉记录
        self.complaint_log_file = os.path.join(self.data_dir, f"complaints_{app_id}.json")
        self.complaint_log = self._load_complaint_log()
    
    def _load_complaint_log(self) -> Dict:
        """加载投诉记录"""
        if os.path.exists(self.complaint_log_file):
            try:
                with open(self.complaint_log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"complaints": [], "reported_ids": set()}
    
    def _save_complaint_log(self):
        """保存投诉记录"""
        os.makedirs(os.path.dirname(self.complaint_log_file), exist_ok=True)
        # 转换 set 为 list 以便 JSON 序列化
        log_data = {
            "last_updated": datetime.now().isoformat(),
            "complaints": self.complaint_log.get("complaints", []),
            "reported_ids": list(self.complaint_log.get("reported_ids", set()))
        }
        with open(self.complaint_log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
    
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
            
            # 创建上下文
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
            )
            
            # 加载 cookies
            self._load_cookies()
            
            self.page = self.context.new_page()
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
    
    def _load_cookies(self):
        """加载保存的 cookies"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                    self.context.add_cookies(cookies)
                print(f"✅ 已加载登录态: {self.cookie_file}")
            except Exception as e:
                print(f"⚠️ 加载 cookies 失败: {e}")
    
    def _save_cookies(self):
        """保存 cookies"""
        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
        cookies = self.context.cookies()
        with open(self.cookie_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存登录态: {self.cookie_file}")
    
    def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
            self._playwright.stop()
    
    def check_login(self) -> bool:
        """检查是否已登录"""
        try:
            self.page.goto(f"{self.base_url}", wait_until='networkidle', timeout=15000)
            time.sleep(2)
            
            # 检查登录状态 - 查找用户头像或用户名
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
            
            # 检查是否有登录按钮
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
        
        # 临时以可见模式启动
        if self.browser:
            self._close_browser()
        
        self.headless = False
        self._start_browser()
        
        # 打开登录页
        self.page.goto(f"{self.base_url}", wait_until='networkidle')
        
        # 等待用户登录
        input("登录成功后按回车继续...")
        
        # 保存 cookies
        self._save_cookies()
        print("✅ 登录态已保存，下次无需重新登录")
    
    def get_review_detail(self, review_id: str) -> Optional[Dict]:
        """获取评价详情"""
        url = f"{self.base_url}/review/{review_id}"
        
        try:
            self.page.goto(url, wait_until='networkidle', timeout=15000)
            time.sleep(2)
            
            # 从 NUXT 数据提取
            nuxt_data = self.page.evaluate('''() => {
                if (window.__NUXT__) return JSON.stringify(window.__NUXT__);
                return null;
            }''')
            
            if nuxt_data:
                data = json.loads(nuxt_data)
                # 解析评价详情...
                return {"id": review_id, "url": url, "data": data}
            
            return {"id": review_id, "url": url}
            
        except Exception as e:
            print(f"获取评价详情失败: {e}")
            return None
    
    def submit_complaint(
        self, 
        review_id: str, 
        reason_type: str = "abuse",
        reason_text: str = "",
        dry_run: bool = False
    ) -> Dict:
        """
        提交投诉
        
        Args:
            review_id: 评价ID
            reason_type: 投诉类型 (abuse/spam/irrelevant/competitor/cheat/other)
            reason_text: 投诉原因描述
            dry_run: 仅模拟，不实际提交
        
        Returns:
            投诉结果
        """
        result = {
            "review_id": review_id,
            "reason_type": reason_type,
            "reason_text": reason_text,
            "status": "pending",
            "message": "",
            "timestamp": datetime.now().isoformat()
        }
        
        # 检查是否已投诉过
        reported_ids = set(self.complaint_log.get("reported_ids", []))
        if review_id in reported_ids:
            result["status"] = "skipped"
            result["message"] = "已投诉过，跳过"
            return result
        
        if dry_run:
            result["status"] = "dry_run"
            result["message"] = "模拟投诉，未实际提交"
            return result
        
        try:
            # 访问评价页面
            url = f"{self.base_url}/review/{review_id}"
            self.page.goto(url, wait_until='networkidle', timeout=15000)
            time.sleep(2)
            
            # 查找投诉按钮
            # TapTap 的投诉按钮通常在评价右侧或下方
            complaint_selectors = [
                'button:has-text("投诉")',
                '[class*="complaint"]',
                '[class*="report"]',
                'button[title*="投诉"]',
                'button[title*="举报"]',
            ]
            
            complaint_btn = None
            for selector in complaint_selectors:
                try:
                    complaint_btn = self.page.wait_for_selector(selector, timeout=3000)
                    if complaint_btn:
                        break
                except:
                    continue
            
            if not complaint_btn:
                # 尝试点击更多按钮
                more_btn = self.page.query_selector('button:has-text("更多"), [class*="more"]')
                if more_btn:
                    more_btn.click()
                    time.sleep(1)
                    complaint_btn = self.page.query_selector('button:has-text("投诉")')
            
            if not complaint_btn:
                result["status"] = "failed"
                result["message"] = "未找到投诉按钮"
                return result
            
            # 点击投诉按钮
            complaint_btn.click()
            time.sleep(1)
            
            # 选择投诉类型
            complaint_info = COMPLAINT_TYPES.get(reason_type, COMPLAINT_TYPES["other"])
            type_selector = f'input[value="{complaint_info["reason_id"]}"], label:has-text("{complaint_info["label"]}")'
            
            try:
                type_elem = self.page.wait_for_selector(type_selector, timeout=3000)
                if type_elem:
                    type_elem.click()
                    time.sleep(0.5)
            except:
                # 如果找不到具体类型，选择第一个
                first_option = self.page.query_selector('input[type="radio"], label[class*="reason"]')
                if first_option:
                    first_option.click()
                    time.sleep(0.5)
            
            # 填写投诉原因（如果有输入框）
            reason_input = self.page.query_selector('textarea[class*="reason"], textarea[placeholder*="原因"]')
            if reason_input and reason_text:
                reason_input.fill(reason_text[:200])  # 限制字数
                time.sleep(0.5)
            
            # 提交投诉
            submit_btn = self.page.query_selector('button:has-text("提交"), button:has-text("确认"), button[type="submit"]')
            if submit_btn:
                submit_btn.click()
                time.sleep(2)
                
                # 检查是否成功
                success_indicators = [
                    'text=投诉成功',
                    'text=提交成功',
                    'text=感谢您的反馈',
                    '[class*="success"]',
                ]
                
                for indicator in success_indicators:
                    try:
                        self.page.wait_for_selector(indicator, timeout=3000)
                        result["status"] = "success"
                        result["message"] = "投诉提交成功"
                        break
                    except:
                        continue
                
                if result["status"] == "pending":
                    result["status"] = "submitted"
                    result["message"] = "已提交投诉，结果未知"
            else:
                result["status"] = "failed"
                result["message"] = "未找到提交按钮"
            
            # 记录已投诉
            if "reported_ids" not in self.complaint_log:
                self.complaint_log["reported_ids"] = []
            self.complaint_log["reported_ids"].append(review_id)
            
            if "complaints" not in self.complaint_log:
                self.complaint_log["complaints"] = []
            self.complaint_log["complaints"].append(result)
            
            self._save_complaint_log()
            
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
        
        return result
    
    def scan_and_report(
        self,
        reviews: List[Dict],
        min_score: int = 3,
        dry_run: bool = False,
        auto_confirm: bool = False
    ) -> List[Dict]:
        """
        扫描评价并自动投诉违规内容
        
        Args:
            reviews: 评价列表
            min_score: 最低评分（低于此分数才检测）
            dry_run: 仅模拟，不实际提交
            auto_confirm: 自动确认（否则每个投诉前询问）
        
        Returns:
            投诉结果列表
        """
        results = []
        
        for review in reviews:
            content = review.get("content", "")
            score = review.get("score", "5")
            review_id = review.get("id", "")
            
            # 跳过高分评价
            try:
                score_num = int(score)
            except:
                score_num = 5
            
            if score_num >= min_score:
                continue
            
            # 检测违规
            is_violation, violation_types, reason_text = self.detector.detect(content)
            
            if not is_violation:
                continue
            
            print(f"\n{'='*50}")
            print(f"发现违规评价:")
            print(f"评分: {score}星")
            print(f"内容: {content[:100]}...")
            print(f"违规类型: {violation_types}")
            print(f"违规原因: {reason_text}")
            print(f"{'='*50}")
            
            # 确认是否投诉
            if not auto_confirm:
                confirm = input("\n是否投诉此评价? (y/n/a=全部自动/s=跳过): ").strip().lower()
                if confirm == 'a':
                    auto_confirm = True
                elif confirm == 's':
                    continue
                elif confirm != 'y':
                    continue
            
            # 提交投诉
            reason_type = violation_types[0] if violation_types else "other"
            result = self.submit_complaint(
                review_id=review_id,
                reason_type=reason_type,
                reason_text=reason_text,
                dry_run=dry_run
            )
            
            print(f"投诉结果: {result['status']} - {result['message']}")
            results.append(result)
            
            # 避免频繁请求
            time.sleep(3)
        
        return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TapTap 差评投诉工具")
    parser.add_argument("--app-id", type=str, default="236096", help="游戏ID")
    parser.add_argument("--login", action="store_true", help="手动登录保存登录态")
    parser.add_argument("--check-login", action="store_true", help="检查登录状态")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际提交投诉")
    parser.add_argument("--auto", action="store_true", help="自动确认所有投诉")
    parser.add_argument("--visible", action="store_true", help="显示浏览器窗口")
    parser.add_argument("--min-score", type=int, default=3, help="最低评分阈值（低于此分数才检测）")
    
    args = parser.parse_args()
    
    complaint = TapTapComplaint(
        app_id=args.app_id,
        headless=not args.visible
    )
    
    try:
        complaint._start_browser()
        
        if args.login:
            complaint.manual_login()
            return
        
        if args.check_login:
            is_logged_in = complaint.check_login()
            print(f"登录状态: {'已登录' if is_logged_in else '未登录'}")
            return
        
        # 默认：检查登录状态
        if not complaint.check_login():
            print("请先运行 --login 进行登录")
            return
        
        print("\n投诉工具已就绪")
        print("请配合 taptap_monitor.py 使用，将获取的评价传入扫描")
        
    finally:
        complaint._close_browser()


if __name__ == "__main__":
    main()