# youtube_analyzer/clients/youtube_client.py
import logging
import os
import subprocess
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
import httplib2
from retry import retry
import ssl
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import os
import socks


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)

class YouTubeAPIClient:
    """
    集成API密钥管理器的YouTube Data API v3客户端
    支持自动密钥切换和代理配置
    """
    def __init__(self) -> None:
        load_dotenv()
        self.logger = logging.getLogger(__name__)
        
        # 设置字幕保存目录
        self.subtitles_dir = "subtitles"
        
        # 初始化API密钥管理器
        api_key = os.environ.get("YOUTUBE_API_KEY")
        
        self.api_keys = [api_key]  # 作为备用
        
        sock_host = os.environ.get("PROXY_HOST")
        sock_port = os.environ.get("PROXY_PORT")
        proxy_username = os.environ.get("PROXY_USERNAME")  # 修正：使用正确的环境变量名
        proxy_password = os.environ.get("PROXY_PASSWORD")

        # 正确设置代理信息
        self.proxy_info = None
        if sock_host and sock_port:
            try:
                sock_port = int(sock_port)  # 转换端口为整数
            except ValueError:
                self.logger.error(f"端口号无效: {sock_port}")
                sock_port = 7897  # 使用默认端口
                
            self.logger.info(f"✅ 代理开始配置: {sock_host}:{sock_port}")
            
            if proxy_username and proxy_password:
                # 带认证的代理
                self.proxy_info = httplib2.ProxyInfo(
                    proxy_type=socks.SOCKS5,
                    proxy_host=sock_host,
                    proxy_port=sock_port,
                    proxy_user=proxy_username,
                    proxy_pass=proxy_password
                )
                self.logger.info(f"✅ 代理配置成功（带认证）: {sock_host}:{sock_port}")
                self.logger.debug(f"🔐 代理认证: {proxy_username}:{'*' * len(proxy_password)}")
            else:
                # 不带认证的代理
                self.proxy_info = httplib2.ProxyInfo(
                    proxy_type=socks.SOCKS5,
                    proxy_host=sock_host,
                    proxy_port=sock_port
                )
                self.logger.info(f"✅ 代理配置成功（无认证）: {sock_host}:{sock_port}") 
        else:
            # 只有在没有配置代理的情况下才设置为None
            self.proxy_info = None
            self.logger.info("未配置代理，使用直连")
        
        # 记录初始化状态
        self.logger.info(f"🚀 YouTubeAPIClient初始化完成")


    def _get_youtube_service(self) -> Tuple[Any, str]:
        """创建YouTube服务实例"""
        try:
            # 添加更详细的代理日志
            if self.proxy_info:
                self.logger.debug(f"使用代理创建HTTP客户端")
                http_client = httplib2.Http(proxy_info=self.proxy_info)
            else:
                self.logger.debug(f"不使用代理，直连")
                http_client = None
                
            service = build('youtube', 'v3', 
                            developerKey=self.api_keys[0], 
                            http=http_client, 
                            static_discovery=False)
            self.logger.debug(f"✅ YouTube服务实例创建成功")
            return service, self.api_keys[0]
        except Exception as e:
            self.logger.error(f"❌ YouTube服务实例创建失败: {e}")
            raise e
    
    def _handle_api_error(self, error: Exception) -> None:
        """处理API错误（简化版本）"""
        self.logger.error(f"API调用失败: {error}")
        # 简单记录错误，不做复杂处理


   
    

    def search(self, query: str, max_results: int = 50, published_after: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """搜索视频"""
        self.logger.info(f"🔍 搜索视频: '{query}' (最大结果: {max_results})")
        
        if published_after is None:
            published_after = datetime.now(timezone.utc) - timedelta(days=1)
        
        published_after_str = published_after.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.logger.debug(f"📅 发布时间过滤: {published_after_str}")

        try:
            youtube, api_key = self._get_youtube_service()
            
            request = youtube.search().list(
                part='snippet',
                q=query,
                maxResults=max_results,
                order='relevance',
                videoDuration='long',
                publishedAfter=published_after_str,
                type='video'
            )
            
            self.logger.debug(f"📤 发送搜索请求...")
            result = request.execute()
            
            result_count = len(result.get('items', []))
            self.logger.info(f"✅ 搜索成功: 找到 {result_count} 个视频")
            self.logger.debug(f"📊 搜索结果统计: {result.get('pageInfo', {})}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 搜索失败: {e}")
            raise

    def get_video_details(self, video_ids: List[str]) -> Optional[Dict[str, Any]]:
        """获取视频详情"""
        self.logger.info(f"📊 获取视频详情: {len(video_ids)} 个视频")
        self.logger.debug(f"📋 视频ID列表: {video_ids}")
        
        if not video_ids:
            self.logger.warning("⚠️ 视频ID列表为空")
            return None
        
        try:
            youtube, api_key = self._get_youtube_service()
            
            request = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids),
                maxResults=50
            )
            
            self.logger.debug(f"📤 发送视频详情请求...")
            result = request.execute()
            
            result_count = len(result.get('items', []))
            self.logger.info(f"✅ 视频详情获取成功: {result_count} 个视频")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 视频详情获取失败: {e}")
            raise

    def get_channel_details(self, channel_ids: List[str] = [], handles: List[str] = []) -> Optional[Dict[str, Any]]:
        """获取频道详情"""
        if not channel_ids and not handles:
            self.logger.warning("⚠️ 频道ID和handle都为空")
            return None

        params = {'part': "snippet,statistics,status,topicDetails,contentDetails"}
        if channel_ids:
            params['id'] = ",".join(channel_ids)
            self.logger.info(f"📺 获取频道详情 (ID): {channel_ids}")
        if handles:
            params['forHandle'] = handles[0]
            self.logger.info(f"📺 获取频道详情 (Handle): {handles[0]}")

        try:
            youtube, api_key = self._get_youtube_service()
            
            request = youtube.channels().list(**params)
            
            self.logger.debug(f"📤 发送频道详情请求...")
            result = request.execute()
            
            result_count = len(result.get('items', []))
            self.logger.info(f"✅ 频道详情获取成功: {result_count} 个频道")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 频道详情获取失败: {e}")
            raise

    #@retry((HttpError, ssl.SSLError, ssl.SSLEOFError), tries=3, delay=2, backoff=2)
    def get_channel_activity(self, channel_id: str, published_after: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """获取频道活动"""
        self.logger.info(f"📈 获取频道活动: {channel_id}")
        
        if published_after is None:
            published_after = datetime.now(timezone.utc) - timedelta(days=7)
        
        published_after_str = published_after.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.logger.debug(f"📅 活动时间过滤: {published_after_str}")
        
        try:
            youtube, api_key = self._get_youtube_service()
            
            request = youtube.activities().list(
                part="contentDetails,snippet",
                channelId=channel_id,
                maxResults=25,
                publishedAfter=published_after_str
            )
            
            self.logger.debug(f"📤 发送频道活动请求...")
            result = request.execute()
            
            result_count = len(result.get('items', []))
            self.logger.info(f"✅ 频道活动获取成功: {result_count} 个活动")
            
            return result
            
        except Exception as e:
            
            self.logger.error(f"❌ 频道活动获取失败: {e}")
            raise

    @retry((HttpError, ssl.SSLError, ssl.SSLEOFError), tries=3, delay=2, backoff=2)
    def get_playlist_items(self, playlist_id: str, max_results: int = 50, page_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取播放列表中的视频"""
        self.logger.info(f"📋 获取播放列表视频: {playlist_id} (最大结果: {max_results})")
        
        try:
            youtube, api_key = self._get_youtube_service()
            
            params = {
                'part': 'snippet,contentDetails',
                'playlistId': playlist_id,
                'maxResults': max_results
            }
            
            if page_token:
                params['pageToken'] = page_token
                self.logger.debug(f"📄 使用分页令牌: {page_token}")
            
            request = youtube.playlistItems().list(**params)
            
            self.logger.debug(f"📤 发送播放列表请求...")
            result = request.execute()
            
            result_count = len(result.get('items', []))
            self.logger.info(f"✅ 播放列表视频获取成功: {result_count} 个视频")
            
            return result
            
        except Exception as e:

            self.logger.error(f"❌ 播放列表视频获取失败: {e}")
            raise

    @retry((HttpError, ssl.SSLError, ssl.SSLEOFError), tries=3, delay=2, backoff=2)
    def get_channel_oldest_videos(self, channel_id: str, video_count: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        获取频道最早的N个视频及其流量数据
        
        Args:
            channel_id: YouTube频道ID
            video_count: 要获取的视频数量（默认100）
            
        Returns:
            包含视频详情和统计信息的列表
        """
        self.logger.info(f"🎬 获取频道最早的 {video_count} 个视频: {channel_id}")
        
        try:
            # 步骤1: 获取频道的上传播放列表ID
            channel_details = self.get_channel_details(channel_ids=[channel_id])
            if not channel_details or not channel_details.get('items'):
                self.logger.error(f"❌ 无法获取频道详情: {channel_id}")
                return None
            
            uploads_playlist_id = channel_details['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            self.logger.info(f"📋 上传播放列表ID: {uploads_playlist_id}")
            
            # 步骤2: 获取播放列表中的所有视频（分页）
            all_videos = []
            next_page_token = None
            
            while len(all_videos) < video_count:
                batch_size = min(50, video_count - len(all_videos))  # YouTube API限制每页最多50个
                
                playlist_response = self.get_playlist_items(
                    playlist_id=uploads_playlist_id,
                    max_results=batch_size,
                    page_token=next_page_token
                )
                
                if not playlist_response or not playlist_response.get('items'):
                    break
                
                all_videos.extend(playlist_response['items'])
                self.logger.debug(f"📊 已获取 {len(all_videos)} 个视频")
                
                # 检查是否有下一页
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    self.logger.info(f"📋 已到达播放列表末尾，共 {len(all_videos)} 个视频")
                    break
            
            # 步骤3: 反转列表以获取最早的视频（播放列表是从新到旧排序的）
            all_videos.reverse()
            oldest_videos = all_videos[:video_count]
            
            self.logger.info(f"🔄 获取最早的 {len(oldest_videos)} 个视频")
            
            # 步骤4: 批量获取视频的统计信息（每批最多50个）
            videos_with_stats = []
            
            for i in range(0, len(oldest_videos), 50):
                batch = oldest_videos[i:i+50]
                video_ids = [item['contentDetails']['videoId'] for item in batch]
                
                # 获取视频详情（包含统计信息）
                video_details = self.get_video_details(video_ids)
                
                if video_details and video_details.get('items'):
                    # 创建视频ID到详情的映射
                    details_map = {item['id']: item for item in video_details['items']}
                    
                    # 合并播放列表信息和视频详情
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
            
            # 按发布时间排序（确保是最早的在前）
            videos_with_stats.sort(key=lambda x: x['published_at'])
            
            return videos_with_stats
            
        except Exception as e:
            self.logger.error(f"❌ 获取频道最早视频失败: {e}")
            return None

    def get_video_comments(self, video_id: str, max_results: int = 20) -> Optional[Dict[str, Any]]:
        """获取视频评论"""
        self.logger.debug(f"💬 获取视频评论: {video_id} (最大: {max_results})")
        
        try:
            youtube, api_key = self._get_youtube_service()
            
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=max_results,
                order="relevance",
                textFormat="plainText"
            )
            
            self.logger.debug(f"📤 发送评论请求...")
            result = request.execute()
            
            result_count = len(result.get('items', []))
            self.logger.debug(f"✅ 评论获取成功: {result_count} 条评论")
            
            return result
            
        except Exception as e:
            
            self.logger.error(f"❌ 评论获取失败:")
            raise e 
        
    def get_video_transcript(self, video_id: str, video_type: Optional[str] = 'long') -> Optional[Tuple[str, str]]:
        """
        使用youtube-transcript-api获取视频字幕并保存到文件
        
        Args:
            video_id: YouTube视频ID
            video_type: 视频类型 ('long' 或 'short')
            
        Returns:
            Tuple[相对文件路径, 字幕内容] 或 None
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
        except ImportError:
            self.logger.error("youtube_transcript_api not installed")
            return None
        
        self.logger.info(f"📝 使用youtube-transcript-api获取字幕: {video_id}")
        
        # 配置代理
        proxies = None
        import requests
        import urllib3
        
        if self.proxy_info:
            # 方案1：如果你的SOCKS代理支持HTTP/HTTPS转发，使用HTTP格式
            # proxies = {
            #     'http': 'http://127.0.0.1:7897',
            #     'https': 'http://127.0.0.1:7897'
            # }
            
            # 方案2：使用SOCKS5代理（已安装pysocks）
            # 从环境变量读取SOCKS5代理配置
            socks5_host = os.getenv('SOCKS5_PROXY_HOST', '127.0.0.1')
            socks5_port = os.getenv('SOCKS5_PROXY_PORT', '7897')
            # 使用 socks5h:// 来确保DNS解析也通过代理
            proxies = {
                'http': f'socks5h://{socks5_host}:{socks5_port}',
                'https': f'socks5h://{socks5_host}:{socks5_port}'
            }
            
            # 临时解决SSL证书验证问题
            # 方法1：设置环境变量（影响全局）
            os.environ['CURL_CA_BUNDLE'] = ""  # 禁用证书验证
            
            # 方法2：修改requests的SSL验证（更安全的方式）
            # 创建一个不验证SSL的session


            
            # 保存原始的创建上下文函数
            original_create_context = ssl.create_default_context
            
            def create_unverified_context(*args, **kwargs):
                """创建一个不验证SSL证书的上下文"""
                context = original_create_context(*args, **kwargs)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                return context
            
            # 临时替换SSL上下文创建函数
            ssl.create_default_context = create_unverified_context
            
            # 禁用urllib3的SSL警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            self.logger.info(f"🔧 使用SOCKS5代理: {socks5_host}:{socks5_port} (开发环境，SSL验证已禁用)")
        
        try:
            # 尝试获取字幕
            transcript_list = YouTubeTranscriptApi.list_transcripts(
                video_id,
                proxies=proxies
            )
            
            # 恢复原始的SSL上下文创建函数
            if self.proxy_info:
                ssl.create_default_context = original_create_context
            
            # 优先获取英文字幕
            transcript = None
            try:
                # 尝试获取英文字幕（手动或自动生成的）
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
                self.logger.info(f"✅ 找到英文字幕: {video_id}")
            except NoTranscriptFound:
                # 如果没有英文字幕，尝试获取其他语言并翻译
                try:
                    # 获取第一个可用的字幕
                    for t in transcript_list:
                        transcript = t
                        self.logger.info(f"🌐 找到{t.language}字幕，尝试翻译为英文: {video_id}")
                        transcript = transcript.translate('en')
                        break
                except Exception as e:
                    self.logger.warning(f"⚠️ 无法翻译字幕: {video_id} - {e}")
                    raise e 
                    return None
            
            if not transcript:
                self.logger.warning(f"⚠️ 没有找到任何字幕: {video_id}")
                return None
            
            # 获取字幕内容
            subtitle_data = transcript.fetch()
            
            # 将字幕转换为纯文本
            subtitle_text = ' '.join([item.text for item in subtitle_data])
            
            # 保存字幕文件
            relative_path = os.path.join(self.subtitles_dir, f"{video_id}.txt")
            absolute_path = os.path.abspath(relative_path)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
            
            # 写入文件
            with open(absolute_path, 'w', encoding='utf-8') as f:
                f.write(subtitle_text)
            
            # 打印前100个字符
            preview = subtitle_text[:100] + "..." if len(subtitle_text) > 100 else subtitle_text
            self.logger.info(f"📄 字幕预览: {preview}")
            self.logger.info(f"✅ 字幕保存成功: {relative_path}")
            
            return relative_path
            
        except TranscriptsDisabled as e: 
            raise e 
            





if __name__ == '__main__':
    # 测试代码
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    
    client = YouTubeAPIClient()
    print(client.api_keys)
    # 测试获取字幕
    video_info = client.get_video_details(["15uh5XyxXho"])
    print(video_info)
    result = client.get_channel_activity("UCH9vY_kzBKhDDrpMavKxTIQ")
    if result:
        print(result)
