#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试debug日志功能
"""

import logging
import sys
from pathlib import Path

# 设置根日志级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 导入图片生成器
from image_prompt_generator import ImagePromptGenerator

def test_debug_logging():
    """测试debug日志功能"""
    
    print("=" * 60)
    print("测试Debug日志功能")
    print("=" * 60)
    
    # 创建生成器实例
    generator = ImagePromptGenerator(
        creator_name="test",
        video_id="debug_test",
        images_per_segment=1,
        generator_type="jimeng",
        art_style="写实摄影风格"
    )
    
    # 检查logs目录是否创建
    log_dir = Path("logs/test/debug_test")
    if log_dir.exists():
        print(f"✅ 日志目录已创建: {log_dir}")
        
        # 列出所有日志文件
        log_files = list(log_dir.glob("*.log"))
        if log_files:
            print(f"✅ 找到{len(log_files)}个日志文件:")
            for log_file in log_files:
                print(f"   - {log_file.name}")
        else:
            print("❌ 未找到日志文件")
    else:
        print(f"❌ 日志目录未创建: {log_dir}")
    
    # 生成一个测试段落的提示词
    print("\n" + "=" * 60)
    print("生成测试提示词...")
    print("=" * 60)
    
    try:
        # 调用处理单个片段的方法
        result = generator.process_single_segment(1)
        print(f"✅ 成功生成{len(result.get('prompts', []))}个提示词")
        
        # 再次检查日志文件
        log_files = list(log_dir.glob("*.log"))
        if log_files:
            latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
            print(f"\n最新日志文件: {latest_log}")
            
            # 读取并显示日志文件的前几行
            with open(latest_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"日志文件包含 {len(lines)} 行")
                
                if len(lines) > 0:
                    print("\n日志文件前10行:")
                    print("-" * 40)
                    for line in lines[:10]:
                        print(line.rstrip())
                    print("-" * 40)
                    
                    if len(lines) > 10:
                        print(f"... 还有 {len(lines) - 10} 行")
    
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_debug_logging()