#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版Pipeline API服务器
集成数据库支持任务历史记录和多账号发布
"""

import os
import sys
import platform

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio
import json
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
import heapq
import threading
import time

# 加载环境变量 - 必须在其他操作之前
from config_loader import load_env_file
load_env_file()

# 配置日志
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()

try:
    from utils.logging_config import setup_logging
    logger = setup_logging(
        name=__name__,
        level=log_level,
        log_file='api_with_db.log'
    )
except ImportError:
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('api_with_db.log', encoding='utf-8')
        ]
    )
    logger = logging.getLogger(__name__)

# 导入数据库和服务模块
from database import init_database, get_db_manager
from account_service import get_account_service
from publish_service import get_publish_service

# 初始化数据库
db_manager = init_database()
account_service = get_account_service()
publish_service = get_publish_service(use_mock=os.environ.get('USE_MOCK_UPLOAD', 'true').lower() == 'true')

# 初始化账号数据（只在账号表为空时初始化）
# 如果已有账号数据，不会重置
try:
    existing_accounts = account_service.get_all_accounts(active_only=False)
    if not existing_accounts:
        logger.info("账号表为空，初始化默认账号...")
        account_service.initialize_accounts()
    else:
        logger.info(f"已存在 {len(existing_accounts)} 个账号，跳过初始化")
except Exception as e:
    logger.warning(f"检查账号时出错: {e}，尝试初始化...")
    account_service.initialize_accounts()

# ============ 定时发布调度器 ============
class PublishScheduler:
    """定时发布调度器"""
    
    def __init__(self):
        """初始化调度器"""
        self.task_heap = []  # 小顶堆，存储(scheduled_time, publish_id)
        self.lock = threading.Lock()
        self.running = False
        self.scheduler_thread = None
        self.check_interval = 30  # 检查间隔（秒）
        logger.info("定时发布调度器初始化完成")
    
    def start(self):
        """启动调度器"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            # 加载已存在的定时任务
            self._load_scheduled_tasks()
            logger.info("定时发布调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("定时发布调度器已停止")
    
    def add_task(self, publish_id: str, scheduled_time: datetime):
        """添加定时任务"""
        with self.lock:
            heapq.heappush(self.task_heap, (scheduled_time, publish_id))
            logger.info(f"添加定时发布任务: {publish_id} 计划时间: {scheduled_time}")
    
    def remove_task(self, publish_id: str):
        """移除定时任务"""
        with self.lock:
            self.task_heap = [(t, pid) for t, pid in self.task_heap if pid != publish_id]
            heapq.heapify(self.task_heap)
            logger.info(f"移除定时发布任务: {publish_id}")
    
    def _load_scheduled_tasks(self):
        """从数据库加载已存在的定时任务"""
        try:
            with db_manager.get_session() as session:
                from database import PublishTask
                # 查询所有待发布的定时任务
                scheduled_tasks = session.query(PublishTask).filter(
                    PublishTask.is_scheduled == True,
                    PublishTask.status == 'pending',
                    PublishTask.scheduled_time != None
                ).all()
                
                with self.lock:
                    for task in scheduled_tasks:
                        heapq.heappush(self.task_heap, (task.scheduled_time, task.publish_id))
                
                logger.info(f"从数据库加载了 {len(scheduled_tasks)} 个定时发布任务")
        except Exception as e:
            logger.error(f"加载定时任务失败: {e}")
    
    def _run_scheduler(self):
        """调度器主循环"""
        logger.info("调度器主循环开始运行")
        
        while self.running:
            try:
                now = datetime.now()
                tasks_to_execute = []
                
                # 获取需要执行的任务
                with self.lock:
                    while self.task_heap and self.task_heap[0][0] <= now:
                        scheduled_time, publish_id = heapq.heappop(self.task_heap)
                        tasks_to_execute.append((scheduled_time, publish_id))
                
                # 执行任务
                for scheduled_time, publish_id in tasks_to_execute:
                    try:
                        logger.info(f"执行定时发布任务: {publish_id} (计划时间: {scheduled_time})")
                        # 异步执行上传
                        asyncio.run(self._execute_publish(publish_id))
                    except Exception as e:
                        logger.error(f"执行定时发布任务失败 {publish_id}: {e}")
                
                # 休眠一段时间
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"调度器循环出错: {e}")
                time.sleep(self.check_interval)
    
    async def _execute_publish(self, publish_id: str):
        """执行发布任务"""
        try:
            # 使用现有的发布服务执行上传
            result = await asyncio.to_thread(publish_service.upload_to_youtube, publish_id)
            if result['success']:
                logger.info(f"定时发布任务成功: {publish_id}")
            else:
                logger.error(f"定时发布任务失败: {publish_id} - {result.get('error')}")
        except Exception as e:
            logger.error(f"执行发布任务异常 {publish_id}: {e}")
    
    def get_queue_status(self):
        """获取队列状态"""
        with self.lock:
            tasks = sorted(self.task_heap)
            return {
                'total': len(tasks),
                'next_task': tasks[0] if tasks else None,
                'tasks': [{'scheduled_time': t[0].isoformat(), 'publish_id': t[1]} for t in tasks[:10]]
            }

