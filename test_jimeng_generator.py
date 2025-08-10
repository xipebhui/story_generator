#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试即梦AI提示词生成器
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

def test_jimeng_generator():
    """测试即梦提示词生成器"""
    
    try:
        # 初始化即梦生成器
        logger.info("初始化即梦提示词生成器...")
        generator = ImagePromptGenerator(
            creator_name="test",
            video_id="Xya-j50aqjM",
            generator_type="jimeng",  # 使用即梦生成器
            images_per_segment=1
        )
        
        # 读取一个片段进行测试
        segment_file = generator.segments_dir / "segment_01.txt"
        if not segment_file.exists():
            logger.error(f"片段文件不存在: {segment_file}")
            return
        
        segment_content = segment_file.read_text(encoding='utf-8')
        logger.info(f"读取片段内容: {len(segment_content)} 字符")
        
        # 提取场景（会调用AI）
        logger.info("\n步骤1: 提取场景...")
        scenes = generator._analyze_segment_scenes(segment_content, 1)
        logger.info(f"提取到 {len(scenes)} 个场景")
        
        # 提取角色信息
        logger.info("\n步骤2: 提取角色信息...")
        characters = generator._extract_character_profiles()
        logger.info(f"提取到 {len(characters)} 个角色")
        
        # 生成即梦提示词（会调用AI）
        logger.info("\n步骤3: 生成即梦中文提示词...")
        result = generator.generate_for_segment(1)
        
        # 显示生成的提示词
        if "prompts" in result:
            logger.info(f"\n生成了 {len(result['prompts'])} 个即梦提示词:")
            for prompt_data in result["prompts"]:
                logger.info(f"\n场景 {prompt_data.get('scene_index', '')}:")
                logger.info(f"描述: {prompt_data.get('scene_description', '')[:50]}...")
                
                # 即梦提示词
                if "jimeng_prompt" in prompt_data:
                    logger.info(f"即梦提示词: {prompt_data['jimeng_prompt'][:100]}...")
                else:
                    # 兼容性：从sd_prompt中获取
                    logger.info(f"即梦提示词: {prompt_data['sd_prompt']['positive'][:100]}...")
        
        # 保存结果
        generator.save_results(result, single=True)
        logger.info(f"\n✅ 结果已保存到: {generator.final_dir}")
        
        # 读取保存的文件
        result_file = generator.final_dir / "sd_prompt_segment_01.md"
        if result_file.exists():
            logger.info(f"✅ Markdown文件已生成: {result_file}")
        
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        logger.info("请确保所有提示词文件都存在，特别是 prompts/jimeng_prompt_generator.md")
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("测试即梦AI提示词生成器")
    logger.info("=" * 60)
    logger.info("")
    logger.info("注意：此测试需要Gemini API支持")
    logger.info("如果没有配置API，会报错")
    logger.info("")
    
    # 检查即梦提示词文件是否存在
    jimeng_prompt_file = Path("prompts/jimeng_prompt_generator.md")
    if not jimeng_prompt_file.exists():
        logger.error(f"即梦提示词文件不存在: {jimeng_prompt_file}")
        logger.error("请先创建该文件")
    else:
        logger.info(f"✅ 即梦提示词文件存在: {jimeng_prompt_file}")
        test_jimeng_generator()