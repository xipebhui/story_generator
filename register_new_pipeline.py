#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
注册新的StoryFullPipeline到系统
"""

import sys
from pathlib import Path

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pipeline_registry import register_story_full_pipeline, get_pipeline_registry


def main():
    """注册新的Pipeline"""
    print("=" * 60)
    print("注册 StoryFullPipeline 到系统")
    print("=" * 60)
    
    # 执行注册
    success = register_story_full_pipeline()
    
    if success:
        print("✅ Pipeline注册成功！")
        
        # 验证注册
        registry = get_pipeline_registry()
        pipeline = registry.get_pipeline("story_full_pipeline")
        
        if pipeline:
            print("\n📋 已注册的Pipeline信息：")
            print(f"  - ID: {pipeline.pipeline_id}")
            print(f"  - 名称: {pipeline.pipeline_name}")
            print(f"  - 类型: {pipeline.pipeline_type}")
            print(f"  - 类路径: {pipeline.pipeline_class}")
            print(f"  - 版本: {pipeline.version}")
            print(f"  - 状态: {pipeline.status}")
            print(f"  - 支持平台: {pipeline.supported_platforms}")
            
            print("\n📝 配置模式：")
            for key, value_type in pipeline.config_schema.items():
                print(f"  - {key}: {value_type}")
            
            print("\n✅ 可以在auto_publish中使用以下配置：")
            print("  pipeline_id: 'story_full_pipeline'")
            print("  pipeline_class: 'pipelines.story_full_pipeline.StoryFullPipeline'")
        else:
            print("⚠️ 注册后无法获取Pipeline信息")
    else:
        print("❌ Pipeline注册失败（可能已经注册过）")
        
        # 尝试获取已有的注册信息
        registry = get_pipeline_registry()
        pipeline = registry.get_pipeline("story_full_pipeline")
        
        if pipeline:
            print("\n📋 已存在的Pipeline信息：")
            print(f"  - ID: {pipeline.pipeline_id}")
            print(f"  - 类路径: {pipeline.pipeline_class}")
            print(f"  - 状态: {pipeline.status}")
            
            if pipeline.status != "active":
                print("\n⚠️ Pipeline状态不是active，可能需要更新状态")
                # 尝试更新状态
                update_success = registry.update_pipeline_status("story_full_pipeline", "active")
                if update_success:
                    print("✅ 已更新Pipeline状态为active")
                else:
                    print("❌ 更新状态失败")
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()