#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频拼接Pipeline调试脚本 - 实际测试版本
将两个不同比例的视频合成到剪映草稿

功能：
1. 使用output/videos下的实际视频
2. 横屏视频(16:9)静音作为背景
3. 竖屏视频(9:16)保留音频作为前景
4. 生成完整的剪映草稿和材料文件
"""

import os
import sys
import json
import uuid
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
import subprocess
import logging

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def setup_logging():
    """设置日志"""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f"video_merge_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

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

def get_video_info(video_path):
    """获取视频信息"""
    if not os.path.exists(video_path):
        logger.error(f"视频文件不存在: {video_path}")
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
            logger.error(f"ffprobe执行失败: {result.stderr}")
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
            logger.error(f"未找到视频流: {video_path}")
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
        
        video_info = VideoInfo(video_path, width, height, duration, fps, has_audio)
        logger.info(f"视频信息: {video_info}")
        return video_info
        
    except Exception as e:
        logger.error(f"读取视频信息失败: {e}")
        return None

def calculate_layout_params(bg_video_info, fg_video_info, canvas_width=1920, canvas_height=1080):
    """
    计算视频布局参数 - 剪映风格
    画布为16:9 (1920x1080)
    """
    logger.info(f"计算布局参数:")
    logger.info(f"  画布尺寸: {canvas_width}x{canvas_height}")
    logger.info(f"  背景视频(16:9): {bg_video_info}")
    logger.info(f"  前景视频(9:16): {fg_video_info}")
    
    # 背景视频(16:9) - 静音，填充画布，在右边
    bg_scale_x = canvas_width / bg_video_info.width
    bg_scale_y = canvas_height / bg_video_info.height
    bg_scale = max(bg_scale_x, bg_scale_y) * 1.05  # 稍微放大避免黑边
    
    # 剪映的transform是归一化坐标 (-1到1)
    # 横屏视频在右边
    bg_transform_x = 0.3121508160703077  # 右侧位置
    bg_transform_y = 0.0
    
    # 前景视频(9:16) - 保留音频，在左边显示
    # 需要适配画布高度
    fg_target_height = canvas_height * 0.9  # 占画布高度的90%
    fg_scale = fg_target_height / fg_video_info.height
    fg_scaled_width = fg_video_info.width * fg_scale
    
    # 前景视频在左边
    fg_transform_x = -0.683792372881356  # 左侧位置
    fg_transform_y = 0.03454773869346739
    
    # 计算裁剪参数（前景视频需要裁剪）
    crop_left = 0.11612903225806433
    crop_right = 0.8048387096774192
    
    return {
        'background': {
            'scale': {'x': bg_scale, 'y': bg_scale},
            'transform': {'x': bg_transform_x, 'y': bg_transform_y},
            'volume': 0.0,  # 背景视频静音
            'track_index': 0,
            'render_index': 0
        },
        'foreground': {
            'scale': {'x': 1.0, 'y': 1.0},  # 前景保持原比例
            'transform': {'x': fg_transform_x, 'y': fg_transform_y},
            'crop': {
                'lower_left_x': crop_left,
                'lower_left_y': 1.0,
                'lower_right_x': crop_right,
                'lower_right_y': 1.0,
                'upper_left_x': crop_left,
                'upper_left_y': 0.0,
                'upper_right_x': crop_right,
                'upper_right_y': 0.0
            },
            'volume': 1.0,  # 保留音频
            'track_index': 1,
            'render_index': 1
        },
        'canvas': {'width': canvas_width, 'height': canvas_height}
    }

def generate_uuid():
    """生成剪映格式的UUID"""
    return str(uuid.uuid4()).upper()

def get_file_md5(file_path):
    """计算文件MD5"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return ""

