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
from datetime import datetime
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
            use_mock: 是否使用mock接口（测试用）
        """
        self.db = get_db_manager()
        self.account_service = get_account_service()
        self.use_mock = use_mock
        self.upload_url = MOCK_UPLOAD_API_URL if use_mock else UPLOAD_API_URL
        logger.info(f"发布服务初始化，使用{'Mock' if use_mock else '真实'}上传接口: {self.upload_url}")
    
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
            publish_data = {
                'publish_id': publish_id,
                'task_id': task_id,
                'account_id': account_id,
                'video_path': video_path,
                'video_title': video_title or youtube_metadata.get('title', f"Video {task_id}"),
                'video_description': video_description or youtube_metadata.get('description', ''),
                'video_tags': video_tags or youtube_metadata.get('tags', []),
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
                    'upload_started_at': datetime.now()
                })
                
                # 构建上传请求 - 符合真实YouTube上传API格式
                upload_request = {
                    'tasks': [
                        {
                            'profileId': account['profile_id'],  # 比特浏览器Profile ID
                            'video': {
                                'uid': publish_id,  # 任务唯一标识
                                'path': publish_task.video_path,  # 视频文件路径
                                'title': publish_task.video_title,  # 视频标题
                                'description': publish_task.video_description,  # 视频描述
                                'tags': json.loads(publish_task.video_tags) if publish_task.video_tags else [],  # 标签数组
                                'visibility': publish_task.privacy_status  # 可见性 (public/unlisted/private)
                            }
                        }
                    ]
                }
                
                # 添加缩略图路径（如果有）- 这是唯一需要的可选参数
                if publish_task.thumbnail_path and Path(publish_task.thumbnail_path).exists():
                    upload_request['tasks'][0]['video']['thumbnail'] = publish_task.thumbnail_path
                
                logger.info(f"发送上传请求到 {self.upload_url}")
                logger.debug(f"请求数据: {json.dumps(upload_request, ensure_ascii=False)}")
                
                # 发送HTTP请求
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.upload_url,
                        json=upload_request,
                        timeout=aiohttp.ClientTimeout(total=600)  # 10分钟超时
                    ) as response:
                        response_data = await response.json()
                        logger.info(f"收到上传响应: {response.status}")
                        logger.debug(f"响应数据: {json.dumps(response_data, ensure_ascii=False)}")
                        
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
                                        'upload_completed_at': datetime.now()
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
                                        'upload_completed_at': datetime.now()
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
                                    'upload_completed_at': datetime.now()
                                })
                                return {'success': False, 'error': error_msg}
                        else:
                            # HTTP状态码非200
                            error_msg = f"HTTP错误: {response.status}"
                            self.db.update_publish_task(publish_id, {
                                'status': 'failed',
                                'error_message': error_msg,
                                'upload_response': response_data if 'response_data' in locals() else None,
                                'upload_completed_at': datetime.now()
                            })
                            return {'success': False, 'error': error_msg}
                            
        except asyncio.TimeoutError:
            error_msg = '上传超时'
            self.db.update_publish_task(publish_id, {
                'status': 'failed',
                'error_message': error_msg,
                'upload_completed_at': datetime.now()
            })
            logger.error(f"上传超时: {publish_id}")
            return {'success': False, 'error': error_msg}
            
        except Exception as e:
            error_msg = str(e)
            self.db.update_publish_task(publish_id, {
                'status': 'failed',
                'error_message': error_msg,
                'upload_completed_at': datetime.now()
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
        获取发布历史
        
        Args:
            task_id: Pipeline任务ID筛选
            account_id: 账号ID筛选
            status: 状态筛选
            limit: 返回数量限制
        
        Returns:
            发布任务列表
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
            return [task.to_dict() for task in tasks]
    
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
    """获取发布服务实例"""
    global publish_service
    if not publish_service:
        publish_service = PublishService(use_mock=use_mock)
    return publish_service