# 创建调度器实例
publish_scheduler = PublishScheduler()

# 启动时打印环境变量状态
logger.info("=" * 60)
logger.info("增强版API服务启动")
logger.info(f"LOG_LEVEL: {log_level}")
logger.info(f"DB_PATH: {os.environ.get('DB_PATH', './data/pipeline_tasks.db')}")
logger.info(f"USE_MOCK_UPLOAD: {os.environ.get('USE_MOCK_UPLOAD', 'true')}")
logger.info(f"YTENGINE_HOST: {os.environ.get('YTENGINE_HOST', 'http://localhost:51077')}")
logger.info("=" * 60)

app = FastAPI(title="Video Pipeline API with DB", version="0.2.0")

# ============ 应用生命周期事件 ============
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    publish_scheduler.start()
    logger.info("应用启动完成，定时发布调度器已启动")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    publish_scheduler.stop()
    logger.info("应用关闭，定时发布调度器已停止")

# ============ 数据模型 ============
class PipelineRequest(BaseModel):
    video_id: str
    creator_id: str
    account_name: Optional[str] = None  # 发布账号名称（可选）
    gender: int = 1  # 0=男性, 1=女性
    duration: int = 60  # 每张图片持续时间
    image_dir: Optional[str] = None
    export_video: bool = False
    enable_subtitle: bool = True

class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    current_stage: Optional[str] = None
    progress: Dict[str, str]
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_duration: Optional[float] = None
    error: Optional[str] = None  # 错误信息

class TaskResult(BaseModel):
    task_id: str
    status: str
    youtube_metadata: Optional[Dict[str, Any]] = None
    video_path: Optional[str] = None
    preview_url: Optional[str] = None
    draft_path: Optional[str] = None
    audio_path: Optional[str] = None
    story_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    error: Optional[str] = None
    publish_tasks: Optional[List[Dict[str, Any]]] = None

class PublishRequest(BaseModel):
    task_id: str
    account_ids: List[str]  # 发布到的账号ID列表
    video_title: Optional[str] = None
    video_description: Optional[str] = None
    video_tags: Optional[List[str]] = None
    thumbnail_path: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    publish_interval_hours: Optional[float] = None  # 发布间隔（小时）
    privacy_status: str = 'public'

class HistoryQuery(BaseModel):
    creator_id: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 20

# ============ Pipeline执行 ============