def generate_draft_content(bg_video_info, fg_video_info, layout_params, output_dir):
    """生成剪映草稿内容JSON"""
    
    # 使用两个视频中较短的时长
    duration_us = min(bg_video_info.duration_us, fg_video_info.duration_us)
    
    # 生成ID
    draft_id = generate_uuid()
    bg_video_id = generate_uuid()
    fg_video_id = generate_uuid()
    bg_speed_id = generate_uuid()
    fg_speed_id = generate_uuid()
    bg_sound_id = generate_uuid()
    fg_sound_id = generate_uuid()
    bg_canvas_id = generate_uuid()
    fg_canvas_id = generate_uuid()
    bg_segment_id = generate_uuid()
    fg_segment_id = generate_uuid()
    bg_track_id = generate_uuid()
    fg_track_id = generate_uuid()
    
    draft = {
        "canvas_config": {
            "height": layout_params['canvas']['height'],
            "ratio": "16:9",
            "width": layout_params['canvas']['width']
        },
        "color_space": 0,
        "config": {
            "adjust_max_index": 1,
            "attachment_info": [],
            "combination_max_index": 1,
            "export_range": None,
            "extract_audio_last_index": 1,
            "lyrics_recognition_id": "",
            "lyrics_sync": True,
            "lyrics_taskinfo": [],
            "maintrack_adsorb": True,
            "material_save_mode": 0,
            "multi_language_current": "none",
            "multi_language_list": [],
            "multi_language_main": "none",
            "multi_language_mode": "none",
            "original_sound_last_index": 1,
            "record_audio_last_index": 1,
            "sticker_max_index": 1,
            "subtitle_keywords_config": None,
            "subtitle_recognition_id": "",
            "subtitle_sync": True,
            "subtitle_taskinfo": [],
            "system_font_list": [],
            "video_mute": False,
            "zoom_info_params": None
        },
        "cover": None,
        "create_time": 0,
        "duration": duration_us,
        "extra_info": None,
        "fps": 30.0,
        "free_render_index_mode_on": False,
        "group_container": None,
        "id": draft_id,
        "keyframe_graph_list": [],
        "keyframes": {
            "adjusts": [],
            "audios": [],
            "effects": [],
            "filters": [],
            "handwrites": [],
            "stickers": [],
            "texts": [],
            "videos": []
        },
        "last_modified_platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.9.0",
            "device_id": "d4d9c34f9062e2e30ab6e7581b8eee4d",
            "hard_disk_id": "",
            "mac_address": "c965a276aebf8dbc7d0ed20374348db6,2e26562dc4bb751e9fa4a35198fca8c3",
            "os": "windows",
            "os_version": "10.0.26100"
        },
        "materials": {
            "ai_translates": [],
            "audio_balances": [],
            "audio_effects": [],
            "audio_fades": [],
            "audio_track_indexes": [],
            "audios": [],
            "beats": [],
            "canvases": [
                {
                    "album_image": "",
                    "blur": 0.0,
                    "color": "",
                    "id": bg_canvas_id,
                    "image": "",
                    "image_id": "",
                    "image_name": "",
                    "source_platform": 0,
                    "team_id": "",
                    "type": "canvas_color"
                },
                {
                    "album_image": "",
                    "blur": 0.0,
                    "color": "",
                    "id": fg_canvas_id,
                    "image": "",
                    "image_id": "",
                    "image_name": "",
                    "source_platform": 0,
                    "team_id": "",
                    "type": "canvas_color"
                }
            ],
            "chromas": [],
            "color_curves": [],
            "digital_humans": [],
            "drafts": [],
            "effects": [],
            "flowers": [],
            "green_screens": [],
            "handwrites": [],
            "hsl": [],
            "images": [],
            "log_color_wheels": [],
            "loudnesses": [],
            "manual_deformations": [],
            "masks": [],
            "material_animations": [],
            "material_colors": [],
            "multi_language_refs": [],
            "placeholders": [],
            "plugin_effects": [],
            "primary_color_wheels": [],
            "realtime_denoises": [],
            "shapes": [],
            "smart_crops": [],
            "smart_relights": [],
            "sound_channel_mappings": [
                {
                    "audio_channel_mapping": 0,
                    "id": bg_sound_id,
                    "is_config_open": False,
                    "type": ""
                },
                {
                    "audio_channel_mapping": 0,
                    "id": fg_sound_id,
                    "is_config_open": False,
                    "type": ""
                }
            ],
            "speeds": [
                {
                    "curve_speed": None,
                    "id": bg_speed_id,
                    "mode": 0,
                    "speed": 1.0,
                    "type": "speed"
                },
                {
                    "curve_speed": None,
                    "id": fg_speed_id,
                    "mode": 0,
                    "speed": 1.0,
                    "type": "speed"
                }
            ],
            "stickers": [],
            "tail_leaders": [],
            "text_templates": [],
            "texts": [],
            "time_marks": [],
            "transitions": [],
            "video_effects": [],
            "video_trackings": [],
            "videos": [
                {
                    "aigc_type": "none",
                    "audio_fade": None,
                    "cartoon_path": "",
                    "category_id": "",
                    "category_name": "local",
                    "check_flag": 63487,
                    "crop": {
                        "lower_left_x": 0.0,
                        "lower_left_y": 1.0,
                        "lower_right_x": 1.0,
                        "lower_right_y": 1.0,
                        "upper_left_x": 0.0,
                        "upper_left_y": 0.0,
                        "upper_right_x": 1.0,
                        "upper_right_y": 0.0
                    },
                    "crop_ratio": "free",
                    "crop_scale": 1.0,
                    "duration": bg_video_info.duration_us,
                    "extra_type_option": 0,
                    "formula_id": "",
                    "freeze": None,
                    "has_audio": bg_video_info.has_audio,
                    "height": bg_video_info.height,
                    "id": bg_video_id,
                    "intensifies_audio_path": "",
                    "intensifies_path": "",
                    "is_ai_generate_content": False,
                    "is_copyright": False,
                    "is_text_edit_overdub": False,
                    "is_unified_beauty_mode": False,
                    "local_id": "",
                    "local_material_id": generate_uuid().lower(),
                    "material_id": "",
                    "material_name": bg_video_info.path.name,
                    "material_url": "",
                    "matting": {
                        "flag": 0,
                        "has_use_quick_brush": False,
                        "has_use_quick_eraser": False,
                        "interactiveTime": [],
                        "path": "",
                        "strokes": []
                    },
                    "media_path": "",
                    "object_locked": None,
                    "origin_material_id": "",
                    "path": f"##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##/materials/{bg_video_info.path.name}",
                    "picture_from": "none",
                    "picture_set_category_id": "",
                    "picture_set_category_name": "",
                    "request_id": "",
                    "reverse_intensifies_path": "",
                    "reverse_path": "",
                    "smart_motion": None,
                    "source": 0,
                    "source_platform": 0,
                    "stable": {
                        "matrix_path": "",
                        "stable_level": 0,
                        "time_range": {
                            "duration": 0,
                            "start": 0
                        }
                    },
                    "team_id": "",
                    "type": "video",
                    "video_algorithm": {
                        "algorithms": [],
                        "complement_frame_config": None,
                        "deflicker": None,
                        "gameplay_configs": [],
                        "motion_blur_config": None,
                        "noise_reduction": None,
                        "path": "",
                        "quality_enhance": None,
                        "time_range": None
                    },
                    "width": bg_video_info.width
                },
                {
                    "aigc_type": "none",
                    "audio_fade": None,
                    "cartoon_path": "",
                    "category_id": "",
                    "category_name": "local",
                    "check_flag": 63487,
                    "crop": layout_params['foreground'].get('crop', {
                        "lower_left_x": 0.11612903225806433,
                        "lower_left_y": 1.0,
                        "lower_right_x": 0.8048387096774192,
                        "lower_right_y": 1.0,
                        "upper_left_x": 0.11612903225806433,
                        "upper_left_y": 0.0,
                        "upper_right_x": 0.8048387096774192,
                        "upper_right_y": 0.0
                    }),
                    "crop_ratio": "free",
                    "crop_scale": 1.0,
                    "duration": fg_video_info.duration_us,
                    "extra_type_option": 0,
                    "formula_id": "",
                    "freeze": None,
                    "has_audio": fg_video_info.has_audio,
                    "height": fg_video_info.height,
                    "id": fg_video_id,
                    "intensifies_audio_path": "",
                    "intensifies_path": "",
                    "is_ai_generate_content": False,
                    "is_copyright": False,
                    "is_text_edit_overdub": False,
                    "is_unified_beauty_mode": False,
                    "local_id": "",
                    "local_material_id": generate_uuid().lower(),
                    "material_id": "",
                    "material_name": fg_video_info.path.name,
                    "material_url": "",
                    "matting": {
                        "flag": 0,
                        "has_use_quick_brush": False,
                        "has_use_quick_eraser": False,
                        "interactiveTime": [],
                        "path": "",
                        "strokes": []
                    },
                    "media_path": "",
                    "object_locked": None,
                    "origin_material_id": "",
                    "path": f"##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##/materials/{fg_video_info.path.name}",
                    "picture_from": "none",
                    "picture_set_category_id": "",
                    "picture_set_category_name": "",
                    "request_id": "",
                    "reverse_intensifies_path": "",
                    "reverse_path": "",
                    "smart_motion": None,
                    "source": 0,
                    "source_platform": 0,
                    "stable": {
                        "matrix_path": "",
                        "stable_level": 0,
                        "time_range": {
                            "duration": 0,
                            "start": 0
                        }
                    },
                    "team_id": "",
                    "type": "video",
                    "video_algorithm": {
                        "algorithms": [],
                        "complement_frame_config": None,
                        "deflicker": None,
                        "gameplay_configs": [],
                        "motion_blur_config": None,
                        "noise_reduction": None,
                        "path": "",
                        "quality_enhance": None,
                        "time_range": None
                    },
                    "width": fg_video_info.width
                }
            ],
            "vocal_beautifys": [],
            "vocal_separations": []
        },
        "mutable_config": None,
        "name": "",
        "new_version": "110.0.0",
        "platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.9.0",
            "device_id": "d4d9c34f9062e2e30ab6e7581b8eee4d",
            "hard_disk_id": "",
            "mac_address": "c965a276aebf8dbc7d0ed20374348db6,2e26562dc4bb751e9fa4a35198fca8c3",
            "os": "windows",
            "os_version": "10.0.26100"
        },
        "relationships": [],
        "render_index_track_mode_on": True,
        "retouch_cover": None,
        "source": "default",
        "static_cover_image_path": "",
        "time_marks": None,
        "tracks": [
            {
                "attribute": 0,
                "flag": 0,
                "id": bg_track_id,
                "is_default_name": True,
                "name": "",
                "segments": [
                    {
                        "caption_info": None,
                        "cartoon": False,
                        "clip": {
                            "alpha": 1.0,
                            "flip": {
                                "horizontal": False,
                                "vertical": False
                            },
                            "rotation": 0.0,
                            "scale": layout_params['background']['scale'],
                            "transform": layout_params['background']['transform']
                        },
                        "common_keyframes": [],
                        "enable_adjust": True,
                        "enable_color_correct_adjust": False,
                        "enable_color_curves": True,
                        "enable_color_match_adjust": False,
                        "enable_color_wheels": True,
                        "enable_lut": True,
                        "enable_smart_color_adjust": False,
                        "extra_material_refs": [bg_speed_id, bg_canvas_id, bg_sound_id],
                        "group_id": "",
                        "hdr_settings": {
                            "intensity": 1.0,
                            "mode": 1,
                            "nits": 1000
                        },
                        "id": bg_segment_id,
                        "intensifies_audio": False,
                        "is_placeholder": False,
                        "is_tone_modify": False,
                        "keyframe_refs": [],
                        "last_nonzero_volume": 1.0,
                        "material_id": bg_video_id,
                        "render_index": layout_params['background']['render_index'],
                        "responsive_layout": {
                            "enable": False,
                            "horizontal_pos_layout": 0,
                            "size_layout": 0,
                            "target_follow": "",
                            "vertical_pos_layout": 0
                        },
                        "reverse": False,
                        "source_timerange": {
                            "duration": duration_us,
                            "start": 0
                        },
                        "speed": 1.0,
                        "target_timerange": {
                            "duration": duration_us,
                            "start": 0
                        },
                        "template_id": "",
                        "template_scene": "default",
                        "track_attribute": 0,
                        "track_render_index": 0,
                        "uniform_scale": {
                            "on": True,
                            "value": 1.0376884422110553
                        },
                        "visible": True,
                        "volume": 0.0  # 背景视频静音
                    }
                ],
                "type": "video"
            },
            {
                "attribute": 1,
                "flag": 2,
                "id": fg_track_id,
                "is_default_name": True,
                "name": "",
                "segments": [
                    {
                        "caption_info": None,
                        "cartoon": False,
                        "clip": {
                            "alpha": 1.0,
                            "flip": {
                                "horizontal": False,
                                "vertical": False
                            },
                            "rotation": 0.0,
                            "scale": layout_params['foreground']['scale'],
                            "transform": layout_params['foreground']['transform']
                        },
                        "common_keyframes": [],
                        "enable_adjust": True,
                        "enable_color_correct_adjust": False,
                        "enable_color_curves": True,
                        "enable_color_match_adjust": False,
                        "enable_color_wheels": True,
                        "enable_lut": True,
                        "enable_smart_color_adjust": False,
                        "extra_material_refs": [fg_speed_id, fg_canvas_id, fg_sound_id],
                        "group_id": "",
                        "hdr_settings": {
                            "intensity": 1.0,
                            "mode": 1,
                            "nits": 1000
                        },
                        "id": fg_segment_id,
                        "intensifies_audio": False,
                        "is_placeholder": False,
                        "is_tone_modify": False,
                        "keyframe_refs": [],
                        "last_nonzero_volume": 1.0,
                        "material_id": fg_video_id,
                        "render_index": layout_params['foreground']['render_index'],
                        "responsive_layout": {
                            "enable": False,
                            "horizontal_pos_layout": 0,
                            "size_layout": 0,
                            "target_follow": "",
                            "vertical_pos_layout": 0
                        },
                        "reverse": False,
                        "source_timerange": {
                            "duration": duration_us,
                            "start": 0
                        },
                        "speed": 1.0,
                        "target_timerange": {
                            "duration": duration_us,
                            "start": 0
                        },
                        "template_id": "",
                        "template_scene": "default",
                        "track_attribute": 1,
                        "track_render_index": 1,
                        "uniform_scale": {
                            "on": True,
                            "value": 1.0
                        },
                        "visible": True,
                        "volume": layout_params['foreground']['volume']
                    }
                ],
                "type": "video"
            }
        ],
        "update_time": 0,
        "version": 360000
    }
    
    return draft

