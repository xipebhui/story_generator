#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化图库表数据
添加默认的图库记录
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_manager, ImageLibrary

def init_image_libraries():
    """初始化图库数据"""
    
    print("="*60)
    print("初始化图库数据")
    print("="*60)
    
    db = get_db_manager()
    
    # 获取当前项目的绝对路径
    project_root = Path(__file__).parent.absolute()
    default_images_path = project_root / "output" / "images"
    
    # 确保目录存在
    default_images_path.mkdir(parents=True, exist_ok=True)
    
    # 默认图库配置
    libraries = [
        {
            'library_name': 'default',
            'library_path': str(default_images_path)
        }
    ]
    
    # 可以添加更多预设图库
    # libraries.append({
    #     'library_name': 'anime',
    #     'library_path': '/path/to/anime/images'
    # })
    
    for lib_data in libraries:
        # 检查是否已存在
        existing = db.get_image_library_by_name(lib_data['library_name'])
        if existing:
            print(f"图库 '{lib_data['library_name']}' 已存在，跳过")
            print(f"  路径: {existing.library_path}")
        else:
            # 创建新图库
            library = db.create_image_library(lib_data)
            print(f"✅ 创建图库 '{library.library_name}'")
            print(f"  路径: {library.library_path}")
    
    print("\n" + "="*60)
    print("当前所有图库：")
    print("="*60)
    
    # 显示所有图库
    all_libraries = db.get_all_image_libraries()
    for lib in all_libraries:
        print(f"- {lib.library_name}: {lib.library_path}")
    
    print("\n初始化完成！")

if __name__ == "__main__":
    init_image_libraries()