async def run_pipeline_async(task_id: str, request: PipelineRequest):
    """异步运行pipeline（集成数据库）"""
    logger.info(f"[Task {task_id}] 开始执行Pipeline")
    
    try:
        # 更新数据库状态
        db_manager.update_task(task_id, {
            'status': 'running',
            'started_at': datetime.now(),
            'current_stage': '初始化'
        })
        
        # 导入并运行pipeline
        from pipeline_core import VideoPipeline
        from models import PipelineRequest as CoreRequest, Gender, StageStatus
        
        # 转换请求
        core_request = CoreRequest(
            video_id=request.video_id,
            creator_id=request.creator_id,
            account_name=request.account_name,  # 传递账号名称
            gender=Gender(request.gender),
            duration=request.duration,
            image_dir=request.image_dir,
            export_video=request.export_video,
            enable_subtitle=request.enable_subtitle
        )
        
        # 创建pipeline实例
        verbose = os.environ.get('LOG_LEVEL', 'INFO').upper() == 'DEBUG'
        pipeline = VideoPipeline(core_request, verbose=verbose)
        
        # 更新阶段状态
        stages = ["故事二创", "语音生成", "剪映草稿生成"]
        if request.export_video:
            stages.append("视频导出")
        
        progress = {stage: "待处理" for stage in stages}
        db_manager.update_task(task_id, {'progress': progress})
        
        # 分阶段执行pipeline
        loop = asyncio.get_event_loop()
        pipeline.start_time = datetime.now()
        
        # 阶段1: 故事二创
        db_manager.update_task(task_id, {
            'current_stage': '故事二创',
            'progress': {**progress, '故事二创': '运行中'}
        })
        stage1 = await loop.run_in_executor(None, pipeline._run_story_generation)
        pipeline.stages_results.append(stage1)
        progress['故事二创'] = '成功' if stage1.status == StageStatus.SUCCESS else '失败'
        
        # 如果故事二创失败，记录具体错误
        update_data = {'progress': progress}
        if stage1.status != StageStatus.SUCCESS:
            error_msg = stage1.error if stage1.error else "故事二创阶段失败"
            
            # 检查是否是字幕获取失败
            if "transcript" in error_msg.lower() or "subtitle" in error_msg.lower():
                error_msg = f"字幕获取失败: {error_msg}. 您可以手动上传字幕文件后重试。"
            
            update_data['error'] = error_msg
            logger.error(f"[Task {task_id}] 故事二创失败: {error_msg}")
        
        db_manager.update_task(task_id, update_data)
        
        if stage1.status == StageStatus.SUCCESS:
            # 阶段2: 语音生成
            db_manager.update_task(task_id, {
                'current_stage': '语音生成',
                'progress': {**progress, '语音生成': '运行中'}
            })
            stage2 = await loop.run_in_executor(None, pipeline._run_voice_generation)
            pipeline.stages_results.append(stage2)
            progress['语音生成'] = '成功' if stage2.status == StageStatus.SUCCESS else '失败'
            
            # 如果语音生成失败，记录错误
            update_data = {'progress': progress}
            if stage2.status != StageStatus.SUCCESS:
                error_msg = stage2.error if stage2.error else "语音生成阶段失败"
                update_data['error'] = error_msg
                logger.error(f"[Task {task_id}] 语音生成失败: {error_msg}")
            
            db_manager.update_task(task_id, update_data)
            
            if stage2.status == StageStatus.SUCCESS:
                # 阶段3: 剪映草稿生成
                db_manager.update_task(task_id, {
                    'current_stage': '剪映草稿生成',
                    'progress': {**progress, '剪映草稿生成': '运行中'}
                })
                stage3 = await loop.run_in_executor(None, pipeline._run_draft_generation)
                pipeline.stages_results.append(stage3)
                progress['剪映草稿生成'] = '成功' if stage3.status == StageStatus.SUCCESS else '失败'
                
                # 如果剪映草稿生成失败，记录错误
                update_data = {'progress': progress}
                if stage3.status != StageStatus.SUCCESS:
                    error_msg = stage3.error if stage3.error else "剪映草稿生成阶段失败"
                    update_data['error'] = error_msg
                    logger.error(f"[Task {task_id}] 剪映草稿生成失败: {error_msg}")
                
                db_manager.update_task(task_id, update_data)
                
                if stage3.status == StageStatus.SUCCESS and request.export_video:
                    # 阶段4: 视频导出
                    db_manager.update_task(task_id, {
                        'current_stage': '视频导出',
                        'progress': {**progress, '视频导出': '运行中'}
                    })
                    stage4 = await loop.run_in_executor(None, pipeline._run_video_export)
                    pipeline.stages_results.append(stage4)
                    progress['视频导出'] = '成功' if stage4.status == StageStatus.SUCCESS else '失败'
                    
                    # 如果视频导出失败，记录错误
                    update_data = {'progress': progress}
                    if stage4.status != StageStatus.SUCCESS:
                        error_msg = stage4.error if stage4.error else "视频导出阶段失败"
                        update_data['error'] = error_msg
                        logger.error(f"[Task {task_id}] 视频导出失败: {error_msg}")
                    
                    db_manager.update_task(task_id, update_data)
        
        pipeline.end_time = datetime.now()
        total_duration = (pipeline.end_time - pipeline.start_time).total_seconds()
        
        # 收集生成的文件路径
        update_data = {
            'current_stage': None,
            'completed_at': datetime.now(),
            'total_duration': total_duration,
            'progress': progress
        }
        
        # 读取YouTube元数据
        youtube_file = Path(f"./story_result/{request.creator_id}/{request.video_id}/final/youtube_metadata.json")
        if youtube_file.exists():
            try:
                with open(youtube_file, 'r', encoding='utf-8') as f:
                    youtube_metadata = json.load(f)
                    if 'strategy' in youtube_metadata:
                        del youtube_metadata['strategy']
                    update_data['youtube_metadata'] = youtube_metadata
            except Exception as e:
                logger.error(f"读取YouTube元数据失败: {e}")
        
        # 收集文件路径
        story_file = Path(f"./story_result/{request.creator_id}/{request.video_id}/final/story.txt")
        if story_file.exists():
            update_data['story_path'] = str(story_file)
        
        audio_file = Path(f"./output/{request.creator_id}_{request.video_id}_story.mp3")
        if audio_file.exists():
            update_data['audio_path'] = str(audio_file)
        
        # 查找草稿路径
        draft_dir = os.environ.get('DRAFT_LOCAL_DIR')
        if draft_dir:
            draft_base = Path(draft_dir)
            if draft_base.exists():
                pattern = f"{request.creator_id}_{request.video_id}_*"
                drafts = list(draft_base.glob(pattern))
                if drafts:
                    update_data['draft_path'] = str(max(drafts, key=lambda p: p.stat().st_mtime))
        
        # 处理视频路径
        if request.export_video and pipeline.stages_results:
            for stage in pipeline.stages_results:
                if stage.name == "视频导出" and stage.output:
                    try:
                        video_info = json.loads(stage.output)
                        if video_info.get('local_path') and Path(video_info['local_path']).exists():
                            update_data['video_path'] = video_info['local_path']
                        if video_info.get('preview_url'):
                            update_data['preview_url'] = video_info['preview_url']
                    except Exception as e:
                        logger.warning(f"解析视频导出信息失败: {e}")
        
        # 判断整体状态
        all_success = all(status == '成功' for status in progress.values())
        update_data['status'] = 'completed' if all_success else 'failed'
        
        # 更新数据库
        db_manager.update_task(task_id, update_data)
        logger.info(f"[Task {task_id}] Pipeline执行完成，状态: {update_data['status']}")
        
    except Exception as e:
        logger.error(f"[Task {task_id}] Pipeline执行错误: {e}")
        logger.exception("详细错误:")
        db_manager.update_task(task_id, {
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.now(),
            'current_stage': None
        })

