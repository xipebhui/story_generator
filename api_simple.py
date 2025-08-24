#!/usr/bin/env python3
"""
简化版Pipeline API服务器
提供最小可用的异步API接口
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import json
import uuid
import logging
import os
from datetime import datetime
from pathlib import Path

# 加载环境变量 - 必须在其他操作之前
from config_loader import load_env_file
load_env_file()

# 配置日志
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 启动时打印环境变量状态
logger.info("=" * 60)
logger.info("API服务启动")
logger.info(f"LOG_LEVEL: {log_level}")
logger.info(f"DRAFT_LOCAL_DIR: {os.environ.get('DRAFT_LOCAL_DIR', 'Not Set')}")
logger.info(f"EXPORT_VIDEO_URL: {os.environ.get('EXPORT_VIDEO_URL', 'Not Set')}")
logger.info("=" * 60)

app = FastAPI(title="Video Pipeline API", version="0.1.0")

# ============ 数据模型 ============
class PipelineRequest(BaseModel):
    video_id: str
    creator_id: str
    gender: int = 1  # 0=男性, 1=女性
    duration: int = 60
    image_dir: Optional[str] = None
    export_video: bool = False

class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    current_stage: Optional[str] = None
    progress: Dict[str, str]  # 各阶段状态
    created_at: str
    completed_at: Optional[str] = None

class TaskResult(BaseModel):
    task_id: str
    status: str
    youtube_metadata: Optional[Dict[str, Any]] = None
    video_path: Optional[str] = None
    draft_path: Optional[str] = None
    audio_path: Optional[str] = None
    story_path: Optional[str] = None
    error: Optional[str] = None

# ============ 任务管理 ============
tasks = {}  # 简单的内存存储

async def run_pipeline_async(task_id: str, request: PipelineRequest):
    """异步运行pipeline"""
    logger.info(f"[Task {task_id}] 开始执行Pipeline")
    logger.debug(f"[Task {task_id}] 请求参数: video_id={request.video_id}, creator_id={request.creator_id}")
    
    try:
        # 更新状态
        tasks[task_id]["status"] = "running"
        tasks[task_id]["current_stage"] = "初始化"
        logger.debug(f"[Task {task_id}] 状态更新为: running")
        
        # 导入并运行pipeline
        from pipeline_core import VideoPipeline
        from models import PipelineRequest as CoreRequest, Gender, StageStatus
        
        # 转换请求
        core_request = CoreRequest(
            video_id=request.video_id,
            creator_id=request.creator_id,
            gender=Gender(request.gender),
            duration=request.duration,
            image_dir=request.image_dir,
            export_video=request.export_video
        )
        
        # 检查环境变量
        logger.debug(f"[Task {task_id}] 环境变量检查:")
        logger.debug(f"  - DRAFT_LOCAL_DIR: {os.environ.get('DRAFT_LOCAL_DIR', 'Not Set')}")
        logger.debug(f"  - EXPORT_VIDEO_URL: {os.environ.get('EXPORT_VIDEO_URL', 'Not Set')}")
        logger.debug(f"  - LOG_LEVEL: {os.environ.get('LOG_LEVEL', 'Not Set')}")
        
        # 创建pipeline实例
        verbose = os.environ.get('LOG_LEVEL', 'INFO').upper() == 'DEBUG'
        logger.debug(f"[Task {task_id}] 创建Pipeline实例, verbose={verbose}")
        pipeline = VideoPipeline(core_request, verbose=verbose)
        
        # 更新阶段状态
        stages = ["故事二创", "语音生成", "剪映草稿生成"]
        if request.export_video:
            stages.append("视频导出")
        
        # 标记所有阶段为待处理
        for stage in stages:
            tasks[task_id]["progress"][stage] = "待处理"
        
        # 分阶段执行pipeline，以便更新状态
        loop = asyncio.get_event_loop()
        pipeline.start_time = datetime.now()
        
        # 阶段1: 故事二创
        tasks[task_id]["current_stage"] = "故事二创"
        tasks[task_id]["progress"]["故事二创"] = "运行中"
        stage1 = await loop.run_in_executor(None, pipeline._run_story_generation)
        pipeline.stages_results.append(stage1)
        tasks[task_id]["progress"]["故事二创"] = "成功" if stage1.status == StageStatus.SUCCESS else "失败"
        
        if stage1.status == StageStatus.SUCCESS:
            # 阶段2: 语音生成
            tasks[task_id]["current_stage"] = "语音生成"
            tasks[task_id]["progress"]["语音生成"] = "运行中"
            stage2 = await loop.run_in_executor(None, pipeline._run_voice_generation)
            pipeline.stages_results.append(stage2)
            tasks[task_id]["progress"]["语音生成"] = "成功" if stage2.status == StageStatus.SUCCESS else "失败"
            
            if stage2.status == StageStatus.SUCCESS:
                # 阶段3: 剪映草稿生成
                tasks[task_id]["current_stage"] = "剪映草稿生成"
                tasks[task_id]["progress"]["剪映草稿生成"] = "运行中"
                stage3 = await loop.run_in_executor(None, pipeline._run_draft_generation)
                pipeline.stages_results.append(stage3)
                tasks[task_id]["progress"]["剪映草稿生成"] = "成功" if stage3.status == StageStatus.SUCCESS else "失败"
                
                if stage3.status == StageStatus.SUCCESS and request.export_video:
                    # 阶段4: 视频导出（可选）
                    tasks[task_id]["current_stage"] = "视频导出"
                    tasks[task_id]["progress"]["视频导出"] = "运行中"
                    stage4 = await loop.run_in_executor(None, pipeline._run_video_export)
                    pipeline.stages_results.append(stage4)
                    tasks[task_id]["progress"]["视频导出"] = "成功" if stage4.status == StageStatus.SUCCESS else "失败"
        
        # 读取生成的报告
        reports = await loop.run_in_executor(None, pipeline._read_generated_reports)
        
        pipeline.end_time = datetime.now()
        total_duration = (pipeline.end_time - pipeline.start_time).total_seconds()
        
        # 读取YouTube元数据
        youtube_metadata = None
        youtube_file = Path(f"./story_result/{request.creator_id}/{request.video_id}/final/youtube_metadata.json")
        if youtube_file.exists():
            try:
                with open(youtube_file, 'r', encoding='utf-8') as f:
                    youtube_metadata = json.load(f)
                    # 移除不需要的strategy字段
                    if youtube_metadata and 'strategy' in youtube_metadata:
                        del youtube_metadata['strategy']
            except Exception as e:
                print(f"读取YouTube元数据失败: {e}")
        
        # 构建文件路径
        video_path = None
        draft_path = None
        audio_path = None
        story_path = None
        
        # 检查生成的文件
        story_file = Path(f"./story_result/{request.creator_id}/{request.video_id}/final/story.txt")
        if story_file.exists():
            story_path = str(story_file)
        
        audio_file = Path(f"./output/{request.creator_id}_{request.video_id}_story.mp3")
        if audio_file.exists():
            audio_path = str(audio_file)
        
        # 草稿路径从环境变量获取
        draft_dir = os.environ.get('DRAFT_LOCAL_DIR')
        if draft_dir:
            # 查找最新的草稿文件夹
            draft_base = Path(draft_dir)
            if draft_base.exists():
                pattern = f"{request.creator_id}_{request.video_id}_*"
                drafts = list(draft_base.glob(pattern))
                if drafts:
                    # 获取最新的草稿
                    draft_path = str(max(drafts, key=lambda p: p.stat().st_mtime))
        
        # 判断整体状态
        all_success = all(
            status == "成功" 
            for status in tasks[task_id]["progress"].values()
        )
        
        # 获取视频URL（如果有）
        video_url = None
        preview_url = None
        
        # 如果启用了视频导出，检查是否有URL
        if request.export_video and pipeline.stages_results:
            for stage in pipeline.stages_results:
                if stage.name == "视频导出" and stage.output:
                    try:
                        import json
                        video_info = json.loads(stage.output)
                        video_url = video_info.get('video_url')
                        preview_url = video_info.get('preview_url')
                    except:
                        pass
        
        # 更新任务结果
        tasks[task_id]["status"] = "completed" if all_success else "failed"
        tasks[task_id]["current_stage"] = None
        tasks[task_id]["result"] = {
            "youtube_metadata": youtube_metadata,
            "video_path": video_path or draft_path,  # 如果没有视频，返回草稿路径
            "video_url": video_url,
            "preview_url": preview_url,
            "draft_path": draft_path,
            "audio_path": audio_path,
            "story_path": story_path
        }
        tasks[task_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["completed_at"] = datetime.now().isoformat()
        print(f"Pipeline执行错误: {e}")

# ============ API端点 ============

@app.post("/api/pipeline/run")
async def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    """
    运行Pipeline（异步）
    
    返回task_id用于查询状态和结果
    """
    # 生成任务ID
    task_id = f"{request.creator_id}_{request.video_id}_{uuid.uuid4().hex[:8]}"
    
    # 初始化任务
    tasks[task_id] = {
        "status": "pending",
        "current_stage": None,
        "progress": {
            "故事二创": "待处理",
            "语音生成": "待处理", 
            "剪映草稿生成": "待处理"
        },
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result": None,
        "error": None
    }
    
    if request.export_video:
        tasks[task_id]["progress"]["视频导出"] = "待处理"
    
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
    """获取任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    return TaskStatus(
        task_id=task_id,
        status=task["status"],
        current_stage=task["current_stage"],
        progress=task["progress"],
        created_at=task["created_at"],
        completed_at=task["completed_at"]
    )

