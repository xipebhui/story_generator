#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline阶段处理函数定义
提供各个阶段的具体实现
"""

import os
import sys
import json
import subprocess
import logging
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def story_generation_stage(context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    故事生成阶段
    调用 StoryPipelineV3Runner 生成故事
    
    Args:
        context: Pipeline上下文（包含params）
        config: 阶段配置
    
    Returns:
        dict: 阶段输出数据
    """
    from pipelines.pipeline_context import PipelineContext
    
    # 如果context是字典，获取PipelineContext实例
    if isinstance(context, dict):
        ctx = context.get('_context')
        params = context.get('params', {})
    else:
        ctx = context
        params = ctx.params
    
    try:
        # 导入故事生成器
        from story_pipeline_v3_runner import StoryPipelineV3Runner
        
        logger.info("Starting story generation stage...")
        
        # 创建运行器实例
        runner = StoryPipelineV3Runner(config)
        
        # 准备参数
        video_id = params.get('video_id')
        # 优先使用selected_creator_id（从video_fetch阶段），否则使用creator_id
        creator_id = params.get('selected_creator_id') or params.get('creator_id', 'default')
        account_id = params.get('account_id', '')
        
        # creator_name应该使用creator_id，而不是account_id
        # account_id只是用于标识哪个账号在执行任务
        creator_name = creator_id
        
        logger.info(f"Story generation params: video_id={video_id}, creator_id={creator_id}, account_id={account_id}")
        
        # 执行故事生成
        result = await runner.execute({
            'video_id': video_id,
            'account_id': account_id,
            'creator_name': creator_name  # 应该是creator_id，不是account_id
        })
        
        if result.get('success'):
            # 提取输出路径
            output_data = {
                'story_path': result.get('story_path'),
                'summary_path': result.get('summary_path'),
                'output_dir': result.get('output_dir'),
                'title': result.get('title'),
                'description': result.get('description'),
                'tags': result.get('tags')
            }
            
            # 保存到上下文
            if ctx:
                ctx.set_stage_output('story_generation', output_data)
                if output_data.get('story_path'):
                    ctx.add_file('story', Path(output_data['story_path']))
            
            logger.info(f"Story generation completed: {output_data.get('story_path')}")
            return output_data
        else:
            raise Exception(f"Story generation failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Story generation stage failed: {e}")
        raise