# ============ API端点 ============

@app.post("/api/pipeline/run")
async def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    """运行Pipeline（支持数据库记录）"""
    # 生成任务ID - 包含 account_name（如果提供）
    if request.account_name:
        task_id = f"{request.creator_id}_{request.account_name}_{request.video_id}_{uuid.uuid4().hex[:8]}"
    else:
        task_id = f"{request.creator_id}_{request.video_id}_{uuid.uuid4().hex[:8]}"
    
    # 创建数据库记录
    task_data = {
        'task_id': task_id,
        'video_id': request.video_id,
        'creator_id': request.creator_id,
        'account_name': request.account_name,  # 存储账号名称
        'gender': request.gender,
        'duration': request.duration,  # 会被转换为image_duration
        'image_dir': request.image_dir,
        'export_video': request.export_video,
        'enable_subtitle': request.enable_subtitle,
        'progress': {
            "故事二创": "待处理",
            "语音生成": "待处理",
            "剪映草稿生成": "待处理"
        }
    }
    
    if request.export_video:
        task_data['progress']["视频导出"] = "待处理"
    
    # 创建任务记录
    db_task = db_manager.create_task(task_data)
    
    # 添加后台任务
    background_tasks.add_task(run_pipeline_async, task_id, request)
    
    return {
        "task_id": task_id,
        "message": "任务已启动",
        "status_url": f"/api/pipeline/status/{task_id}",
        "result_url": f"/api/pipeline/result/{task_id}"
    }

@app.get("/api/pipeline/status/{task_id}")
async def get_status(task_id: str):
    """获取任务状态（从数据库）"""
    task = db_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_dict = task.to_dict()
    return TaskStatus(
        task_id=task_id,
        status=task_dict['status'],
        current_stage=task_dict.get('current_stage'),
        progress=task_dict.get('progress', {}),
        created_at=task_dict['created_at'],
        started_at=task_dict.get('started_at'),
        completed_at=task_dict.get('completed_at'),
        total_duration=task_dict.get('total_duration'),
        error=task_dict.get('error')  # 添加错误信息
    )

