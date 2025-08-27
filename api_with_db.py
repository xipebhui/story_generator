#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版Pipeline API服务器
集成数据库支持任务历史记录和多账号发布
"""

import os
import sys
import platform

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, File, UploadFile, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
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
from database import init_database, get_db_manager, PipelineTask, PublishTask, User
from account_service import get_account_service
from publish_service import get_publish_service
from auth_middleware import (
    get_current_user, require_auth, hash_password, verify_password,
    generate_api_key, get_invite_code, get_auth_enabled
)

# 初始化数据库
db_manager = init_database()
account_service = get_account_service()
# 始终使用真实的YouTube上传API
publish_service = get_publish_service(use_mock=False)  # 强制使用真实接口

# 初始化账号数据
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

# 配置CORS
if os.environ.get('CORS_ENABLED', 'true').lower() == 'true':
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.environ.get('CORS_ORIGIN', 'http://localhost:3000')],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
    privacy_status: str = 'public'

class HistoryQuery(BaseModel):
    creator_id: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    page_size: int = 20

# ============ 认证相关模型 ============
class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    invite_code: str

class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str

class AuthResponse(BaseModel):
    """认证响应"""
    username: str
    api_key: str
    message: str

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

# ============ 认证接口 ============

@app.post("/api/auth/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """用户注册"""
    # 验证邀请码
    if request.invite_code != get_invite_code():
        raise HTTPException(status_code=400, detail="无效的邀请码")
    
    # 检查用户名是否已存在
    db_manager = get_db_manager()
    existing_user = db_manager.get_user_by_username(request.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建新用户
    user_data = {
        'username': request.username,
        'password_hash': hash_password(request.password),
        'api_key': generate_api_key(),
        'is_active': True
    }
    
    try:
        user = db_manager.create_user(user_data)
        return AuthResponse(
            username=user.username,
            api_key=user.api_key,
            message="注册成功"
        )
    except Exception as e:
        logger.error(f"注册失败: {e}")
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")

@app.post("/api/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """用户登录"""
    db_manager = get_db_manager()
    user = db_manager.get_user_by_username(request.username)
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")
    
    # 更新最后登录时间
    from datetime import datetime
    db_manager.update_user(user.id, {'last_login': datetime.now()})
    
    return AuthResponse(
        username=user.username,
        api_key=user.api_key,
        message="登录成功"
    )

@app.post("/api/auth/change-password", response_model=Dict[str, str])
async def change_password(request: ChangePasswordRequest, current_user: User = Depends(require_auth)):
    """修改密码（需要认证）"""
    db_manager = get_db_manager()
    
    # 验证旧密码
    if not verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")
    
    # 更新密码
    update_data = {
        'password_hash': hash_password(request.new_password)
    }
    
    updated_user = db_manager.update_user(current_user.id, update_data)
    if updated_user:
        return {"message": "密码修改成功"}
    else:
        raise HTTPException(status_code=500, detail="密码修改失败")

@app.post("/api/auth/reset-api-key", response_model=AuthResponse)
async def reset_api_key(current_user: User = Depends(require_auth)):
    """重置API Key（需要认证）"""
    db_manager = get_db_manager()
    
    # 生成新的API Key
    new_api_key = generate_api_key()
    update_data = {
        'api_key': new_api_key
    }
    
    updated_user = db_manager.update_user(current_user.id, update_data)
    if updated_user:
        return AuthResponse(
            username=updated_user.username,
            api_key=updated_user.api_key,
            message="API Key重置成功"
        )
    else:
        raise HTTPException(status_code=500, detail="API Key重置失败")

@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(require_auth)):
    """获取当前用户信息（需要认证）"""
    # 确定用户状态
    if not current_user.is_active:
        status = "inactive"
    elif hasattr(current_user, 'status'):
        status = current_user.status
    else:
        status = "active"
    
    return {
        "username": current_user.username,
        "api_key": current_user.api_key,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "status": status
    }

# ============ Pipeline接口 ============

@app.post("/api/pipeline/run")
async def run_pipeline(
    request: PipelineRequest, 
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user)
):
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
async def get_status(
    task_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
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
async def get_result(
    task_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
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
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "tasks": [task.to_dict() for task in tasks]
    }

@app.get("/api/pipeline/statistics")
async def get_statistics(
    creator_id: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user)
):
    """获取统计信息"""
    stats = db_manager.get_statistics(creator_id)
    return stats

@app.delete("/api/pipeline/task/{task_id}")
async def delete_task(
    task_id: str,
    current_user: Optional[User] = Depends(get_current_user)
):
    """删除任务（仅删除数据库记录）
    
    Args:
        task_id: 任务ID
    
    Returns:
        删除结果信息
    """
    # 检查任务是否存在
    task = db_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 删除相关的发布任务
    deleted_publish_count = 0
    try:
        publish_tasks = db_manager.get_publish_tasks_by_task(task_id)
        deleted_publish_count = len(publish_tasks)
        if deleted_publish_count > 0:
            with db_manager.get_session() as session:
                for pt in publish_tasks:
                    # 重新查询以确保对象关联到当前会话
                    publish_task = session.query(PublishTask).filter_by(id=pt.id).first()
                    if publish_task:
                        session.delete(publish_task)
                session.commit()
            logger.info(f"删除了 {deleted_publish_count} 个相关发布任务")
    except Exception as e:
        logger.error(f"删除发布任务失败: {e}")
    
    # 删除任务记录
    try:
        with db_manager.get_session() as session:
            # 重新查询任务以确保关联到当前会话
            task_to_delete = session.query(PipelineTask).filter_by(task_id=task_id).first()
            if task_to_delete:
                session.delete(task_to_delete)
                session.commit()
                logger.info(f"成功删除任务: {task_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")
    
    return {
        "message": "任务删除成功",
        "task_id": task_id,
        "deleted_publish_tasks": deleted_publish_count
    }

@app.post("/api/pipeline/retry/{task_id}")
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user)
):
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
    
    # 生成新的任务ID
    parts = task_id.split('_')
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="无效的任务ID格式")
    
    # 获取原始参数
    creator_id = task_dict['creator_id']
    video_id = task_dict['video_id'] 
    account_name = task_dict.get('account_name')
    
    # 生成新的任务ID（使用新的UUID）
    if account_name:
        new_task_id = f"{creator_id}_{account_name}_{video_id}_{uuid.uuid4().hex[:8]}"
    else:
        new_task_id = f"{creator_id}_{video_id}_{uuid.uuid4().hex[:8]}"
    
    # 创建新的请求对象
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
    
    # 创建新的任务记录
    new_task_data = {
        'task_id': new_task_id,
        'video_id': video_id,
        'creator_id': creator_id,
        'account_name': account_name,
        'gender': retry_request.gender,
        'duration': retry_request.duration,
        'image_dir': retry_request.image_dir,
        'export_video': retry_request.export_video,
        'enable_subtitle': retry_request.enable_subtitle,
        'progress': {
            "故事二创": "待处理",
            "语音生成": "待处理",
            "剪映草稿生成": "待处理"
        }
    }
    
    if retry_request.export_video:
        new_task_data['progress']["视频导出"] = "待处理"
    
    # 创建任务记录
    db_task = db_manager.create_task(new_task_data)
    
    # 添加后台任务
    background_tasks.add_task(run_pipeline_async, new_task_id, retry_request)
    
    return {
        "task_id": new_task_id,
        "message": f"重试任务已创建（原任务: {task_id}）",
        "status_url": f"/api/pipeline/status/{new_task_id}",
        "result_url": f"/api/pipeline/result/{new_task_id}",
        "original_task_id": task_id
    }

# ============ 发布相关端点 ============

@app.post("/api/pipeline/upload-subtitle")
async def upload_subtitle(
    task_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    手动上传字幕文件
    字幕文件将保存到任务的 cache/video_id/raw/subtitle.txt 路径
    """
    try:
        # 获取任务信息
        task = db_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 获取video_id - 从任务记录中直接获取
        video_id = task.video_id
        
        # 创建raw目录
        raw_dir = Path(f"cache/{video_id}/raw")
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存字幕文件
        subtitle_path = raw_dir / "subtitle.txt"
        
        # 读取上传的内容
        content = await file.read()
        
        # 尝试解码为文本
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                text_content = content.decode('gbk')
            except:
                text_content = content.decode('utf-8', errors='ignore')
        
        # 保存文件
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        logger.info(f"✅ 字幕文件上传成功: {subtitle_path}")
        
        # 更新任务状态，标记已有手动字幕
        # 先获取现有的progress
        existing_task = db_manager.get_task(task_id)
        existing_progress = {}
        if existing_task and existing_task.progress:
            try:
                existing_progress = json.loads(existing_task.progress)
            except:
                existing_progress = {}
        
        # 更新progress，注意所有值都应该是字符串
        existing_progress['manual_subtitle'] = 'uploaded'  # 使用字符串而不是布尔值
        existing_progress['subtitle_uploaded_at'] = datetime.now().isoformat()
        
        update_data = {
            'progress': json.dumps(existing_progress)
        }
        db_manager.update_task(task_id, update_data)
        
        return {
            "message": "字幕文件已上传",
            "path": str(subtitle_path),  # 相对路径
            "video_id": video_id,
            "file_size": len(text_content)  # 文件大小（字符数）
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传字幕文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.post("/api/publish/upload-thumbnail")
async def upload_thumbnail(
    task_id: str = Form(...),
    file: UploadFile = File(...)
):
    """上传缩略图文件
    
    Args:
        task_id: 任务ID
        file: 缩略图文件
    
    Returns:
        缩略图保存路径
    """
    # 检查文件类型
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}。只支持: {', '.join(allowed_types)}"
        )
    
    # 检查文件大小（最大2MB）
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    if file_size > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"文件太大: {file_size / 1024 / 1024:.2f}MB。最大允许2MB"
        )
    
    # 重置文件指针
    await file.seek(0)
    
    # 创建缩略图目录
    thumbnail_dir = Path("thumbnails")
    thumbnail_dir.mkdir(exist_ok=True)
    
    # 生成唯一文件名
    file_ext = Path(file.filename).suffix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    thumbnail_filename = f"{task_id}_{timestamp}{file_ext}"
    thumbnail_path = thumbnail_dir / thumbnail_filename
    
    # 保存文件
    try:
        with open(thumbnail_path, "wb") as f:
            f.write(contents)
        logger.info(f"保存缩略图: {thumbnail_path}")
    except Exception as e:
        logger.error(f"保存缩略图失败: {e}")
        raise HTTPException(status_code=500, detail="保存文件失败")
    
    # 获取绝对路径
    absolute_path = thumbnail_path.resolve()
    
    # 更新任务的缩略图路径（如果任务存在）- 保存绝对路径
    task = db_manager.get_task(task_id)
    if task:
        db_manager.update_task(task_id, {
            'thumbnail_path': str(absolute_path)
        })
    
    return {
        "message": "缩略图上传成功",
        "thumbnail_path": str(absolute_path),  # 返回绝对路径
        "relative_path": str(thumbnail_path),   # 也返回相对路径供参考
        "filename": thumbnail_filename,
        "size": file_size
    }

