#!/usr/bin/env python3
"""
Pipeline核心执行类
负责协调和执行视频生成的三个阶段
"""

import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import asyncio

from models import (
    PipelineRequest,
    PipelineResponse,
    StageResult,
    StageStatus,
    TaskStatus,
    ContentReport,
    YouTubeSuggestions
)

# 配置日志系统
def setup_logging(log_file: Optional[str] = None, verbose: bool = False):
    """设置日志配置"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # 配置控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 根日志器设置为DEBUG，由handler控制输出级别
    root_logger.handlers = []  # 清空现有handlers
    root_logger.addHandler(console_handler)
    
    # 如果指定了日志文件，添加文件handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)
    
    return logging.getLogger(__name__)

# 默认配置
logger = setup_logging()


class VideoPipeline:
    """视频生成Pipeline核心类"""
    
    def __init__(self, request: PipelineRequest, scripts_base_dir: str = None, 
                 log_file: Optional[str] = None, verbose: bool = False, use_cache: bool = True):
        """
        初始化Pipeline
        
        Args:
            request: Pipeline执行请求
            scripts_base_dir: 脚本所在的基础目录，默认为当前目录
            log_file: 日志文件路径
            verbose: 是否输出详细日志
            use_cache: 是否使用缓存（跳过已完成的步骤）
        """
        self.request = request
        self.stages_results = []
        self.start_time = None
        self.end_time = None
        self.verbose = verbose
        self.use_cache = use_cache
        
        # 设置日志
        if log_file or verbose:
            global logger
            logger = setup_logging(log_file, verbose)
        
        # 设置脚本基础目录（因为现在在同一目录，简化逻辑）
        if scripts_base_dir:
            self.scripts_base_dir = Path(scripts_base_dir)
        else:
            # 默认使用当前目录
            self.scripts_base_dir = Path(".")
        
        logger.info(f"使用脚本目录: {self.scripts_base_dir.resolve()}")
        
        # 构建输出目录路径
        self.output_dir = Path(f"outputs/{request.creator_id}/{request.video_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志文件（如果没有指定，使用默认位置）
        if not log_file:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = log_dir / f"pipeline_{request.creator_id}_{request.video_id}_{timestamp}.log"
            # 重新设置日志
            logger = setup_logging(str(self.log_file), verbose)
            logger.info(f"日志文件: {self.log_file}")
        else:
            self.log_file = Path(log_file)
        
        # 初始化文件路径
        self.paths = {
            'story': self.output_dir / "story.txt",
            'audio': self.output_dir / "audio.mp3",
            'draft': self.output_dir / "draft.jy",
            'video': self.output_dir / "final_video.mp4",
            'report': self.output_dir / "report.json",
            'youtube': self.output_dir / "youtube_suggestions.json"
        }
        
        logger.info(f"Pipeline初始化完成 - Creator: {request.creator_id}, Video: {request.video_id}")
        logger.debug(f"请求参数: gender={request.gender}, duration={request.duration}, image_dir={request.image_dir}")
    
    def execute_sync(self) -> PipelineResponse:
        """
        同步执行Pipeline
        
        Returns:
            PipelineResponse: 执行结果
        """
        logger.info("开始执行Pipeline（同步模式）")
        self.start_time = datetime.now()
        response_status = TaskStatus.COMPLETED
        error_message = None
        
        try:
            # 阶段1: 故事二创
            stage1 = self._run_story_generation()
            self.stages_results.append(stage1)
            
            if stage1.status == StageStatus.FAILED:
                response_status = TaskStatus.FAILED
                error_message = f"故事二创失败: {stage1.error}"
                logger.error(error_message)
            else:
                # 阶段2: 语音生成
                stage2 = self._run_voice_generation()
                self.stages_results.append(stage2)
                
                if stage2.status == StageStatus.FAILED:
                    response_status = TaskStatus.FAILED
                    error_message = f"语音生成失败: {stage2.error}"
                    logger.error(error_message)
                else:
                    # 阶段3: 剪映草稿生成
                    stage3 = self._run_draft_generation()
                    self.stages_results.append(stage3)
                    
                    if stage3.status == StageStatus.FAILED:
                        response_status = TaskStatus.FAILED
                        error_message = f"剪映草稿生成失败: {stage3.error}"
                        logger.error(error_message)
            
            # 读取生成的报告
            reports = self._read_generated_reports()
            
        except Exception as e:
            response_status = TaskStatus.FAILED
            error_message = str(e)
            logger.exception("Pipeline执行出错")
        
        self.end_time = datetime.now()
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        # 构建响应
        response = PipelineResponse(
            status=response_status,
            video_id=self.request.video_id,
            creator_id=self.request.creator_id,
            video_path=str(self.paths['video']) if self.paths['video'].exists() else None,
            draft_path=str(self.paths['draft']) if self.paths['draft'].exists() else None,
            audio_path=str(self.paths['audio']) if self.paths['audio'].exists() else None,
            story_path=str(self.paths['story']) if self.paths['story'].exists() else None,
            content_report=reports.get('content') if 'reports' in locals() else None,
            youtube_suggestions=reports.get('youtube') if 'reports' in locals() else None,
            report_file_paths=reports.get('file_paths', {}) if 'reports' in locals() else {},
            stages=self.stages_results,
            total_duration=total_duration,
            created_at=self.start_time,
            completed_at=self.end_time,
            error_message=error_message
        )
        
        logger.info(f"Pipeline执行完成 - 状态: {response_status}, 耗时: {total_duration:.2f}秒")
        return response
    
    async def execute(self) -> PipelineResponse:
        """
        异步执行Pipeline（为API准备）
        
        Returns:
            PipelineResponse: 执行结果
        """
        logger.info("开始执行Pipeline（异步模式）")
        
        # 在新的事件循环中运行同步方法
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute_sync)
    
    def _run_command(self, command: List[str], stage_name: str, timeout: int = 300) -> StageResult:
        """
        执行子进程命令
        
        Args:
            command: 命令列表
            stage_name: 阶段名称
            timeout: 超时时间（秒）
            
        Returns:
            StageResult: 执行结果
        """
        logger.info(f"{'='*60}")
        logger.info(f"开始执行阶段: {stage_name}")
        logger.info(f"{'='*60}")
        logger.debug(f"执行命令: {' '.join(command)}")
        
        start_time = datetime.now()
        result = StageResult(
            name=stage_name,
            status=StageStatus.PROCESSING,
            start_time=start_time
        )
        
        try:
            # 执行命令，实时捕获输出
            # Windows系统使用系统默认编码，其他系统使用UTF-8
            import platform
            if platform.system() == 'Windows':
                # Windows使用GBK或系统默认编码
                import locale
                system_encoding = locale.getpreferredencoding() or 'gbk'
            else:
                system_encoding = 'utf-8'
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并stderr到stdout
                text=True,
                encoding=system_encoding,
                errors='replace',  # 遇到无法解码的字符时替换而不是报错
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )
            
            # 实时读取输出
            output_lines = []
            logger.debug(f"--- {stage_name} 输出开始 ---")
            
            # 使用超时机制
            import threading
            import queue
            
            def read_output(proc, q):
                for line in proc.stdout:
                    q.put(line)
                proc.stdout.close()
            
            q = queue.Queue()
            thread = threading.Thread(target=read_output, args=(process, q))
            thread.daemon = True
            thread.start()
            
            # 读取输出直到超时或进程结束
            deadline = time.time() + timeout
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    process.kill()
                    raise subprocess.TimeoutExpired(command, timeout)
                
                try:
                    line = q.get(timeout=min(remaining, 0.1))
                    output_lines.append(line)
                    # 记录到日志（去除换行符）
                    log_line = line.rstrip()
                    if log_line:
                        logger.debug(f"[{stage_name}] {log_line}")
                except queue.Empty:
                    if process.poll() is not None:
                        # 进程已结束
                        break
            
            # 获取返回码
            returncode = process.wait()
            
            logger.debug(f"--- {stage_name} 输出结束 ---")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            stdout = ''.join(output_lines)
            
            if returncode == 0:
                result.status = StageStatus.SUCCESS
                result.output = stdout
                logger.info(f"✅ 阶段 {stage_name} 执行成功，耗时: {duration:.2f}秒")
            else:
                result.status = StageStatus.FAILED
                result.error = f"命令返回非零状态码: {returncode}\n{stdout}"
                logger.error(f"❌ 阶段 {stage_name} 执行失败，返回码: {returncode}")
                logger.error(f"错误输出:\n{stdout}")
            
            result.end_time = end_time
            result.duration = duration
            
        except subprocess.TimeoutExpired:
            result.status = StageStatus.FAILED
            result.error = f"执行超时（{timeout}秒）"
            result.end_time = datetime.now()
            result.duration = (result.end_time - start_time).total_seconds()
            logger.error(f"⏱️ 阶段 {stage_name} 执行超时 ({timeout}秒)")
            process.kill()
            
        except Exception as e:
            result.status = StageStatus.FAILED
            result.error = str(e)
            result.end_time = datetime.now()
            result.duration = (result.end_time - start_time).total_seconds()
            logger.exception(f"💥 阶段 {stage_name} 执行出错")
        
        logger.info(f"{'='*60}")
        return result
    
    def _run_story_generation(self) -> StageResult:
        """
        执行故事二创阶段
        
        Returns:
            StageResult: 执行结果
        """
        # 检查是否已经完成（缓存检测）
        story_file = Path(f"./story_result/{self.request.creator_id}/{self.request.video_id}/final/story.txt")
        if self.use_cache and story_file.exists():
            logger.info("✅ 故事二创已完成（使用缓存）")
            result = StageResult(
                name="故事二创",
                status=StageStatus.SUCCESS,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=0,
                output="使用已存在的故事文件"
            )
            output_files = []
            for path in [story_file, 
                        story_file.parent / "report.md", 
                        story_file.parent / "youtube_metadata.json"]:
                if path.exists():
                    output_files.append(str(path))
            result.output_files = output_files
            return result
        
        script_path = self.scripts_base_dir / "story_pipeline_v3_runner.py"
        command = [
            sys.executable,
            str(script_path),
            self.request.video_id,
            "--creator",
            self.request.creator_id
        ]
        
        result = self._run_command(command, "故事二创", timeout=600)
        
        # 记录生成的文件
        if result.status == StageStatus.SUCCESS:
            output_files = []
            for path in [self.paths['story'], self.paths['report'], self.paths['youtube']]:
                if path.exists():
                    output_files.append(str(path))
            result.output_files = output_files
        
        return result
    
    def _preprocess_story_for_tts(self) -> bool:
        """
        预处理故事文本，为TTS做准备
        - 去除空行
        - 合并过短的句子（小于300字符）
        
        Returns:
            bool: 是否成功处理
        """
        # 使用实际的故事文件路径（与tts_client.py一致）
        story_file = Path(f"./story_result/{self.request.creator_id}/{self.request.video_id}/final/story.txt")
        processed_file = story_file.parent / "story_processed.txt"
        
        if not story_file.exists():
            logger.error(f"故事文件不存在: {story_file}")
            return False
        
        try:
            logger.info("开始预处理故事文本...")
            
            # 先备份原始文件
            backup_file = story_file.parent / "story_original.txt"
            if story_file.exists() and not backup_file.exists():
                import shutil
                shutil.copy2(story_file, backup_file)
                logger.debug(f"已备份原始文件到: {backup_file}")
            
            # 读取原始文本
            with open(story_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 去除空行和首尾空格
            lines = [line.strip() for line in lines if line.strip()]
            
            logger.debug(f"原始行数: {len(lines)}")
            
            # 合并短句子
            processed_lines = []
            current_line = ""
            min_length = 300  # 最小长度要求
            
            for i, line in enumerate(lines):
                # 如果这一行本身就够长，直接添加
                if len(line) >= min_length:
                    # 如果有累积的内容，先保存
                    if current_line:
                        processed_lines.append(current_line)
                        logger.debug(f"保存累积行（在遇到长行前）: {len(current_line)} 字符")
                        current_line = ""
                    # 添加当前长行
                    processed_lines.append(line)
                    logger.debug(f"添加长行 {len(processed_lines)}: {len(line)} 字符")
                else:
                    # 短行需要累积
                    if not current_line:
                        current_line = line
                    else:
                        # 添加一个空格分隔
                        current_line += " " + line
                    
                    # 检查累积长度是否达到要求
                    if len(current_line) >= min_length:
                        processed_lines.append(current_line)
                        logger.debug(f"累积行达到长度要求 {len(processed_lines)}: {len(current_line)} 字符")
                        current_line = ""
                
                # 如果是最后一行且还有累积内容，保存它
                if i == len(lines) - 1 and current_line:
                    processed_lines.append(current_line)
                    logger.debug(f"保存最后的累积行: {len(current_line)} 字符")
            
            logger.info(f"预处理完成: {len(lines)} 行 → {len(processed_lines)} 行")
            
            if not processed_lines:
                logger.warning("处理后没有有效的文本行")
                return False
            
            # 保存处理后的文本（同时保留原始文件）
            with open(processed_file, 'w', encoding='utf-8') as f:
                for line in processed_lines:
                    f.write(line + '\n')
            
            # 同时更新原始story.txt（语音生成脚本读取这个文件）
            with open(story_file, 'w', encoding='utf-8') as f:
                for line in processed_lines:
                    f.write(line + '\n')
            
            logger.info(f"处理后的文本已保存: {processed_file}")
            
            # 统计信息
            lengths = [len(l) for l in processed_lines]
            logger.debug(f"句子长度统计: 最短={min(lengths)}字符, "
                        f"最长={max(lengths)}字符, "
                        f"平均={sum(lengths)/len(lengths):.1f}字符")
            
            # 输出一些具体信息帮助调试
            short_lines = [i+1 for i, l in enumerate(processed_lines) if len(l) < 300]
            if short_lines:
                logger.info(f"仍有 {len(short_lines)} 行短于300字符: 第 {short_lines[:5]} 行..." if len(short_lines) > 5 else f"仍有 {len(short_lines)} 行短于300字符: 第 {short_lines} 行")
            
            return True
            
        except Exception as e:
            logger.error(f"预处理故事文本失败: {e}")
            logger.exception("详细错误:")
            return False
    
    def _run_voice_generation(self) -> StageResult:
        """
        执行语音生成阶段
        
        Returns:
            StageResult: 执行结果
        """
        # 检查是否已经完成（缓存检测）
        audio_path = Path(f"./output/{self.request.creator_id}_{self.request.video_id}_story.mp3")
        srt_path = Path(f"./output/{self.request.creator_id}_{self.request.video_id}_story.srt")
        
        if self.use_cache and audio_path.exists():
            logger.info("✅ 语音生成已完成（使用缓存）")
            result = StageResult(
                name="语音生成",
                status=StageStatus.SUCCESS,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=0,
                output="使用已存在的音频文件"
            )
            output_files = []
            if audio_path.exists():
                output_files.append(str(audio_path))
                self.paths['audio'] = audio_path
            if srt_path.exists():
                output_files.append(str(srt_path))
            result.output_files = output_files
            return result
        
        # 先进行文本预处理
        logger.info("准备进行语音生成...")
        if not self._preprocess_story_for_tts():
            logger.warning("故事文本预处理失败，但继续尝试语音生成")
        
        script_path = self.scripts_base_dir / "voice_gen" / "tts_client.py"
        
        # 确保gender是整数值
        gender_value = self.request.gender.value if hasattr(self.request.gender, 'value') else int(self.request.gender)
        
        command = [
            sys.executable,
            str(script_path),
            "--cid",
            self.request.creator_id,
            "--vid",
            self.request.video_id,
            "--gender",
            str(gender_value)
        ]
        
        logger.debug(f"语音生成参数: cid={self.request.creator_id}, vid={self.request.video_id}, gender={gender_value}")
        
        result = self._run_command(command, "语音生成", timeout=900)
        
        # 记录生成的文件（语音生成脚本输出到./output/目录）
        if result.status == StageStatus.SUCCESS:
            audio_path = Path(f"./output/{self.request.creator_id}_{self.request.video_id}_story.mp3")
            srt_path = Path(f"./output/{self.request.creator_id}_{self.request.video_id}_story.srt")
            output_files = []
            if audio_path.exists():
                output_files.append(str(audio_path))
                # 更新路径引用
                self.paths['audio'] = audio_path
            if srt_path.exists():
                output_files.append(str(srt_path))
            result.output_files = output_files
        
        return result
    
    def _run_draft_generation(self) -> StageResult:
        """
        执行剪映草稿生成阶段
        
        Returns:
            StageResult: 执行结果
        """
        script_path = self.scripts_base_dir / "draft_gen" / "generateDraftService.py"
        command = [
            sys.executable,
            str(script_path),
            "--cid",
            self.request.creator_id,
            "--vid",
            self.request.video_id,
            "--duration",
            str(self.request.duration)
        ]
        
        # 如果指定了图库目录，添加参数
        if self.request.image_dir:
            command.extend(["--image_dir", self.request.image_dir])
        
        result = self._run_command(command, "剪映草稿生成", timeout=600)
        
        # 记录生成的文件
        if result.status == StageStatus.SUCCESS:
            output_files = []
            
            # 处理草稿ZIP文件 - 解压并移动到配置的目录
            draft_zip = Path(f"./output/drafts/{self.request.creator_id}_{self.request.video_id}_story.zip")
            draft_folder = Path(f"./output/drafts/{self.request.creator_id}_{self.request.video_id}_story")
            
            if draft_zip.exists():
                # 获取目标目录
                draft_dir = os.environ.get('DRAFT_LOCAL_DIR')
                if draft_dir:
                    draft_target_dir = Path(draft_dir)
                    draft_target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 生成目标文件夹名（包含时间戳以避免覆盖）
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    draft_folder_name = f"{self.request.creator_id}_{self.request.video_id}_{timestamp}"
                    draft_target = draft_target_dir / draft_folder_name
                    
                    import shutil
                    import zipfile
                    try:
                        # 解压ZIP文件到目标目录
                        with zipfile.ZipFile(draft_zip, 'r') as zip_ref:
                            zip_ref.extractall(draft_target)
                        logger.info(f"✅ 草稿已解压到: {draft_target}")
                        output_files.append(str(draft_target))
                        self.paths['draft'] = draft_target
                        
                        # 删除原始ZIP文件（可选）
                        draft_zip.unlink()
                        logger.debug(f"已删除ZIP文件: {draft_zip}")
                        
                        # 如果原始文件夹存在，也删除它
                        if draft_folder.exists():
                            shutil.rmtree(draft_folder)
                            logger.debug(f"已删除原始文件夹: {draft_folder}")
                            
                    except Exception as e:
                        logger.error(f"处理草稿文件失败: {e}")
                        # 如果处理失败，仍然记录原始位置
                        output_files.append(str(draft_zip))
                else:
                    logger.warning("未配置 DRAFT_LOCAL_DIR，草稿文件保留在原位置")
                    output_files.append(str(draft_zip))
            elif draft_folder.exists():
                # 如果只有文件夹没有ZIP，直接移动文件夹
                draft_dir = os.environ.get('DRAFT_LOCAL_DIR')
                if draft_dir:
                    draft_target_dir = Path(draft_dir)
                    draft_target_dir.mkdir(parents=True, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    draft_folder_name = f"{self.request.creator_id}_{self.request.video_id}_{timestamp}"
                    draft_target = draft_target_dir / draft_folder_name
                    
                    import shutil
                    try:
                        shutil.move(str(draft_folder), str(draft_target))
                        logger.info(f"✅ 草稿文件夹已移动到: {draft_target}")
                        output_files.append(str(draft_target))
                        self.paths['draft'] = draft_target
                    except Exception as e:
                        logger.error(f"移动草稿文件夹失败: {e}")
                        output_files.append(str(draft_folder))
                else:
                    logger.warning("未配置 DRAFT_LOCAL_DIR，草稿文件夹保留在原位置")
                    output_files.append(str(draft_folder))
            else:
                logger.warning(f"草稿文件不存在: {draft_zip} 或 {draft_folder}")
            
            # 处理其他可能的输出文件
            for path in [self.paths['video']]:
                if path.exists():
                    output_files.append(str(path))
            
            result.output_files = output_files
        
        return result
    
    def _read_generated_reports(self) -> Dict[str, Any]:
        """
        读取第一阶段生成的报告文件
        
        Returns:
            包含内容报告和YouTube建议的字典
        """
        logger.info("读取生成的报告文件")
        
        result = {
            'content': None,
            'youtube': None,
            'file_paths': {}
        }
        
        # 读取内容报告
        if self.paths['report'].exists():
            try:
                with open(self.paths['report'], 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                    result['content'] = ContentReport(**report_data) if report_data else None
                    result['file_paths']['report'] = str(self.paths['report'])
                    logger.info(f"成功读取内容报告: {self.paths['report']}")
            except Exception as e:
                logger.error(f"读取内容报告失败: {e}")
        
        # 读取YouTube建议
        if self.paths['youtube'].exists():
            try:
                with open(self.paths['youtube'], 'r', encoding='utf-8') as f:
                    youtube_data = json.load(f)
                    result['youtube'] = YouTubeSuggestions(**youtube_data) if youtube_data else None
                    result['file_paths']['youtube'] = str(self.paths['youtube'])
                    logger.info(f"成功读取YouTube建议: {self.paths['youtube']}")
            except Exception as e:
                logger.error(f"读取YouTube建议失败: {e}")
        
        return result
    
    def check_prerequisites(self) -> List[str]:
        """
        检查执行先决条件
        
        Returns:
            缺失的先决条件列表
        """
        missing = []
        
        # 检查必要的脚本文件
        required_scripts = [
            self.scripts_base_dir / "story_pipeline_v3_runner.py",
            self.scripts_base_dir / "voice_gen" / "tts_client.py",
            self.scripts_base_dir / "draft_gen" / "generateDraftService.py"
        ]
        
        for script_path in required_scripts:
            if not script_path.exists():
                missing.append(f"脚本文件不存在: {script_path}")
        
        # 检查图库目录（如果指定）
        if self.request.image_dir and not Path(self.request.image_dir).exists():
            missing.append(f"图库目录不存在: {self.request.image_dir}")
        
        return missing