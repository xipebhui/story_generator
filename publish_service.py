#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布管理服务
负责视频发布到YouTube的流程管理
"""

import os
import json
import uuid
import logging
import asyncio
import aiohttp
import re
from datetime import datetime
from timezone_config import get_beijing_now
from typing import List, Dict, Any, Optional
from pathlib import Path

from database import get_db_manager, PublishTask
from account_service import get_account_service

logger = logging.getLogger(__name__)

# YTEngine上传服务配置
YTENGINE_HOST = os.environ.get('YTENGINE_HOST', 'http://localhost:51077')
UPLOAD_API_URL = f"{YTENGINE_HOST}/api/upload"
MOCK_UPLOAD_API_URL = f"{YTENGINE_HOST}/api/mock-upload"


class PublishService:
    """发布管理服务类"""
    
    def __init__(self, use_mock: bool = False):
        """
        初始化发布服务
        
        Args:
            use_mock: 是否使用mock接口（测试用）- 默认使用真实接口
        """
        self.db = get_db_manager()
        self.account_service = get_account_service()
        # 强制使用真实接口，除非明确设置use_mock=True
        self.use_mock = False  # 始终使用真实接口
        self.upload_url = UPLOAD_API_URL  # 始终使用真实上传接口
        logger.info(f"发布服务初始化，使用真实上传接口: {self.upload_url}")
    
    def create_publish_task(
        self,
        task_id: str,
        account_id: str,
        video_title: Optional[str] = None,
        video_description: Optional[str] = None,
        video_tags: Optional[List[str]] = None,
        thumbnail_path: Optional[str] = None,
        scheduled_time: Optional[datetime] = None,
        privacy_status: str = 'public'
    ) -> Optional[Dict[str, Any]]:
        """
        创建发布任务
        
        Args:
            task_id: Pipeline任务ID
            account_id: 发布账号ID
            video_title: 视频标题（可选，不提供则使用YouTube元数据）
            video_description: 视频描述（可选）
            video_tags: 标签列表（可选）
            thumbnail_path: 封面图路径（可选）
            scheduled_time: 定时发布时间（可选）
            privacy_status: 隐私设置
        
        Returns:
            发布任务信息
        """
        try:
            # 获取Pipeline任务信息
            pipeline_task = self.db.get_task(task_id)
            if not pipeline_task:
                logger.error(f"Pipeline任务不存在: {task_id}")
                return None
            
            # 检查任务是否已完成
            if pipeline_task.status != 'completed':
                logger.error(f"Pipeline任务未完成: {task_id}, 状态: {pipeline_task.status}")
                return None
            
            # 获取账号信息
            account = self.account_service.get_account_by_id(account_id)
            if not account:
                logger.error(f"账号不存在: {account_id}")
                return None
            
            # 检查视频文件是否存在
            video_path = pipeline_task.video_path
            if not video_path or not Path(video_path).exists():
                logger.error(f"视频文件不存在: {video_path}")
                return None
            
            # 获取YouTube元数据
            youtube_metadata = json.loads(pipeline_task.youtube_metadata) if pipeline_task.youtube_metadata else {}
            
            # 构建发布数据
            publish_id = f"pub_{task_id}_{account_id}_{uuid.uuid4().hex[:8]}"
            
            # 不再处理video_tags和video_description，避免特殊字符问题
            # 这些信息可以从pipeline_task的youtube_metadata中获取
            
            publish_data = {
                'publish_id': publish_id,
                'task_id': task_id,
                'account_id': account_id,
                'video_path': video_path,
                'video_title': video_title or youtube_metadata.get('title', f"Video {task_id}"),
                'video_description': '',  # 留空，避免特殊字符问题
                'video_tags': json.dumps([], ensure_ascii=False),  # 空标签列表
                'thumbnail_path': thumbnail_path or pipeline_task.thumbnail_path,
                'scheduled_time': scheduled_time,
                'is_scheduled': scheduled_time is not None,
                'privacy_status': privacy_status,
                'status': 'pending'
            }
            
            # 创建发布任务
            publish_task = self.db.create_publish_task(publish_data)
            logger.info(f"创建发布任务成功: {publish_id}")
            
            return publish_task.to_dict()
            
        except Exception as e:
            logger.error(f"创建发布任务失败: {e}")
            logger.exception("详细错误:")
            return None
    
    async def upload_to_youtube_async(self, publish_id: str) -> Dict[str, Any]:
        """
        异步上传视频到YouTube
        
        Args:
            publish_id: 发布任务ID
        
        Returns:
            上传结果
        """
        try:
            # 获取发布任务
            with self.db.get_session() as session:
                publish_task = session.query(PublishTask).filter_by(publish_id=publish_id).first()
                if not publish_task:
                    return {'success': False, 'error': '发布任务不存在'}
                
                # 获取账号信息
                account = self.account_service.get_account_by_id(publish_task.account_id)
                if not account:
                    return {'success': False, 'error': '账号不存在'}
                
                # 更新状态为上传中
                self.db.update_publish_task(publish_id, {
                    'status': 'uploading',
                    'upload_started_at': get_beijing_now()
                })
                
                # 优先使用 publish_task 中的标签和描述（从请求中传入的）
                # 如果没有，则从 PipelineTask 的 youtube_metadata 中获取
                
                # 处理描述
                description = publish_task.video_description or ""
                
                # 如果 publish_task 没有描述，尝试从 youtube_metadata 获取
                if not description:
                    from database import PipelineTask
                    pipeline_task = session.query(PipelineTask).filter_by(task_id=publish_task.task_id).first()
                    if pipeline_task and pipeline_task.youtube_metadata:
                        youtube_metadata = json.loads(pipeline_task.youtube_metadata)
                        description = youtube_metadata.get('description', '')
                
                # 清理描述中的特殊字符
                if description:
                    description = description.replace('\x00', '').replace('\r', '\n')
                    # YouTube描述限制5000字符
                    if len(description) > 5000:
                        description = description[:4997] + '...'
                
                # 处理标签
                tags_for_upload = []
                
                # 优先使用 publish_task 中的标签
                if publish_task.video_tags:
                    tags_data = json.loads(publish_task.video_tags) if isinstance(publish_task.video_tags, str) else publish_task.video_tags
                    
                    # 如果是列表格式
                    if isinstance(tags_data, list):
                        # 过滤出英文标签
                        for tag in tags_data:
                            if tag and re.match(r'^[a-zA-Z0-9\s\-\'&.,!]+$', tag):
                                tags_for_upload.append(tag)
                                if len(tags_for_upload) >= 20:  # YouTube限制最多20个标签
                                    break
                    # 如果是字典格式（有可能前端传来的是结构化的）
                    elif isinstance(tags_data, dict):
                        if 'english' in tags_data and tags_data['english']:
                            tags_for_upload = tags_data['english'][:20]
                        elif 'mixed' in tags_data:
                            for tag in tags_data['mixed']:
                                if tag and re.match(r'^[a-zA-Z0-9\s\-\'&.,!]+$', tag):
                                    tags_for_upload.append(tag)
                                    if len(tags_for_upload) >= 20:
                                        break
                
                # 如果没有标签，尝试从 youtube_metadata 获取
                if not tags_for_upload:
                    from database import PipelineTask
                    pipeline_task = session.query(PipelineTask).filter_by(task_id=publish_task.task_id).first()
                    if pipeline_task and pipeline_task.youtube_metadata:
                        youtube_metadata = json.loads(pipeline_task.youtube_metadata)
                        tags_data = youtube_metadata.get('tags', [])
                        
                        if isinstance(tags_data, dict):
                            if 'english' in tags_data and tags_data['english']:
                                tags_for_upload = tags_data['english'][:20]
                            elif 'mixed' in tags_data:
                                for tag in tags_data['mixed']:
                                    if tag and re.match(r'^[a-zA-Z0-9\s\-\'&.,!]+$', tag):
                                        tags_for_upload.append(tag)
                                        if len(tags_for_upload) >= 20:
                                            break
                        elif isinstance(tags_data, list):
                            for tag in tags_data:
                                if tag and re.match(r'^[a-zA-Z0-9\s\-\'&.,!]+$', tag):
                                    tags_for_upload.append(tag)
                                    if len(tags_for_upload) >= 20:
                                        break
                
                logger.debug(f"[标签处理] 最终标签: {tags_for_upload}")
                logger.debug(f"[描述处理] 描述长度: {len(description)}")
                
                # 构建上传请求 - 符合真实YouTube上传API格式
                upload_request = {
                    'tasks': [
                        {
                            'profileId': account['profile_id'],  # 比特浏览器Profile ID
                            'video': {
                                'uid': publish_id,  # 任务唯一标识
                                'path': publish_task.video_path,  # 视频文件路径
                                'title': publish_task.video_title,  # 视频标题
                                'description': description,  # 从youtube_metadata获取的描述
                                'tags': tags_for_upload,  # 从youtube_metadata获取的标签
                                'visibility': publish_task.privacy_status  # 可见性 (public/unlisted/private)
                            }
                        }
                    ]
                }
                
                # 添加缩略图路径（如果有）- 这是唯一需要的可选参数
                if publish_task.thumbnail_path and Path(publish_task.thumbnail_path).exists():
                    upload_request['tasks'][0]['video']['thumbnail'] = publish_task.thumbnail_path
                
                # 详细的请求日志，用于调试
                logger.info("="*60)
                logger.info(f"[上传请求] 发送到真实YouTube上传API")
                logger.info(f"[上传URL] {self.upload_url}")
                logger.info(f"[请求数据] 完整JSON:")
                logger.info(json.dumps(upload_request, ensure_ascii=False, indent=2))
                logger.info("="*60)
                
                # 额外的调试信息
                logger.debug(f"[调试] Profile ID: {account['profile_id']}")
                logger.debug(f"[调试] 视频路径: {publish_task.video_path}")
                logger.debug(f"[调试] 视频标题: {publish_task.video_title}")
                logger.debug(f"[调试] 视频描述长度: {len(description)}")
                logger.debug(f"[调试] 标签数量: {len(tags_for_upload)}")
                logger.debug(f"[调试] 隐私设置: {publish_task.privacy_status}")
                logger.debug(f"[调试] 缩略图: {'有' if publish_task.thumbnail_path else '无'}")
                
                # 发送HTTP请求
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.upload_url,
                        json=upload_request,
                        timeout=aiohttp.ClientTimeout(total=2400)  # 40分钟超时
                    ) as response:
                        response_text = await response.text()
                        
                        # 详细的响应日志
                        logger.info("="*60)
                        logger.info(f"[上传响应] HTTP状态码: {response.status}")
                        logger.info(f"[响应头] Content-Type: {response.headers.get('Content-Type', 'N/A')}")
                        
                        # 尝试解析JSON响应
                        try:
                            response_data = json.loads(response_text)
                            logger.info(f"[响应数据] 完整JSON:")
                            logger.info(json.dumps(response_data, ensure_ascii=False, indent=2))
                        except json.JSONDecodeError:
                            logger.error(f"[响应错误] 无法解析JSON响应:")
                            logger.error(response_text)
                            response_data = {'error': 'Invalid JSON response', 'raw': response_text}
                        
                        logger.info("="*60)
                        
                        # 处理响应 - 根据真实API响应格式
                        if response.status == 200:
                            # 检查响应中的结果
                            results = response_data.get('results', [])
                            if results and len(results) > 0:
                                result = results[0]
                                
                                # 检查单个任务的状态 (真实API返回 "SUCCESS" 或 "FAIL")
                                if result.get('status') == 'SUCCESS':
                                    # 提取YouTube URL中的视频ID
                                    youtube_url = result.get('url', '')
                                    video_id = ''
                                    if 'youtu.be/' in youtube_url:
                                        video_id = youtube_url.split('youtu.be/')[-1].split('?')[0]
                                    elif 'youtube.com/watch?v=' in youtube_url:
                                        video_id = youtube_url.split('v=')[1].split('&')[0]
                                    
                                    # 更新发布任务状态为成功
                                    self.db.update_publish_task(publish_id, {
                                        'status': 'success',
                                        'youtube_video_id': video_id,
                                        'youtube_video_url': youtube_url,
                                        'upload_response': response_data,
                                        'upload_completed_at': get_beijing_now()
                                    })
                                    logger.info(f"视频上传成功: {youtube_url}")
                                    return {
                                        'success': True,
                                        'video_id': video_id,
                                        'video_url': youtube_url,
                                        'execution_time': result.get('executionTime', 0)
                                    }
                                else:
                                    # 任务失败 (status == "FAIL")
                                    error_msg = result.get('error', '上传失败')
                                    self.db.update_publish_task(publish_id, {
                                        'status': 'failed',
                                        'error_message': error_msg,
                                        'upload_response': response_data,
                                        'upload_completed_at': get_beijing_now()
                                    })
                                    logger.error(f"视频上传失败: {error_msg}")
                                    return {'success': False, 'error': error_msg}
                            else:
                                # 没有结果
                                error_msg = '上传响应中没有结果'
                                self.db.update_publish_task(publish_id, {
                                    'status': 'failed',
                                    'error_message': error_msg,
                                    'upload_response': response_data,
                                    'upload_completed_at': get_beijing_now()
                                })
                                return {'success': False, 'error': error_msg}
                        else:
                            # HTTP状态码非200
                            error_msg = f"HTTP错误: {response.status}"
                            self.db.update_publish_task(publish_id, {
                                'status': 'failed',
                                'error_message': error_msg,
                                'upload_response': response_data if 'response_data' in locals() else None,
                                'upload_completed_at': get_beijing_now()
                            })
                            return {'success': False, 'error': error_msg}
                            
        except asyncio.TimeoutError:
            error_msg = '上传超时'
            self.db.update_publish_task(publish_id, {
                'status': 'failed',
                'error_message': error_msg,
                'upload_completed_at': get_beijing_now()
            })
            logger.error(f"上传超时: {publish_id}")
            return {'success': False, 'error': error_msg}
            
        except Exception as e:
            error_msg = str(e)
            self.db.update_publish_task(publish_id, {
                'status': 'failed',
                'error_message': error_msg,
                'upload_completed_at': get_beijing_now()
            })
            logger.error(f"上传失败: {e}")
            logger.exception("详细错误:")
            return {'success': False, 'error': error_msg}
    
    def upload_to_youtube(self, publish_id: str) -> Dict[str, Any]:
        """
        同步上传视频到YouTube
        
        Args:
            publish_id: 发布任务ID
        
        Returns:
            上传结果
        """
        # 创建新的事件循环来运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.upload_to_youtube_async(publish_id))
        finally:
            loop.close()
    
    def batch_publish(
        self,
        task_id: str,
        account_ids: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量发布到多个账号
        
        Args:
            task_id: Pipeline任务ID
            account_ids: 账号ID列表
            **kwargs: 其他发布参数
        
        Returns:
            发布结果列表
        """
        results = []
        
        for account_id in account_ids:
            try:
                # 创建发布任务
                publish_task = self.create_publish_task(
                    task_id=task_id,
                    account_id=account_id,
                    **kwargs
                )
                
                if publish_task:
                    # 执行上传
                    upload_result = self.upload_to_youtube(publish_task['publish_id'])
                    results.append({
                        'publish_id': publish_task['publish_id'],
                        'account_id': account_id,
                        'success': upload_result['success'],
                        'video_url': upload_result.get('video_url'),
                        'error': upload_result.get('error')
                    })
                else:
                    results.append({
                        'account_id': account_id,
                        'success': False,
                        'error': '创建发布任务失败'
                    })
                    
            except Exception as e:
                logger.error(f"发布到账号 {account_id} 失败: {e}")
                results.append({
                    'account_id': account_id,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def get_publish_history(
        self,
        task_id: Optional[str] = None,
        account_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取发布历史，包含账号名称信息
        
        Args:
            task_id: Pipeline任务ID筛选
            account_id: 账号ID筛选
            status: 状态筛选
            limit: 返回数量限制
        
        Returns:
            发布任务列表，包含账号名称
        """
        with self.db.get_session() as session:
            query = session.query(PublishTask)
            
            if task_id:
                query = query.filter(PublishTask.task_id == task_id)
            if account_id:
                query = query.filter(PublishTask.account_id == account_id)
            if status:
                query = query.filter(PublishTask.status == status)
            
            query = query.order_by(PublishTask.created_at.desc())
            query = query.limit(limit)
            
            tasks = query.all()
            
            # 增强返回数据，添加账号名称信息
            result = []
            for task in tasks:
                task_dict = task.to_dict()
                
                # 获取账号信息
                account_info = self.account_service.get_account_by_id(task.account_id)
                if account_info:
                    # 添加账号名称和YouTube账号名称
                    task_dict['account_name'] = account_info.get('account_name', task.account_id)
                    task_dict['youtube_channel_name'] = account_info.get('channel_name', account_info.get('account_name', ''))
                else:
                    # 如果找不到账号信息，使用account_id作为默认值
                    task_dict['account_name'] = task.account_id
                    task_dict['youtube_channel_name'] = task.account_id
                
                # 确保发布完成时间字段存在
                if not task_dict.get('upload_completed_at') and task.status == 'success':
                    # 如果成功但没有完成时间，使用创建时间
                    task_dict['upload_completed_at'] = task_dict.get('created_at')
                
                result.append(task_dict)
            
            return result
    
    def retry_failed_publish(self, publish_id: str) -> Dict[str, Any]:
        """
        重试失败的发布任务
        
        Args:
            publish_id: 发布任务ID
        
        Returns:
            重试结果
        """
        # 重置状态为pending
        self.db.update_publish_task(publish_id, {
            'status': 'pending',
            'error_message': None,
            'upload_response': None
        })
        
        # 重新上传
        return self.upload_to_youtube(publish_id)


# 全局服务实例
publish_service: Optional[PublishService] = None

def get_publish_service(use_mock: bool = False) -> PublishService:
    """
    获取发布服务实例
    
    Args:
        use_mock: 是否使用mock接口（已废弃，始终使用真实接口）
    """
    global publish_service
    if not publish_service:
        # 强制使用真实接口，忽略use_mock参数
        publish_service = PublishService(use_mock=False)
        logger.info("初始化发布服务，强制使用真实YouTube上传API")
    return publish_service