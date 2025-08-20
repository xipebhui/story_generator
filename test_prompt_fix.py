#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试提示词加载修复
验证framework_generatorv3.md不会因为JSON示例被误解析
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pipeline_architecture import PromptManager

def test_prompt_loading():
    """测试提示词加载"""
    
    print("="*60)
    print("测试提示词加载（修复后）")
    print("="*60)
    
    # 创建提示词管理器
    prompt_manager = PromptManager(Path("prompts"))
    
    # 测试加载各个提示词
    test_prompts = [
        'framework_generatorv3',
        'story_header',
        'segment_generator',
        'final_polisher'
    ]
    
    for prompt_name in test_prompts:
        try:
            print(f"\n测试加载: {prompt_name}")
            
            # 加载提示词
            template = prompt_manager.load_prompt(prompt_name)
            
            # 获取提示词内容（不传递任何变量）
            content = prompt_manager.get_prompt(prompt_name)
            
            # 检查是否包含预期的内容
            if prompt_name == 'framework_generatorv3':
                # 应该包含JSON示例
                assert '"adaptationAnalysis"' in content
                assert '"storyBlueprint"' in content
                print(f"  ✅ 成功加载，包含JSON结构")
            else:
                print(f"  ✅ 成功加载")
            
            print(f"  - 长度: {len(content)} 字符")
            print(f"  - 变量: {template.variables}")
            
        except Exception as e:
            print(f"  ❌ 加载失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    test_prompt_loading()