@app.post("/api/publish/schedule")
async def schedule_publish(request: PublishRequest):
    """创建定时发布任务（支持立即发布和定时发布）"""
    results = []
    immediate_tasks = []
    scheduled_tasks = []
    
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
            if request.scheduled_time and request.scheduled_time > datetime.now():
                # 定时发布：添加到调度器
                publish_scheduler.add_task(publish_task['publish_id'], request.scheduled_time)
                scheduled_tasks.append(publish_task)
                results.append({
                    'publish_id': publish_task['publish_id'],
                    'account_id': account_id,
                    'status': 'scheduled',
                    'scheduled_time': request.scheduled_time.isoformat(),
                    'message': f'已安排在 {request.scheduled_time} 发布'
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

@app.post("/api/publish/create")
async def create_publish_task(request: PublishRequest):
    """创建发布任务（保留兼容性）"""
    results = []
    
    for account_id in request.account_ids:
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
            # 如果是定时任务，添加到调度器
            if request.scheduled_time and request.scheduled_time > datetime.now():
                publish_scheduler.add_task(publish_task['publish_id'], request.scheduled_time)
            results.append(publish_task)
        else:
            results.append({
                'account_id': account_id,
                'success': False,
                'error': '创建发布任务失败'
            })
    
    return {
        "message": f"创建了 {len(results)} 个发布任务",
        "publish_tasks": results
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
    limit: int = Query(100, ge=1, le=500),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    查询发布历史
    
    返回数据包含：
    - account_name: 账号名称
    - youtube_channel_name: YouTube频道名称
    - upload_completed_at: 发布完成时间
    - status: 发布状态
    - youtube_video_url: YouTube视频链接
    """
    history = publish_service.get_publish_history(
        task_id=task_id,
        account_id=account_id,
        status=status,
        limit=limit
    )
    
    # 简化返回的数据结构，只返回前端需要的关键字段
    simplified_history = []
    for task in history:
        simplified_history.append({
            'publish_id': task.get('publish_id'),
            'task_id': task.get('task_id'),
            'account_id': task.get('account_id'),
            'account_name': task.get('account_name'),  # 新增：账号名称
            'youtube_channel_name': task.get('youtube_channel_name'),  # 新增：YouTube频道名称
            'video_title': task.get('video_title'),
            'status': task.get('status'),
            'youtube_video_url': task.get('youtube_video_url'),
            'error_message': task.get('error_message'),
            'created_at': task.get('created_at'),
            'upload_completed_at': task.get('upload_completed_at'),  # 发布完成时间
            'privacy_status': task.get('privacy_status')
        })
    
    return {
        "total": len(simplified_history),
        "publish_tasks": simplified_history
    }

@app.post("/api/publish/retry/{publish_id}")
async def retry_publish(publish_id: str, background_tasks: BackgroundTasks):
    """重试失败的发布"""
    background_tasks.add_task(publish_service.retry_failed_publish, publish_id)
    
    return {
        "message": "重试任务已启动",
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

class CreateAccountRequest(BaseModel):
    """创建账号请求模型"""
    account_id: str
    account_name: str
    profile_id: str
    window_number: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    channel_url: Optional[str] = None

@app.post("/api/accounts")
async def create_account(
    request: CreateAccountRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    创建新账号
    
    必需字段:
    - account_id: 账号唯一标识
    - account_name: 账号名称
    - profile_id: 比特浏览器Profile ID
    
    可选字段:
    - window_number: 窗口序号
    - description: 描述信息
    - is_active: 是否激活（默认True）
    - channel_url: YouTube频道URL
    """
    # 构建账号数据
    account_data = {
        'account_id': request.account_id,
        'account_name': request.account_name,
        'profile_id': request.profile_id,
        'window_number': request.window_number,
        'description': request.description,
        'is_active': request.is_active,
        'channel_url': request.channel_url
    }
    
    # 过滤掉None值
    account_data = {k: v for k, v in account_data.items() if v is not None}
    
    # 创建账号
    account = account_service.create_account(account_data)
    if not account:
        raise HTTPException(
            status_code=400,
            detail="创建账号失败，可能账号ID已存在或缺少必需字段"
        )
    
    logger.info(f"用户 {current_user.username if current_user else 'anonymous'} 创建了账号 {request.account_id}")
    
    return {
        "message": f"账号 {request.account_name} 创建成功",
        "account": account
    }

@app.delete("/api/accounts/{account_id}")
async def delete_account(
    account_id: str,
    force: bool = Query(False, description="强制删除，即使有发布任务"),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    删除账号
    
    注意：
    - 如果账号有相关的发布任务，默认只会标记为不活跃而非真正删除
    - 使用 force=true 参数可以强制删除（慎用）
    """
    # 检查账号是否存在
    account = account_service.get_account_by_id(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    # 删除账号
    success = account_service.delete_account(account_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除账号失败")
    
    logger.info(f"用户 {current_user.username if current_user else 'anonymous'} 删除了账号 {account_id}")
    
    # 检查是否是软删除（标记为不活跃）
    account_after = account_service.get_account_by_id(account_id)
    if account_after and not account_after.get('is_active'):
        return {
            "message": f"账号 {account['account_name']} 有相关发布任务，已标记为不活跃",
            "action": "deactivated",
            "account_id": account_id
        }
    else:
        return {
            "message": f"账号 {account['account_name']} 已删除",
            "action": "deleted",
            "account_id": account_id
        }

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