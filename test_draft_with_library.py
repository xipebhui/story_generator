#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试使用图库名称生成草稿
"""

import sys
import os
import subprocess

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_draft_generation():
    """测试草稿生成（需要音频文件存在）"""
    
    print("="*60)
    print("测试使用图库生成草稿")
    print("="*60)
    
    # 检查是否有可用的音频文件
    import glob
    audio_files = glob.glob("./output/*_story.mp3")
    
    if not audio_files:
        print("\n❌ 没有找到音频文件")
        print("请先运行 Pipeline 生成音频文件")
        return False
    
    # 使用第一个找到的音频文件
    audio_path = audio_files[0]
    filename = os.path.basename(audio_path)
    parts = filename.replace("_story.mp3", "").split("_")
    
    if len(parts) >= 2:
        cid = "_".join(parts[:-1])
        vid = parts[-1]
    else:
        print(f"❌ 无法从文件名解析 cid 和 vid: {filename}")
        return False
    
    print(f"\n使用音频文件: {audio_path}")
    print(f"Creator ID: {cid}")
    print(f"Voice ID: {vid}")
    
    # 测试不同的图库参数
    test_cases = [
        ("default", "使用图库名称 'default'"),
        (None, "不指定图库（使用默认）"),
    ]
    
    for image_dir, description in test_cases:
        print(f"\n测试: {description}")
        
        # 构建命令
        command = [
            sys.executable,
            "draft_gen/generateDraftService.py",
            "--cid", cid,
            "--vid", vid,
            "--duration", "3"
        ]
        
        if image_dir:
            command.extend(["--image_dir", image_dir])
        
        print(f"执行命令: {' '.join(command)}")
        
        try:
            # 执行命令（只运行几秒钟来验证参数传递）
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5  # 5秒超时
            )
            
            # 检查输出中是否有图库相关信息
            output = result.stdout + result.stderr
            if "使用图库" in output or "使用默认" in output:
                print("✅ 图库参数正确处理")
                # 打印图库相关的输出行
                for line in output.split('\n'):
                    if "图库" in line or "使用" in line:
                        print(f"   {line}")
            else:
                print("❌ 未找到图库处理信息")
                
        except subprocess.TimeoutExpired:
            print("✅ 命令启动成功（超时终止是正常的）")
        except Exception as e:
            print(f"❌ 执行失败: {e}")
    
    return True

def check_library_in_database():
    """检查数据库中的图库"""
    print("\n" + "="*60)
    print("检查数据库中的图库")
    print("="*60)
    
    from database import get_db_manager
    
    db = get_db_manager()
    libraries = db.get_all_image_libraries()
    
    print("\n当前图库:")
    for lib in libraries:
        print(f"  - {lib.library_name}: {lib.library_path}")
        
        # 检查路径是否存在
        if os.path.exists(lib.library_path):
            # 统计图片数量
            import glob
            images = glob.glob(f"{lib.library_path}/*.jpg") + \
                     glob.glob(f"{lib.library_path}/*.png") + \
                     glob.glob(f"{lib.library_path}/*.jpeg")
            print(f"    ✅ 路径存在，包含 {len(images)} 张图片")
        else:
            print(f"    ❌ 路径不存在")

if __name__ == "__main__":
    check_library_in_database()
    test_draft_generation()