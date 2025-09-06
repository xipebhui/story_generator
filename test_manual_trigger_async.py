#!/usr/bin/env python3
"""测试手动触发异步Pipeline执行"""

import requests
import json
import time
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# API 基础URL
BASE_URL = "http://localhost:51082"

def test_manual_trigger():
    """测试手动触发配置"""
    logger.info("="*60)
    logger.info("测试手动触发异步Pipeline执行")
    logger.info("="*60)
    
    # 1. 获取所有配置
    logger.info("\n1. 获取所有发布配置...")
    response = requests.get(f"{BASE_URL}/api/auto-publish/publish-configs")
    
    if response.status_code != 200:
        logger.error(f"获取配置失败: {response.status_code}")
        return False
    
    configs = response.json()
    logger.info(f"找到 {len(configs)} 个配置")
    
    if not configs:
        logger.warning("没有配置可以触发")
        # 创建一个测试配置
        logger.info("\n创建测试配置...")
        test_config = {
            "config_name": "测试异步执行",
            "group_id": "group_001",
            "pipeline_id": "reddit_to_video",
            "trigger_type": "manual",
            "trigger_config": {},
            "pipeline_params": {
                "video_id": "test_async_trigger"
            },
            "priority": 50
        }
        
        response = requests.post(
            f"{BASE_URL}/api/auto-publish/publish-configs",
            json=test_config,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            config_data = response.json()
            config_id = config_data["config_id"]
            logger.info(f"创建配置成功: {config_id}")
        else:
            logger.error(f"创建配置失败: {response.status_code}")
            return False
    else:
        # 使用第一个配置
        config_id = configs[0]["config_id"]
        logger.info(f"使用配置: {config_id} - {configs[0]['config_name']}")
    
    # 2. 手动触发配置
    logger.info(f"\n2. 手动触发配置 {config_id}...")
    start_time = time.time()
    
    response = requests.post(f"{BASE_URL}/api/auto-publish/publish-configs/{config_id}/manual-trigger")
    
    if response.status_code != 200:
        logger.error(f"触发失败: {response.status_code}")
        logger.error(f"响应: {response.text}")
        return False
    
    trigger_result = response.json()
    logger.info(f"触发成功: {trigger_result['message']}")
    
    # 获取创建的任务
    if trigger_result.get("tasks"):
        task_id = trigger_result["tasks"][0]["task_id"]
        logger.info(f"创建的任务ID: {task_id}")
        
        # 3. 检查任务状态
        logger.info(f"\n3. 监控任务状态...")
        for i in range(10):  # 最多等待10秒
            time.sleep(1)
            
            response = requests.get(f"{BASE_URL}/api/auto-publish/tasks/{task_id}")
            if response.status_code == 200:
                task = response.json()
                status = task.get("pipeline_status", "unknown")
                logger.info(f"  [{i+1}秒] 任务状态: {status}")
                
                if status in ["completed", "failed"]:
                    end_time = time.time()
                    logger.info(f"\n任务执行完成，耗时: {end_time - start_time:.2f}秒")
                    
                    if status == "completed":
                        logger.info("✅ 异步执行成功!")
                        if task.get("pipeline_result"):
                            logger.info(f"Pipeline结果: {json.dumps(task['pipeline_result'], indent=2, ensure_ascii=False)}")
                    else:
                        logger.error(f"❌ 执行失败: {task.get('error_message')}")
                    break
            else:
                logger.warning(f"获取任务状态失败: {response.status_code}")
    
    logger.info("\n" + "="*60)
    logger.info("测试完成")
    logger.info("="*60)
    
    return True

if __name__ == "__main__":
    test_manual_trigger()