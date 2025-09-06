#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频下载和发布Pipeline（数据库版本）
从抖音创作者ID列表获取视频，使用数据库跟踪处理状态，下载最新视频及封面，然后发布到YouTube
"""

import logging
import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pipelines.base_pipeline import BasePipeline
from pipelines.pipeline_context import PipelineContext

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)


class DouyinDownloadPublishPipeline(BasePipeline):
    """
    抖音视频下载和发布Pipeline（数据库版本）
    
    执行流程：
    1. fetch_creator_videos: 从所有创作者获取视频列表，选择最新的
    2. download_media: 下载视频和封面
    3. publish_to_youtube: 发布视频到YouTube
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Pipeline
        
        Args:
            config: Pipeline配置，包含：
                - api_base_url: API基础URL (默认: http://localhost:51084)
                - max_videos_per_creator: 每个创作者获取的最大视频数 (默认: 10)
                - download_timeout: 下载超时时间（秒）(默认: 300)
                - storage_base_path: 存储基础路径 (默认: douyin_videos)
                - cache_dir: 缓存目录，用于去重检查 (默认: douyin_cache)
                - use_database: 是否使用数据库跟踪状态 (默认: True)
        """
        super().__init__(config)
        
        # 设置默认配置
        self.api_base_url = self.config.get('api_base_url', 'http://localhost:51084')
        self.max_videos = self.config.get('max_videos_per_creator', 10)
        self.download_timeout = self.config.get('download_timeout', 300)
        self.storage_base = Path(self.config.get('storage_base_path', 'douyin_videos'))
        self.cache_dir = Path(self.config.get('cache_dir', 'douyin_cache'))
        self.use_database = self.config.get('use_database', True)
        
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
            # 阶段1: 获取最新的未处理视频
            video_to_process = await self.fetch_latest_unprocessed_video(
                context, 
                params['creator_ids']
            )
            
            stages_results.append({
                'name': 'fetch_latest_video',
                'success': video_to_process is not None,
                'data': {'video_found': video_to_process is not None}
            })
            
            if not video_to_process:
                return {
                    'success': False,
                    'error': 'No unprocessed videos found',
                    'stages': stages_results
                }
            
            # 阶段2: 下载媒体文件
            download_result = await self.download_media(
                context,
                video_to_process
            )
            
            stages_results.append({
                'name': 'download_media',
                'success': download_result is not None,
                'data': {'video_downloaded': download_result is not None}
            })
            
            if not download_result:
                return {
                    'success': False,
                    'error': 'Failed to download video',
                    'stages': stages_results
                }
            
            # 阶段3: 发布视频到YouTube
            publish_result = await self.publish_to_youtube(
                context,
                download_result,
                params['account_id']
            )
            
            stages_results.append({
                'name': 'publish_to_youtube',
                'success': publish_result.get('success', False),
                'data': publish_result
            })
            
            self.end_time = datetime.now()
            
            return {
                'success': True,
                'data': {
                    'video_processed': video_to_process,
                    'download_result': download_result,
                    'publish_result': publish_result
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
    
    async def fetch_latest_unprocessed_video(self, context: PipelineContext, creator_ids: List[str]) -> Optional[Dict[str, Any]]:
        """
        获取所有创作者中最新的未处理视频
        
        Args:
            context: Pipeline上下文
            creator_ids: 创作者ID列表
        
        Returns:
            最新的未处理视频信息，如果没有则返回None
        """
        stage_name = 'fetch_latest_unprocessed_video'
        logger.info(f"[FETCH_DOUYIN] Starting {stage_name} for {len(creator_ids)} creators")
        logger.info(f"[FETCH_DOUYIN] Creator IDs: {creator_ids}")
        
        if self.use_database:
            from services.video_processing_service import VideoProcessingService
            from models.video_processing import Platform
            from database import get_db_url
            
            # 创建数据库连接
            engine = create_engine(get_db_url())
            Session = sessionmaker(bind=engine)
            db_session = Session()
            
            try:
                service = VideoProcessingService(db_session)
                
                # 首先从数据库获取未处理的视频
                logger.info("[FETCH_DOUYIN] Checking database for unprocessed videos...")
                unprocessed_video = service.get_latest_unprocessed_video(
                    platform='douyin',
                    creator_list=creator_ids
                )
                
                if unprocessed_video:
                    logger.info(f"[FETCH_DOUYIN] Found unprocessed video in DB: {unprocessed_video.video_id}")
                    return {
                        'aweme_id': unprocessed_video.video_id,
                        'creator_id': unprocessed_video.creator_id,
                        'desc': unprocessed_video.video_title,
                        'share_url': unprocessed_video.video_url or f"https://www.iesdouyin.com/share/video/{unprocessed_video.video_id}/",
                        'from_database': True
                    }
                
                logger.info("[FETCH_DOUYIN] No unprocessed videos in DB, fetching from Douyin...")
                
                # 收集所有创作者的所有视频
                all_videos = []
                max_videos = context.params.get('max_videos_per_creator', self.max_videos)
                
                async with aiohttp.ClientSession() as session:
                    for creator_id in creator_ids:
                        logger.info(f"[FETCH_DOUYIN] Checking creator: {creator_id}")
                        
                        try:
                            # 调用API获取视频列表
                            url = f"{self.api_base_url}/api/douyin/web/fetch_user_post_videos"
                            params = {
                                'sec_user_id': creator_id,
                                'max_cursor': 0,
                                'count': max_videos
                            }
                            
                            async with session.get(url, params=params, timeout=30) as response:
                                if response.status != 200:
                                    logger.error(f"Failed to fetch videos for {creator_id}: {response.status}")
                                    continue
                                
                                data = await response.json()
                                aweme_list = data.get('data', {}).get('aweme_list', [])
                                logger.info(f"[FETCH_DOUYIN] Found {len(aweme_list)} videos for creator {creator_id}")
                                
                                for video in aweme_list[:max_videos]:
                                    video_info = self.extract_video_info(video)
                                    if video_info:
                                        # 检查数据库中是否已存在
                                        existing = service.get_video_status('douyin', creator_id, video_info['aweme_id'])
                                        
                                        if not existing:
                                            # 创建新记录
                                            published_at = datetime.fromtimestamp(
                                                video.get('create_time', 0), 
                                                tz=timezone.utc
                                            ) if video.get('create_time') else datetime.now(timezone.utc)
                                            
                                            video_status = service.create_or_update_video(
                                                platform='douyin',
                                                creator_id=creator_id,
                                                video_id=video_info['aweme_id'],
                                                video_title=video_info.get('desc', ''),
                                                video_url=video_info.get('share_url'),
                                                published_at=published_at,
                                                processing_stage='fetched',
                                                account_id=context.params.get('account_id')
                                            )
                                            logger.info(f"[FETCH_DOUYIN] Added new video to DB: {video_info['aweme_id']}")
                                            
                                            video_info['creator_id'] = creator_id
                                            video_info['published_at'] = published_at.isoformat()
                                            all_videos.append(video_info)
                                            
                                        elif not existing.is_completed:
                                            # 如果存在但未完成，也加入列表
                                            video_info['creator_id'] = creator_id
                                            video_info['published_at'] = existing.published_at.isoformat() if existing.published_at else ''
                                            all_videos.append(video_info)
                                
                        except Exception as e:
                            logger.error(f"Error fetching videos for creator {creator_id}: {e}")
                            continue
                
                # 按发布时间排序，选择最新的
                if all_videos:
                    logger.info(f"[FETCH_DOUYIN] Found {len(all_videos)} total unprocessed videos")
                    all_videos.sort(key=lambda x: x.get('published_at', ''), reverse=True)
                    
                    newest_video = all_videos[0]
                    logger.info(f"[FETCH_DOUYIN] Selected newest video: {newest_video['aweme_id']} from {newest_video['creator_id']}")
                    
                    # 更新context参数
                    context.params['video_id'] = newest_video['aweme_id']
                    context.params['creator_id'] = newest_video['creator_id']
                    
                    return newest_video
                
                logger.info("[FETCH_DOUYIN] No unprocessed videos found")
                return None
                
            finally:
                db_session.close()
        
        else:
            # 不使用数据库，使用原有的文件检查逻辑
            logger.info("[FETCH_DOUYIN] Database disabled, using file-based checking")
            return await self._fetch_latest_video_file_based(context, creator_ids)
    
    async def _fetch_latest_video_file_based(self, context: PipelineContext, creator_ids: List[str]) -> Optional[Dict[str, Any]]:
        """
        基于文件系统的视频获取（原有逻辑）
        """
        all_videos = []
        max_videos = context.params.get('max_videos_per_creator', self.max_videos)
        
        async with aiohttp.ClientSession() as session:
            for creator_id in creator_ids:
                try:
                    url = f"{self.api_base_url}/api/douyin/web/fetch_user_post_videos"
                    params = {
                        'sec_user_id': creator_id,
                        'max_cursor': 0,
                        'count': max_videos
                    }
                    
                    async with session.get(url, params=params, timeout=30) as response:
                        if response.status != 200:
                            continue
                        
                        data = await response.json()
                        aweme_list = data.get('data', {}).get('aweme_list', [])
                        
                        for video in aweme_list[:max_videos]:
                            video_info = self.extract_video_info(video)
                            if video_info and not self._is_video_processed(video_info['aweme_id'], creator_id):
                                video_info['creator_id'] = creator_id
                                video_info['published_at'] = datetime.fromtimestamp(
                                    video.get('create_time', 0), 
                                    tz=timezone.utc
                                ).isoformat() if video.get('create_time') else datetime.now(timezone.utc).isoformat()
                                all_videos.append(video_info)
                                
                except Exception as e:
                    logger.error(f"Error fetching videos for creator {creator_id}: {e}")
                    continue
        
        # 按发布时间排序，返回最新的
        if all_videos:
            all_videos.sort(key=lambda x: x.get('published_at', ''), reverse=True)
            return all_videos[0]
        
        return None
    
    def _is_video_processed(self, aweme_id: str, creator_id: str) -> bool:
        """
        检查视频是否已处理（基于文件系统）
        """
        try:
            possible_paths = [
                self.cache_dir / f"{creator_id}_{aweme_id}.done",
                self.storage_base / creator_id / aweme_id / f"{aweme_id}.mp4",
                self.cache_dir / f"published_{aweme_id}.json"
            ]
            
            for path in possible_paths:
                if path.exists():
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return False
    
    def extract_video_info(self, video_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从API响应中提取视频信息
        """
        try:
            aweme_id = video_data.get('aweme_id')
            if not aweme_id:
                return None
                
            video_info = {
                'aweme_id': aweme_id,
                'desc': video_data.get('desc', ''),
                'create_time': video_data.get('create_time'),
            }
            
            # 提取视频URL
            video_obj = video_data.get('video', {})
            play_addr = video_obj.get('play_addr', {})
            url_list = play_addr.get('url_list', [])
            
            if url_list:
                video_info['video_url'] = url_list[0]
            else:
                download_addr = video_obj.get('download_addr', {})
                url_list = download_addr.get('url_list', [])
                if url_list:
                    video_info['video_url'] = url_list[0]
            
            # 提取封面图片
            cover = video_obj.get('cover', {})
            cover_url_list = cover.get('url_list', [])
            if cover_url_list:
                video_info['cover_url'] = cover_url_list[0]
            
            # 提取或构造分享URL
            share_info = video_data.get('share_info', {})
            share_url = share_info.get('share_url', '')
            if not share_url:
                share_url = f"https://www.iesdouyin.com/share/video/{aweme_id}/"
            video_info['share_url'] = share_url
            
            return video_info
            
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None
    
    async def download_media(self, context: PipelineContext, video: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        下载单个视频和封面文件
        """
        logger.info(f"[DOWNLOAD] Starting download for video {video['aweme_id']}")
        
        try:
            async with aiohttp.ClientSession() as session:
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
                    try:
                        cover_path = await self.download_cover(
                            session,
                            video['cover_url'],
                            video_dir / f"{video['aweme_id']}_cover.jpg"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to download cover: {e}")
                
                # 更新视频信息
                video['video_path'] = str(video_path)
                video['cover_path'] = str(cover_path) if cover_path else None
                video['download_time'] = datetime.now().isoformat()
                
                # 如果使用数据库，更新状态
                if self.use_database:
                    from services.video_processing_service import VideoProcessingService
                    from database import get_db_url
                    
                    engine = create_engine(get_db_url())
                    Session = sessionmaker(bind=engine)
                    db_session = Session()
                    
                    try:
                        service = VideoProcessingService(db_session)
                        video_status = service.get_video_status('douyin', video['creator_id'], video['aweme_id'])
                        if video_status:
                            service.update_processing_stage(
                                video_status,
                                'video_exported',
                                video_path=str(video_path)
                            )
                    finally:
                        db_session.close()
                
                # 创建下载成功的缓存标记
                cache_file = self.cache_dir / f"{video['creator_id']}_{video['aweme_id']}.done"
                cache_file.write_text(datetime.now().isoformat())
                
                logger.info(f"[DOWNLOAD] Successfully downloaded video {video['aweme_id']}")
                return video
                
        except Exception as e:
            logger.error(f"[DOWNLOAD] Error downloading video {video.get('aweme_id')}: {e}")
            
            # 如果使用数据库，标记为失败
            if self.use_database:
                from services.video_processing_service import VideoProcessingService
                from database import get_db_url
                
                engine = create_engine(get_db_url())
                Session = sessionmaker(bind=engine)
                db_session = Session()
                
                try:
                    service = VideoProcessingService(db_session)
                    video_status = service.get_video_status('douyin', video['creator_id'], video['aweme_id'])
                    if video_status:
                        service.mark_as_failed(video_status, str(e))
                finally:
                    db_session.close()
            
            return None
    
    async def download_video(self, session: aiohttp.ClientSession, share_url: str, save_path: Path) -> Path:
        """
        下载视频文件
        """
        download_url = f"{self.api_base_url}/api/download"
        params = {
            'url': share_url,
            'prefix': 'true',
            'with_watermark': 'false'
        }
        
        async with session.get(download_url, params=params, timeout=self.download_timeout) as response:
            if response.status != 200:
                raise Exception(f"Download failed with status {response.status}")
            
            with open(save_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
        
        return save_path
    
    async def download_cover(self, session: aiohttp.ClientSession, cover_url: str, save_path: Path) -> Path:
        """
        下载封面图片
        """
        async with session.get(cover_url, timeout=30) as response:
            if response.status != 200:
                raise Exception(f"Cover download failed with status {response.status}")
            
            with open(save_path, 'wb') as f:
                f.write(await response.read())
        
        return save_path
    
    async def publish_to_youtube(self, context: PipelineContext, video: Dict[str, Any], account_id: str) -> Dict[str, Any]:
        """
        发布视频到YouTube
        """
        logger.info(f"[PUBLISH] Starting publish for video {video['aweme_id']}")
        
        try:
            from publish_service import get_publish_service
            from database import get_db_manager, PipelineTask
            import uuid
            
            publish_service = get_publish_service()
            db = get_db_manager()
            
            # 为视频创建一个临时的Pipeline任务记录
            task_id = f"douyin_{video['aweme_id']}_{uuid.uuid4().hex[:8]}"
            
            # 创建Pipeline任务记录
            with db.get_session() as session:
                pipeline_task = PipelineTask(
                    task_id=task_id,
                    creator_id=video['creator_id'],
                    video_id=video['aweme_id'],
                    video_path=video['video_path'],
                    thumbnail_path=video.get('cover_path'),
                    status='completed',
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
                
                # 如果使用数据库，更新状态
                if self.use_database and upload_result['success']:
                    from services.video_processing_service import VideoProcessingService
                    from database import get_db_url
                    
                    engine = create_engine(get_db_url())
                    Session = sessionmaker(bind=engine)
                    db_session = Session()
                    
                    try:
                        service = VideoProcessingService(db_session)
                        video_status = service.get_video_status('douyin', video['creator_id'], video['aweme_id'])
                        if video_status:
                            service.update_processing_stage(
                                video_status,
                                'published',
                                video_path=video['video_path']
                            )
                    finally:
                        db_session.close()
                
                # 创建缓存标记
                if upload_result['success']:
                    cache_file = self.cache_dir / f"published_{video['aweme_id']}.json"
                    with open(cache_file, 'w') as f:
                        json.dump({
                            'aweme_id': video['aweme_id'],
                            'creator_id': video['creator_id'],
                            'youtube_url': upload_result.get('video_url'),
                            'published_at': datetime.now().isoformat()
                        }, f)
                
                logger.info(f"[PUBLISH] Publish result for {video['aweme_id']}: {upload_result['success']}")
                return upload_result
            else:
                raise Exception("Failed to create publish task")
                
        except Exception as e:
            logger.error(f"[PUBLISH] Error publishing video {video['aweme_id']}: {e}")
            
            # 如果使用数据库，标记为失败
            if self.use_database:
                from services.video_processing_service import VideoProcessingService
                from database import get_db_url
                
                engine = create_engine(get_db_url())
                Session = sessionmaker(bind=engine)
                db_session = Session()
                
                try:
                    service = VideoProcessingService(db_session)
                    video_status = service.get_video_status('douyin', video['creator_id'], video['aweme_id'])
                    if video_status:
                        service.mark_as_failed(video_status, f"Publish failed: {str(e)}")
                finally:
                    db_session.close()
            
            return {
                'success': False,
                'error': str(e)
            }