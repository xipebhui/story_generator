#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量YouTube视频元信息提取器
支持从视频列表批量提取元数据并生成汇总报告
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from youtube_metadata_extractor import YouTubeMetadataExtractor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class BatchMetadataExtractor:
    """批量YouTube视频元信息提取器"""
    
    def __init__(self, output_base_dir: str = "batch_metadata"):
        """
        初始化批量提取器
        
        Args:
            output_base_dir: 输出基础目录
        """
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建批次目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.batch_dir = self.output_base_dir / f"batch_{timestamp}"
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = []
        
        logger.info(f"📁 批次输出目录: {self.batch_dir}")
    
    def extract_video(self, video_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        提取单个视频的元数据
        
        Args:
            video_id: YouTube视频ID
            force_refresh: 是否强制刷新
            
        Returns:
            提取结果
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🎬 处理视频: {video_id}")
        
        result = {
            'video_id': video_id,
            'status': 'pending',
            'error': None,
            'metadata': None
        }
        
        try:
            # 创建提取器
            video_dir = self.batch_dir / video_id
            extractor = YouTubeMetadataExtractor(
                video_id=video_id,
                output_dir=str(video_dir)
            )
            
            # 提取元数据
            metadata = extractor.extract_all_metadata(force_refresh=force_refresh)
            
            # 生成报告
            report = extractor.generate_summary_report(metadata)
            
            result['status'] = 'success'
            result['metadata'] = metadata
            
            logger.info(f"✅ 视频 {video_id} 处理成功")
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            logger.error(f"❌ 视频 {video_id} 处理失败: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def extract_from_list(self, video_ids: List[str], 
                         force_refresh: bool = False,
                         delay_seconds: int = 2) -> List[Dict[str, Any]]:
        """
        从视频ID列表批量提取
        
        Args:
            video_ids: 视频ID列表
            force_refresh: 是否强制刷新
            delay_seconds: 每个视频之间的延迟（秒）
            
        Returns:
            所有提取结果
        """
        logger.info(f"📋 开始批量提取 {len(video_ids)} 个视频")
        
        for i, video_id in enumerate(video_ids, 1):
            logger.info(f"\n进度: {i}/{len(video_ids)}")
            
            result = self.extract_video(video_id, force_refresh)
            self.results.append(result)
            
            # 添加延迟避免API限制
            if i < len(video_ids):
                logger.info(f"⏸️ 等待 {delay_seconds} 秒...")
                time.sleep(delay_seconds)
        
        # 保存批次结果
        self._save_batch_results()
        
        # 生成汇总报告
        self._generate_batch_report()
        
        return self.results
    
    def extract_from_file(self, file_path: str, 
                         force_refresh: bool = False,
                         delay_seconds: int = 2) -> List[Dict[str, Any]]:
        """
        从文件读取视频ID列表并批量提取
        
        Args:
            file_path: 包含视频ID的文件路径（每行一个ID）
            force_refresh: 是否强制刷新
            delay_seconds: 延迟秒数
            
        Returns:
            所有提取结果
        """
        video_ids = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 支持URL格式
                    if 'youtube.com/watch?v=' in line:
                        video_id = line.split('v=')[1].split('&')[0]
                    elif 'youtu.be/' in line:
                        video_id = line.split('youtu.be/')[1].split('?')[0]
                    else:
                        video_id = line
                    
                    video_ids.append(video_id)
        
        logger.info(f"📄 从文件加载了 {len(video_ids)} 个视频ID")
        
        return self.extract_from_list(video_ids, force_refresh, delay_seconds)
    
    def _save_batch_results(self):
        """保存批次结果"""
        results_file = self.batch_dir / "batch_results.json"
        
        # 准备保存的数据（简化版）
        save_data = []
        for result in self.results:
            item = {
                'video_id': result['video_id'],
                'status': result['status'],
                'error': result['error']
            }
            
            if result['status'] == 'success' and result['metadata']:
                metadata = result['metadata']
                video_info = metadata.get('video_info', {})
                item['title'] = video_info.get('title', 'N/A')
                item['channel'] = video_info.get('channel_title', 'N/A')
                item['views'] = video_info.get('view_count', 0)
                item['likes'] = video_info.get('like_count', 0)
                item['comments_count'] = len(metadata.get('comments', []))
                item['subtitle_length'] = metadata.get('subtitle_length', 0)
            
            save_data.append(item)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 批次结果已保存: {results_file}")
    
    def _generate_batch_report(self):
        """生成批次汇总报告"""
        report_file = self.batch_dir / "batch_report.md"
        
        # 统计信息
        total = len(self.results)
        success = sum(1 for r in self.results if r['status'] == 'success')
        failed = sum(1 for r in self.results if r['status'] == 'failed')
        
        report = f"""# 批量YouTube视频元数据提取报告

## 📊 汇总统计

- **处理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **总视频数**: {total}
- **成功**: {success}
- **失败**: {failed}
- **成功率**: {(success/total*100):.1f}%

## 📋 视频列表

| # | 视频ID | 标题 | 频道 | 观看数 | 点赞数 | 评论数 | 字幕长度 | 状态 |
|---|--------|------|------|--------|--------|--------|----------|------|
"""
        
        for i, result in enumerate(self.results, 1):
            video_id = result['video_id']
            status = "✅" if result['status'] == 'success' else "❌"
            
            if result['status'] == 'success' and result['metadata']:
                metadata = result['metadata']
                video_info = metadata.get('video_info', {})
                title = video_info.get('title', 'N/A')[:30] + '...' if len(video_info.get('title', '')) > 30 else video_info.get('title', 'N/A')
                channel = video_info.get('channel_title', 'N/A')[:20]
                views = f"{video_info.get('view_count', 0):,}"
                likes = f"{video_info.get('like_count', 0):,}"
                comments = len(metadata.get('comments', []))
                subtitle_len = metadata.get('subtitle_length', 0)
                
                report += f"| {i} | {video_id} | {title} | {channel} | {views} | {likes} | {comments} | {subtitle_len} | {status} |\n"
            else:
                error = result.get('error', 'Unknown error')[:30]
                report += f"| {i} | {video_id} | Error: {error} | - | - | - | - | - | {status} |\n"
        
        # 添加失败详情
        if failed > 0:
            report += "\n## ❌ 失败详情\n\n"
            for result in self.results:
                if result['status'] == 'failed':
                    report += f"- **{result['video_id']}**: {result.get('error', 'Unknown error')}\n"
        
        # 添加热门视频分析
        if success > 0:
            report += "\n## 🔥 热门视频 (按观看数)\n\n"
            
            successful_results = [r for r in self.results if r['status'] == 'success' and r['metadata']]
            sorted_results = sorted(
                successful_results,
                key=lambda x: x['metadata']['video_info'].get('view_count', 0),
                reverse=True
            )[:5]
            
            for i, result in enumerate(sorted_results, 1):
                video_info = result['metadata']['video_info']
                report += f"{i}. **{video_info['title'][:50]}**\n"
                report += f"   - 频道: {video_info['channel_title']}\n"
                report += f"   - 观看: {video_info.get('view_count', 0):,}\n"
                report += f"   - 点赞: {video_info.get('like_count', 0):,}\n\n"
        
        report += f"""
## 📁 输出目录

所有提取的数据已保存到:
`{self.batch_dir}`

每个视频的详细数据在各自的子目录中。

---
*Generated by Batch YouTube Metadata Extractor*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"📄 批次报告已生成: {report_file}")
        
        return report


def main():
    """主函数 - 命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='批量YouTube视频元数据提取器')
    
    # 输入方式（互斥）
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--video-ids', '-v', nargs='+', 
                            help='视频ID列表（空格分隔）')
    input_group.add_argument('--file', '-f', 
                            help='包含视频ID的文件路径（每行一个）')
    
    parser.add_argument('--output-dir', '-o', default='batch_metadata',
                       help='输出基础目录（默认: batch_metadata）')
    parser.add_argument('--force-refresh', '-r', action='store_true',
                       help='强制刷新所有数据')
    parser.add_argument('--delay', '-d', type=int, default=2,
                       help='每个视频之间的延迟秒数（默认: 2）')
    
    args = parser.parse_args()
    
    # 创建批量提取器
    extractor = BatchMetadataExtractor(output_base_dir=args.output_dir)
    
    # 执行提取
    if args.video_ids:
        results = extractor.extract_from_list(
            video_ids=args.video_ids,
            force_refresh=args.force_refresh,
            delay_seconds=args.delay
        )
    else:
        results = extractor.extract_from_file(
            file_path=args.file,
            force_refresh=args.force_refresh,
            delay_seconds=args.delay
        )
    
    # 打印汇总
    success = sum(1 for r in results if r['status'] == 'success')
    failed = sum(1 for r in results if r['status'] == 'failed')
    
    print(f"\n{'='*60}")
    print(f"✅ 批量提取完成！")
    print(f"📊 成功: {success}, 失败: {failed}")
    print(f"📁 结果已保存到: {extractor.batch_dir}")


if __name__ == "__main__":
    main()