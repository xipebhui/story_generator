#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Pipeline config_schema保存和读取问题
"""

import json
import logging
from pipeline_registry import get_pipeline_registry
from database import get_db_manager
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_database_directly():
    """直接查询数据库检查config_schema"""
    print("\n" + "="*50)
    print("直接查询数据库")
    print("="*50)
    
    db = get_db_manager()
    with db.get_session() as session:
        results = session.execute(text("""
            SELECT pipeline_id, pipeline_name, config_schema
            FROM pipeline_registry
            WHERE status = 'active'
        """)).fetchall()
        
        for row in results:
            print(f"\nPipeline: {row[0]} ({row[1]})")
            print(f"config_schema原始值: {row[2]}")
            if row[2]:
                try:
                    # 尝试解析JSON
                    schema = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                    print(f"config_schema解析后: {json.dumps(schema, indent=2, ensure_ascii=False)}")
                except Exception as e:
                    print(f"解析失败: {e}")

def check_through_registry():
    """通过Registry检查config_schema"""
    print("\n" + "="*50)
    print("通过Registry获取")
    print("="*50)
    
    registry = get_pipeline_registry()
    pipelines = registry.list_pipelines()
    
    for p in pipelines:
        print(f"\nPipeline: {p.pipeline_id} ({p.pipeline_name})")
        print(f"config_schema: {p.config_schema}")
        print(f"config_schema类型: {type(p.config_schema)}")

def test_register_new_pipeline():
    """测试注册新Pipeline"""
    print("\n" + "="*50)
    print("测试注册新Pipeline")
    print("="*50)
    
    registry = get_pipeline_registry()
    
    # 标准的JSON Schema格式
    test_schema = {
        "type": "object",
        "properties": {
            "test_field": {
                "type": "string",
                "description": "测试字段"
            },
            "test_number": {
                "type": "integer",
                "default": 10,
                "minimum": 1,
                "maximum": 100
            }
        },
        "required": ["test_field"]
    }
    
    pipeline_id = "test_pipeline_debug"
    
    # 先删除如果存在
    registry.delete_pipeline(pipeline_id)
    
    # 注册
    print(f"\n注册Pipeline: {pipeline_id}")
    print(f"Schema: {json.dumps(test_schema, indent=2, ensure_ascii=False)}")
    
    success = registry.register_pipeline(
        pipeline_id=pipeline_id,
        pipeline_name="测试Pipeline调试",
        pipeline_type="test",
        pipeline_class="test.TestPipeline",
        config_schema=test_schema,
        supported_platforms=["test"],
        version="1.0.0"
    )
    
    if success:
        print("✅ 注册成功")
        
        # 立即查询验证
        pipeline = registry.get_pipeline(pipeline_id)
        if pipeline:
            print(f"\n获取到的Pipeline:")
            print(f"  config_schema: {pipeline.config_schema}")
            print(f"  类型: {type(pipeline.config_schema)}")
            
            # 直接查询数据库
            db = get_db_manager()
            with db.get_session() as session:
                result = session.execute(text("""
                    SELECT config_schema FROM pipeline_registry
                    WHERE pipeline_id = :pipeline_id
                """), {"pipeline_id": pipeline_id}).fetchone()
                
                if result:
                    print(f"\n数据库中的值:")
                    print(f"  原始: {result[0]}")
                    print(f"  类型: {type(result[0])}")
        
        # 清理测试数据
        registry.delete_pipeline(pipeline_id)
        print("\n✅ 测试数据已清理")
    else:
        print("❌ 注册失败")

def update_existing_pipeline_schemas():
    """更新现有Pipeline的schema为正确格式"""
    print("\n" + "="*50)
    print("更新现有Pipeline的Schema")
    print("="*50)
    
    registry = get_pipeline_registry()
    
    # story_v3的正确schema
    story_v3_schema = {
        "type": "object",
        "properties": {
            "video_id": {
                "type": "string",
                "description": "YouTube视频ID"
            },
            "creator_name": {
                "type": "string", 
                "description": "创作者名称"
            },
            "cache_dir": {
                "type": "string",
                "description": "缓存目录路径"
            },
            "save_intermediate": {
                "type": "integer",
                "description": "是否保存中间结果(0或1)",
                "default": 1
            },
            "image_library": {
                "type": "string",
                "description": "图库名称",
                "default": "default",
                "enum": ["default", "nature", "cartoon", "abstract"]
            },
            "image_duration": {
                "type": "integer",
                "description": "单张图片持续时长(秒)",
                "default": 5,
                "minimum": 3,
                "maximum": 10
            },
            "voice_speed": {
                "type": "number",
                "description": "语音速度",
                "default": 1.0,
                "minimum": 0.5,
                "maximum": 2.0
            },
            "gender": {
                "type": "integer",
                "description": "语音性别(0=女声,1=男声)",
                "default": 0,
                "enum": [0, 1]
            },
            "duration": {
                "type": "integer",
                "description": "总时长限制(秒)",
                "minimum": 60,
                "maximum": 600
            }
        },
        "required": ["video_id", "creator_name"]
    }
    
    # 更新story_v3
    print("\n更新story_v3...")
    success = registry.update_pipeline(
        pipeline_id="story_v3",
        update_data={
            "config_schema": story_v3_schema
        }
    )
    
    if success:
        print("✅ story_v3更新成功")
    else:
        print("⚠️ story_v3不存在或更新失败")
    
    # 更新youtube_story_v3
    print("\n更新youtube_story_v3...")
    success = registry.update_pipeline(
        pipeline_id="youtube_story_v3",
        update_data={
            "config_schema": story_v3_schema
        }
    )
    
    if success:
        print("✅ youtube_story_v3更新成功")
    else:
        print("⚠️ youtube_story_v3不存在或更新失败")

if __name__ == "__main__":
    print("Pipeline Config Schema 调试工具")
    print("="*50)
    
    # 1. 检查数据库
    print("\n步骤1: 检查数据库中的config_schema")
    check_database_directly()
    
    # 2. 通过Registry检查
    print("\n步骤2: 通过Registry API获取")
    check_through_registry()
    
    # 3. 测试注册新Pipeline
    print("\n步骤3: 测试注册功能")
    test_register_new_pipeline()
    
    # 4. 询问是否更新
    print("\n" + "="*50)
    response = input("是否要更新现有Pipeline的schema? (y/n): ")
    if response.lower() == 'y':
        update_existing_pipeline_schemas()
    
    print("\n调试完成！")
    print("\n建议:")
    print("1. 检查日志输出，查看config_schema的保存和读取过程")
    print("2. 如果schema格式不正确，运行更新功能")
    print("3. 重启服务后测试API接口")