#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试三步提示词流程
"""

import os
import logging
from pathlib import Path
from image_prompt_generator import ImagePromptGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_three_step_flow():
    """测试三步提示词生成流程"""
    
    # 禁用Gemini API以使用规则生成（避免超时）
    os.environ["DISABLE_GEMINI"] = "1"
    
    try:
        # 初始化生成器
        logger.info("初始化图片提示词生成器...")
        generator = ImagePromptGenerator(
            creator_name="test",
            video_id="Xya-j50aqjM",
            images_per_segment=2  # 生成2个场景
        )
        
        # 读取一个片段进行测试
        segment_file = generator.segments_dir / "segment_01.txt"
        if not segment_file.exists():
            logger.error(f"片段文件不存在: {segment_file}")
            return
        
        segment_content = segment_file.read_text(encoding='utf-8')
        logger.info(f"读取片段内容: {len(segment_content)} 字符")
        
        # 步骤1: 场景提取（使用规则）
        logger.info("\n步骤1: 分析片段提取场景...")
        scenes = generator._analyze_with_rules(segment_content, 1)
        logger.info(f"提取到 {len(scenes)} 个场景")
        for i, scene in enumerate(scenes, 1):
            logger.info(f"  场景{i}: {scene.get('description', '')[:50]}...")
            logger.info(f"    - 情感: {scene.get('emotion', '')}")
            logger.info(f"    - 色调: {scene.get('color_mood', '')}")
            logger.info(f"    - 元素: {', '.join(scene.get('visual_elements', []))}")
        
        # 步骤2: 获取角色信息
        logger.info("\n步骤2: 提取角色信息...")
        characters = generator._extract_character_profiles()
        for name, profile in characters.items():
            logger.info(f"  {name}: {profile.get('visual_description', '')}")
        
        # 步骤3: 生成SD提示词（使用规则）
        logger.info("\n步骤3: 生成SD提示词...")
        prompts = []
        for scene in scenes:
            prompt = generator._build_sd_prompt(scene, characters)
            prompts.append({
                "scene_index": scene.get("scene_index", 1),
                "scene_description": scene.get("description", ""),
                "sd_prompt": prompt
            })
        
        # 显示生成的提示词
        logger.info(f"\n生成了 {len(prompts)} 个SD提示词:")
        for prompt_data in prompts:
            logger.info(f"\n场景 {prompt_data['scene_index']}:")
            logger.info(f"描述: {prompt_data['scene_description'][:50]}...")
            logger.info(f"正面提示词: {prompt_data['sd_prompt']['positive'][:100]}...")
            logger.info(f"负面提示词: {prompt_data['sd_prompt']['negative'][:50]}...")
        
        # 保存结果
        result = {
            "segment_id": 1,
            "scenes": scenes,
            "prompts": prompts
        }
        generator.save_results(result, single=True)
        logger.info(f"\n✅ 结果已保存到: {generator.final_dir}")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("测试三步提示词生成流程")
    logger.info("=" * 60)
    test_three_step_flow()