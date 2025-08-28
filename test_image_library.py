#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试图库功能
"""

import sys
import os
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_manager

def test_image_library():
    """测试图库功能"""
    
    print("="*60)
    print("测试图库功能")
    print("="*60)
    
    db = get_db_manager()
    
    # 1. 测试获取所有图库
    print("\n1. 获取所有图库:")
    libraries = db.get_all_image_libraries()
    for lib in libraries:
        print(f"  - {lib.library_name}: {lib.library_path}")
    
    # 2. 测试根据名称获取图库
    print("\n2. 根据名称获取图库:")
    default_lib = db.get_image_library_by_name('default')
    if default_lib:
        print(f"  找到默认图库: {default_lib.library_path}")
    else:
        print("  未找到默认图库")
    
    # 3. 测试不存在的图库
    print("\n3. 查询不存在的图库:")
    non_exist = db.get_image_library_by_name('non_exist')
    print(f"  结果: {non_exist}")
    
    # 4. 测试草稿生成服务的图库查询逻辑
    print("\n4. 测试草稿生成服务的图库查询逻辑:")
    
    # 导入草稿生成服务的函数
    from draft_gen.generateDraftService import generate_draft_from_story
    
    # 测试不同的image_dir参数
    test_cases = [
        (None, "不指定，使用默认图库"),
        ("default", "使用图库名称 'default'"),
        ("/absolute/path/to/images", "使用绝对路径"),
        ("non_exist_library", "使用不存在的图库名称")
    ]
    
    for image_dir_param, description in test_cases:
        print(f"\n  测试: {description}")
        print(f"  参数: image_dir='{image_dir_param}'")
        
        # 模拟路径处理逻辑
        if image_dir_param:
            if not os.path.isabs(image_dir_param) and not os.path.exists(image_dir_param):
                library = db.get_image_library_by_name(image_dir_param)
                if library:
                    result_path = library.library_path
                    print(f"  结果: 找到图库 '{image_dir_param}' -> {result_path}")
                else:
                    default_lib = db.get_image_library_by_name('default')
                    if default_lib:
                        result_path = default_lib.library_path
                        print(f"  结果: 未找到图库 '{image_dir_param}'，使用默认图库 -> {result_path}")
                    else:
                        result_path = "./output/images"
                        print(f"  结果: 使用默认路径 -> {result_path}")
            else:
                result_path = image_dir_param
                print(f"  结果: 使用指定路径 -> {result_path}")
        else:
            default_lib = db.get_image_library_by_name('default')
            if default_lib:
                result_path = default_lib.library_path
                print(f"  结果: 使用默认图库 -> {result_path}")
            else:
                result_path = "./output/images"
                print(f"  结果: 使用默认路径 -> {result_path}")
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

def test_api_endpoint():
    """测试API端点"""
    print("\n" + "="*60)
    print("测试API端点")
    print("="*60)
    
    import requests
    
    # 假设API服务在本地运行
    api_url = "http://localhost:8000/api/image_libraries"
    
    print(f"\n测试API: GET {api_url}")
    print("注意：需要先启动API服务并提供有效的Bearer Token")
    
    # 示例请求（需要有效的token）
    # headers = {"Authorization": "Bearer YOUR_API_KEY"}
    # try:
    #     response = requests.get(api_url, headers=headers)
    #     if response.status_code == 200:
    #         data = response.json()
    #         print(f"成功获取图库列表: {data}")
    #     else:
    #         print(f"请求失败: {response.status_code}")
    # except Exception as e:
    #     print(f"连接失败: {e}")

if __name__ == "__main__":
    test_image_library()
    test_api_endpoint()