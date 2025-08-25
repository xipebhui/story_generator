#!/usr/bin/env python3
"""
YouTube API 客户端 - 使用 requests 库替代 googleapiclient
专门为 Windows + SOCKS5 代理环境优化
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests
from retry import retry

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)

class YouTubeAPIClientRequests:
    """
    使用 requests 库的 YouTube Data API v3 客户端
    支持 SOCKS5 代理
    """
    
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    def __init__(self) -> None:
        load_dotenv()
        self.logger = logging.getLogger(__name__)
        
        # 设置字幕保存目录
        self.subtitles_dir = "subtitles"
        
        # API密钥
        self.api_key = os.environ.get("YOUTUBE_API_KEY")
        if not self.api_key:
            self.logger.error("未设置 YOUTUBE_API_KEY")
            raise ValueError("YOUTUBE_API_KEY is required")
        
        # 配置代理
        proxy_host = os.environ.get("PROXY_HOST")
        proxy_port = os.environ.get("PROXY_PORT")
        
        self.proxies = None
        if proxy_host and proxy_port:
            # 使用 SOCKS5 代理
            proxy_url = f"socks5://{proxy_host}:{proxy_port}"
            self.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            self.logger.info(f"[OK] 使用SOCKS5代理: {proxy_host}:{proxy_port}")
        else:
            self.logger.info("未配置代理，使用直连")
        
        # 创建 session
        self.session = requests.Session()
        if self.proxies:
            self.session.proxies.update(self.proxies)
        
        self.logger.info(f"[READY] YouTubeAPIClientRequests 初始化完成")
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        发送 API 请求
        
        Args:
            endpoint: API 端点（如 'videos', 'search'）
            params: 请求参数
            
        Returns:
            响应数据或 None
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        # 添加 API key
        params['key'] = self.api_key
        
        self.logger.debug(f"请求 URL: {url}")
        self.logger.debug(f"参数: {params}")
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"API错误: HTTP {response.status_code}")
                self.logger.error(f"响应: {response.text}")
                return None
                
        except requests.exceptions.ProxyError as e:
            self.logger.error(f"代理错误: {e}")
            return None
        except requests.exceptions.Timeout as e:
            self.logger.error(f"请求超时: {e}")
            return None
        except Exception as e:
            self.logger.error(f"请求失败: {e}")
            return None
    
    def search(self, query: str, max_results: int = 50, published_after: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """搜索视频"""
        self.logger.info(f"🔍 搜索视频: '{query}' (最大结果: {max_results})")
        
        if published_after is None:
            published_after = datetime.now(timezone.utc) - timedelta(days=1)
        
        published_after_str = published_after.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        params = {
            'part': 'snippet',
            'q': query,
            'maxResults': max_results,
            'order': 'relevance',
            'videoDuration': 'long',
            'publishedAfter': published_after_str,
            'type': 'video'
        }
        
        result = self._make_request('search', params)
        
        if result:
            result_count = len(result.get('items', []))
            self.logger.info(f"✅ 搜索成功: 找到 {result_count} 个视频")
        
        return result
    
    def get_video_details(self, video_ids: List[str]) -> Optional[Dict[str, Any]]:
        """获取视频详情"""
        self.logger.info(f"📊 获取视频详情: {len(video_ids)} 个视频")
        self.logger.debug(f"📋 视频ID列表: {video_ids}")
        
        if not video_ids:
            self.logger.warning("⚠️ 视频ID列表为空")
            return None
        
        params = {
            'part': 'snippet,statistics,contentDetails',
            'id': ','.join(video_ids),
            'maxResults': 50
        }
        
        result = self._make_request('videos', params)
        
        if result:
            result_count = len(result.get('items', []))
            self.logger.info(f"✅ 视频详情获取成功: {result_count} 个视频")
        
        return result
    
    def get_channel_details(self, channel_ids: List[str] = [], handles: List[str] = []) -> Optional[Dict[str, Any]]:
        """获取频道详情"""
        if not channel_ids and not handles:
            self.logger.warning("⚠️ 频道ID和handle都为空")
            return None
        
        params = {'part': 'snippet,statistics,status,topicDetails,contentDetails'}
        
        if channel_ids:
            params['id'] = ','.join(channel_ids)
            self.logger.info(f"📺 获取频道详情 (ID): {channel_ids}")
        if handles:
            params['forHandle'] = handles[0]
            self.logger.info(f"📺 获取频道详情 (Handle): {handles[0]}")
        
        result = self._make_request('channels', params)
        
        if result:
            result_count = len(result.get('items', []))
            self.logger.info(f"✅ 频道详情获取成功: {result_count} 个频道")
        
        return result
    
    @retry(Exception, tries=3, delay=2, backoff=2)
    def get_channel_activity(self, channel_id: str, published_after: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """获取频道活动"""
        self.logger.info(f"📈 获取频道活动: {channel_id}")
        
        if published_after is None:
            published_after = datetime.now(timezone.utc) - timedelta(days=7)
        
        published_after_str = published_after.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        params = {
            'part': 'contentDetails,snippet',
            'channelId': channel_id,
            'maxResults': 25,
            'publishedAfter': published_after_str
        }
        
        result = self._make_request('activities', params)
        
        if result:
            result_count = len(result.get('items', []))
            self.logger.info(f"✅ 频道活动获取成功: {result_count} 个活动")
        
        return result
    
    @retry(Exception, tries=3, delay=2, backoff=2)
    def get_playlist_items(self, playlist_id: str, max_results: int = 50, page_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取播放列表中的视频"""
        self.logger.info(f"📋 获取播放列表视频: {playlist_id} (最大结果: {max_results})")
        
        params = {
            'part': 'snippet,contentDetails',
            'playlistId': playlist_id,
            'maxResults': max_results
        }
        
        if page_token:
            params['pageToken'] = page_token
            self.logger.debug(f"📄 使用分页令牌: {page_token}")
        
        result = self._make_request('playlistItems', params)
        
        if result:
            result_count = len(result.get('items', []))
            self.logger.info(f"✅ 播放列表视频获取成功: {result_count} 个视频")
        
        return result
    
    def get_video_comments(self, video_id: str, max_results: int = 20) -> Optional[Dict[str, Any]]:
        """获取视频评论"""
        self.logger.debug(f"💬 获取视频评论: {video_id} (最大: {max_results})")
        
        params = {
            'part': 'snippet',
            'videoId': video_id,
            'maxResults': max_results,
            'order': 'relevance',
            'textFormat': 'plainText'
        }
        
        result = self._make_request('commentThreads', params)
        
        if result:
            result_count = len(result.get('items', []))
            self.logger.debug(f"✅ 评论获取成功: {result_count} 条评论")
        
        return result
    
    def get_video_transcript(self, video_id: str, video_type: Optional[str] = 'long') -> Optional[str]:
        """
        获取视频字幕并保存到文件
        
        Args:
            video_id: YouTube视频ID
            video_type: 视频类型（long/short）
            
        Returns:
            字幕文件路径 或 None
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
        except ImportError:
            self.logger.error("[ERROR] youtube_transcript_api 未安装，请运行: pip install youtube-transcript-api")
            return None
        
        self.logger.info(f"[INFO] 获取视频字幕: {video_id}")
        
        # 配置代理（如果有的话）
        proxies = None
        if self.proxies:
            # 使用已配置的代理
            proxies = self.proxies
            self.logger.debug(f"使用代理获取字幕")
        
        try:
            # 获取字幕列表
            transcript_list = YouTubeTranscriptApi.list_transcripts(
                video_id,
                proxies=proxies
            )
            
            # 优先获取英文字幕
            transcript = None
            try:
                # 尝试获取英文字幕（手动或自动生成的）
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
                self.logger.info(f"[OK] 找到英文字幕")
            except NoTranscriptFound:
                # 如果没有英文字幕，尝试获取其他语言并翻译
                try:
                    # 获取第一个可用的字幕
                    for t in transcript_list:
                        transcript = t
                        self.logger.info(f"[INFO] 找到{t.language}字幕，尝试翻译为英文")
                        transcript = transcript.translate('en')
                        break
                except Exception as e:
                    self.logger.warning(f"[WARNING] 无法翻译字幕: {e}")
                    pass
            
            if not transcript:
                self.logger.warning(f"[WARNING] 没有找到任何字幕: {video_id}")
                return None
            
            # 获取字幕内容
            subtitle_data = transcript.fetch()
            
            # 格式化字幕内容
            subtitle_text = []
            for item in subtitle_data:
                # 清理文本中的特殊字符
                # item是FetchedTranscriptSnippet对象，直接访问其text属性
                text = item.text.replace('\n', ' ').strip()
                if text:
                    subtitle_text.append(text)
            
            # 合并字幕文本
            full_subtitle = ' '.join(subtitle_text)
            
            # 保存字幕到文件
            import os
            subtitle_dir = "subtitles"
            os.makedirs(subtitle_dir, exist_ok=True)
            
            subtitle_file = os.path.join(subtitle_dir, f"{video_id}_subtitle.txt")
            with open(subtitle_file, 'w', encoding='utf-8') as f:
                f.write(full_subtitle)
            
            self.logger.info(f"[OK] 字幕已保存到: {subtitle_file}")
            return subtitle_file
            
        except VideoUnavailable:
            self.logger.error(f"[ERROR] 视频不可用: {video_id}")
            return None
        except TranscriptsDisabled:
            self.logger.error(f"[ERROR] 视频字幕已禁用: {video_id}")
            return None
        except NoTranscriptFound:
            self.logger.error(f"[ERROR] 没有找到可用字幕: {video_id}")
            return None
        except Exception as e:
            self.logger.error(f"[ERROR] 获取字幕失败: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
    
    def get_channel_oldest_videos(self, channel_id: str, video_count: int = 100) -> Optional[List[Dict[str, Any]]]:
        """获取频道最早的N个视频"""
        self.logger.info(f"🎬 获取频道最早的 {video_count} 个视频: {channel_id}")
        
        try:
            # 步骤1: 获取频道的上传播放列表ID
            channel_details = self.get_channel_details(channel_ids=[channel_id])
            if not channel_details or not channel_details.get('items'):
                self.logger.error(f"❌ 无法获取频道详情: {channel_id}")
                return None
            
            uploads_playlist_id = channel_details['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            self.logger.info(f"📋 上传播放列表ID: {uploads_playlist_id}")
            
            # 步骤2: 获取播放列表中的所有视频
            all_videos = []
            next_page_token = None
            
            while len(all_videos) < video_count:
                batch_size = min(50, video_count - len(all_videos))
                
                playlist_response = self.get_playlist_items(
                    playlist_id=uploads_playlist_id,
                    max_results=batch_size,
                    page_token=next_page_token
                )
                
                if not playlist_response or not playlist_response.get('items'):
                    break
                
                all_videos.extend(playlist_response['items'])
                self.logger.debug(f"📊 已获取 {len(all_videos)} 个视频")
                
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    self.logger.info(f"📋 已到达播放列表末尾，共 {len(all_videos)} 个视频")
                    break
            
            # 步骤3: 反转列表获取最早的视频
            all_videos.reverse()
            oldest_videos = all_videos[:video_count]
            
            self.logger.info(f"🔄 获取最早的 {len(oldest_videos)} 个视频")
            
            # 步骤4: 批量获取视频统计信息
            videos_with_stats = []
            
            for i in range(0, len(oldest_videos), 50):
                batch = oldest_videos[i:i+50]
                video_ids = [item['contentDetails']['videoId'] for item in batch]
                
                video_details = self.get_video_details(video_ids)
                
                if video_details and video_details.get('items'):
                    details_map = {item['id']: item for item in video_details['items']}
                    
                    for playlist_item in batch:
                        video_id = playlist_item['contentDetails']['videoId']
                        if video_id in details_map:
                            merged_item = {
                                'video_id': video_id,
                                'title': playlist_item['snippet']['title'],
                                'published_at': playlist_item['snippet']['publishedAt'],
                                'position': playlist_item['snippet']['position'],
                                'statistics': details_map[video_id].get('statistics', {}),
                                'duration': details_map[video_id]['contentDetails'].get('duration'),
                                'view_count': int(details_map[video_id].get('statistics', {}).get('viewCount', 0))
                            }
                            videos_with_stats.append(merged_item)
                
                self.logger.info(f"✅ 已获取 {len(videos_with_stats)}/{len(oldest_videos)} 个视频的统计信息")
            
            self.logger.info(f"🎉 成功获取 {len(videos_with_stats)} 个最早视频的完整信息")
            
            # 按发布时间排序
            videos_with_stats.sort(key=lambda x: x['published_at'])
            
            return videos_with_stats
            
        except Exception as e:
            self.logger.error(f"❌ 获取频道最早视频失败: {e}")
            return None
    
    # 为了兼容性，添加 _handle_api_error 方法
    def _handle_api_error(self, error: Exception) -> None:
        """处理API错误（兼容性方法）"""
        self.logger.error(f"API调用失败: {error}")


# 为了兼容，创建一个别名
YouTubeAPIClient = YouTubeAPIClientRequests


if __name__ == '__main__':
    # 测试代码
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    client = YouTubeAPIClient()
    
    # 测试获取视频详情
    video_info = client.get_video_details(["dQw4w9WgXcQ"])
    if video_info:
        print(json.dumps(video_info, indent=2, ensure_ascii=False))