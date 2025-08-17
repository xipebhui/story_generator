#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube视频元信息提取器
独立脚本用于提取和缓存YouTube视频的元数据
包括：视频详情、评论、字幕等
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入项目模块
from youtube_client import YouTubeAPIClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class YouTubeMetadataExtractor:
    """YouTube视频元信息提取器"""
    
    def __init__(self, video_id: str, output_dir: str = None):
        """
        初始化元信息提取器
        
        Args:
            video_id: YouTube视频ID
            output_dir: 输出目录路径（可选）
        """
        self.video_id = video_id
        
        # 设置输出目录
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path("metadata") / video_id
        
        # 创建目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化YouTube客户端
        self._init_youtube_client()
        
        logger.info(f"✅ 初始化完成 - 视频ID: {video_id}")
        logger.info(f"📁 输出目录: {self.output_dir}")
    
    def _init_youtube_client(self):
        """初始化YouTube API客户端"""
        # YouTube API密钥
        youtube_api_key = os.getenv("YOUTUBE_API_KEY", "AIzaSyCdbljoACNX1Ov3GsU6KRrnwWnCHAyyjVQ")
        
        self.youtube_client = YouTubeAPIClient()
        logger.info("✅ YouTube客户端初始化完成")
    
    def extract_video_info(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        提取视频基本信息
        
        Args:
            force_refresh: 是否强制刷新（忽略缓存）
            
        Returns:
            视频信息字典
        """
        video_info_file = self.output_dir / "video_info.json"
        
        # 检查缓存
        if not force_refresh and video_info_file.exists():
            logger.info("📂 发现视频详情缓存，从文件加载...")
            try:
                with open(video_info_file, 'r', encoding='utf-8') as f:
                    video_info = json.load(f)
                logger.info(f"✅ 视频标题: {video_info['title']}")
                return video_info
            except Exception as e:
                logger.warning(f"⚠️ 加载视频详情失败: {e}")
        
        # 从YouTube获取
        logger.info("📊 从YouTube获取视频详情...")
        try:
            video_details = self.youtube_client.get_video_details([self.video_id])
            if video_details and video_details.get('items'):
                video_item = video_details['items'][0]
                snippet = video_item['snippet']
                statistics = video_item.get('statistics', {})
                
                video_info = {
                    'video_id': self.video_id,
                    'title': snippet['title'],
                    'description': snippet['description'],
                    'channel_id': snippet['channelId'],
                    'channel_title': snippet['channelTitle'],
                    'published_at': snippet['publishedAt'],
                    'tags': snippet.get('tags', []),
                    'category_id': snippet.get('categoryId'),
                    'duration': video_item.get('contentDetails', {}).get('duration'),
                    'view_count': int(statistics.get('viewCount', 0)),
                    'like_count': int(statistics.get('likeCount', 0)),
                    'comment_count': int(statistics.get('commentCount', 0)),
                    'thumbnail': snippet['thumbnails'].get('maxres', 
                                snippet['thumbnails'].get('high', {})).get('url', ''),
                    'thumbnails': snippet['thumbnails']
                }
                
                # 保存到文件
                with open(video_info_file, 'w', encoding='utf-8') as f:
                    json.dump(video_info, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ 视频标题: {video_info['title']}")
                logger.info(f"📊 观看次数: {video_info['view_count']:,}")
                logger.info(f"👍 点赞数: {video_info['like_count']:,}")
                logger.info(f"💬 评论数: {video_info['comment_count']:,}")
                logger.info(f"💾 视频详情已保存到: {video_info_file}")
                
                return video_info
                
        except Exception as e:
            logger.error(f"❌ 获取视频详情失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_comments(self, max_results: int = 20, force_refresh: bool = False) -> Optional[List[Dict]]:
        """
        提取视频评论
        
        Args:
            max_results: 最多获取的评论数
            force_refresh: 是否强制刷新
            
        Returns:
            评论列表
        """
        comments_file = self.output_dir / "comments.json"
        
        # 检查缓存
        if not force_refresh and comments_file.exists():
            logger.info("📂 发现评论缓存，从文件加载...")
            try:
                with open(comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
                logger.info(f"✅ 加载了 {len(comments)} 条评论")
                return comments
            except Exception as e:
                logger.warning(f"⚠️ 加载评论失败: {e}")
        
        # 从YouTube获取
        logger.info(f"💬 从YouTube获取视频评论（最多{max_results}条）...")
        try:
            comments_data = self.youtube_client.get_video_comments(self.video_id, max_results=max_results)
            if comments_data and comments_data.get('items'):
                comments = []
                for item in comments_data['items']:
                    snippet = item['snippet']['topLevelComment']['snippet']
                    comment_info = {
                        'text_original': snippet['textOriginal']
                    }

                    comments.append(comment_info)

                # 保存到文件
                with open(comments_file, 'w', encoding='utf-8') as f:
                    json.dump(comments, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ 获取了 {len(comments)} 条评论")
                logger.info(f"🔥 最热评论: {comments[0]['text_original'][:100]}..." if comments else "无评论")
                logger.info(f"💾 评论已保存到: {comments_file}")
                
                return comments
            else:
                logger.warning("⚠️ 未获取到评论")
                return []
                
        except Exception as e:
            logger.warning(f"⚠️ 获取评论失败（非致命）: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def extract_subtitle(self, language: str = 'zh', force_refresh: bool = False) -> Optional[str]:
        """
        提取视频字幕
        
        Args:
            language: 字幕语言代码（已废弃，保留参数以兼容）
            force_refresh: 是否强制刷新
            
        Returns:
            字幕文本
        """
        subtitle_file = self.output_dir / "subtitle.txt"
        
        # 检查缓存
        if not force_refresh and subtitle_file.exists():
            logger.info(f"📂 发现字幕缓存，从文件加载...")
            try:
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    subtitle_text = f.read()
                logger.info(f"✅ 加载字幕成功，长度: {len(subtitle_text)}字")
                return subtitle_text
            except Exception as e:
                logger.warning(f"⚠️ 加载字幕失败: {e}")
        
        # 从YouTube获取
        logger.info(f"📝 从YouTube获取视频字幕...")
        try:
            # get_video_transcript 不接受 language 参数
            result = self.youtube_client.get_video_transcript(self.video_id)
            if result:
                # get_video_transcript返回的是元组: (relative_path, subtitle_text)
                relative_path, subtitle_text = result
                
                # 保存纯文本字幕
                with open(subtitle_file, 'w', encoding='utf-8') as f:
                    f.write(subtitle_text)
                
                logger.info(f"✅ 获取字幕成功，长度: {len(subtitle_text)}字")
                logger.info(f"💾 字幕已保存到: {subtitle_file}")
                
                return subtitle_text
            else:
                logger.warning(f"⚠️ 未找到{language}语言字幕")
                return None
                
        except Exception as e:
            logger.error(f"❌ 获取字幕失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_all_metadata(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        提取所有元数据
        
        Args:
            force_refresh: 是否强制刷新所有数据
            
        Returns:
            包含所有元数据的字典
        """
        logger.info(f"🔍 开始提取YouTube视频完整元数据: {self.video_id}")
        
        metadata = {
            'video_id': self.video_id,
            'video_info': None,
            'comments': [],
            'subtitle': None,
            'extraction_time': None
        }
        
        # 1. 提取视频信息
        video_info = self.extract_video_info(force_refresh)
        if video_info:
            metadata['video_info'] = video_info
        
        # 2. 提取评论
        comments = self.extract_comments(max_results=20, force_refresh=force_refresh)
        if comments:
            metadata['comments'] = comments
            metadata['top_comments'] = comments[:5]  # 前5条热门评论
        
        # 3. 提取字幕
        subtitle = self.extract_subtitle(language='zh', force_refresh=force_refresh)
        if not subtitle:
            # 尝试英文字幕
            subtitle = self.extract_subtitle(language='en', force_refresh=force_refresh)
        
        if subtitle:
            metadata['subtitle'] = subtitle
            metadata['subtitle_length'] = len(subtitle)
        
        # 4. 添加提取时间
        from datetime import datetime
        metadata['extraction_time'] = datetime.now().isoformat()
        
        # 5. 保存完整元数据
        metadata_file = self.output_dir / "metadata_complete.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            # subtitle可能很长，单独处理
            save_data = metadata.copy()
            if 'subtitle' in save_data and save_data['subtitle']:
                save_data['subtitle'] = save_data['subtitle'][:1000] + '...(truncated)'
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        logger.info("✅ 元数据提取完成！")
        logger.info(f"📊 视频: {metadata['video_info']['title'] if metadata['video_info'] else 'N/A'}")
        logger.info(f"💬 评论数: {len(metadata['comments'])}")
        logger.info(f"📝 字幕长度: {metadata.get('subtitle_length', 0)}字")
        logger.info(f"💾 完整元数据已保存到: {metadata_file}")
        
        return metadata
    


def main():
    """主函数 - 命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube视频元数据提取器')
    parser.add_argument('video_id', help='YouTube视频ID')
    parser.add_argument('--output-dir', '-o', help='输出目录路径')
    parser.add_argument('--force-refresh', '-f', action='store_true', 
                       help='强制刷新所有数据（忽略缓存）')
    parser.add_argument('--comments', '-c', type=int, default=20,
                       help='要获取的评论数量（默认20）')
    parser.add_argument('--language', '-l', default='zh',
                       help='字幕语言代码（默认zh）')
    parser.add_argument('--report', '-r', action='store_true',
                       help='生成摘要报告')
    
    args = parser.parse_args()
    
    # 创建提取器
    extractor = YouTubeMetadataExtractor(
        video_id=args.video_id,
        output_dir=args.output_dir
    )
    
    # 提取所有元数据
    metadata = extractor.extract_all_metadata(force_refresh=args.force_refresh)

    
    print(f"\n✅ 完成！所有文件已保存到: {extractor.output_dir}")


if __name__ == "__main__":
    main()