def generate_draft_meta(draft_name, duration_us, output_dir):
    """生成草稿元信息"""
    
    draft_id = generate_uuid()
    timestamp = int(datetime.now().timestamp() * 1000000)
    
    meta = {
        "cloud_package_completed_time": "",
        "draft_cloud_capcut_purchase_info": "",
        "draft_cloud_last_action_download": False,
        "draft_cloud_materials": [],
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": "draft_cover.jpg",
        "draft_deeplink_url": "",
        "draft_enterprise_info": {
            "draft_enterprise_extra": "",
            "draft_enterprise_id": "",
            "draft_enterprise_name": "",
            "enterprise_material": []
        },
        "draft_fold_path": str(output_dir),
        "draft_id": draft_id,
        "draft_is_ai_packaging_used": False,
        "draft_is_ai_shorts": False,
        "draft_is_ai_translate": False,
        "draft_is_article_video_draft": False,
        "draft_is_from_deeplink": "false",
        "draft_is_invisible": False,
        "draft_materials": [
            {"type": 0, "value": []},
            {"type": 1, "value": []},
            {"type": 2, "value": []},
            {"type": 3, "value": []},
            {"type": 6, "value": []},
            {"type": 7, "value": []},
            {"type": 8, "value": []}
        ],
        "draft_materials_copied_info": [],
        "draft_name": draft_name,
        "draft_new_version": "",
        "draft_removable_storage_device": "",
        "draft_root_path": str(output_dir.parent),
        "draft_segment_extra_info": [],
        "draft_timeline_materials_size_": 0,
        "draft_type": "",
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_modified": 0,
        "tm_draft_create": timestamp,
        "tm_draft_modified": timestamp,
        "tm_draft_removed": 0,
        "tm_duration": duration_us
    }
    
    return meta

