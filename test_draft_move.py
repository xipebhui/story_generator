#!/usr/bin/env python3
"""
测试草稿移动功能
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# 加载环境变量
from config_loader import load_env_file
load_env_file()

# 获取配置
draft_dir = os.environ.get('DRAFT_LOCAL_DIR')
print(f"DRAFT_LOCAL_DIR: {draft_dir}")

# 测试草稿文件夹
test_draft = Path("output/drafts/test_P3hKojLuG1c_story")

if test_draft.exists():
    print(f"草稿文件夹存在: {test_draft}")
    
    if draft_dir:
        print(f"目标目录: {draft_dir}")
        
        # 创建目标目录
        draft_target_dir = Path(draft_dir)
        draft_target_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一的目标文件夹名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        draft_folder_name = f"test_P3hKojLuG1c_{timestamp}_test"
        draft_target = draft_target_dir / draft_folder_name
        
        print(f"目标路径: {draft_target}")
        
        # 复制（而不是移动，以保留原始文件）
        try:
            shutil.copytree(str(test_draft), str(draft_target))
            print(f"✅ 成功复制到: {draft_target}")
            
            # 验证
            if draft_target.exists():
                print(f"✅ 目标文件夹存在")
                print(f"   内容: {list(draft_target.iterdir())}")
        except Exception as e:
            print(f"❌ 复制失败: {e}")
    else:
        print("❌ DRAFT_LOCAL_DIR 未配置")
else:
    print(f"❌ 草稿文件夹不存在: {test_draft}")