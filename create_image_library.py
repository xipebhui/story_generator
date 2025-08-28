#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建图库记录脚本
验证路径存在性和图片文件存在性
"""

import os
import sys
import argparse
from pathlib import Path
from database import DatabaseManager, ImageLibrary
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 支持的图片格式
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', 
    '.webp', '.tiff', '.tif', '.svg', '.ico'
}

def validate_library_path(path: str) -> tuple[bool, str, int]:
    """
    验证图库路径
    
    Args:
        path: 图库路径
    
    Returns:
        (是否有效, 错误消息, 图片数量)
    """
    # 检查路径是否存在
    if not os.path.exists(path):
        return False, f"❌ 路径不存在: {path}", 0
    
    # 检查是否为目录
    if not os.path.isdir(path):
        return False, f"❌ 路径不是目录: {path}", 0
    
    # 检查目录权限
    if not os.access(path, os.R_OK):
        return False, f"❌ 没有读取权限: {path}", 0
    
    # 递归查找图片文件
    image_count = 0
    image_files = []
    
    for root, dirs, files in os.walk(path):
        for file in files:
            ext = os.path.splitext(file.lower())[1]
            if ext in IMAGE_EXTENSIONS:
                image_count += 1
                if len(image_files) < 5:  # 只记录前5个用于展示
                    rel_path = os.path.relpath(os.path.join(root, file), path)
                    image_files.append(rel_path)
    
    if image_count == 0:
        return False, f"❌ 目录中没有找到图片文件", 0
    
    # 构建成功消息
    msg = f"✅ 找到 {image_count} 个图片文件"
    if image_files:
        msg += "\n   示例文件:"
        for f in image_files[:3]:  # 显示前3个
            msg += f"\n     - {f}"
        if image_count > 3:
            msg += f"\n     ... 还有 {image_count - 3} 个文件"
    
    return True, msg, image_count

def check_library_exists(db_manager: DatabaseManager, library_name: str) -> bool:
    """
    检查图库是否已存在
    
    Args:
        db_manager: 数据库管理器
        library_name: 图库名称
    
    Returns:
        是否存在
    """
    existing = db_manager.get_image_library_by_name(library_name)
    return existing is not None

def create_library(library_name: str, library_path: str, force: bool = False):
    """
    创建图库记录
    
    Args:
        library_name: 图库名称
        library_path: 图库路径
        force: 是否强制覆盖已存在的记录
    """
    print("=" * 60)
    print("创建图库记录")
    print("=" * 60)
    
    # 转换为绝对路径
    library_path = os.path.abspath(library_path)
    print(f"\n图库名称: {library_name}")
    print(f"图库路径: {library_path}")
    
    # 验证路径
    print("\n1. 验证图库路径...")
    is_valid, message, image_count = validate_library_path(library_path)
    print(f"   {message}")
    
    if not is_valid:
        print("\n创建失败: 路径验证未通过")
        return False
    
    # 连接数据库
    print("\n2. 连接数据库...")
    try:
        db_manager = DatabaseManager()
        print("   ✅ 数据库连接成功")
    except Exception as e:
        print(f"   ❌ 数据库连接失败: {e}")
        return False
    
    # 检查是否已存在
    print("\n3. 检查图库是否已存在...")
    if check_library_exists(db_manager, library_name):
        if not force:
            print(f"   ❌ 图库 '{library_name}' 已存在")
            print("   提示: 使用 --force 参数可以覆盖已存在的记录")
            return False
        else:
            print(f"   ⚠️ 图库 '{library_name}' 已存在，将覆盖")
            # 删除旧记录
            with db_manager.get_session() as session:
                old_library = session.query(ImageLibrary).filter_by(library_name=library_name).first()
                if old_library:
                    session.delete(old_library)
                    session.commit()
                    print("   ✅ 已删除旧记录")
    else:
        print(f"   ✅ 图库 '{library_name}' 不存在，可以创建")
    
    # 创建图库记录
    print("\n4. 创建图库记录...")
    try:
        library_data = {
            'library_name': library_name,
            'library_path': library_path
        }
        
        library = db_manager.create_image_library(library_data)
        print(f"   ✅ 图库创建成功")
        print(f"   - ID: {library.id}")
        print(f"   - 名称: {library.library_name}")
        print(f"   - 路径: {library.library_path}")
        print(f"   - 图片数量: {image_count}")
        print(f"   - 创建时间: {library.created_at}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 创建失败: {e}")
        return False

def list_libraries():
    """列出所有图库"""
    print("=" * 60)
    print("所有图库列表")
    print("=" * 60)
    
    try:
        db_manager = DatabaseManager()
        libraries = db_manager.get_all_image_libraries()
        
        if not libraries:
            print("\n当前没有任何图库")
            return
        
        print(f"\n找到 {len(libraries)} 个图库:\n")
        
        for lib in libraries:
            print(f"📁 {lib.library_name}")
            print(f"   路径: {lib.library_path}")
            
            # 验证路径状态
            if os.path.exists(lib.library_path):
                if os.path.isdir(lib.library_path):
                    # 统计图片数量
                    image_count = 0
                    for root, dirs, files in os.walk(lib.library_path):
                        for file in files:
                            ext = os.path.splitext(file.lower())[1]
                            if ext in IMAGE_EXTENSIONS:
                                image_count += 1
                    print(f"   状态: ✅ 有效 ({image_count} 张图片)")
                else:
                    print(f"   状态: ⚠️ 路径不是目录")
            else:
                print(f"   状态: ❌ 路径不存在")
            
            print(f"   创建时间: {lib.created_at}")
            print()
            
    except Exception as e:
        print(f"错误: {e}")

def main():
    parser = argparse.ArgumentParser(description='图库管理工具')
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 创建图库命令
    create_parser = subparsers.add_parser('create', help='创建新的图库')
    create_parser.add_argument('name', help='图库名称')
    create_parser.add_argument('path', help='图库路径')
    create_parser.add_argument('--force', action='store_true', 
                              help='强制覆盖已存在的图库')
    
    # 列出图库命令
    list_parser = subparsers.add_parser('list', help='列出所有图库')
    
    # 验证路径命令
    validate_parser = subparsers.add_parser('validate', help='验证路径是否适合作为图库')
    validate_parser.add_argument('path', help='要验证的路径')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'create':
        success = create_library(args.name, args.path, args.force)
        sys.exit(0 if success else 1)
    
    elif args.command == 'list':
        list_libraries()
    
    elif args.command == 'validate':
        # 只验证路径，不创建记录
        path = os.path.abspath(args.path)
        print(f"验证路径: {path}\n")
        is_valid, message, image_count = validate_library_path(path)
        print(message)
        sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()