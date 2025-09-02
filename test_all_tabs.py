#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合测试所有Tab功能
"""

import asyncio
import json
from playwright.async_api import async_playwright

API_KEY = "2552be3f-8a68-4505-abb9-e4ddbb69869a"

async def test_all_tabs():
    """测试所有Tab的功能"""
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # 记录API调用
        api_calls = []
        errors = []
        
        def log_api_request(request):
            if 'api/auto-publish' in request.url or 'api/accounts' in request.url:
                api_calls.append({
                    'type': 'request',
                    'method': request.method,
                    'url': request.url
                })
                print(f"[API请求] {request.method} {request.url}")
        
        def log_api_response(response):
            if 'api/auto-publish' in response.url or 'api/accounts' in response.url:
                api_calls.append({
                    'type': 'response',
                    'status': response.status,
                    'url': response.url
                })
                if response.status >= 400:
                    errors.append(f"API错误: {response.status} {response.url}")
                    print(f"[API错误] {response.status} {response.url}")
                else:
                    print(f"[API响应] {response.status} {response.url}")
        
        page.on("request", log_api_request)
        page.on("response", log_api_response)
        
        # 监听控制台错误
        page.on("console", lambda msg: errors.append(f"Console: {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda msg: errors.append(f"Page error: {msg}"))
        
        print("=" * 80)
        print("自动发布系统综合测试")
        print("=" * 80)
        
        try:
            # 1. 设置API Key并导航到页面
            print("\n1. 导航到自动发布系统...")
            await page.goto("http://localhost:51083")
            await page.wait_for_timeout(1000)
            
            # 注入API key
            await page.evaluate(f"""
                localStorage.setItem('api_key', '{API_KEY}');
            """)
            
            # 重新导航到自动发布页面
            await page.goto("http://localhost:51083/auto-publish")
            await page.wait_for_load_state("networkidle")
            print("✅ 页面加载完成")
            
            # 等待Tab加载
            await page.wait_for_timeout(3000)
            
            # 截图首页
            await page.screenshot(path="test_home.png")
            print("📸 截图: test_home.png")
            
            # 2. 测试Tab 0: 全局概览
            print("\n2. 测试Tab 0: 全局概览...")
            # 默认应该就在概览页
            await page.wait_for_timeout(2000)
            
            # 检查概览组件
            overview_visible = await page.locator('.ant-statistic').count() > 0
            if overview_visible:
                print("  ✅ 全局概览组件已加载")
                stat_count = await page.locator('.ant-statistic').count()
                print(f"  统计卡片数量: {stat_count}")
            else:
                errors.append("全局概览组件未加载")
                print("  ❌ 全局概览组件未加载")
            
            # 3. 测试Tab 1: Pipeline管理
            print("\n3. 测试Tab 1: Pipeline管理...")
            await page.click('text=Pipeline管理')
            await page.wait_for_timeout(2000)
            
            # 检查Pipeline表格
            if await page.locator('.ant-table').is_visible():
                print("  ✅ Pipeline表格已显示")
                rows = await page.locator('.ant-table-tbody tr').count()
                print(f"  Pipeline数量: {rows}")
            else:
                errors.append("Pipeline表格未显示")
                print("  ❌ Pipeline表格未显示")
            
            await page.screenshot(path="test_pipeline.png")
            print("  📸 截图: test_pipeline.png")
            
            # 4. 测试Tab 2: 发布配置
            print("\n4. 测试Tab 2: 发布配置...")
            await page.click('text=发布配置')
            await page.wait_for_timeout(2000)
            
            # 检查配置表格
            if await page.locator('.ant-table').nth(0).is_visible():
                print("  ✅ 发布配置表格已显示")
                config_rows = await page.locator('.ant-table-tbody tr').count()
                print(f"  配置数量: {config_rows}")
            else:
                errors.append("发布配置表格未显示")
                print("  ❌ 发布配置表格未显示")
            
            await page.screenshot(path="test_config.png")
            print("  📸 截图: test_config.png")
            
            # 5. 测试Tab 3: 执行记录（新增）
            print("\n5. 测试Tab 3: 执行记录...")
            task_tab = page.locator('text=执行记录')
            if await task_tab.is_visible():
                await task_tab.click()
                await page.wait_for_timeout(2000)
                
                # 检查任务表格
                if await page.locator('.ant-table').is_visible():
                    print("  ✅ 执行记录表格已显示")
                    
                    # 检查是否有API调用
                    task_api_calls = [c for c in api_calls if '/tasks' in c['url']]
                    if task_api_calls:
                        print(f"  ✅ 检测到 {len(task_api_calls)} 个任务相关API调用")
                    else:
                        print("  ⚠️ 未检测到任务相关API调用")
                else:
                    errors.append("执行记录表格未显示")
                    print("  ❌ 执行记录表格未显示")
                
                await page.screenshot(path="test_tasks.png")
                print("  📸 截图: test_tasks.png")
            else:
                errors.append("执行记录Tab不存在")
                print("  ❌ 执行记录Tab不存在")
            
            # 6. 测试Tab 4: 账号组管理（增强版）
            print("\n6. 测试Tab 4: 账号组管理...")
            group_tab = page.locator('text=账号组管理')
            if await group_tab.is_visible():
                await group_tab.click()
                await page.wait_for_timeout(2000)
                
                # 检查账号组表格
                if await page.locator('.ant-table').is_visible():
                    print("  ✅ 账号组表格已显示")
                    group_rows = await page.locator('.ant-table-tbody tr').count()
                    print(f"  账号组数量: {group_rows}")
                    
                    # 检查创建按钮
                    if await page.locator('button:has-text("创建账号组")').is_visible():
                        print("  ✅ 创建账号组按钮可见")
                else:
                    errors.append("账号组表格未显示")
                    print("  ❌ 账号组表格未显示")
                
                await page.screenshot(path="test_groups.png")
                print("  📸 截图: test_groups.png")
            else:
                errors.append("账号组管理Tab不存在")
                print("  ❌ 账号组管理Tab不存在")
            
            # 7. 测试创建账号组功能
            print("\n7. 测试创建账号组功能...")
            create_btn = page.locator('button:has-text("创建账号组")')
            if await create_btn.is_visible():
                await create_btn.click()
                await page.wait_for_timeout(1000)
                
                if await page.locator('.ant-modal').is_visible():
                    print("  ✅ 创建账号组弹窗已打开")
                    await page.screenshot(path="test_create_group_modal.png")
                    print("  📸 截图: test_create_group_modal.png")
                    
                    # 关闭弹窗
                    cancel_btn = page.locator('.ant-modal button:has-text("取消")')
                    if await cancel_btn.is_visible():
                        await cancel_btn.click()
                        print("  关闭弹窗")
            
            # 8. 总结
            print("\n" + "=" * 80)
            print("测试总结:")
            print(f"  总API调用次数: {len(api_calls)}")
            print(f"  成功的API调用: {len([c for c in api_calls if c['type'] == 'response' and c['status'] < 400])}")
            print(f"  失败的API调用: {len([c for c in api_calls if c['type'] == 'response' and c['status'] >= 400])}")
            
            if errors:
                print(f"\n  发现 {len(errors)} 个错误:")
                for error in errors[:10]:  # 只显示前10个错误
                    print(f"    - {error}")
            else:
                print("\n  ✅ 未发现错误")
            
            print("=" * 80)
            
        except Exception as e:
            print(f"\n❌ 测试出错: {e}")
            await page.screenshot(path="error.png")
            print("错误截图: error.png")
        
        finally:
            print("\n测试结束，浏览器将在5秒后关闭...")
            await page.wait_for_timeout(5000)
            await browser.close()

if __name__ == "__main__":
    print("启动综合测试...")
    asyncio.run(test_all_tabs())