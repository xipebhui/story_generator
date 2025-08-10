#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查看和分析debug日志文件
"""

import sys
import re
from pathlib import Path
from datetime import datetime

def view_debug_log(creator_name=None, video_id=None):
    """查看debug日志文件"""
    
    # 如果没有指定，使用默认值
    if not creator_name:
        creator_name = "test"
    if not video_id:
        video_id = "Xya-j50aqjM"
    
    log_dir = Path("logs") / creator_name / video_id
    
    if not log_dir.exists():
        print(f"❌ 日志目录不存在: {log_dir}")
        return
    
    # 找到最新的日志文件
    log_files = list(log_dir.glob("*.log"))
    if not log_files:
        print(f"❌ 没有找到日志文件在: {log_dir}")
        return
    
    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    print(f"📄 查看日志文件: {latest_log}")
    print(f"📏 文件大小: {latest_log.stat().st_size:,} bytes")
    print("=" * 80)
    
    with open(latest_log, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 统计各个部分
    scene_extract_count = content.count("场景提取 - 输入")
    jimeng_count = content.count("即梦提示词生成 - 输入")
    sd_count = content.count("SD提示词生成 - 输入")
    
    print(f"📊 统计信息:")
    print(f"   - 场景提取调用: {scene_extract_count} 次")
    print(f"   - 即梦提示词生成: {jimeng_count} 次")
    print(f"   - SD提示词生成: {sd_count} 次")
    print("=" * 80)
    
    # 提取并显示各部分内容
    sections = re.split(r'={80}', content)
    
    # 显示场景提取的输入输出
    print("\n📝 场景提取示例:")
    print("-" * 40)
    for i, section in enumerate(sections):
        if "场景提取 - 输入" in section:
            # 显示输入的前500个字符
            print("输入片段:")
            lines = sections[i+1].strip().split('\n')
            for line in lines:
                if "故事片段" in line:
                    # 找到故事片段后的内容
                    idx = lines.index(line)
                    if idx + 1 < len(lines):
                        story_content = '\n'.join(lines[idx+1:idx+6])
                        print(story_content[:500] + "..." if len(story_content) > 500 else story_content)
                    break
            break
    
    # 显示场景提取的输出
    print("\n输出片段:")
    for i, section in enumerate(sections):
        if "场景提取 - 输出" in section:
            # 显示输出的前500个字符
            output = sections[i+1].strip()
            print(output[:500] + "..." if len(output) > 500 else output)
            break
    
    print("-" * 40)
    
    # 显示即梦提示词生成示例
    print("\n🎨 即梦提示词生成示例:")
    print("-" * 40)
    for i, section in enumerate(sections):
        if "即梦提示词生成 - 输出" in section:
            # 找到生成的提示词
            output = sections[i+1].strip()
            # 提取full_prompt内容
            match = re.search(r'"full_prompt":\s*"([^"]+)"', output)
            if match:
                prompt = match.group(1)
                # 处理转义字符
                prompt = prompt.replace('\\n', '\n')
                print("生成的提示词:")
                print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            break
    print("-" * 40)
    
    print(f"\n💡 提示: 完整日志文件位于 {latest_log}")

if __name__ == "__main__":
    # 从命令行参数获取
    creator = sys.argv[1] if len(sys.argv) > 1 else None
    video = sys.argv[2] if len(sys.argv) > 2 else None
    
    view_debug_log(creator, video)