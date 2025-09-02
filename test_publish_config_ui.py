#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Playwright测试发布配置管理界面
"""

import asyncio
import time
from playwright.async_api import async_playwright
import json

API_KEY = "2552be3f-8a68-4505-abb9-e4ddbb69869a"

async def test_publish_config_ui():
    """测试发布配置管理界面的完整功能"""
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        # 在localStorage中设置API key
        await context.add_init_script(f"""
            window.localStorage.setItem('api_key', '{API_KEY}');
        """)
        
        page = await context.new_page()
        
        # 启用控制台日志
        page.on("console", lambda msg: print(f"[浏览器控制台] {msg.type}: {msg.text}"))
        
        # 监听网络请求
        def log_request(request):
            if 'api/auto-publish' in request.url:
                print(f"[API请求] {request.method} {request.url}")
        
        def log_response(response):
            if 'api/auto-publish' in response.url:
                print(f"[API响应] {response.status} {response.url}")
        
        page.on("request", log_request)
        page.on("response", log_response)
        
        print("=" * 60)
        print("发布配置管理界面测试")
        print("=" * 60)
        
        # 1. 导航到主页面
        print("\n1. 导航到自动发布系统...")
        await page.goto("http://localhost:51083")
        await page.wait_for_load_state("networkidle")
        
        # 检查是否需要输入API key
        if await page.locator("text=请输入API Key").is_visible():
            print("   需要输入API Key...")
            await page.fill('input[placeholder="请输入API Key"]', API_KEY)
            await page.click('button:has-text("确定")')
            await page.wait_for_load_state("networkidle")
        
        # 2. 切换到发布配置tab
        print("\n2. 切换到发布配置管理tab...")
        await page.click('div[role="tab"]:has-text("发布配置")')
        await page.wait_for_timeout(2000)
        
        # 3. 检查页面元素
        print("\n3. 检查页面元素...")
        
        # 检查统计卡片
        stats_cards = await page.locator('.ant-statistic-title').all_text_contents()
        print(f"   统计卡片: {stats_cards}")
        
        # 检查表格
        if await page.locator('.ant-table').is_visible():
            print("   ✅ 配置表格已加载")
            
            # 获取表格中的配置数量
            rows = await page.locator('.ant-table-tbody tr').count()
            print(f"   当前有 {rows} 个配置")
        
        # 4. 创建新配置
        print("\n4. 创建新的发布配置...")
        await page.click('button:has-text("创建配置")')
        await page.wait_for_selector('.ant-modal-content')
        
        print("   填写配置表单...")
        
        # 基础配置
        await page.fill('input[id="config_name"]', 'Playwright测试配置')
        
        # 选择Pipeline
        await page.click('div[id="pipeline_id"]')
        await page.wait_for_timeout(500)
        # 选择第一个可用的Pipeline
        await page.click('.ant-select-dropdown .ant-select-item:first-child')
        
        # 选择账号组
        await page.click('div[id="group_id"]')
        await page.wait_for_timeout(500)
        # 选择第一个可用的账号组
        await page.click('.ant-select-dropdown .ant-select-item:first-child')
        
        # 设置优先级
        await page.fill('input[id="priority"]', '75')
        
        # 切换到触发配置tab
        await page.click('.ant-tabs-tab:has-text("触发配置")')
        await page.wait_for_timeout(1000)
        
        # 选择定时触发
        await page.click('.ant-radio-button-wrapper:has-text("定时触发")')
        
        # 保存配置
        print("   保存配置...")
        await page.click('button:has-text("保存")')
        await page.wait_for_timeout(2000)
        
        # 检查是否创建成功
        if await page.locator('text=配置创建成功').is_visible():
            print("   ✅ 配置创建成功！")
        
        # 5. 搜索配置
        print("\n5. 搜索配置...")
        await page.fill('input[placeholder="搜索配置名称"]', 'Playwright')
        await page.press('input[placeholder="搜索配置名称"]', 'Enter')
        await page.wait_for_timeout(1000)
        
        # 检查搜索结果
        search_results = await page.locator('.ant-table-tbody tr').count()
        print(f"   搜索到 {search_results} 个配置")
        
        # 6. 查看配置详情
        print("\n6. 查看配置详情...")
        if search_results > 0:
            # 点击第一个配置的名称查看详情
            await page.click('.ant-table-tbody tr:first-child button[type="link"]')
            await page.wait_for_selector('.ant-drawer-content')
            
            # 检查详情内容
            if await page.locator('.ant-drawer-title').is_visible():
                title = await page.locator('.ant-drawer-title').text_content()
                print(f"   详情标题: {title}")
            
            # 切换统计tab
            await page.click('.ant-tabs-tab:has-text("执行统计")')
            await page.wait_for_timeout(1000)
            print("   ✅ 查看执行统计")
            
            # 切换执行记录tab
            await page.click('.ant-tabs-tab:has-text("执行记录")')
            await page.wait_for_timeout(1000)
            print("   ✅ 查看执行记录")
            
            # 关闭详情
            await page.click('.ant-drawer-close')
            await page.wait_for_timeout(1000)
        
        # 7. 编辑配置
        print("\n7. 编辑配置...")
        if search_results > 0:
            await page.click('.ant-table-tbody tr:first-child button[aria-label="编辑"]')
            await page.wait_for_selector('.ant-modal-content')
            
            # 修改配置名称
            await page.fill('input[id="config_name"]', 'Playwright测试配置-已修改')
            
            # 保存
            await page.click('button:has-text("保存")')
            await page.wait_for_timeout(2000)
            
            if await page.locator('text=配置更新成功').is_visible():
                print("   ✅ 配置更新成功！")
        
        # 8. 切换配置状态
        print("\n8. 切换配置状态...")
        if search_results > 0:
            # 找到切换开关
            switch = page.locator('.ant-table-tbody tr:first-child .ant-switch').first
            is_checked = await switch.get_attribute('aria-checked')
            print(f"   当前状态: {'启用' if is_checked == 'true' else '禁用'}")
            
            await switch.click()
            await page.wait_for_timeout(1000)
            
            new_status = await switch.get_attribute('aria-checked')
            print(f"   新状态: {'启用' if new_status == 'true' else '禁用'}")
        
        # 9. 删除配置
        print("\n9. 删除测试配置...")
        if search_results > 0:
            await page.click('.ant-table-tbody tr:first-child button[aria-label="删除"]')
            await page.wait_for_selector('.ant-popconfirm')
            
            # 确认删除
            await page.click('.ant-popconfirm button:has-text("确定")')
            await page.wait_for_timeout(2000)
            
            if await page.locator('text=配置删除成功').is_visible():
                print("   ✅ 配置删除成功！")
        
        # 10. 测试筛选功能
        print("\n10. 测试筛选功能...")
        
        # 清空搜索
        await page.fill('input[placeholder="搜索配置名称"]', '')
        await page.press('input[placeholder="搜索配置名称"]', 'Enter')
        
        # 按状态筛选
        await page.click('.ant-select:has-text("筛选状态")')
        await page.wait_for_timeout(500)
        await page.click('.ant-select-dropdown .ant-select-item:has-text("启用")')
        await page.wait_for_timeout(1000)
        
        enabled_count = await page.locator('.ant-table-tbody tr').count()
        print(f"   启用的配置: {enabled_count} 个")
        
        print("\n" + "=" * 60)
        print("✅ 发布配置管理界面测试完成！")
        print("=" * 60)
        
        # 截图保存
        await page.screenshot(path="publish_config_test_screenshot.png")
        print("\n截图已保存为: publish_config_test_screenshot.png")
        
        # 等待几秒查看结果
        await page.wait_for_timeout(3000)
        
        # 关闭浏览器
        await browser.close()

if __name__ == "__main__":
    print("启动Playwright测试...")
    asyncio.run(test_publish_config_ui())