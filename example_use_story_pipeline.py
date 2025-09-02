#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube故事生成Pipeline使用示例
演示如何通过自动发布系统使用Pipeline
"""

import json
from datetime import datetime

def example_pipeline_configs():
    """不同场景的Pipeline配置示例"""
    
    print("="*60)
    print("YouTube故事生成Pipeline配置示例")
    print("="*60)
    
    # 场景1：快节奏短视频（1分钟，适合TikTok/Shorts）
    config_short = {
        "pipeline_id": "youtube_story_v3",
        "config": {
            "video_id": "dQw4w9WgXcQ",        # YouTube视频ID
            "image_library": "cartoon",        # 使用卡通图库（活泼）
            "image_duration": 3,               # 每张图3秒（快节奏）
            "duration": 60,                    # 总时长60秒
            "gender": 2                        # 女声（更活泼）
        },
        "metadata": {
            "name": "快节奏短视频配置",
            "description": "适合YouTube Shorts、TikTok等短视频平台",
            "target_audience": "年轻用户",
            "expected_views": "10K-50K"
        }
    }
    
    print("\n1. 快节奏短视频配置（YouTube Shorts/TikTok）:")
    print(json.dumps(config_short, indent=2, ensure_ascii=False))
    
    # 场景2：标准故事视频（2-3分钟）
    config_standard = {
        "pipeline_id": "youtube_story_v3",
        "config": {
            "video_id": "dQw4w9WgXcQ",
            "image_library": "default",        # 默认图库
            "image_duration": 5,               # 每张图5秒（标准）
            "duration": 150,                   # 总时长2.5分钟
            "gender": 1                        # 男声（沉稳）
        },
        "metadata": {
            "name": "标准故事视频配置",
            "description": "适合大多数YouTube频道的标准配置",
            "target_audience": "通用受众",
            "expected_views": "5K-20K"
        }
    }
    
    print("\n2. 标准故事视频配置:")
    print(json.dumps(config_standard, indent=2, ensure_ascii=False))
    
    # 场景3：深度长视频（5-10分钟）
    config_long = {
        "pipeline_id": "youtube_story_v3",
        "config": {
            "video_id": "dQw4w9WgXcQ",
            "image_library": "nature",         # 自然风景（舒缓）
            "image_duration": 8,               # 每张图8秒（慢节奏）
            "duration": 480,                   # 总时长8分钟
            "gender": 1                        # 男声（适合长内容）
        },
        "metadata": {
            "name": "深度长视频配置",
            "description": "适合深度内容、睡前故事等",
            "target_audience": "成人观众",
            "expected_views": "2K-10K"
        }
    }
    
    print("\n3. 深度长视频配置:")
    print(json.dumps(config_long, indent=2, ensure_ascii=False))
    
    # 场景4：儿童故事配置
    config_kids = {
        "pipeline_id": "youtube_story_v3",
        "config": {
            "video_id": "dQw4w9WgXcQ",
            "image_library": "cartoon",        # 卡通图库
            "image_duration": 4,               # 每张图4秒
            "duration": 180,                   # 总时长3分钟
            "gender": 2                        # 女声（温柔）
        },
        "metadata": {
            "name": "儿童故事配置",
            "description": "适合儿童观看的故事视频",
            "target_audience": "3-10岁儿童",
            "expected_views": "20K-100K"
        }
    }
    
    print("\n4. 儿童故事配置:")
    print(json.dumps(config_kids, indent=2, ensure_ascii=False))

def create_publish_workflow():
    """创建完整的发布工作流示例"""
    
    print("\n" + "="*60)
    print("完整的自动发布工作流")
    print("="*60)
    
    # Step 1: 创建账号组
    account_group = {
        "group_name": "story_channels",
        "group_type": "production",
        "description": "故事频道账号组",
        "account_ids": [
            "yt_001_novel",    # 小说频道
            "yt_002_story",    # 故事频道
            "yt_003_kids"      # 儿童频道
        ]
    }
    
    print("\nStep 1: 创建账号组")
    print(json.dumps(account_group, indent=2, ensure_ascii=False))
    
    # Step 2: 创建发布配置
    publish_config = {
        "config_name": "每日故事发布",
        "group_id": "story_channels",
        "pipeline_id": "youtube_story_v3",
        "trigger_type": "scheduled",
        "trigger_config": {
            "schedule": "daily",
            "time": "20:00",           # 每晚8点
            "timezone": "Asia/Shanghai"
        },
        "pipeline_config": {
            "image_library": "nature",
            "image_duration": 5,
            "duration": 180,
            "gender": 1
        },
        "priority": 80
    }
    
    print("\nStep 2: 创建发布配置")
    print(json.dumps(publish_config, indent=2, ensure_ascii=False))
    
    # Step 3: 创建环形调度
    ring_schedule = {
        "config_id": "daily_story_config",
        "target_date": "2024-12-25",
        "start_hour": 8,               # 早8点开始
        "end_hour": 22,                # 晚10点结束
        "accounts": [
            "yt_001_novel",
            "yt_002_story",
            "yt_003_kids"
        ]
    }
    
    print("\nStep 3: 创建环形调度（均匀分布发布时间）")
    print(json.dumps(ring_schedule, indent=2, ensure_ascii=False))
    print("\n说明：3个账号在14小时内均匀分布，每个账号间隔约4.7小时")
    print("- yt_001_novel: 08:00")
    print("- yt_002_story: 12:40")
    print("- yt_003_kids: 17:20")
    
    # Step 4: A/B测试策略
    ab_test_strategy = {
        "strategy_name": "图库效果测试",
        "strategy_type": "ab_test",
        "parameters": {
            "variants": [
                {
                    "name": "control",
                    "pipeline_config": {
                        "image_library": "default",
                        "image_duration": 5
                    }
                },
                {
                    "name": "variant_a",
                    "pipeline_config": {
                        "image_library": "nature",
                        "image_duration": 7
                    }
                },
                {
                    "name": "variant_b",
                    "pipeline_config": {
                        "image_library": "cartoon",
                        "image_duration": 3
                    }
                }
            ],
            "metric": "view_duration",
            "sample_size": 1000
        }
    }
    
    print("\nStep 4: A/B测试策略（测试不同图库效果）")
    print(json.dumps(ab_test_strategy, indent=2, ensure_ascii=False))

def monitoring_and_optimization():
    """监控和优化示例"""
    
    print("\n" + "="*60)
    print("监控和优化配置")
    print("="*60)
    
    # 监控配置
    monitor_config = {
        "monitor_type": "competitor",
        "platform": "youtube",
        "target_channels": [
            "@MrBeast",           # 竞品频道1
            "@PewDiePie",        # 竞品频道2
            "@StoryTime"         # 竞品频道3
        ],
        "check_interval": 3600,   # 每小时检查
        "trigger_action": {
            "type": "auto_generate",
            "pipeline_id": "youtube_story_v3",
            "config": {
                "image_library": "trending",  # 使用流行图库
                "image_duration": 4,
                "duration": 120
            }
        }
    }
    
    print("\n监控竞品频道配置:")
    print(json.dumps(monitor_config, indent=2, ensure_ascii=False))
    
    # 性能指标
    performance_metrics = {
        "metrics": [
            {
                "name": "平均观看时长",
                "target": "180秒",
                "current": "145秒",
                "optimization": "增加图片持续时间到6-7秒"
            },
            {
                "name": "点击率(CTR)",
                "target": "8%",
                "current": "5.2%",
                "optimization": "使用更吸引人的图库（cartoon/abstract）"
            },
            {
                "name": "完播率",
                "target": "40%",
                "current": "32%",
                "optimization": "缩短总时长到120-150秒"
            }
        ]
    }
    
    print("\n性能优化建议:")
    print(json.dumps(performance_metrics, indent=2, ensure_ascii=False))

def image_library_guide():
    """图库使用指南"""
    
    print("\n" + "="*60)
    print("图库使用指南")
    print("="*60)
    
    libraries = {
        "default": {
            "description": "默认通用图库",
            "best_for": "大多数故事内容",
            "image_count": "1000+",
            "style": "混合风格"
        },
        "nature": {
            "description": "自然风景图库",
            "best_for": "舒缓、深度内容、睡前故事",
            "image_count": "500+",
            "style": "风景、动植物、自然现象"
        },
        "cartoon": {
            "description": "卡通动漫图库",
            "best_for": "儿童内容、轻松故事、短视频",
            "image_count": "800+",
            "style": "可爱、活泼、色彩丰富"
        },
        "abstract": {
            "description": "抽象艺术图库",
            "best_for": "科幻、悬疑、思考类内容",
            "image_count": "300+",
            "style": "抽象、几何、艺术感"
        },
        "vintage": {
            "description": "复古怀旧图库",
            "best_for": "历史故事、怀旧内容",
            "image_count": "400+",
            "style": "复古、黑白、老照片"
        },
        "trending": {
            "description": "流行趋势图库（动态更新）",
            "best_for": "热点内容、时事相关",
            "image_count": "200+（每周更新）",
            "style": "当前流行风格"
        }
    }
    
    for lib_name, lib_info in libraries.items():
        print(f"\n📚 {lib_name}:")
        print(f"   描述: {lib_info['description']}")
        print(f"   适用: {lib_info['best_for']}")
        print(f"   图片数: {lib_info['image_count']}")
        print(f"   风格: {lib_info['style']}")
    
    print("\n图片持续时间建议:")
    print("├─ 3-4秒: 快节奏、短视频、年轻观众")
    print("├─ 5-6秒: 标准节奏、通用内容")
    print("├─ 7-8秒: 慢节奏、深度内容、成人观众")
    print("└─ 9-10秒: 超慢节奏、冥想、睡前故事")

if __name__ == "__main__":
    # 1. 展示不同场景的配置
    example_pipeline_configs()
    
    # 2. 展示完整的发布工作流
    create_publish_workflow()
    
    # 3. 展示监控和优化
    monitoring_and_optimization()
    
    # 4. 图库使用指南
    image_library_guide()
    
    print("\n" + "="*60)
    print("使用提示")
    print("="*60)
    print("\n1. Pipeline已成功注册: youtube_story_v3")
    print("2. 支持平台: YouTube, Bilibili")
    print("3. 可配置参数:")
    print("   - video_id: YouTube视频ID（必需）")
    print("   - image_library: 图库名称（可选）")
    print("   - image_duration: 单图持续时长（可选）")
    print("   - duration: 总时长（可选）")
    print("   - gender: 语音性别（可选）")
    print("\n4. 通过API创建任务: POST /api/auto-publish/tasks/create")
    print("5. 通过调度器自动执行: 配置trigger_type为'scheduled'")