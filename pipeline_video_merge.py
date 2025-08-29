#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频拼接Pipeline服务
将多个竖屏视频和一个横屏视频合成为剪映草稿

功能：
1. 从两个文件夹随机选择视频
2. 横屏视频作为背景（静音）
3. 竖屏视频拼接到横屏视频时长
4. 生成完整的剪映草稿
"""

import os
import sys
import json
import uuid
import random
import shutil
from datetime import datetime
from pathlib import Path
import subprocess
import logging
from typing import List, Dict, Optional, Tuple

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def setup_logging(task_id: str = None):
    """设置日志"""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"video_merge_{task_id if task_id else timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

class VideoInfo:
    """视频信息类"""
    def __init__(self, path, width=0, height=0, duration=0.0, fps=30.0, has_audio=True):
        self.path = Path(path)
        self.width = width
        self.height = height
        self.duration = duration
        self.fps = fps
        self.has_audio = has_audio
        self.aspect_ratio = width / height if height > 0 else 0
        self.duration_us = int(duration * 1000000)  # 微秒
    
    def __str__(self):
        return f"VideoInfo(path={self.path.name}, w={self.width}, h={self.height}, dur={self.duration:.2f}s, ratio={self.aspect_ratio:.3f})"

class VideoMergePipeline:
    """视频拼接Pipeline"""
    
    def __init__(self, task_id: str = None):
        self.task_id = task_id or self._generate_task_id()
        self.logger = setup_logging(self.task_id)
        
        # 项目配置
        self.project_config = {
            "canvas_width": 1920,
            "canvas_height": 1080,
            "canvas_ratio": "16:9",
            "fps": 30.0,
            "platform": "windows",
            "app_version": "5.9.0"
        }
        
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        return datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + str(uuid.uuid4())[:8]
    
    def _generate_uuid(self) -> str:
        """生成UUID"""
        return str(uuid.uuid4()).upper()
    
    def scan_video_folder(self, folder_path: str, expected_ratio: float = None) -> List[str]:
        """
        扫描文件夹中的视频文件
        
        Args:
            folder_path: 文件夹路径
            expected_ratio: 期望的宽高比（用于筛选）
            
        Returns:
            视频文件路径列表
        """
        folder = Path(folder_path)
        if not folder.exists():
            self.logger.error(f"文件夹不存在: {folder_path}")
            return []
        
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(folder.glob(f'*{ext}'))
            video_files.extend(folder.glob(f'*{ext.upper()}'))
        
        # 如果指定了期望比例，进行筛选
        if expected_ratio:
            filtered_files = []
            for video_file in video_files:
                info = self.get_video_info(str(video_file))
                if info and abs(info.aspect_ratio - expected_ratio) < 0.1:
                    filtered_files.append(str(video_file))
            video_files = filtered_files
        else:
            video_files = [str(f) for f in video_files]
        
        self.logger.info(f"在 {folder_path} 找到 {len(video_files)} 个视频文件")
        return video_files
    
    def get_video_info(self, video_path: str) -> Optional[VideoInfo]:
        """获取视频信息"""
        if not os.path.exists(video_path):
            self.logger.error(f"视频文件不存在: {video_path}")
            return None
        
        try:
            cmd = [
                'ffprobe', 
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                self.logger.error(f"ffprobe执行失败: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            
            # 查找视频流
            video_stream = None
            has_audio = False
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                elif stream.get('codec_type') == 'audio':
                    has_audio = True
            
            if not video_stream:
                self.logger.error(f"未找到视频流: {video_path}")
                return None
            
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            
            # 获取时长
            duration = 0.0
            if 'duration' in video_stream:
                duration = float(video_stream['duration'])
            elif 'duration' in data.get('format', {}):
                duration = float(data['format']['duration'])
            
            # 获取帧率
            fps = 30.0
            fps_str = video_stream.get('r_frame_rate', '30/1')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den) if float(den) > 0 else 30.0
            
            return VideoInfo(video_path, width, height, duration, fps, has_audio)
            
        except Exception as e:
            self.logger.error(f"读取视频信息失败: {e}")
            return None
    
    def select_videos(self, portrait_folder: str, landscape_folder: str) -> Tuple[VideoInfo, List[VideoInfo]]:
        """
        选择视频文件
        
        Args:
            portrait_folder: 竖屏视频文件夹
            landscape_folder: 横屏视频文件夹
            
        Returns:
            (横屏背景视频, 竖屏视频列表)
        """
        # 扫描横屏视频（16:9）
        landscape_videos = self.scan_video_folder(landscape_folder, expected_ratio=1.77)
        if not landscape_videos:
            raise ValueError(f"横屏视频文件夹中没有找到视频: {landscape_folder}")
        
        # 随机选择一个横屏视频
        landscape_video_path = random.choice(landscape_videos)
        landscape_info = self.get_video_info(landscape_video_path)
        if not landscape_info:
            raise ValueError(f"无法读取横屏视频信息: {landscape_video_path}")
        
        self.logger.info(f"选择横屏视频: {landscape_info}")
        
        # 扫描竖屏视频（9:16）
        portrait_videos = self.scan_video_folder(portrait_folder, expected_ratio=0.56)
        if not portrait_videos:
            raise ValueError(f"竖屏视频文件夹中没有找到视频: {portrait_folder}")
        
        # 随机选择竖屏视频直到总时长接近横屏视频
        portrait_list = []
        total_duration = 0.0
        target_duration = landscape_info.duration
        
        # 打乱竖屏视频列表
        random.shuffle(portrait_videos)
        
        for video_path in portrait_videos:
            if total_duration >= target_duration:
                break
            
            video_info = self.get_video_info(video_path)
            if video_info:
                portrait_list.append(video_info)
                total_duration += video_info.duration
                self.logger.info(f"添加竖屏视频: {video_info}, 当前总时长: {total_duration:.2f}s")
        
        # 如果时长不够，循环使用竖屏视频
        while total_duration < target_duration and portrait_videos:
            for video_path in portrait_videos:
                if total_duration >= target_duration:
                    break
                
                video_info = self.get_video_info(video_path)
                if video_info:
                    portrait_list.append(video_info)
                    total_duration += video_info.duration
                    self.logger.info(f"循环添加竖屏视频: {video_info}, 当前总时长: {total_duration:.2f}s")
        
        self.logger.info(f"选择了 {len(portrait_list)} 个竖屏视频，总时长: {total_duration:.2f}s")
        
        return landscape_info, portrait_list
    
    def calculate_layout_params(self, landscape_info: VideoInfo, portrait_info: VideoInfo, 
                               canvas_width: int = 1920, canvas_height: int = 1080) -> Dict:
        """计算视频布局参数"""
        # 横屏视频在右边，作为背景
        bg_scale_x = canvas_width / landscape_info.width
        bg_scale_y = canvas_height / landscape_info.height
        bg_scale = max(bg_scale_x, bg_scale_y) * 1.05  # 稍微放大避免黑边
        
        # 竖屏视频在左边
        fg_target_height = canvas_height * 0.9
        fg_scale = fg_target_height / portrait_info.height
        
        return {
            'background': {
                'scale': {'x': bg_scale, 'y': bg_scale},
                'transform': {'x': 0.3121508160703077, 'y': 0.0},  # 右侧
                'volume': 0.0,  # 静音
            },
            'foreground': {
                'scale': {'x': 1.0, 'y': 1.0},
                'transform': {'x': -0.683792372881356, 'y': 0.03454773869346739},  # 左侧
                'crop': {
                    'lower_left_x': 0.11612903225806433,
                    'lower_left_y': 1.0,
                    'lower_right_x': 0.8048387096774192,
                    'lower_right_y': 1.0,
                    'upper_left_x': 0.11612903225806433,
                    'upper_left_y': 0.0,
                    'upper_right_x': 0.8048387096774192,
                    'upper_right_y': 0.0
                },
                'volume': 1.0,  # 保留音频
            },
            'canvas': {'width': canvas_width, 'height': canvas_height}
        }
    
    def create_video_material(self, video_info: VideoInfo, material_index: int) -> Dict:
        """创建视频材料"""
        # 使用固定的placeholder UUID
        placeholder_uuid = "0E685133-18CE-45ED-8CB8-2904A212EC80"
        return {
            "id": self._generate_uuid(),
            "type": "video",
            "path": f"##_draftpath_placeholder_{placeholder_uuid}_##/materials/{video_info.path.name}",
            "width": video_info.width,
            "height": video_info.height,
            "duration": video_info.duration_us,
            "has_audio": video_info.has_audio,
            "material_name": video_info.path.name,
            # 其他必要字段...
        }
    
    def create_video_segment(self, material_id: str, start_time: int, duration: int, 
                           layout_params: Dict, is_background: bool, render_index: int) -> Dict:
        """创建视频轨道段"""
        params = layout_params['background'] if is_background else layout_params['foreground']
        
        return {
            "id": self._generate_uuid(),
            "material_id": material_id,
            "target_timerange": {
                "start": start_time,
                "duration": duration
            },
            "source_timerange": {
                "start": 0,
                "duration": duration
            },
            "clip": {
                "scale": params['scale'],
                "transform": params['transform']
            },
            "volume": params['volume'],
            "render_index": render_index,
            # 如果是前景视频，添加裁剪参数
            "crop": params.get('crop') if not is_background else None,
            # 其他必要字段...
        }
    
    def generate_draft(self, landscape_info: VideoInfo, portrait_list: List[VideoInfo], 
                      task_id: str, output_dir: str) -> Dict:
        """生成剪映草稿"""
        self.logger.info(f"生成剪映草稿: {task_id}")
        
        # 创建输出目录
        output_path = Path(output_dir) / task_id
        output_path.mkdir(parents=True, exist_ok=True)
        materials_dir = output_path / "materials"
        materials_dir.mkdir(exist_ok=True)
        
        # 复制视频文件
        # 复制横屏视频
        landscape_dest = materials_dir / landscape_info.path.name
        if not landscape_dest.exists():
            shutil.copy2(landscape_info.path, landscape_dest)
            self.logger.info(f"复制横屏视频: {landscape_info.path.name}")
        
        # 复制竖屏视频
        for portrait_info in portrait_list:
            portrait_dest = materials_dir / portrait_info.path.name
            if not portrait_dest.exists():
                shutil.copy2(portrait_info.path, portrait_dest)
                self.logger.info(f"复制竖屏视频: {portrait_info.path.name}")
        
        # 计算总时长（以横屏视频为准）
        total_duration_us = landscape_info.duration_us
        
        # 创建材料列表
        materials = {
            "videos": [],
            "canvases": [],
            "speeds": [],
            "sound_channel_mappings": [],
            # 其他材料类型...
        }
        
        # 添加横屏视频材料
        landscape_material = self.create_video_material(landscape_info, 0)
        materials["videos"].append(landscape_material)
        
        # 添加竖屏视频材料
        portrait_materials = []
        for i, portrait_info in enumerate(portrait_list):
            material = self.create_video_material(portrait_info, i + 1)
            materials["videos"].append(material)
            portrait_materials.append((material, portrait_info))
        
        # 创建轨道
        tracks = []
        
        # 背景轨道（横屏视频）
        layout_params = self.calculate_layout_params(landscape_info, portrait_list[0])
        bg_segment = self.create_video_segment(
            landscape_material["id"], 
            0, 
            total_duration_us,
            layout_params, 
            is_background=True,
            render_index=0
        )
        
        bg_track = {
            "id": self._generate_uuid(),
            "type": "video",
            "segments": [bg_segment],
            "attribute": 0,
            "flag": 0
        }
        tracks.append(bg_track)
        
        # 前景轨道（竖屏视频序列）
        fg_segments = []
        current_time = 0
        segment_index = 0
        
        # 循环添加竖屏视频段，直到填满时长
        while current_time < total_duration_us:
            for material, video_info in portrait_materials:
                if current_time >= total_duration_us:
                    break
                
                # 计算当前段的时长
                segment_duration = min(video_info.duration_us, total_duration_us - current_time)
                
                segment = self.create_video_segment(
                    material["id"],
                    current_time,
                    segment_duration,
                    layout_params,
                    is_background=False,
                    render_index=segment_index + 1
                )
                
                fg_segments.append(segment)
                current_time += segment_duration
                segment_index += 1
                
                self.logger.info(f"添加竖屏段 {segment_index}: {current_time/1000000:.2f}s / {total_duration_us/1000000:.2f}s")
        
        fg_track = {
            "id": self._generate_uuid(),
            "type": "video",
            "segments": fg_segments,
            "attribute": 1,
            "flag": 2
        }
        tracks.append(fg_track)
        
        # 构建完整草稿
        draft = {
            "canvas_config": {
                "width": self.project_config["canvas_width"],
                "height": self.project_config["canvas_height"],
                "ratio": self.project_config["canvas_ratio"]
            },
            "duration": total_duration_us,
            "fps": self.project_config["fps"],
            "id": self._generate_uuid(),
            "materials": materials,
            "tracks": tracks,
            "version": 360000,
            # 其他必要字段...
        }
        
        # 保存草稿文件
        draft_file = output_path / "draft_content.json"
        with open(draft_file, 'w', encoding='utf-8') as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"草稿生成完成: {draft_file}")
        
        # 生成元信息
        meta_info = {
            "draft_id": task_id,
            "draft_name": task_id,
            "tm_duration": total_duration_us,
            "tm_draft_create": int(datetime.now().timestamp() * 1000000),
            # 其他元信息...
        }
        
        meta_file = output_path / "draft_meta_info.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta_info, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "task_id": task_id,
            "draft_path": str(output_path),
            "duration": total_duration_us / 1000000,
            "landscape_video": landscape_info.path.name,
            "portrait_videos": [info.path.name for info in portrait_list],
            "message": "视频拼接草稿生成成功"
        }
    
    def process(self, portrait_folder: str, landscape_folder: str, 
               output_dir: str = None, custom_id: str = None) -> Dict:
        """
        处理视频拼接任务
        
        Args:
            portrait_folder: 竖屏视频文件夹路径
            landscape_folder: 横屏视频文件夹路径
            output_dir: 输出目录（可选）
            custom_id: 自定义ID（可选）
            
        Returns:
            处理结果
        """
        try:
            # 使用自定义ID或生成新ID
            task_id = custom_id or self.task_id
            
            self.logger.info(f"开始处理视频拼接任务: {task_id}")
            self.logger.info(f"竖屏视频文件夹: {portrait_folder}")
            self.logger.info(f"横屏视频文件夹: {landscape_folder}")
            
            # 选择视频
            landscape_info, portrait_list = self.select_videos(portrait_folder, landscape_folder)
            
            # 设置输出目录
            if not output_dir:
                output_dir = project_root / "output" / "drafts"
            
            # 生成草稿
            result = self.generate_draft(landscape_info, portrait_list, task_id, output_dir)
            
            self.logger.info(f"视频拼接任务完成: {task_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"视频拼接任务失败: {e}", exc_info=True)
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "message": f"视频拼接失败: {e}"
            }


def main():
    """测试函数"""
    pipeline = VideoMergePipeline()
    
    # 测试参数
    portrait_folder = "output/videos/portrait"  # 竖屏视频文件夹
    landscape_folder = "output/videos/landscape"  # 横屏视频文件夹
    custom_id = "test_merge_" + datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 执行拼接
    result = pipeline.process(
        portrait_folder=portrait_folder,
        landscape_folder=landscape_folder,
        custom_id=custom_id
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()