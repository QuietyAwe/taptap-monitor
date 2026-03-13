#!/usr/bin/env python3
"""TapTap 登录脚本 - 远程调试模式"""
import asyncio
from playwright.async_api import async_playwright
import os

MARKER_FILE = "/tmp/taptap_login_done"

async def login_remote():
    # 清除标记文件
    if os.path.exists(MARKER_FILE):
        os.remove(MARKER_FILE)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--remote-debugging-port=9222", "--remote-debugging-address=0.0.0.0"]
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        print("打开 TapTap...")
        await page.goto("https://www.taptap.cn/")
        
        print("")
        print("="*50)
        print("远程调试已启动!")
        print("="*50)
        print("请在 Windows 浏览器访问: http://localhost:9222")
        print("点击登录按钮完成登录")
        print("")
        print("登录完成后，运行以下命令继续:")
        print("  touch /tmp/taptap_login_done")
        print("="*50)
        
        # 等待标记文件出现
        while not os.path.exists(MARKER_FILE):
            await asyncio.sleep(1)
        
        print("检测到登录完成标记，保存状态...")
        
        # 保存登录状态
        await context.storage_state(path="taptap_cookies.json")
        print("✅ 登录状态已保存到 taptap_cookies.json")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(login_remote())