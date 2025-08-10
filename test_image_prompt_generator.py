#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试脚本：测试图片提示词生成器的独立运行功能
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from image_prompt_generator import ImagePromptGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_single_segment():
    """测试单个片段的提示词生成"""
    logger.info("=" * 60)
    logger.info("测试1: 生成单个片段的提示词")
    logger.info("=" * 60)
    
    try:
        generator = ImagePromptGenerator(
            creator_name="test",
            video_id="Xya-j50aqjM",
            images_per_segment=2
        )
        
        # 生成片段1的提示词
        result = generator.generate_for_segment(1)
        
        # 显示结果
        logger.info(f"✅ 成功生成片段1的提示词")
        logger.info(f"   - 场景数: {len(result.get('scenes', []))}")
        logger.info(f"   - 提示词数: {len(result.get('prompts', []))}")
        
        # 保存结果
        generator.save_results(result, single=True)
        logger.info(f"💾 结果已保存")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_segments():
    """测试多个片段的提示词生成"""
    logger.info("=" * 60)
    logger.info("测试2: 生成多个片段的提示词")
    logger.info("=" * 60)
    
    try:
        generator = ImagePromptGenerator(
            creator_name="test",
            video_id="Xya-j50aqjM",
            images_per_segment=1
        )
        
        # 生成片段1,5,9的提示词
        segment_ids = [1, 5, 9]
        results = generator.generate_for_segments(segment_ids)
        
        # 显示结果
        logger.info(f"✅ 成功处理 {len(segment_ids)} 个片段")
        logger.info(f"   - 总提示词数: {results.get('total_prompts', 0)}")
        
        # 检查每个片段的结果
        for seg_id in segment_ids:
            seg_key = f"segment_{seg_id:02d}"
            if seg_key in results["segments"]:
                seg_data = results["segments"][seg_key]
                if "error" in seg_data:
                    logger.warning(f"   - 片段{seg_id}: ❌ {seg_data['error']}")
                else:
                    logger.info(f"   - 片段{seg_id}: ✅ {len(seg_data.get('prompts', []))} 个提示词")
        
        # 保存结果
        generator.save_results(results)
        logger.info(f"💾 结果已保存")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_segments():
    """测试所有片段的提示词生成"""
    logger.info("=" * 60)
    logger.info("测试3: 生成所有片段的提示词")
    logger.info("=" * 60)
    
    try:
        generator = ImagePromptGenerator(
            creator_name="test",
            video_id="Xya-j50aqjM",
            images_per_segment=1
        )
        
        # 生成所有片段的提示词
        results = generator.generate_for_segments()
        
        # 显示结果
        logger.info(f"✅ 成功处理所有片段")
        logger.info(f"   - 片段总数: {results.get('total_segments', 0)}")
        logger.info(f"   - 总提示词数: {results.get('total_prompts', 0)}")
        
        # 统计成功和失败的片段
        if "segments" in results:
            success_count = sum(1 for v in results["segments"].values() if "prompts" in v)
            error_count = sum(1 for v in results["segments"].values() if "error" in v)
            logger.info(f"   - 成功: {success_count} 个片段")
            logger.info(f"   - 失败: {error_count} 个片段")
        
        # 保存结果
        generator.save_results(results)
        logger.info(f"💾 结果已保存")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_path_validation():
    """测试路径验证功能"""
    logger.info("=" * 60)
    logger.info("测试4: 路径验证功能")
    logger.info("=" * 60)
    
    # 测试不存在的项目
    try:
        generator = ImagePromptGenerator(
            creator_name="not_exist",
            video_id="not_exist",
            images_per_segment=1
        )
        logger.error("❌ 应该抛出FileNotFoundError")
        return False
    except FileNotFoundError as e:
        logger.info(f"✅ 正确检测到不存在的路径: {e}")
    
    # 测试存在的项目
    try:
        generator = ImagePromptGenerator(
            creator_name="test",
            video_id="Xya-j50aqjM",
            images_per_segment=1
        )
        logger.info("✅ 成功验证存在的路径")
        
        # 测试自动发现片段
        segment_ids = generator._discover_segments()
        logger.info(f"✅ 自动发现 {len(segment_ids)} 个片段文件: {segment_ids}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False


def test_character_extraction():
    """测试角色信息提取功能"""
    logger.info("=" * 60)
    logger.info("测试5: 角色信息提取")
    logger.info("=" * 60)
    
    try:
        generator = ImagePromptGenerator(
            creator_name="test",
            video_id="Xya-j50aqjM",
            images_per_segment=1
        )
        
        # 提取角色信息
        characters = generator._extract_character_profiles()
        
        logger.info(f"✅ 成功提取 {len(characters)} 个角色")
        for name, profile in characters.items():
            logger.info(f"   - {name}:")
            logger.info(f"     视觉描述: {profile.get('visual_description', '')[:50]}...")
            logger.info(f"     SD特征: {profile.get('sd_features', '')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    logger.info("🚀 开始测试图片提示词生成器")
    logger.info("")
    
    tests = [
        ("路径验证", test_path_validation),
        ("角色提取", test_character_extraction),
        ("单个片段", test_single_segment),
        ("多个片段", test_multiple_segments),
        ("所有片段", test_all_segments),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"测试 {test_name} 异常: {e}")
            results.append((test_name, False))
        logger.info("")
    
    # 显示测试结果汇总
    logger.info("=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"{test_name}: {status}")
    
    # 计算通过率
    passed = sum(1 for _, success in results if success)
    total = len(results)
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    logger.info("")
    logger.info(f"通过率: {passed}/{total} ({pass_rate:.1f}%)")
    
    if passed == total:
        logger.info("🎉 所有测试通过！")
    else:
        logger.warning(f"⚠️ {total - passed} 个测试失败")


if __name__ == "__main__":
    main()