@app.get("/api/pipeline/result/{task_id}")
async def get_result(task_id: str):
    """获取任务结果（从数据库）"""
    task = db_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_dict = task.to_dict()
    
    if task_dict['status'] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail=f"任务未完成，当前状态: {task_dict['status']}")
    
    # 获取发布任务
    publish_tasks = db_manager.get_publish_tasks_by_task(task_id)
    
    return TaskResult(
        task_id=task_id,
        status=task_dict['status'],
        youtube_metadata=task_dict.get('youtube_metadata'),
        video_path=task_dict.get('video_path'),
        preview_url=task_dict.get('preview_url'),
        draft_path=task_dict.get('draft_path'),
        audio_path=task_dict.get('audio_path'),
        story_path=task_dict.get('story_path'),
        thumbnail_path=task_dict.get('thumbnail_path'),
        error=task_dict.get('error'),
        publish_tasks=[pt.to_dict() for pt in publish_tasks]
    )

def get_task_publish_status(task_id: str) -> dict:
    """获取任务的发布状态统计"""
    publish_tasks = db_manager.get_publish_tasks_by_task(task_id)
    
    status_count = {
        'total': len(publish_tasks),
        'success': 0,
        'pending': 0,
        'uploading': 0,
        'failed': 0
    }
    
    published_accounts = []
    
    for pt in publish_tasks:
        # 统计各状态数量
        if pt.status == 'success':
            status_count['success'] += 1
        elif pt.status == 'pending':
            status_count['pending'] += 1
        elif pt.status == 'uploading':
            status_count['uploading'] += 1
        elif pt.status == 'failed':
            status_count['failed'] += 1
        
        # 获取账号信息
        account = account_service.get_account_by_id(pt.account_id)
        published_accounts.append({
            'publish_id': pt.publish_id,  # 添加publish_id
            'account_id': pt.account_id,
            'account_name': account['account_name'] if account else pt.account_id,
            'status': pt.status,
            'youtube_video_url': pt.youtube_video_url,
            'published_at': pt.upload_completed_at.isoformat() if pt.upload_completed_at else None,
            'error_message': pt.error_message
        })
    
    return {
        'publish_status': status_count,
        'published_accounts': published_accounts
    }

# ============ 认证相关 API ============
@app.post("/api/auth/login")
async def login(credentials: dict):
    """登录接口"""
    username = credentials.get('username')
    password = credentials.get('password')
    
    # 简单的模拟登录验证
    # 实际应该验证数据库中的用户信息
    if username and password:
        return {
            "username": username,
            "api_key": f"sk_{username}_mock_key",
            "message": "登录成功"
        }
    
    raise HTTPException(status_code=401, detail="用户名或密码错误")

@app.post("/api/auth/register")
async def register(user_data: dict):
    """注册接口"""
    username = user_data.get('username')
    password = user_data.get('password')
    invite_code = user_data.get('invite_code')  # 修正字段名
    
    # 验证邀请码
    if invite_code != "15361578057":
        raise HTTPException(status_code=400, detail="邀请码无效")
    
    # 简单的模拟注册
    if username and password:
        return {
            "username": username,
            "api_key": f"sk_{username}_mock_key",
            "message": "注册成功"
        }
    
    raise HTTPException(status_code=400, detail="注册信息不完整")

