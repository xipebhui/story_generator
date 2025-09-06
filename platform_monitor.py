#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台监控适配器模块
支持多平台内容监控和数据采集
"""

import logging
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import re

from database import get_db_manager
from youtube_client import YouTubeAPIClient as YouTubeClient

logger = logging.getLogger(__name__)


class Platform(Enum):
    """支持的平台"""
    YOUTUBE = "youtube"
    BILIBILI = "bilibili"
    DOUYIN = "douyin"
    TIKTOK = "tiktok"


class MonitorType(Enum):
    """监控类型"""
    COMPETITOR = "competitor"  # 竞争对手监控
    TRENDING = "trending"      # 热门趋势监控
    KEYWORD = "keyword"        # 关键词监控
    CHANNEL = "channel"        # 频道监控


@dataclass
class MonitorConfig:
    """监控配置"""
    monitor_id: str
    platform: str
    monitor_type: str
    target_identifier: str  # 频道ID、关键词等
    check_interval: int = 3600  # 检查间隔(秒)
    config: Optional[Dict[str, Any]] = None
    is_active: bool = True
    last_check: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ContentItem:
    """内容项"""
    content_id: str
    platform: str
    title: str
    author: str
    author_id: str
    publish_time: datetime
    url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None  # 秒
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['publish_time'] = self.publish_time.isoformat()
        return data


class PlatformAdapter(ABC):
    """平台适配器基类"""
    
    def __init__(self, platform: str):
        self.platform = platform
        self.session = None
    
    @abstractmethod
    async def fetch_channel_videos(
        self,
        channel_id: str,
        max_results: int = 10
    ) -> List[ContentItem]:
        """获取频道视频"""
        pass
    
    @abstractmethod
    async def fetch_trending_videos(
        self,
        category: Optional[str] = None,
        max_results: int = 10
    ) -> List[ContentItem]:
        """获取热门视频"""
        pass
    
    @abstractmethod
    async def search_videos(
        self,
        keyword: str,
        max_results: int = 10
    ) -> List[ContentItem]:
        """搜索视频"""
        pass
    
    @abstractmethod
    async def get_video_details(self, video_id: str) -> Optional[ContentItem]:
        """获取视频详情"""
        pass
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()


class YouTubeAdapter(PlatformAdapter):
    """YouTube平台适配器"""
    
    def __init__(self):
        super().__init__(Platform.YOUTUBE.value)
        self.youtube_client = YouTubeClient()
    
    async def fetch_channel_videos(
        self,
        channel_id: str,
        max_results: int = 10
    ) -> List[ContentItem]:
        """获取YouTube频道视频"""
        try:
            videos = await asyncio.to_thread(
                self.youtube_client.get_channel_videos,
                channel_id,
                max_results
            )
            
            items = []
            for video in videos:
                item = self._convert_youtube_video(video)
                if item:
                    items.append(item)
            
            logger.info(f"获取YouTube频道 {channel_id} 的 {len(items)} 个视频")
            return items
            
        except Exception as e:
            logger.error(f"获取YouTube频道视频失败: {e}")
            return []
    
    async def fetch_trending_videos(
        self,
        category: Optional[str] = None,
        max_results: int = 10
    ) -> List[ContentItem]:
        """获取YouTube热门视频"""
        try:
            videos = await asyncio.to_thread(
                self.youtube_client.get_trending_videos,
                category,
                max_results
            )
            
            items = []
            for video in videos:
                item = self._convert_youtube_video(video)
                if item:
                    items.append(item)
            
            logger.info(f"获取YouTube热门视频 {len(items)} 个")
            return items
            
        except Exception as e:
            logger.error(f"获取YouTube热门视频失败: {e}")
            return []
    
    async def search_videos(
        self,
        keyword: str,
        max_results: int = 10
    ) -> List[ContentItem]:
        """搜索YouTube视频"""
        try:
            videos = await asyncio.to_thread(
                self.youtube_client.search_videos,
                keyword,
                max_results
            )
            
            items = []
            for video in videos:
                item = self._convert_youtube_video(video)
                if item:
                    items.append(item)
            
            logger.info(f"搜索YouTube视频 '{keyword}' 得到 {len(items)} 个结果")
            return items
            
        except Exception as e:
            logger.error(f"搜索YouTube视频失败: {e}")
            return []
    
    async def get_video_details(self, video_id: str) -> Optional[ContentItem]:
        """获取YouTube视频详情"""
        try:
            video = await asyncio.to_thread(
                self.youtube_client.get_video_details,
                video_id
            )
            
            if video:
                return self._convert_youtube_video(video)
            
        except Exception as e:
            logger.error(f"获取YouTube视频详情失败: {e}")
        
        return None
    
    def _convert_youtube_video(self, video_data: Dict[str, Any]) -> Optional[ContentItem]:
        """转换YouTube视频数据"""
        try:
            # 解析时长
            duration = self._parse_duration(video_data.get('duration', ''))
            
            # 解析发布时间
            publish_time = self._parse_publish_time(video_data.get('publishedAt', ''))
            
            return ContentItem(
                content_id=video_data.get('id', ''),
                platform=self.platform,
                title=video_data.get('title', ''),
                author=video_data.get('channelTitle', ''),
                author_id=video_data.get('channelId', ''),
                publish_time=publish_time,
                url=f"https://www.youtube.com/watch?v={video_data.get('id', '')}",
                thumbnail_url=video_data.get('thumbnail', ''),
                duration=duration,
                view_count=int(video_data.get('viewCount', 0)),
                like_count=int(video_data.get('likeCount', 0)),
                comment_count=int(video_data.get('commentCount', 0)),
                tags=video_data.get('tags', []),
                description=video_data.get('description', ''),
                metadata=video_data
            )
        except Exception as e:
            logger.error(f"转换YouTube视频数据失败: {e}")
            return None
    
    def _parse_duration(self, duration_str: str) -> int:
        """解析ISO 8601时长格式"""
        if not duration_str:
            return 0
        
        # PT15M33S -> 15分33秒
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        
        return 0
    
    def _parse_publish_time(self, time_str: str) -> datetime:
        """解析发布时间"""
        if not time_str:
            return datetime.now()
        
        try:
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except:
            return datetime.now()


class BilibiliAdapter(PlatformAdapter):
    """Bilibili平台适配器"""
    
    def __init__(self):
        super().__init__(Platform.BILIBILI.value)
        self.api_base = "https://api.bilibili.com"
    
    async def fetch_channel_videos(
        self,
        channel_id: str,
        max_results: int = 10
    ) -> List[ContentItem]:
        """获取B站UP主视频"""
        try:
            url = f"{self.api_base}/x/space/arc/search"
            params = {
                'mid': channel_id,
                'ps': max_results,
                'pn': 1,
                'order': 'pubdate'
            }
            
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('code') == 0:
                    videos = data.get('data', {}).get('list', {}).get('vlist', [])
                    items = []
                    
                    for video in videos:
                        item = self._convert_bilibili_video(video)
                        if item:
                            items.append(item)
                    
                    logger.info(f"获取B站UP主 {channel_id} 的 {len(items)} 个视频")
                    return items
                
        except Exception as e:
            logger.error(f"获取B站UP主视频失败: {e}")
        
        return []
    
    async def fetch_trending_videos(
        self,
        category: Optional[str] = None,
        max_results: int = 10
    ) -> List[ContentItem]:
        """获取B站热门视频"""
        try:
            url = f"{self.api_base}/x/web-interface/ranking/v2"
            params = {
                'rid': category or 0,  # 分区ID，0为全站
                'type': 'all'
            }
            
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('code') == 0:
                    videos = data.get('data', {}).get('list', [])[:max_results]
                    items = []
                    
                    for video in videos:
                        item = self._convert_bilibili_video(video)
                        if item:
                            items.append(item)
                    
                    logger.info(f"获取B站热门视频 {len(items)} 个")
                    return items
                
        except Exception as e:
            logger.error(f"获取B站热门视频失败: {e}")
        
        return []
    
    async def search_videos(
        self,
        keyword: str,
        max_results: int = 10
    ) -> List[ContentItem]:
        """搜索B站视频"""
        try:
            url = f"{self.api_base}/x/web-interface/search/type"
            params = {
                'search_type': 'video',
                'keyword': keyword,
                'page': 1,
                'page_size': max_results
            }
            
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('code') == 0:
                    videos = data.get('data', {}).get('result', [])
                    items = []
                    
                    for video in videos:
                        item = self._convert_bilibili_video(video)
                        if item:
                            items.append(item)
                    
                    logger.info(f"搜索B站视频 '{keyword}' 得到 {len(items)} 个结果")
                    return items
                
        except Exception as e:
            logger.error(f"搜索B站视频失败: {e}")
        
        return []
    
    async def get_video_details(self, video_id: str) -> Optional[ContentItem]:
        """获取B站视频详情"""
        try:
            url = f"{self.api_base}/x/web-interface/view"
            params = {'bvid': video_id} if video_id.startswith('BV') else {'aid': video_id}
            
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get('code') == 0:
                    video = data.get('data', {})
                    return self._convert_bilibili_video(video)
                
        except Exception as e:
            logger.error(f"获取B站视频详情失败: {e}")
        
        return None
    
    def _convert_bilibili_video(self, video_data: Dict[str, Any]) -> Optional[ContentItem]:
        """转换B站视频数据"""
        try:
            # 获取视频ID
            video_id = video_data.get('bvid') or video_data.get('aid', '')
            
            # 解析发布时间
            pubdate = video_data.get('pubdate') or video_data.get('created', 0)
            if isinstance(pubdate, int):
                publish_time = datetime.fromtimestamp(pubdate)
            else:
                publish_time = datetime.now()
            
            return ContentItem(
                content_id=str(video_id),
                platform=self.platform,
                title=video_data.get('title', ''),
                author=video_data.get('author') or video_data.get('owner', {}).get('name', ''),
                author_id=str(video_data.get('mid') or video_data.get('owner', {}).get('mid', '')),
                publish_time=publish_time,
                url=f"https://www.bilibili.com/video/{video_id}",
                thumbnail_url=video_data.get('pic', ''),
                duration=video_data.get('duration', 0),
                view_count=video_data.get('view') or video_data.get('play', 0),
                like_count=video_data.get('like', 0),
                comment_count=video_data.get('reply', 0),
                share_count=video_data.get('share', 0),
                tags=video_data.get('tag', '').split(',') if video_data.get('tag') else [],
                description=video_data.get('desc', ''),
                metadata=video_data
            )
        except Exception as e:
            logger.error(f"转换B站视频数据失败: {e}")
            return None


class PlatformMonitor:
    """平台监控器"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.adapters = {
            Platform.YOUTUBE.value: YouTubeAdapter(),
            Platform.BILIBILI.value: BilibiliAdapter(),
            # Platform.DOUYIN.value: DouyinAdapter(),  # 待实现
            # Platform.TIKTOK.value: TikTokAdapter(),  # 待实现
        }
        self._running = False
    
    async def start_monitoring(self):
        """启动监控"""
        if self._running:
            logger.warning("监控器已在运行")
            return
        
        self._running = True
        logger.info("平台监控器启动")
        
        # 启动监控循环
        await self._monitor_loop()
    
    async def stop_monitoring(self):
        """停止监控"""
        self._running = False
        logger.info("平台监控器停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                # 获取所有活跃的监控配置
                configs = self._get_active_configs()
                
                for config in configs:
                    if self._should_check(config):
                        await self._execute_monitor(config)
                
                # 休眠
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(10)
    
    async def _execute_monitor(self, config: MonitorConfig):
        """执行监控"""
        try:
            adapter = self.adapters.get(config.platform)
            if not adapter:
                logger.warning(f"不支持的平台: {config.platform}")
                return
            
            items = []
            
            async with adapter:
                if config.monitor_type == MonitorType.CHANNEL.value:
                    items = await adapter.fetch_channel_videos(
                        config.target_identifier,
                        max_results=10
                    )
                elif config.monitor_type == MonitorType.TRENDING.value:
                    items = await adapter.fetch_trending_videos(
                        category=config.target_identifier,
                        max_results=20
                    )
                elif config.monitor_type == MonitorType.KEYWORD.value:
                    items = await adapter.search_videos(
                        config.target_identifier,
                        max_results=20
                    )
                elif config.monitor_type == MonitorType.COMPETITOR.value:
                    # 竞争对手监控，获取其最新视频
                    items = await adapter.fetch_channel_videos(
                        config.target_identifier,
                        max_results=5
                    )
            
            # 保存监控结果
            if items:
                self._save_monitor_results(config, items)
                logger.info(f"监控 {config.monitor_id} 获取 {len(items)} 个内容")
            
            # 更新最后检查时间
            self._update_last_check(config.monitor_id)
            
        except Exception as e:
            logger.error(f"执行监控失败 {config.monitor_id}: {e}")
    
    def _get_active_configs(self) -> List[MonitorConfig]:
        """获取活跃的监控配置"""
        # 这里简化处理，实际应该从数据库查询
        return [
            MonitorConfig(
                monitor_id="monitor_1",
                platform=Platform.YOUTUBE.value,
                monitor_type=MonitorType.TRENDING.value,
                target_identifier="",
                check_interval=3600
            )
        ]
    
    def _should_check(self, config: MonitorConfig) -> bool:
        """判断是否应该检查"""
        if not config.is_active:
            return False
        
        if not config.last_check:
            return True
        
        next_check = config.last_check + timedelta(seconds=config.check_interval)
        return datetime.now() >= next_check
    
    def _save_monitor_results(self, config: MonitorConfig, items: List[ContentItem]):
        """保存监控结果"""
        try:
            # 这里简化处理，实际应该保存到monitor_results表
            for item in items:
                logger.debug(f"保存监控结果: {item.content_id} - {item.title}")
        except Exception as e:
            logger.error(f"保存监控结果失败: {e}")
    
    def _update_last_check(self, monitor_id: str):
        """更新最后检查时间"""
        try:
            # 这里简化处理，实际应该更新platform_monitors表
            logger.debug(f"更新监控 {monitor_id} 的最后检查时间")
        except Exception as e:
            logger.error(f"更新最后检查时间失败: {e}")
    
    async def fetch_content(
        self,
        platform: str,
        monitor_type: str,
        target: str,
        max_results: int = 10
    ) -> List[ContentItem]:
        """手动获取内容"""
        adapter = self.adapters.get(platform)
        if not adapter:
            logger.error(f"不支持的平台: {platform}")
            return []
        
        try:
            async with adapter:
                if monitor_type == MonitorType.CHANNEL.value:
                    return await adapter.fetch_channel_videos(target, max_results)
                # elif monitor_type == MonitorType.TRENDING.value:
                #     return await adapter.fetch_trending_videos(target, max_results)
                elif monitor_type == MonitorType.KEYWORD.value:
                    return await adapter.search_videos(target, max_results)
                else:
                    logger.error(f"不支持的监控类型: {monitor_type}")
                    return []
        except Exception as e:
            logger.error(f"获取内容失败: {e}")
            return []


# 全局实例
_platform_monitor = None


def get_platform_monitor() -> PlatformMonitor:
    """获取平台监控器实例"""
    global _platform_monitor
    if _platform_monitor is None:
        _platform_monitor = PlatformMonitor()
    return _platform_monitor