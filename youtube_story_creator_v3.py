#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube Story Creator V3
使用新的framework_generatorv3提示词
简化版本，专注于生成框架
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入项目模块
from youtube_metadata_extractor import YouTubeMetadataExtractor
from gemini_client import GeminiClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class YouTubeStoryCreatorV3:
    """YouTube Story Creator V3 - 使用新的框架生成器"""
    
    def __init__(self, video_id: str, output_dir: str = None):
        """
        初始化
        
        Args:
            video_id: YouTube视频ID
            output_dir: 输出目录
        """
        self.video_id = video_id
        
        # 设置输出目录
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path("story_v3") / video_id
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化客户端
        self._init_clients()
        
        logger.info(f"✅ 初始化完成 - 视频ID: {video_id}")
        logger.info(f"📁 输出目录: {self.output_dir}")
    
    def _init_clients(self):
        """初始化API客户端"""
        # Gemini API密钥
        gemini_api_key = os.getenv("NEWAPI_API_KEY", "sk-oFdSWMX8z3cAYYCrGYCcwAupxMdiErcOKBsfi5k0QdRxELCu")
        if not gemini_api_key:
            gemini_api_key = os.getenv("GEMINI_API_KEY", "your_gemini_api_key")
            logger.warning("⚠️ 使用默认Gemini API密钥")
        
        self.gemini_client = GeminiClient(api_key=gemini_api_key)
        logger.info("✅ Gemini客户端初始化完成")
    
    def extract_metadata(self) -> Dict[str, Any]:
        """
        提取视频元数据
        
        Returns:
            元数据字典
        """
        logger.info("📊 开始提取视频元数据...")
        
        # 创建元数据提取器
        metadata_dir = self.output_dir / "metadata"
        extractor = YouTubeMetadataExtractor(
            video_id=self.video_id,
            output_dir=str(metadata_dir)
        )
        
        # 提取所有元数据
        metadata = extractor.extract_all_metadata()
        
        if not metadata:
            logger.error("❌ 无法提取元数据")
            return None
        
        # 确保有必要的数据
        if not metadata.get('video_info'):
            logger.error("❌ 缺少视频信息")
            return None
        
        if not metadata.get('subtitle'):
            logger.error("❌ 缺少字幕")
            return None
        
        logger.info("✅ 元数据提取成功")
        return metadata
    
    def generate_framework(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成故事框架
        
        Args:
            metadata: 视频元数据
            
        Returns:
            框架JSON对象
        """
        logger.info("🎯 开始生成故事框架...")
        
        # 准备输入数据
        video_info = metadata.get('video_info', {})
        comments = metadata.get('comments', [])
        subtitle = metadata.get('subtitle', '')
        
        # 构建输入文本
        input_data = self._build_input_data(video_info, comments, subtitle)
        
        # 加载提示词
        prompt_file = project_root / "prompts" / "framework_generatorv3.md"
        if not prompt_file.exists():
            logger.error(f"❌ 提示词文件不存在: {prompt_file}")
            return None
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # 构建完整提示
        full_prompt = f"{prompt_template}\n{input_data}\n[END_OF_INPUT_DATA]"
        
        # 记录输入日志
        logger.info("📝 构建的输入数据:")
        logger.info("=" * 60)
        logger.info(input_data)
        logger.info("=" * 60)
        
        try:
            # 调用Gemini API
            logger.info("🤖 调用Gemini API生成框架...")
            response = self.gemini_client.generate_content(full_prompt)
            
            if response:
                # 记录输出
                logger.info("📤 Gemini API响应:")
                logger.info("=" * 60)
                print(response)  # 直接打印到控制台
                logger.info("=" * 60)
                
                # 保存原始响应
                response_file = self.output_dir / "framework_response.txt"
                with open(response_file, 'w', encoding='utf-8') as f:
                    f.write(response)
                logger.info(f"💾 原始响应已保存到: {response_file}")
                
                # 尝试解析JSON
                try:
                    # 提取JSON部分
                    import re
                    json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # 尝试直接解析
                        json_str = response
                    
                    framework_json = json.loads(json_str)
                    
                    # 保存JSON
                    json_file = self.output_dir / "framework.json"
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(framework_json, f, ensure_ascii=False, indent=2)
                    logger.info(f"💾 框架JSON已保存到: {json_file}")
                    
                    return framework_json
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ JSON解析失败: {e}")
                    logger.info("返回原始文本响应")
                    return {"raw_response": response}
            else:
                logger.error("❌ Gemini API响应为空")
                return None
                
        except Exception as e:
            logger.error(f"❌ 生成框架失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_input_data(self, video_info: Dict, comments: List, subtitle: str) -> str:
        """
        构建输入数据格式
        
        Args:
            video_info: 视频信息
            comments: 评论列表
            subtitle: 字幕文本
            
        Returns:
            格式化的输入数据
        """
        # 获取标题
        title = video_info.get('title', 'Unknown Title')
        
        # 估算原故事字数
        word_count = len(subtitle) if subtitle else 0
        
        # 获取热门评论（前5条）- 适配新的数据格式
        hot_comments = []
        for comment in comments[:5]:
            # 新格式只有 text_original
            comment_text = comment.get('text_original', comment.get('text', ''))
            if comment_text:
                hot_comments.append(comment_text)
        
        # 构建输入文本
        input_data = "[START_OF_INPUT_DATA]\n"
        input_data += "Original Title\n"
        input_data += f"{title}\n"
        input_data += "Original Reference Word Count\n"
        input_data += f"{word_count}\n"
        input_data += "Hot Comments\n"
        
        for comment in hot_comments:
            input_data += f"{comment}\n"
        
        input_data += "Original Story Text\n"
        input_data += subtitle
        
        return input_data
    
    def run(self):
        """
        运行完整流程
        """
        logger.info(f"🚀 开始处理视频: {self.video_id}")
        
        # 1. 提取元数据
        metadata = self.extract_metadata()
        if not metadata:
            logger.error("❌ 元数据提取失败，终止处理")
            return None
        
        # 2. 生成框架
        framework = self.generate_framework(metadata)
        if not framework:
            logger.error("❌ 框架生成失败")
            return None
        
        # 3. 生成报告
        self.generate_report(metadata, framework)
        
        logger.info(f"✅ 处理完成！结果保存在: {self.output_dir}")
        return framework
    
    def generate_report(self, metadata: Dict[str, Any], framework: Any):
        """
        生成处理报告
        
        Args:
            metadata: 元数据
            framework: 框架数据
        """
        video_info = metadata.get('video_info', {})
        
        report = f"""# YouTube Story Creator V3 Report

## 📌 视频信息
- **视频ID**: {self.video_id}
- **标题**: {video_info.get('title', 'N/A')}
- **频道**: {video_info.get('channel_title', 'N/A')}
- **观看数**: {video_info.get('view_count', 0):,}
- **点赞数**: {video_info.get('like_count', 0):,}

## 📝 字幕信息
- **字幕长度**: {metadata.get('subtitle_length', 0)}字

## 💬 评论分析
- **总评论数**: {len(metadata.get('comments', []))}
- **热门评论数**: {len(metadata.get('top_comments', []))}

## 🎯 框架生成
- **状态**: {'成功' if framework else '失败'}
- **类型**: {'JSON' if isinstance(framework, dict) and 'adaptationAnalysis' in framework else '原始文本'}

## 📁 输出文件
- `metadata/` - 元数据文件夹
  - `video_info.json` - 视频信息
  - `comments.json` - 评论数据
  - `subtitle_*.txt` - 字幕文件
- `framework_response.txt` - 原始AI响应
- `framework.json` - 框架JSON（如果成功解析）

---
Generated by YouTube Story Creator V3
"""
        
        report_file = self.output_dir / "report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"📄 报告已生成: {report_file}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Story Creator V3')
    parser.add_argument('video_id', help='YouTube视频ID')
    parser.add_argument('--output-dir', '-o', help='输出目录')
    
    args = parser.parse_args()
    
    # 创建处理器
    creator = YouTubeStoryCreatorV3(
        video_id=args.video_id,
        output_dir=args.output_dir
    )
    
    # 运行
    framework = creator.run()
    
    if framework:
        print("\n✅ 成功生成框架！")
        if isinstance(framework, dict) and 'adaptationAnalysis' in framework:
            print(f"📖 新故事标题: {framework['adaptationAnalysis'].get('newStoryTitle', 'N/A')}")
            print(f"💡 核心概念: {framework['adaptationAnalysis'].get('coreConcept', 'N/A')}")
    else:
        print("\n❌ 生成失败")


if __name__ == "__main__":
    main()