@app.get("/api/pipeline/tasks")
async def get_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取任务列表（使用history接口的数据）"""
    # 计算分页
    offset = (page - 1) * page_size
    
    # 查询数据库
    tasks = db_manager.get_tasks_history(
        limit=page_size,
        offset=offset
    )
    
    # 为每个任务添加发布状态
    tasks_with_publish = []
    for task in tasks:
        task_dict = task.to_dict()
        # 添加发布状态信息
        publish_info = get_task_publish_status(task.task_id)
        task_dict.update(publish_info)
        tasks_with_publish.append(task_dict)
    
    return {
        "total": len(tasks_with_publish),
        "page": page,
        "page_size": page_size,
        "tasks": tasks_with_publish
    }

@app.get("/api/pipeline/history")
async def get_history(
    creator_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """查询任务历史"""
    # 解析日期
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    # 计算分页
    offset = (page - 1) * page_size
    
    # 查询数据库
    tasks = db_manager.get_tasks_history(
        creator_id=creator_id,
        status=status,
        start_date=start_dt,
        end_date=end_dt,
        limit=page_size,
        offset=offset
    )
    
    # 获取总数（简化处理，实际应该单独查询）
    total = len(tasks)  # 这里简化了，实际应该查询总数
    
    # 为每个任务添加发布状态
    tasks_with_publish = []
    for task in tasks:
        task_dict = task.to_dict()
        # 添加发布状态信息
        publish_info = get_task_publish_status(task.task_id)
        task_dict.update(publish_info)
        tasks_with_publish.append(task_dict)
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "tasks": tasks_with_publish
    }

@app.get("/api/pipeline/statistics")
async def get_statistics(creator_id: Optional[str] = Query(None)):
    """获取统计信息"""
    stats = db_manager.get_statistics(creator_id)
    return stats

@app.post("/api/pipeline/retry/{task_id}")
async def retry_task(task_id: str, background_tasks: BackgroundTasks):
    """重试失败的任务
    
    为失败的任务创建新的任务ID并重新执行，保留原始参数
    """
    # 获取原始任务
    original_task = db_manager.get_task(task_id)
    if not original_task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_dict = original_task.to_dict()
    
    # 检查任务状态
    if task_dict['status'] not in ['failed', 'completed']:
        raise HTTPException(
            status_code=400, 
            detail=f"只能重试失败或已完成的任务，当前状态: {task_dict['status']}"
        )
    
    # 获取原始参数
    creator_id = task_dict['creator_id']
    video_id = task_dict['video_id'] 
    account_name = task_dict.get('account_name')
    
    # 创建请求对象（使用原任务的所有参数）
    retry_request = PipelineRequest(
        video_id=video_id,
        creator_id=creator_id,
        account_name=account_name,
        gender=task_dict.get('gender', 1),
        duration=task_dict.get('image_duration', 60),
        image_dir=task_dict.get('image_dir'),
        export_video=task_dict.get('export_video', False),
        enable_subtitle=task_dict.get('enable_subtitle', True)
    )
    
    # 重置原任务的状态和进度
    reset_data = {
        'status': 'pending',
        'started_at': None,
        'completed_at': None,
        'current_stage': None,
        'error_message': None,
        'retry_count': task_dict.get('retry_count', 0) + 1,
        'progress': {
            "故事二创": "待处理",
            "语音生成": "待处理",
            "剪映草稿生成": "待处理"
        }
    }
    
    if retry_request.export_video:
        reset_data['progress']["视频导出"] = "待处理"
    
    # 更新原任务状态
    db_manager.update_task(task_id, reset_data)
    
    # 后台执行（使用原任务ID）
    background_tasks.add_task(run_pipeline_async, task_id, retry_request)
    
    logger.info(f"重试任务: {task_id} (第 {reset_data['retry_count']} 次重试)")
    
    return {
        "task_id": task_id,
        "message": f"任务已开始重试 (第 {reset_data['retry_count']} 次)",
        "retry_count": reset_data['retry_count'],
        "status_url": f"/api/pipeline/status/{task_id}",
        "result_url": f"/api/pipeline/result/{task_id}"
    }

# ============ 发布相关端点 ============

@app.post("/api/publish/schedule")
async def schedule_publish(request: PublishRequest):
    """创建定时发布任务（支持立即发布、定时发布和间隔发布）"""
    results = []
    immediate_tasks = []
    scheduled_tasks = []
    
    # 计算发布时间
    current_time = datetime.now()
    
    for i, account_id in enumerate(request.account_ids):
        # 计算每个账号的发布时间
        if request.publish_interval_hours is not None and request.publish_interval_hours > 0:
            # 间隔发布模式：第一个立即发布，后续按间隔时间递增
            if i == 0:
                scheduled_time = None  # 第一个立即发布
            else:
                scheduled_time = current_time + timedelta(hours=request.publish_interval_hours * i)
        else:
            # 使用传入的定时时间或立即发布
            scheduled_time = request.scheduled_time
        
        # 创建发布任务
        publish_task = publish_service.create_publish_task(
            task_id=request.task_id,
            account_id=account_id,
            video_title=request.video_title,
            video_description=request.video_description,
            video_tags=request.video_tags,
            thumbnail_path=request.thumbnail_path,
            scheduled_time=scheduled_time,
            privacy_status=request.privacy_status
        )
        
        if publish_task:
            if scheduled_time and scheduled_time > current_time:
                # 定时发布：添加到调度器
                publish_scheduler.add_task(publish_task['publish_id'], scheduled_time)
                scheduled_tasks.append(publish_task)
                results.append({
                    'publish_id': publish_task['publish_id'],
                    'account_id': account_id,
                    'status': 'scheduled',
                    'scheduled_time': scheduled_time.isoformat(),
                    'message': f'已安排在 {scheduled_time.strftime("%Y-%m-%d %H:%M:%S")} 发布'
                })
            else:
                # 立即发布
                immediate_tasks.append(publish_task)
                # 异步执行上传
                asyncio.create_task(asyncio.to_thread(
                    publish_service.upload_to_youtube, 
                    publish_task['publish_id']
                ))
                results.append({
                    'publish_id': publish_task['publish_id'],
                    'account_id': account_id,
                    'status': 'uploading',
                    'message': '正在上传到YouTube'
                })
        else:
            results.append({
                'account_id': account_id,
                'status': 'failed',
                'error': '创建发布任务失败'
            })
    
    return {
        "message": f"创建了 {len(results)} 个发布任务（{len(immediate_tasks)}个立即发布，{len(scheduled_tasks)}个定时发布）",
        "results": results,
        "summary": {
            "total": len(results),
            "immediate": len(immediate_tasks),
            "scheduled": len(scheduled_tasks),
            "failed": len([r for r in results if r.get('status') == 'failed'])
        }
    }


@app.post("/api/publish/execute/{publish_id}")
async def execute_publish(publish_id: str, background_tasks: BackgroundTasks):
    """执行发布任务（上传到YouTube）"""
    # 异步执行上传
    background_tasks.add_task(publish_service.upload_to_youtube, publish_id)
    
    return {
        "message": "发布任务已启动",
        "publish_id": publish_id
    }

@app.post("/api/publish/batch")
async def batch_publish(request: PublishRequest, background_tasks: BackgroundTasks):
    """批量发布（创建并执行）"""
    results = []
    
    for account_id in request.account_ids:
        # 创建发布任务
        publish_task = publish_service.create_publish_task(
            task_id=request.task_id,
            account_id=account_id,
            video_title=request.video_title,
            video_description=request.video_description,
            video_tags=request.video_tags,
            thumbnail_path=request.thumbnail_path,
            scheduled_time=request.scheduled_time,
            privacy_status=request.privacy_status
        )
        
        if publish_task:
            # 执行上传
            background_tasks.add_task(
                publish_service.upload_to_youtube,
                publish_task['publish_id']
            )
            results.append({
                'publish_id': publish_task['publish_id'],
                'account_id': account_id,
                'status': 'started'
            })
        else:
            results.append({
                'account_id': account_id,
                'status': 'failed',
                'error': '创建发布任务失败'
            })
    
    return {
        "message": f"启动了 {len(results)} 个发布任务",
        "results": results
    }

@app.get("/api/publish/history")
async def get_publish_history(
    task_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
):
    """查询发布历史"""
    history = publish_service.get_publish_history(
        task_id=task_id,
        account_id=account_id,
        status=status,
        limit=limit
    )
    return {
        "total": len(history),
        "publish_tasks": history
    }

@app.post("/api/publish/retry/{publish_id}")
async def retry_publish(publish_id: str, background_tasks: BackgroundTasks):
    """重试失败的发布"""
    # 首先检查发布任务是否存在
    publish_task = db_manager.get_publish_task(publish_id)
    if not publish_task:
        raise HTTPException(status_code=404, detail="发布任务不存在")
    
    # 检查任务状态是否允许重试（只允许失败或取消的任务重试）
    if publish_task.status not in ['failed', 'cancelled']:
        raise HTTPException(
            status_code=400, 
            detail=f"任务状态不允许重试，当前状态: {publish_task.status}"
        )
    
    background_tasks.add_task(publish_service.retry_failed_publish, publish_id)
    
    return {
        "message": "重试任务已启动",
        "publish_id": publish_id
    }

@app.delete("/api/publish/task/{publish_id}")
async def delete_publish_task(publish_id: str):
    """删除发布任务记录"""
    # 检查发布任务是否存在
    publish_task = db_manager.get_publish_task(publish_id)
    if not publish_task:
        raise HTTPException(status_code=404, detail="发布任务不存在")
    
    # 检查任务状态，如果正在上传则不允许删除
    if publish_task.status == 'uploading':
        raise HTTPException(
            status_code=400, 
            detail="正在上传的任务不能删除，请等待上传完成或失败后再删除"
        )
    
    # 如果是定时任务且还未执行，从调度器中移除
    if publish_task.is_scheduled and publish_task.status == 'pending':
        publish_scheduler.remove_task(publish_id)
        logger.info(f"已从定时发布调度器中移除任务: {publish_id}")
    
    # 删除数据库记录
    success = db_manager.delete_publish_task(publish_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除发布任务失败")
    
    return {
        "message": "发布任务已删除",
        "publish_id": publish_id
    }

@app.get("/api/publish/scheduler/queue")
async def get_scheduler_queue():
    """获取定时发布队列状态"""
    return publish_scheduler.get_queue_status()

@app.delete("/api/publish/scheduler/{publish_id}")
async def cancel_scheduled_publish(publish_id: str):
    """取消定时发布任务"""
    # 从调度器移除
    publish_scheduler.remove_task(publish_id)
    
    # 更新数据库状态
    db_manager.update_publish_task(publish_id, {
        'status': 'cancelled',
        'error_message': '任务已取消'
    })
    
    return {
        "message": "定时发布任务已取消",
        "publish_id": publish_id
    }

@app.post("/api/publish/scheduler/reschedule/{publish_id}")
async def reschedule_publish(publish_id: str, new_time: datetime):
    """重新安排发布时间"""
    # 从调度器移除旧任务
    publish_scheduler.remove_task(publish_id)
    
    # 更新数据库
    db_manager.update_publish_task(publish_id, {
        'scheduled_time': new_time,
        'is_scheduled': True,
        'status': 'pending'
    })
    
    # 添加新的定时任务
    publish_scheduler.add_task(publish_id, new_time)
    
    return {
        "message": f"发布时间已更新为 {new_time}",
        "publish_id": publish_id,
        "new_scheduled_time": new_time.isoformat()
    }

# ============ 账号管理端点 ============

@app.get("/api/accounts")
async def get_accounts(active_only: bool = Query(True)):
    """获取所有账号"""
    accounts = account_service.get_all_accounts(active_only=active_only)
    return {
        "total": len(accounts),
        "accounts": accounts
    }

@app.get("/api/accounts/{account_id}")
async def get_account(account_id: str):
    """获取单个账号信息"""
    account = account_service.get_account_by_id(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return account

@app.get("/api/accounts/{account_id}/statistics")
async def get_account_statistics(account_id: str):
    """获取账号统计信息"""
    stats = account_service.get_account_statistics(account_id)
    return stats

@app.put("/api/accounts/{account_id}/status")
async def update_account_status(account_id: str, is_active: bool):
    """更新账号状态"""
    success = account_service.update_account_status(account_id, is_active)
    if not success:
        raise HTTPException(status_code=404, detail="账号不存在")
    return {"message": f"账号状态已更新为 {'激活' if is_active else '禁用'}"}

# ============ 其他端点 ============

@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected",
        "accounts_loaded": len(account_service.get_all_accounts(active_only=False))
    }

@app.get("/")
async def root():
    """API根路径"""
    return {
        "name": "Video Pipeline API with Database",
        "version": "0.2.0",
        "endpoints": {
            "pipeline": {
                "run": "/api/pipeline/run",
                "status": "/api/pipeline/status/{task_id}",
                "result": "/api/pipeline/result/{task_id}",
                "retry": "/api/pipeline/retry/{task_id}",
                "history": "/api/pipeline/history",
                "statistics": "/api/pipeline/statistics"
            },
            "publish": {
                "schedule": "/api/publish/schedule",
                "create": "/api/publish/create",
                "execute": "/api/publish/execute/{publish_id}",
                "batch": "/api/publish/batch",
                "history": "/api/publish/history",
                "retry": "/api/publish/retry/{publish_id}",
                "delete_task": "/api/publish/task/{publish_id}",
                "scheduler_queue": "/api/publish/scheduler/queue",
                "cancel_scheduled": "/api/publish/scheduler/{publish_id}",
                "reschedule": "/api/publish/scheduler/reschedule/{publish_id}"
            },
            "accounts": {
                "list": "/api/accounts",
                "detail": "/api/accounts/{account_id}",
                "statistics": "/api/accounts/{account_id}/statistics",
                "update_status": "/api/accounts/{account_id}/status"
            },
            "health": "/health"
        }
    }

# ============ 启动服务器 ============
if __name__ == "__main__":
    import uvicorn
    print("启动增强版Pipeline API服务器...")
    print("访问 http://localhost:51082 查看API")
    print("访问 http://localhost:51082/docs 查看交互式文档")
    print("按 Ctrl+C 停止服务器\n")
    
    uvicorn.run(app, host="0.0.0.0", port=51082)