def copy_material_files(bg_video_info, fg_video_info, output_dir):
    """复制材料文件到草稿目录"""
    materials_dir = output_dir / "materials"
    materials_dir.mkdir(exist_ok=True)
    
    # 复制背景视频
    bg_dest = materials_dir / bg_video_info.path.name
    if not bg_dest.exists():
        shutil.copy2(bg_video_info.path, bg_dest)
        logger.info(f"复制背景视频: {bg_video_info.path.name}")
    
    # 复制前景视频
    fg_dest = materials_dir / fg_video_info.path.name
    if not fg_dest.exists():
        shutil.copy2(fg_video_info.path, fg_dest)
        logger.info(f"复制前景视频: {fg_video_info.path.name}")
    
    return True

def test_video_merge():
    """测试视频合并功能"""
    logger.info("=" * 60)
    logger.info("开始视频拼接Pipeline测试")
    logger.info("=" * 60)
    
    # 设置视频路径
    videos_dir = Path("output/videos")
    
    # 查找视频文件
    bg_video_path = videos_dir / "Sunset painting  ｜ Poster colour painting ideas for beginners [JyxnlVCEoyU].mp4"
    fg_video_path = videos_dir / "户晨风跳胃袋舞 #户晨风 #戶晨風 [nhRRym9G_ZI].mp4"
    
    # 检查文件存在
    if not bg_video_path.exists():
        logger.error(f"背景视频不存在: {bg_video_path}")
        return False
    
    if not fg_video_path.exists():
        logger.error(f"前景视频不存在: {fg_video_path}")
        return False
    
    # 获取视频信息
    bg_video_info = get_video_info(bg_video_path)
    fg_video_info = get_video_info(fg_video_path)
    
    if not bg_video_info or not fg_video_info:
        logger.error("无法获取视频信息")
        return False
    
    # 创建输出目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    draft_name = f"video_merge_test_{timestamp}"
    output_dir = Path("output/drafts") / draft_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"输出目录: {output_dir}")
    
    # 计算布局参数
    layout_params = calculate_layout_params(bg_video_info, fg_video_info)
    
    # 生成草稿内容
    draft_content = generate_draft_content(bg_video_info, fg_video_info, layout_params, output_dir)
    
    # 生成元信息
    duration_us = min(bg_video_info.duration_us, fg_video_info.duration_us)
    draft_meta = generate_draft_meta(draft_name, duration_us, output_dir)
    
    # 保存JSON文件
    try:
        # 保存草稿内容
        content_file = output_dir / "draft_content.json"
        with open(content_file, 'w', encoding='utf-8') as f:
            json.dump(draft_content, f, indent=2, ensure_ascii=False)
        logger.info(f"草稿内容已保存: {content_file}")
        
        # 保存元信息
        meta_file = output_dir / "draft_meta_info.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(draft_meta, f, indent=2, ensure_ascii=False)
        logger.info(f"元信息已保存: {meta_file}")
        
        # 复制材料文件
        copy_material_files(bg_video_info, fg_video_info, output_dir)
        
        # 生成调试信息
        debug_info = {
            "test_time": datetime.now().isoformat(),
            "videos": {
                "background": {
                    "path": str(bg_video_path),
                    "size": f"{bg_video_info.width}x{bg_video_info.height}",
                    "duration": f"{bg_video_info.duration:.2f}s",
                    "aspect_ratio": f"{bg_video_info.aspect_ratio:.3f}",
                    "has_audio": bg_video_info.has_audio,
                    "role": "背景视频(静音)"
                },
                "foreground": {
                    "path": str(fg_video_path),
                    "size": f"{fg_video_info.width}x{fg_video_info.height}",
                    "duration": f"{fg_video_info.duration:.2f}s",
                    "aspect_ratio": f"{fg_video_info.aspect_ratio:.3f}",
                    "has_audio": fg_video_info.has_audio,
                    "role": "前景视频(保留音频)"
                }
            },
            "layout": layout_params,
            "output": {
                "draft_dir": str(output_dir),
                "files": [
                    "draft_content.json",
                    "draft_meta_info.json",
                    "materials/"
                ]
            },
            "notes": [
                "背景视频(16:9)已静音，填充整个画布",
                "前景视频(9:16)保留音频，居中显示",
                "画布尺寸为1920x1080 (16:9)",
                "使用两个视频中较短的时长"
            ]
        }
        
        debug_file = output_dir / "debug_info.json"
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(debug_info, f, indent=2, ensure_ascii=False)
        logger.info(f"调试信息已保存: {debug_file}")
        
        logger.info("=" * 60)
        logger.info("✅ 视频拼接测试成功!")
        logger.info(f"草稿已生成到: {output_dir}")
        logger.info("文件列表:")
        logger.info("  - draft_content.json (草稿内容)")
        logger.info("  - draft_meta_info.json (元信息)")
        logger.info("  - debug_info.json (调试信息)")
        logger.info("  - materials/ (视频文件)")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        return False

def main():
    """主函数"""
    print("\n🎬 视频拼接Pipeline测试工具")
    print("=" * 60)
    print("功能说明:")
    print("  1. 使用output/videos下的实际视频")
    print("  2. 16:9横屏视频作为静音背景")
    print("  3. 9:16竖屏视频保留音频作为前景")
    print("  4. 生成完整剪映草稿和材料文件")
    print("=" * 60)
    
    try:
        success = test_video_merge()
        if success:
            print("\n✅ 测试完成！请查看output/drafts目录下的草稿文件。")
        else:
            print("\n❌ 测试失败！请查看日志了解详情。")
    
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}", exc_info=True)
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()