@app.get("/api/pipeline/result/{task_id}")
async def get_result(task_id: str):
    """
    获取任务结果
    
    返回YouTube元数据和视频/草稿路径
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    
    if task["status"] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail=f"任务未完成，当前状态: {task['status']}")
    
    result_data = task.get("result", {})
    
    return TaskResult(
        task_id=task_id,
        status=task["status"],
        youtube_metadata=result_data.get("youtube_metadata"),
        video_path=result_data.get("video_path"),
        draft_path=result_data.get("draft_path"),
        audio_path=result_data.get("audio_path"),
        story_path=result_data.get("story_path"),
        error=task.get("error")
    )

@app.get("/api/pipeline/tasks")
async def list_tasks():
    """列出所有任务"""
    return {
        "total": len(tasks),
        "tasks": [
            {
                "task_id": tid,
                "status": t["status"],
                "created_at": t["created_at"],
                "completed_at": t.get("completed_at")
            }
            for tid, t in tasks.items()
        ]
    }

@app.delete("/api/pipeline/clear")
async def clear_tasks():
    """清空所有任务（用于测试）"""
    count = len(tasks)
    tasks.clear()
    return {"message": f"已清空 {count} 个任务"}

@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "tasks_count": len(tasks)
    }

@app.get("/")
async def root():
    """API根路径"""
    return {
        "name": "Video Pipeline API",
        "version": "0.1.0",
        "endpoints": {
            "run": "/api/pipeline/run",
            "status": "/api/pipeline/status/{task_id}",
            "result": "/api/pipeline/result/{task_id}",
            "tasks": "/api/pipeline/tasks",
            "health": "/health"
        }
    }

# ============ 启动服务器 ============
if __name__ == "__main__":
    import uvicorn
    print("启动Pipeline API服务器...")
    print("访问 http://localhost:8888 查看API")
    print("访问 http://localhost:8888/docs 查看交互式文档")
    print("按 Ctrl+C 停止服务器\n")
    
    # 直接运行时不使用reload，避免警告
    uvicorn.run(app, host="0.0.0.0", port=51082)