async def tts_generation_stage(context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    语音生成阶段
    调用TTS服务生成音频
    
    Args:
        context: Pipeline上下文
        config: 阶段配置
    
    Returns:
        dict: 阶段输出数据
    """
    from pipelines.pipeline_context import PipelineContext
    
    # 获取上下文
    if isinstance(context, dict):
        ctx = context.get('_context')
        params = context.get('params', {})
    else:
        ctx = context
        params = ctx.params
    
    try:
        logger.info("Starting TTS generation stage...")
        
        # 获取故事文件路径（使用兼容性方法）
        if ctx and hasattr(ctx, 'get_story_source_path'):
            story_path = ctx.get_story_source_path()
        else:
            # 直接使用旧版路径
            # 优先使用selected_creator_id（从video_fetch阶段）
            creator_id = params.get('selected_creator_id') or params.get('creator_id', 'default')
            video_id = params.get('video_id')
            story_path = Path(f"story_result/{creator_id}/{video_id}/final/story.txt")
        
        if not Path(story_path).exists():
            raise Exception(f"Story file not found: {story_path}")
        
        # 准备TTS命令
        script_path = project_root / "voice_gen" / "tts_client.py"
        gender = params.get('gender', 1)  # 默认男声
        
        # 使用selected_creator_id或creator_id
        creator_id = params.get('selected_creator_id') or params.get('creator_id', 'default')
        
        command = [
            sys.executable,
            str(script_path),
            "--cid", creator_id,
            "--vid", params.get('video_id'),
            "--gender", str(gender)
        ]
        
        # 如果有account_id，添加到命令
        account_id = params.get('account_id')
        if account_id:
            command.extend(["--account", account_id])
        
        # 执行TTS命令
        logger.info(f"Executing TTS command: {' '.join(command)}")
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8') if stderr else "TTS generation failed"
            raise Exception(error_msg)
        
        # 获取音频文件路径（使用兼容性方法）
        if ctx and hasattr(ctx, 'get_audio_output_path'):
            audio_path = ctx.get_audio_output_path()
            # SRT路径与音频路径相同，只是扩展名不同
            srt_path = audio_path.with_suffix('.srt')
        else:
            # 直接使用旧版路径格式
            creator_id = params.get('creator_id', 'default')
            video_id = params.get('video_id')
            if account_id:
                audio_path = Path(f"output/{creator_id}_{account_id}_{video_id}_story.mp3")
                srt_path = Path(f"output/{creator_id}_{account_id}_{video_id}_story.srt")
            else:
                audio_path = Path(f"output/{creator_id}_{video_id}_story.mp3")
                srt_path = Path(f"output/{creator_id}_{video_id}_story.srt")
        
        output_data = {}
        if audio_path.exists():
            output_data['audio_path'] = str(audio_path)
            if ctx:
                ctx.add_file('audio', audio_path)
        
        if srt_path.exists():
            output_data['srt_path'] = str(srt_path)
            if ctx:
                ctx.add_file('srt', srt_path)
        
        if ctx:
            ctx.set_stage_output('tts_generation', output_data)
        
        logger.info(f"TTS generation completed: {audio_path}")
        return output_data
        
    except Exception as e:
        logger.error(f"TTS generation stage failed: {e}")
        raise


async def draft_generation_stage(context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    草稿生成阶段
    调用剪映草稿生成服务
    
    Args:
        context: Pipeline上下文
        config: 阶段配置
    
    Returns:
        dict: 阶段输出数据
    """
    from pipelines.pipeline_context import PipelineContext
    import shutil
    
    # 获取上下文
    if isinstance(context, dict):
        ctx = context.get('_context')
        params = context.get('params', {})
    else:
        ctx = context
        params = ctx.params
    
    try:
        logger.info("Starting draft generation stage...")
        
        # 准备草稿生成命令
        script_path = project_root / "draft_gen" / "generateDraftService.py"
        
        # 使用selected_creator_id或creator_id
        creator_id = params.get('selected_creator_id') or params.get('creator_id', 'default')
        
        command = [
            sys.executable,
            str(script_path),
            "--cid", creator_id,
            "--vid", params.get('video_id'),
            "--duration", str(params.get('duration', 300))
        ]
        
        # generateDraftService.py 不支持 --account 参数，跳过
        account_id = params.get('account_id')
        # if account_id:
        #     command.extend(["--account", account_id])
        
        # 如果有图库目录，添加到命令
        image_dir = params.get('image_dir')
        if image_dir:
            command.extend(["--image_dir", image_dir])
        
        # 如果启用字幕，添加到命令
        if params.get('enable_subtitle', False):
            command.append("--enable-subtitle")
        
        # 执行草稿生成命令
        logger.info(f"Executing draft generation command: {' '.join(command)}")
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8') if stderr else "Draft generation failed"
            raise Exception(error_msg)
        
        # 获取草稿文件路径（使用兼容性方法）
        if ctx and hasattr(ctx, 'get_draft_output_path'):
            draft_folder = ctx.get_draft_output_path()
            draft_zip = draft_folder.with_suffix('.zip')
        else:
            # 直接使用旧版路径格式
            creator_id = params.get('creator_id', 'default')
            video_id = params.get('video_id')
            if account_id:
                draft_folder = Path(f"output/drafts/{creator_id}_{account_id}_{video_id}_story")
                draft_zip = Path(f"output/drafts/{creator_id}_{account_id}_{video_id}_story.zip")
            else:
                draft_folder = Path(f"output/drafts/{creator_id}_{video_id}_story")
                draft_zip = Path(f"output/drafts/{creator_id}_{video_id}_story.zip")
        
        output_data = {}
        
        # 处理草稿文件夹
        if draft_folder.exists():
            # 如果配置了目标目录，移动草稿
            draft_dir = os.environ.get('DRAFT_LOCAL_DIR')
            if draft_dir:
                try:
                    draft_target_dir = Path(draft_dir)
                    draft_target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 生成唯一的目标文件夹名
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    if account_id:
                        draft_folder_name = f"{creator_id}_{account_id}_{video_id}_{timestamp}"
                    else:
                        draft_folder_name = f"{creator_id}_{video_id}_{timestamp}"
                    
                    draft_target = draft_target_dir / draft_folder_name
                    
                    # 移动文件夹
                    shutil.move(str(draft_folder), str(draft_target))
                    logger.info(f"Draft moved to: {draft_target}")
                    
                    output_data['draft_path'] = str(draft_target)
                    if ctx:
                        ctx.add_file('draft', draft_target)
                        
                except Exception as e:
                    logger.error(f"Failed to move draft: {e}")
                    output_data['draft_path'] = str(draft_folder)
            else:
                output_data['draft_path'] = str(draft_folder)
                if ctx:
                    ctx.add_file('draft', draft_folder)
        
        # 清理ZIP文件
        if draft_zip.exists():
            try:
                draft_zip.unlink()
                logger.debug(f"Deleted ZIP file: {draft_zip}")
            except Exception as e:
                logger.debug(f"Failed to delete ZIP file: {e}")
        
        if ctx:
            ctx.set_stage_output('draft_generation', output_data)
        
        logger.info(f"Draft generation completed: {output_data.get('draft_path')}")
        return output_data
        
    except Exception as e:
        logger.error(f"Draft generation stage failed: {e}")
        raise


async def video_export_stage(context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    视频导出阶段（必选）
    调用视频导出服务
    
    Args:
        context: Pipeline上下文
        config: 阶段配置
    
    Returns:
        dict: 阶段输出数据
    """
    from pipelines.pipeline_context import PipelineContext
    
    # 获取上下文
    if isinstance(context, dict):
        ctx = context.get('_context')
        params = context.get('params', {})
    else:
        ctx = context
        params = ctx.params
    
    try:
        logger.info("Starting video export stage...")
        
        # 获取草稿路径
        draft_path = None
        if ctx:
            draft_output = ctx.get_stage_output('draft_generation')
            if draft_output:
                draft_path = draft_output.get('draft_path')
        
        if not draft_path:
            raise Exception("No draft available for video export")
        
        draft_path = Path(draft_path)
        if not draft_path.exists():
            raise Exception(f"Draft path not found: {draft_path}")
        
        # 导入导出函数
        from export_video_simple import export_video
        
        # 草稿名称就是文件夹名
        draft_name = draft_path.name
        
        logger.info(f"Exporting video for draft: {draft_name}")
        
        # 调用导出函数
        video_path = await asyncio.get_event_loop().run_in_executor(
            None, export_video, draft_name
        )
        
        if not video_path:
            raise Exception("Export service returned empty path")
        
        video_path = Path(video_path)
        logger.info(f"Video exported successfully: {video_path}")
        
        output_data = {
            'video_path': str(video_path),
            'video_exists': video_path.exists()
        }
        
        # 生成预览视频（如果配置了输出目录）
        video_output_dir = os.environ.get('VIDEO_OUTPUT_DIR')
        video_server_url = os.environ.get('VIDEO_SERVER_URL')
        
        if video_output_dir and video_server_url:
            try:
                output_dir = Path(video_output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # 生成预览视频
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                account_id = params.get('account_id')
                creator_id = params.get('creator_id', 'default')
                video_id = params.get('video_id')
                
                if account_id:
                    preview_filename = f"{creator_id}_{account_id}_{video_id}_{timestamp}_preview.mp4"
                else:
                    preview_filename = f"{creator_id}_{video_id}_{timestamp}_preview.mp4"
                
                preview_path = output_dir / preview_filename
                
                # 使用ffmpeg生成30秒预览
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-t', '30',
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    '-y',
                    str(preview_path)
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await process.communicate()
                
                if process.returncode == 0 and preview_path.exists():
                    preview_url = f"{video_server_url}/{preview_filename}"
                    output_data['preview_url'] = preview_url
                    output_data['preview_path'] = str(preview_path)
                    logger.info(f"Preview video generated: {preview_url}")
                    
            except Exception as e:
                logger.warning(f"Failed to generate preview video: {e}")
        
        if ctx:
            ctx.set_stage_output('video_export', output_data)
            ctx.add_file('video', video_path)
        
        return output_data
        
    except Exception as e:
        logger.error(f"Video export stage failed: {e}")
        raise


async def youtube_publish_stage(context: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    YouTube发布阶段（可选）
    调用发布服务上传视频
    
    Args:
        context: Pipeline上下文
        config: 阶段配置
    
    Returns:
        dict: 阶段输出数据
    """
    from pipelines.pipeline_context import PipelineContext
    
    # 获取上下文
    if isinstance(context, dict):
        ctx = context.get('_context')
        params = context.get('params', {})
    else:
        ctx = context
        params = ctx.params
    
    try:
        logger.info("Starting YouTube publish stage...")
        
        # 获取视频路径
        video_path = None
        if ctx:
            video_output = ctx.get_stage_output('video_export')
            if video_output:
                video_path = video_output.get('video_path')
        
        if not video_path or not Path(video_path).exists():
            raise Exception("No video available for publishing")
        
        # 导入发布服务
        from publish_service import get_publish_service
        
        publish_service = get_publish_service()
        
        # 准备发布参数
        publish_params = params.get('publish_params', {})
        
        # 获取YouTube元数据
        youtube_metadata = {}
        if ctx:
            story_output = ctx.get_stage_output('story_generation')
            if story_output:
                youtube_metadata = {
                    'title': story_output.get('title'),
                    'description': story_output.get('description'),
                    'tags': story_output.get('tags')
                }
        
        # 创建发布任务
        # 注意：这里需要task_id，可能需要从params中获取或生成
        task_id = params.get('task_id', f"pipeline_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        account_id = params.get('account_id')
        
        if not account_id:
            raise Exception("Account ID is required for publishing")
        
        # 创建模拟的Pipeline任务记录（如果需要）
        # 实际使用时应该已经有task记录
        
        publish_task = publish_service.create_publish_task(
            task_id=task_id,
            account_id=account_id,
            video_title=youtube_metadata.get('title') or publish_params.get('title'),
            video_description=youtube_metadata.get('description') or publish_params.get('description'),
            video_tags=youtube_metadata.get('tags') or publish_params.get('tags'),
            thumbnail_path=publish_params.get('thumbnail_path'),
            scheduled_time=publish_params.get('scheduled_time'),
            privacy_status=publish_params.get('privacy_status', 'public')
        )
        
        if not publish_task:
            raise Exception("Failed to create publish task")
        
        # 执行上传
        upload_result = await publish_service.upload_to_youtube_async(publish_task['publish_id'])
        
        output_data = {
            'publish_id': publish_task['publish_id'],
            'success': upload_result.get('success', False),
            'video_url': upload_result.get('video_url'),
            'video_id': upload_result.get('video_id'),
            'error': upload_result.get('error')
        }
        
        if ctx:
            ctx.set_stage_output('youtube_publish', output_data)
        
        if output_data['success']:
            logger.info(f"YouTube publish completed: {output_data['video_url']}")
        else:
            logger.error(f"YouTube publish failed: {output_data.get('error')}")
        
        return output_data
        
    except Exception as e:
        logger.error(f"YouTube publish stage failed: {e}")
        raise