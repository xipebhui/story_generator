#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频下载和发布Pipeline
从抖音创作者ID列表获取视频，下载最新视频及封面，然后发布到YouTube
"""

import logging
import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from pipelines.base_pipeline import BasePipeline
from pipelines.pipeline_context import PipelineContext

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)


class DouyinDownloadPublishPipeline(BasePipeline):
    """
    抖音视频下载和发布Pipeline
    
    执行流程：
    1. fetch_creator_videos: 获取创作者视频列表
    2. download_media: 下载视频和封面
    3. publish_to_youtube: 发布视频到YouTube
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Pipeline
        
        Args:
            config: Pipeline配置，包含：
                - api_base_url: API基础URL (默认: http://localhost:51084)
                - max_videos_per_creator: 每个创作者获取的最大视频数 (默认: 1)
                - download_timeout: 下载超时时间（秒）(默认: 300)
                - storage_base_path: 存储基础路径 (默认: douyin_videos)
                - cache_dir: 缓存目录，用于去重检查 (默认: douyin_cache)
        """
        super().__init__(config)
        
        # 设置默认配置
        self.api_base_url = self.config.get('api_base_url', 'http://localhost:51084')
        self.max_videos = self.config.get('max_videos_per_creator', 1)
        self.download_timeout = self.config.get('download_timeout', 300)
        self.storage_base = Path(self.config.get('storage_base_path', 'douyin_videos'))
        self.cache_dir = Path(self.config.get('cache_dir', 'douyin_cache'))
        
        # 确保存储目录存在
        self.storage_base.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Pipeline
        
        Args:
            params: 执行参数
                - creator_ids: 创作者ID列表 (必需)
                - account_id: 发布账号ID (必需)
                - max_videos_per_creator: 每个创作者获取的视频数 (可选，默认使用配置)
        
        Returns:
            执行结果
        """
        self.start_time = datetime.now()
        
        # 验证参数
        is_valid, error_msg = self.validate_params(params, ['creator_ids', 'account_id'])
        if not is_valid:
            return self.handle_error(Exception(error_msg), 'validation')
        
        # 创建Pipeline上下文
        context = PipelineContext(params)
        stages_results = []
        
        try:
            # 阶段1: 获取视频信息（包含去重检查）
            videos_to_process = await self.fetch_creator_videos(
                context, 
                params['creator_ids']
            )
            
            stages_results.append({
                'name': 'fetch_creator_videos',
                'success': True,
                'data': {'videos_found': len(videos_to_process)}
            })
            
            if not videos_to_process:
                return {
                    'success': False,
                    'error': 'No unprocessed videos found',
                    'stages': stages_results
                }
            
            # 阶段2: 下载媒体文件
            downloaded_videos = await self.download_media(
                context,
                videos_to_process
            )
            
            stages_results.append({
                'name': 'download_media',
                'success': True,
                'data': {'videos_downloaded': len(downloaded_videos)}
            })
            
            if not downloaded_videos:
                return {
                    'success': False,
                    'error': 'No videos downloaded successfully',
                    'stages': stages_results
                }
            
            # 阶段3: 发布视频到YouTube
            publish_results = await self.publish_to_youtube(
                context,
                downloaded_videos,
                params['account_id']
            )
            
            stages_results.append({
                'name': 'publish_to_youtube',
                'success': True,
                'data': {
                    'videos_published': len([r for r in publish_results if r['success']])
                }
            })
            
            self.end_time = datetime.now()
            
            return {
                'success': True,
                'data': {
                    'total_processed': len(videos_to_process),
                    'total_downloaded': len(downloaded_videos),
                    'total_published': len([r for r in publish_results if r['success']]),
                    'publish_results': publish_results
                },
                'stages': stages_results,
                'metadata': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': self.end_time.isoformat(),
                    'duration': (self.end_time - self.start_time).total_seconds()
                }
            }
            
        except Exception as e:
            return self.handle_error(e, 'execution')
    
    async def fetch_creator_videos(self, context: PipelineContext, creator_ids: List[str]) -> List[Dict[str, Any]]:
        """
        获取创作者视频列表（包含去重检查）
        
        Args:
            context: Pipeline上下文
            creator_ids: 创作者ID列表
        
        Returns:
            待处理的视频列表（已过滤掉已处理的视频）
        """
        stage_name = 'fetch_creator_videos'
        logger.info(f"Starting {stage_name} for {len(creator_ids)} creators")
        logger.info(f"Creator IDs: {creator_ids}")
        
        videos_to_process = []
        max_videos = context.params.get('max_videos_per_creator', self.max_videos)
        logger.info(f"Max videos per creator: {max_videos}")
        
        async with aiohttp.ClientSession() as session:
            for creator_id in creator_ids:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing creator: {creator_id}")
                
                try:
                    # 调用API获取视频列表
                    url = f"{self.api_base_url}/api/douyin/web/fetch_user_post_videos"
                    params = {
                        'sec_user_id': creator_id,
                        'max_cursor': 0,
                        'count': max_videos
                    }
                    
                    logger.info(f"API URL: {url}")
                    logger.info(f"Request params: {params}")
                    
                    async with session.get(url, params=params, timeout=30) as response:
                        logger.info(f"Response status: {response.status}")
                        if response.status != 200:
                            response_text = await response.text()
                            logger.error(f"Failed to fetch videos for {creator_id}: {response.status}")
                            logger.error(f"Response: {response_text[:500]}")
                            continue
                        
                        data = await response.json()
                        logger.info(f"Response received, parsing data..., data = {data.get('data', {})}")

                        # 打印响应数据结构
                        if 'aweme_list' in data:
                            logger.info(f"Found aweme_list with {len(data.get('aweme_list', []))} items")
                        else:
                            logger.warning(f"No aweme_list in response. Keys: {list(data.keys())}")
                        
                        # 解析视频数据
                        aweme_list = data.get('data').get('aweme_list', [])
                        logger.info(f"Processing {len(aweme_list[:max_videos])} videos from aweme_list")
                        
                        for idx, video in enumerate(aweme_list[:max_videos]):
                            logger.info(f"\n  Video {idx + 1}/{min(len(aweme_list), max_videos)}:")
                            
                            # 打印视频基本信息
                            logger.debug(f"  - aweme_id: {video.get('aweme_id', 'N/A')}")
                            logger.debug(f"  - desc: {video.get('desc', '')[:50]}...")
                            
                            video_info = self.extract_video_info(video)
                            if video_info:
                                logger.info(f"  - Extracted video info for: {video_info['aweme_id']}")
                                logger.debug(f"    - Share URL: {video_info.get('share_url', 'N/A')}")
                                logger.debug(f"    - Has video URL: {'video_url' in video_info}")
                                logger.debug(f"    - Has cover URL: {'cover_url' in video_info}")
                                
                                # 检查视频是否已处理（去重）
                                is_processed = self._is_video_processed(video_info['aweme_id'], creator_id)
                                logger.info(f"  - Processed check for {video_info['aweme_id']}: {is_processed}")
                                
                                if not is_processed:
                                    video_info['creator_id'] = creator_id
                                    videos_to_process.append(video_info)
                                    logger.info(f"  ✅ Added unprocessed video: {video_info['aweme_id']}")
                                else:
                                    logger.info(f"  ⏭️  Video already processed: {video_info['aweme_id']}")
                            else:
                                logger.warning(f"  ❌ Failed to extract video info for video at index {idx}")
                                
                except asyncio.TimeoutError:
                    logger.error(f"Timeout fetching videos for creator {creator_id}")
                    continue
                except Exception as e:
                    logger.error(f"Error fetching videos for creator {creator_id}: {e}")
                    logger.exception("Detailed error:")
                    continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Total unprocessed videos found: {len(videos_to_process)}")
        return videos_to_process
    
    def _is_video_processed(self, aweme_id: str, creator_id: str) -> bool:
        """
        检查视频是否已处理（参考pipeline_stages_video_fetch.py的逻辑）
        
        Args:
            aweme_id: 抖音视频ID
            creator_id: 创作者ID
        
        Returns:
            bool: 是否已处理
        """
        try:
            logger.debug(f"Checking if video {aweme_id} is processed...")
            
            # 检查多个可能的缓存位置
            possible_paths = [
                # 缓存标记文件
                self.cache_dir / f"{creator_id}_{aweme_id}.done",
                # 下载的视频文件
                self.storage_base / creator_id / aweme_id / f"{aweme_id}.mp4",
                # 发布记录文件
                self.cache_dir / f"published_{aweme_id}.json"
            ]
            
            logger.debug(f"Cache dir: {self.cache_dir}")
            logger.debug(f"Storage base: {self.storage_base}")
            
            for path in possible_paths:
                logger.debug(f"  Checking: {path}")
                if path.exists():
                    logger.debug(f"  ✅ Found processed cache: {path}")
                    return True
                else:
                    logger.debug(f"  ❌ Not found: {path}")
            
            logger.debug(f"Video {aweme_id} is not processed")
            return False
            
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return False
    
    def extract_video_info(self, video_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从API响应中提取视频信息
        
        Args:
            video_data: 视频数据
        
        Returns:
            提取的视频信息
        """
        try:
            logger.debug("Extracting video info from data...")
            
            # 提取基本信息
            aweme_id = video_data.get('aweme_id')
            if not aweme_id:
                logger.warning("No aweme_id found in video data")
                return None
                
            video_info = {
                'aweme_id': aweme_id,
                'desc': video_data.get('desc', ''),
                'create_time': video_data.get('create_time'),
            }
            
            logger.debug(f"Basic info - aweme_id: {aweme_id}")
            
            # 提取视频URL
            video_obj = video_data.get('video', {})
            if not video_obj:
                logger.warning(f"No video object found for {aweme_id}")
                logger.debug(f"Available keys in video_data: {list(video_data.keys())}")
            
            # 优先获取无水印URL
            play_addr = video_obj.get('play_addr', {})
            url_list = play_addr.get('url_list', [])
            
            logger.debug(f"play_addr url_list count: {len(url_list)}")
            
            if url_list:
                # 选择第一个可用的URL
                video_info['video_url'] = url_list[0]
                logger.debug(f"Using play_addr URL: {url_list[0][:50]}...")
            else:
                # 尝试获取下载地址
                download_addr = video_obj.get('download_addr', {})
                url_list = download_addr.get('url_list', [])
                logger.debug(f"download_addr url_list count: {len(url_list)}")
                
                if url_list:
                    video_info['video_url'] = url_list[0]
                    logger.debug(f"Using download_addr URL: {url_list[0][:50]}...")
                else:
                    logger.warning(f"No video URL found for {aweme_id}")
            
            # 提取封面图片
            cover = video_obj.get('cover', {})
            cover_url_list = cover.get('url_list', [])
            logger.debug(f"Cover url_list count: {len(cover_url_list)}")
            
            if cover_url_list:
                video_info['cover_url'] = cover_url_list[0]
                logger.debug(f"Cover URL: {cover_url_list[0][:50]}...")
            else:
                logger.warning(f"No cover URL found for {aweme_id}")
            
            # 提取分享URL（用于下载API）
            share_info = video_data.get('share_info', {})
            share_url = share_info.get('share_url', '')
            
            if not share_url:
                # 构造分享URL
                share_url = f"https://www.iesdouyin.com/share/video/{aweme_id}/"
                logger.debug(f"Constructed share URL: {share_url}")
            else:
                logger.debug(f"Found share URL: {share_url}")
                
            video_info['share_url'] = share_url
            
            logger.debug(f"Successfully extracted video info for {aweme_id}")
            return video_info
            
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            logger.exception("Detailed error:")
            return None
    
    async def download_media(self, context: PipelineContext, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        下载视频和封面文件
        
        Args:
            context: Pipeline上下文
            videos: 视频信息列表
        
        Returns:
            成功下载的视频列表
        """
        stage_name = 'download_media'
        logger.info(f"Starting {stage_name} for {len(videos)} videos")
        
        downloaded_videos = []
        
        async with aiohttp.ClientSession() as session:
            for video in videos:
                try:
                    # 创建存储目录
                    video_dir = self.storage_base / video['creator_id'] / video['aweme_id']
                    video_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 下载视频
                    video_path = await self.download_video(
                        session, 
                        video['share_url'],
                        video_dir / f"{video['aweme_id']}.mp4"
                    )
                    
                    # 下载封面
                    cover_path = None
                    if video.get('cover_url'):
                        cover_path = await self.download_cover(
                            session,
                            video['cover_url'],
                            video_dir / f"{video['aweme_id']}_cover.jpg"
                        )
                    
                    # 更新视频信息
                    video['video_path'] = str(video_path)
                    video['cover_path'] = str(cover_path) if cover_path else None
                    video['download_time'] = datetime.now().isoformat()
                    
                    # 创建下载成功的缓存标记
                    cache_file = self.cache_dir / f"{video['creator_id']}_{video['aweme_id']}.done"
                    cache_file.write_text(datetime.now().isoformat())
                    
                    downloaded_videos.append(video)
                    logger.info(f"Downloaded video {video['aweme_id']}")
                    
                except Exception as e:
                    logger.error(f"Error downloading video {video.get('aweme_id')}: {e}")
                    continue
        
        # 阶段结果已在execute方法中处理
        
        return downloaded_videos
    
    async def download_video(self, session: aiohttp.ClientSession, share_url: str, save_path: Path) -> Path:
        """
        下载视频文件（默认不保留水印）
        
        Args:
            session: HTTP会话
            share_url: 视频分享URL
            save_path: 保存路径
        
        Returns:
            保存的文件路径
        """
        # 使用下载API，默认不保留水印
        download_url = f"{self.api_base_url}/api/download"
        params = {
            'url': share_url,
            'prefix': 'true',
            'with_watermark': 'false'  # 默认不保留水印
        }
        
        async with session.get(download_url, params=params, timeout=self.download_timeout) as response:
            if response.status != 200:
                raise Exception(f"Download failed with status {response.status}")
            
            # 保存视频文件
            with open(save_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
        
        return save_path
    
    async def download_cover(self, session: aiohttp.ClientSession, cover_url: str, save_path: Path) -> Path:
        """
        下载封面图片
        
        Args:
            session: HTTP会话
            cover_url: 封面URL
            save_path: 保存路径
        
        Returns:
            保存的文件路径
        """
        async with session.get(cover_url) as response:
            if response.status != 200:
                raise Exception(f"Cover download failed with status {response.status}")
            
            # 保存封面文件
            with open(save_path, 'wb') as f:
                f.write(await response.read())
        
        return save_path
    
    async def publish_to_youtube(self, context: PipelineContext, videos: List[Dict[str, Any]], account_id: str) -> List[Dict[str, Any]]:
        """
        发布视频到YouTube
        
        Args:
            context: Pipeline上下文
            videos: 视频信息列表
            account_id: YouTube账号ID
        
        Returns:
            发布结果列表
        """
        stage_name = 'publish_to_youtube'
        logger.info(f"Starting {stage_name} for {len(videos)} videos")
        
        # 导入发布服务
        from publish_service import get_publish_service
        from database import get_db_manager, PipelineTask
        import uuid
        
        publish_service = get_publish_service()
        db = get_db_manager()
        publish_results = []
        
        for video in videos:
            try:
                # 为每个视频创建一个临时的Pipeline任务记录
                task_id = f"douyin_{video['aweme_id']}_{uuid.uuid4().hex[:8]}"
                
                # 创建Pipeline任务记录（publish_service需要）
                with db.get_session() as session:
                    pipeline_task = PipelineTask(
                        task_id=task_id,
                        creator_id=video['creator_id'],
                        video_id=video['aweme_id'],
                        video_path=video['video_path'],
                        thumbnail_path=video.get('cover_path'),
                        status='completed',  # 标记为已完成，以便可以发布
                        youtube_metadata=json.dumps({
                            'title': video['desc'][:100] if video['desc'] else f"Video {video['aweme_id']}",
                            'description': video['desc'],
                            'tags': []
                        })
                    )
                    session.add(pipeline_task)
                    session.commit()
                
                # 创建发布任务
                publish_task = publish_service.create_publish_task(
                    task_id=task_id,
                    account_id=account_id,
                    video_title=video['desc'][:100] if video['desc'] else f"Video {video['aweme_id']}",
                    video_description=video['desc'],
                    thumbnail_path=video.get('cover_path'),
                    privacy_status='public'
                )
                
                if publish_task:
                    # 执行上传
                    upload_result = await publish_service.upload_to_youtube_async(publish_task['publish_id'])
                    
                    # 如果发布成功，创建缓存标记
                    if upload_result['success']:
                        cache_file = self.cache_dir / f"published_{video['aweme_id']}.json"
                        with open(cache_file, 'w') as f:
                            json.dump({
                                'aweme_id': video['aweme_id'],
                                'creator_id': video['creator_id'],
                                'youtube_url': upload_result.get('video_url'),
                                'published_at': datetime.now().isoformat()
                            }, f)
                    
                    publish_results.append({
                        'aweme_id': video['aweme_id'],
                        'success': upload_result['success'],
                        'youtube_url': upload_result.get('video_url'),
                        'error': upload_result.get('error')
                    })
                else:
                    publish_results.append({
                        'aweme_id': video['aweme_id'],
                        'success': False,
                        'error': '创建发布任务失败'
                    })
                
            except Exception as e:
                logger.error(f"Error publishing video {video['aweme_id']}: {e}")
                publish_results.append({
                    'aweme_id': video['aweme_id'],
                    'success': False,
                    'error': str(e)
                })
        
        logger.info(f"Published {len([r for r in publish_results if r['success']])} videos successfully")
        return publish_results