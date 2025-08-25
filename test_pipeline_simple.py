#!/usr/bin/env python3
"""
测试简化版Pipeline
"""

import os
import sys
from pathlib import Path

# 加载环境变量
from config_loader import load_env_file
load_env_file()

# 测试环境变量
print("=" * 60)
print("环境变量检查")
print("=" * 60)
draft_dir = os.environ.get('DRAFT_LOCAL_DIR')
print(f"DRAFT_LOCAL_DIR: {draft_dir}")
if draft_dir:
    draft_path = Path(draft_dir)
    print(f"  - 路径存在: {draft_path.exists()}")
    print(f"  - 是目录: {draft_path.is_dir()}")
    print(f"  - 可写入: {os.access(draft_path, os.W_OK) if draft_path.exists() else 'N/A'}")

export_url = os.environ.get('EXPORT_VIDEO_URL')
print(f"\nEXPORT_VIDEO_URL: {export_url}")

print("\n" + "=" * 60)
print("测试草稿移动逻辑")
print("=" * 60)

# 模拟草稿文件夹路径
test_folder = Path("./output/drafts/test_creator_test_video_story")
print(f"测试文件夹: {test_folder}")
print(f"  - 存在: {test_folder.exists()}")

if test_folder.exists() and draft_dir:
    from datetime import datetime
    import shutil
    
    try:
        draft_target_dir = Path(draft_dir)
        draft_target_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        draft_folder_name = f"test_creator_test_video_{timestamp}"
        draft_target = draft_target_dir / draft_folder_name
        
        print(f"\n目标路径: {draft_target}")
        print("  - 准备移动...")
        
        # 注意：实际运行会移动文件夹
        # shutil.move(str(test_folder), str(draft_target))
        print("  - [模拟] 移动成功")
        
    except Exception as e:
        print(f"  - 错误: {e}")
else:
    if not test_folder.exists():
        print("  - 测试文件夹不存在")
    if not draft_dir:
        print("  - DRAFT_LOCAL_DIR 未配置")

print("\n" + "=" * 60)
print("测试完成")