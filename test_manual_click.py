#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动交互测试发布配置页面
"""

import asyncio
from playwright.async_api import async_playwright

API_KEY = "2552be3f-8a68-4505-abb9-e4ddbb69869a"

async def manual_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        
        # 设置API key
        await context.add_init_script(f"""
            localStorage.setItem('api_key', '{API_KEY}');
        """)
        
        page = await context.new_page()
        
        # 监听API调用
        def log_api(request):
            if 'api/auto-publish' in request.url:
                print(f"[API] {request.method} {request.url.split('/')[-1]}")
        
        page.on("request", log_api)
        
        print("正在打开页面...")
        await page.goto("http://localhost:51083/auto-publish")
        await page.wait_for_load_state("networkidle")
        
        print("\n页面已加载，请手动操作：")
        print("1. 点击'发布配置'Tab")
        print("2. 查看控制台输出的API调用")
        print("3. 尝试创建、编辑、删除配置")
        print("\n按Ctrl+C退出...")
        
        # 保持浏览器打开
        try:
            while True:
                await page.wait_for_timeout(1000)
        except KeyboardInterrupt:
            print("\n关闭浏览器...")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(manual_test())