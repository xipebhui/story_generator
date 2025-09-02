#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的发布配置管理UI测试
"""

import asyncio
import time
from playwright.async_api import async_playwright
import json

API_KEY = "2552be3f-8a68-4505-abb9-e4ddbb69869a"

async def simple_test():
    """简单测试发布配置管理界面"""
    
    async with async_playwright() as p:
        # 启动浏览器（非无头模式，方便观察）
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # 监听控制台消息
        page.on("console", lambda msg: print(f"[控制台] {msg.text}"))
        
        # 监听网络请求和响应
        def log_api_request(request):
            if 'api/auto-publish' in request.url:
                print(f"\n[API请求] {request.method} {request.url}")
                if request.method == "POST" or request.method == "PUT":
                    try:
                        data = request.post_data
                        if data:
                            print(f"[请求数据] {data[:200]}")  # 只显示前200字符
                    except:
                        pass
        
        def log_api_response(response):
            if 'api/auto-publish' in response.url:
                print(f"[API响应] {response.status} {response.url}")
        
        page.on("request", log_api_request)
        page.on("response", log_api_response)
        
        print("=" * 80)
        print("发布配置管理界面简单测试")
        print("=" * 80)
        
        try:
            # 1. 先设置localStorage，然后导航
            print("\n步骤1: 设置API Key并导航到页面...")
            
            # 先导航到页面设置localStorage
            await page.goto("http://localhost:51083")
            await page.wait_for_timeout(1000)
            
            # 注入API key到localStorage
            await page.evaluate(f"""
                localStorage.setItem('api_key', '{API_KEY}');
            """)
            
            # 重新导航以应用API key（不用reload）
            await page.goto("http://localhost:51083/auto-publish")
            await page.wait_for_load_state("networkidle")
            print("✅ 页面加载完成")
            
            # 2. 截图当前页面
            await page.screenshot(path="step1_homepage.png")
            print("📸 截图保存: step1_homepage.png")
            
            # 3. 查找并点击Tab
            print("\n步骤2: 查找发布配置Tab...")
            await page.wait_for_timeout(2000)
            
            # 尝试不同的选择器
            tab_selectors = [
                'text=发布配置',
                ':text("发布配置")',
                '.ant-tabs-tab:has-text("发布配置")',
                '//span[contains(text(), "发布配置")]',
                'span:has-text("发布配置")'
            ]
            
            tab_clicked = False
            for selector in tab_selectors:
                try:
                    if await page.locator(selector).is_visible():
                        print(f"  找到Tab使用选择器: {selector}")
                        await page.click(selector)
                        tab_clicked = True
                        break
                except:
                    continue
            
            if tab_clicked:
                print("✅ 成功点击发布配置Tab")
                await page.wait_for_timeout(2000)
                
                # 截图配置页面
                await page.screenshot(path="step2_config_page.png")
                print("📸 截图保存: step2_config_page.png")
                
                # 4. 检查页面元素
                print("\n步骤3: 检查页面元素...")
                
                # 检查是否有创建按钮
                if await page.locator('button:has-text("创建配置")').is_visible():
                    print("✅ 找到创建配置按钮")
                
                # 检查是否有表格
                if await page.locator('.ant-table').is_visible():
                    print("✅ 找到配置表格")
                    
                    # 获取配置数量
                    rows = await page.locator('.ant-table-tbody tr').count()
                    print(f"  当前有 {rows} 个配置")
                
                # 5. 尝试创建配置
                print("\n步骤4: 尝试创建新配置...")
                create_btn = page.locator('button:has-text("创建配置")')
                if await create_btn.is_visible():
                    await create_btn.click()
                    print("  点击创建按钮")
                    
                    await page.wait_for_timeout(1000)
                    
                    # 检查弹窗是否打开
                    if await page.locator('.ant-modal').is_visible():
                        print("✅ 配置创建弹窗已打开")
                        
                        # 截图弹窗
                        await page.screenshot(path="step3_create_modal.png")
                        print("📸 截图保存: step3_create_modal.png")
                        
                        # 关闭弹窗
                        cancel_btn = page.locator('.ant-modal button:has-text("取消")')
                        if await cancel_btn.is_visible():
                            await cancel_btn.click()
                            print("  关闭弹窗")
                
                # 6. 测试搜索功能
                print("\n步骤5: 测试搜索功能...")
                search_input = page.locator('input[placeholder*="搜索"]').first
                if await search_input.is_visible():
                    await search_input.fill("测试")
                    await search_input.press("Enter")
                    print("✅ 执行搜索: '测试'")
                    await page.wait_for_timeout(1000)
                
                # 7. 测试筛选功能
                print("\n步骤6: 测试筛选功能...")
                # 尝试点击筛选下拉框
                filter_selects = await page.locator('.ant-select').all()
                print(f"  找到 {len(filter_selects)} 个筛选器")
                
            else:
                print("❌ 未能找到发布配置Tab")
                # 列出所有可见的Tab
                tabs = await page.locator('.ant-tabs-tab').all_text_contents()
                print(f"  可见的Tabs: {tabs}")
            
        except Exception as e:
            print(f"\n❌ 测试出错: {e}")
            # 错误时截图
            await page.screenshot(path="error_screenshot.png")
            print("📸 错误截图保存: error_screenshot.png")
        
        finally:
            print("\n" + "=" * 80)
            print("测试结束")
            print("=" * 80)
            
            # 等待几秒让用户查看
            print("\n浏览器将在5秒后关闭...")
            await page.wait_for_timeout(5000)
            
            # 关闭浏览器
            await browser.close()

if __name__ == "__main__":
    print("启动简单的Playwright测试...")
    print("提示: 测试将打开浏览器窗口，请观察操作过程")
    asyncio.run(simple_test())