#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试发布配置管理API和UI
"""

import asyncio
import json
from playwright.async_api import async_playwright

API_KEY = "2552be3f-8a68-4505-abb9-e4ddbb69869a"

async def test_config_api():
    """测试发布配置管理的API和界面"""
    
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
        
        def log_api_request(request):
            if 'api/auto-publish' in request.url:
                api_calls.append({
                    'type': 'request',
                    'method': request.method,
                    'url': request.url
                })
                print(f"[API请求] {request.method} {request.url}")
        
        def log_api_response(response):
            if 'api/auto-publish' in response.url:
                api_calls.append({
                    'type': 'response',
                    'status': response.status,
                    'url': response.url
                })
                print(f"[API响应] {response.status} {response.url}")
        
        page.on("request", log_api_request)
        page.on("response", log_api_response)
        
        print("=" * 80)
        print("发布配置管理API和UI测试")
        print("=" * 80)
        
        try:
            # 1. 直接导航到发布配置页面，并设置API key
            print("\n1. 导航到发布配置管理页面...")
            
            # 添加API key到localStorage的初始化脚本
            await context.add_init_script(f"""
                localStorage.setItem('api_key', '{API_KEY}');
            """)
            
            # 直接导航到发布配置tab
            await page.goto("http://localhost:51083/auto-publish?tab=configs")
            await page.wait_for_load_state("networkidle")
            
            # 等待页面加载
            await page.wait_for_timeout(3000)
            
            # 截图
            await page.screenshot(path="config_page_loaded.png")
            print("✅ 页面加载完成，截图: config_page_loaded.png")
            
            # 2. 检查API调用
            print("\n2. 检查API调用...")
            config_api_calls = [call for call in api_calls if 'publish-config' in call['url']]
            
            if config_api_calls:
                print(f"  发现 {len(config_api_calls)} 个发布配置相关的API调用:")
                for call in config_api_calls:
                    if call['type'] == 'request':
                        print(f"    请求: {call['method']} {call['url']}")
                    else:
                        print(f"    响应: {call['status']} {call['url']}")
            else:
                print("  ⚠️ 未检测到发布配置API调用")
            
            # 3. 检查页面元素
            print("\n3. 检查页面元素...")
            
            # 检查统计卡片
            stat_cards = await page.locator('.ant-statistic').count()
            print(f"  统计卡片数量: {stat_cards}")
            
            # 检查表格
            if await page.locator('.ant-table').is_visible():
                print("  ✅ 配置表格已显示")
                
                # 获取表格行数
                rows = await page.locator('.ant-table-tbody tr').count()
                print(f"  表格中有 {rows} 行数据")
                
                # 如果有数据，获取第一行的信息
                if rows > 0:
                    first_row_text = await page.locator('.ant-table-tbody tr:first-child').text_content()
                    print(f"  第一行内容: {first_row_text[:100]}...")  # 只显示前100字符
            else:
                print("  ⚠️ 配置表格未显示")
            
            # 检查操作按钮
            if await page.locator('button:has-text("创建配置")').is_visible():
                print("  ✅ 创建配置按钮可见")
            
            if await page.locator('button:has-text("刷新")').is_visible():
                print("  ✅ 刷新按钮可见")
            
            # 4. 测试刷新功能
            print("\n4. 测试刷新功能...")
            
            # 清空之前的API调用记录
            api_calls.clear()
            
            # 点击刷新按钮
            refresh_btn = page.locator('button:has-text("刷新")')
            if await refresh_btn.is_visible():
                await refresh_btn.click()
                print("  点击刷新按钮")
                
                # 等待API响应
                await page.wait_for_timeout(2000)
                
                # 检查是否有新的API调用
                refresh_calls = [call for call in api_calls if 'publish-config' in call['url']]
                if refresh_calls:
                    print(f"  ✅ 刷新触发了 {len(refresh_calls)} 个API调用")
                else:
                    print("  ⚠️ 刷新未触发API调用")
            
            # 5. 测试创建配置弹窗
            print("\n5. 测试创建配置弹窗...")
            
            create_btn = page.locator('button:has-text("创建配置")')
            if await create_btn.is_visible():
                await create_btn.click()
                print("  点击创建配置按钮")
                
                # 等待弹窗出现
                await page.wait_for_timeout(1000)
                
                if await page.locator('.ant-modal').is_visible():
                    print("  ✅ 创建配置弹窗已打开")
                    
                    # 截图弹窗
                    await page.screenshot(path="create_config_modal.png")
                    print("  截图: create_config_modal.png")
                    
                    # 检查表单字段
                    form_fields = {
                        '配置名称': 'input#config_name',
                        'Pipeline': '#pipeline_id',
                        '账号组': '#group_id',
                        '优先级': 'input#priority'
                    }
                    
                    for field_name, selector in form_fields.items():
                        if await page.locator(selector).count() > 0:
                            print(f"    ✅ {field_name}字段存在")
                        else:
                            print(f"    ❌ {field_name}字段不存在")
                    
                    # 关闭弹窗
                    close_btn = page.locator('.ant-modal button:has-text("取消")')
                    if await close_btn.is_visible():
                        await close_btn.click()
                        print("  关闭弹窗")
            
            # 6. 总结
            print("\n" + "=" * 80)
            print("测试总结:")
            print(f"  总API调用次数: {len(api_calls)}")
            print(f"  发布配置相关API调用: {len([c for c in api_calls if 'publish-config' in c['url']])}")
            print(f"  页面元素加载: {'成功' if stat_cards > 0 else '失败'}")
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
    print("启动发布配置管理API和UI测试...")
    asyncio.run(test_config_api())