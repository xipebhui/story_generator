#!/usr/bin/env python3
"""
剪映草稿生成器 - 从SRT字幕和音频文件生成完整的剪映项目
"""

import re
import json
import uuid
import os
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from datetime import datetime


class JianyingDraftGenerator:
    """剪映草稿生成器"""
    
    def __init__(self):
        # 项目基本配置
        self.project_config = {
            "canvas_width": 1920,
            "canvas_height": 1080,
            "canvas_ratio": "16:9",
            "fps": 30.0,
            "platform": "windows",
            "app_version": "5.9.0"
        }
        
        # 字幕样式配置
        self.subtitle_style = {
            "font_path": "D:/tmp/jy/JianyingPro/5.9.0.11632/Resources/Font/后现代体.otf",
            "font_id": "6740435494053614093",
            "font_title": "后现代体",
            "font_size": 13.0,
            "text_size": 30,
            "text_color": "#ffde00",  # 黄色
            "text_alpha": 1.0,
            "border_color": "#000000",  # 黑色描边
            "border_width": 0.08,
            "border_alpha": 1.0,
            "shadow_angle": -45.0,
            "shadow_distance": 5.0,
            "shadow_alpha": 0.9,
            "position_y": -0.8,  # 底部位置
            "alignment": 1,  # 居中对齐
        }
        
        # 入场动画配置
        self.animation_config = {
            "animation_id": "14235878",
            "animation_name": "打字光标",
            "animation_duration": 100000,  # 0.1秒
            "category_id": "ruchang",
            "category_name": "入场",
            "resource_id": "7237411357514011192"
        }
    
    def validate_files(self, audio_path: str, srt_path: str) -> bool:
        """
        校验音频和字幕文件名是否匹配
        
        Args:
            audio_path: 音频文件路径
            srt_path: 字幕文件路径
            
        Returns:
            bool: 文件名是否匹配
        """
        audio_name = Path(audio_path).stem
        srt_name = Path(srt_path).stem
        
        if audio_name != srt_name:
            print(f"警告：音频文件名 '{audio_name}' 与字幕文件名 '{srt_name}' 不匹配！")
            return False
        
        # 检查文件是否存在
        if not os.path.exists(audio_path):
            print(f"错误：音频文件不存在：{audio_path}")
            return False
        
        if not os.path.exists(srt_path):
            print(f"错误：字幕文件不存在：{srt_path}")
            return False
        
        print(f"✓ 文件校验通过：{audio_name}")
        return True
    
    def parse_srt(self, srt_content: str) -> List[Dict]:
        """解析SRT文件内容"""
        subtitles = []
        
        # 分割字幕块
        blocks = re.split(r'\n\n+', srt_content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    # 提取序号
                    index = int(lines[0].strip())
                    
                    # 提取时间戳
                    time_match = re.match(
                        r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
                        lines[1].strip()
                    )
                    if time_match:
                        start_time = self._time_to_microseconds(
                            int(time_match.group(1)),
                            int(time_match.group(2)),
                            int(time_match.group(3)),
                            int(time_match.group(4))
                        )
                        end_time = self._time_to_microseconds(
                            int(time_match.group(5)),
                            int(time_match.group(6)),
                            int(time_match.group(7)),
                            int(time_match.group(8))
                        )
                        
                        # 提取文本（可能多行）
                        text = ' '.join(lines[2:]).strip()
                        
                        subtitles.append({
                            'index': index,
                            'start': start_time,
                            'end': end_time,
                            'duration': end_time - start_time,
                            'text': text
                        })
                except (ValueError, IndexError) as e:
                    print(f"解析字幕块时出错：{e}")
                    continue
        
        return subtitles
    
    def _time_to_microseconds(self, hours: int, minutes: int, seconds: int, milliseconds: int) -> int:
        """将时间转换为微秒"""
        total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
        return total_ms * 1000  # 转换为微秒
    
    def _generate_uuid(self) -> str:
        """生成UUID"""
        return str(uuid.uuid4()).upper().replace('-', '')
    
    def get_audio_duration(self, audio_path: str) -> int:
        """
        获取音频文件时长（微秒）
        注意：这里简化处理，实际使用时应该用音频处理库获取准确时长
        """
        # 这里应该使用 mutagen 或 pydub 等库获取实际音频时长
        # 暂时返回一个默认值或从字幕推算
        return 125000000  # 125秒的默认值
    
    def create_audio_material(self, audio_path: str, duration: int) -> Dict:
        """创建音频材料"""
        material_id = self._generate_uuid()
        audio_name = Path(audio_path).name
        
        return {
            "id": material_id,
            "type": "music",
            "name": "背景音乐",
            "path": f"##_draftpath_placeholder_{self._generate_uuid()}_##/materials/{audio_name}",
            "duration": duration,
            "check_flag": 1,
            "copyright_limit_type": "none",
            "is_ai_clone_tone": False,
            "is_text_edit_overdub": False,
            "is_ugc": False,
            "wave_points": [],
            # 其他必要字段
            "app_id": 0,
            "category_id": "",
            "category_name": "",
            "effect_id": "",
            "formula_id": "",
            "intensifies_path": "",
            "local_material_id": "",
            "music_id": "",
            "query": "",
            "request_id": "",
            "resource_id": "",
            "search_id": "",
            "source_from": "",
            "source_platform": 0,
            "team_id": "",
            "text_id": "",
            "tone_category_id": "",
            "tone_category_name": "",
            "tone_effect_id": "",
            "tone_effect_name": "",
            "tone_platform": "",
            "tone_second_category_id": "",
            "tone_second_category_name": "",
            "tone_speaker": "",
            "tone_type": "",
            "video_id": ""
        }
    
    def create_text_material(self, subtitle: Dict) -> Dict:
        """创建单个字幕材料"""
        material_id = self._generate_uuid()
        
        # 构建富文本内容
        content = {
            "styles": [{
                "fill": {
                    "content": {
                        "render_type": "solid",
                        "solid": {
                            "alpha": 1.0,
                            "color": [1.0, 0.8705882430076599, 0.0]  # 黄色RGB
                        }
                    }
                },
                "font": {
                    "id": self.subtitle_style["font_id"],
                    "path": self.subtitle_style["font_path"]
                },
                "range": [0, len(subtitle['text'])],
                "size": self.subtitle_style["font_size"],
                "strokes": [{
                    "alpha": self.subtitle_style["border_alpha"],
                    "content": {
                        "render_type": "solid",
                        "solid": {
                            "alpha": 1.0,
                            "color": [0.0, 0.0, 0.0]  # 黑色描边
                        }
                    },
                    "width": self.subtitle_style["border_width"]
                }],
                "useLetterColor": True
            }],
            "text": subtitle['text']
        }
        
        return {
            "id": material_id,
            "type": "subtitle",
            "content": json.dumps(content, ensure_ascii=False),
            "text_color": self.subtitle_style["text_color"],
            "text_alpha": self.subtitle_style["text_alpha"],
            "text_size": self.subtitle_style["text_size"],
            "font_path": self.subtitle_style["font_path"],
            "font_resource_id": self.subtitle_style["font_id"],
            "font_title": self.subtitle_style["font_title"],
            "font_size": self.subtitle_style["font_size"],
            "border_color": self.subtitle_style["border_color"],
            "border_width": self.subtitle_style["border_width"],
            "border_alpha": self.subtitle_style["border_alpha"],
            "shadow_alpha": self.subtitle_style["shadow_alpha"],
            "shadow_angle": self.subtitle_style["shadow_angle"],
            "shadow_distance": self.subtitle_style["shadow_distance"],
            "shadow_point": {
                "x": 0.6363961030678928,
                "y": -0.6363961030678928
            },
            "alignment": self.subtitle_style["alignment"],
            "add_type": 2,
            "background_alpha": 1.0,
            "background_color": "#000000",
            "background_style": 0,
            "background_height": 0.14,
            "background_width": 0.14,
            "background_horizontal_offset": 0.0,
            "background_vertical_offset": 0.0,
            "background_round_radius": 0.0,
            "base_content": "",
            "bold_width": 0.0,
            "check_flag": 15,
            "combo_info": {"text_templates": []},
            "fixed_height": -1.0,
            "fixed_width": -1.0,
            "force_apply_line_max_width": False,
            "global_alpha": 1.0,
            "has_shadow": False,
            "initial_scale": 1.0,
            "inner_padding": -1.0,
            "is_rich_text": False,
            "italic_degree": 0,
            "ktv_color": "",
            "language": "",
            "layer_weight": 1,
            "letter_spacing": 0.0,
            "line_feed": 1,
            "line_max_width": 0.82,
            "line_spacing": 0.02,
            "multi_language_current": "none",
            "name": "",
            "original_size": [],
            "preset_has_set_alignment": False,
            "recognize_type": 0,
            "relevance_segment": [],
            "shadow_smoothing": 0.45,
            "shape_clip_x": False,
            "shape_clip_y": False,
            "sub_type": 0,
            "subtitle_template_original_fontsize": 0.0,
            "tts_auto_update": False,
            "typesetting": 0,
            "underline": False,
            "underline_offset": 0.22,
            "underline_width": 0.05,
            "use_effect_default_color": True,
            "words": {
                "end_time": [],
                "start_time": [],
                "text": []
            },
            "fonts": [{
                "category_id": "preset",
                "category_name": "剪映预设",
                "effect_id": self.subtitle_style["font_id"],
                "file_uri": "",
                "id": self._generate_uuid(),
                "path": "",
                "request_id": "",
                "resource_id": self.subtitle_style["font_id"],
                "source_platform": 0,
                "team_id": "",
                "title": self.subtitle_style["font_title"]
            }]
        }
    
    def create_animation_material(self) -> Dict:
        """创建动画材料"""
        return {
            "id": self._generate_uuid(),
            "type": "sticker_animation",
            "multi_language_current": "none",
            "animations": [{
                "anim_adjust_params": None,
                "category_id": self.animation_config["category_id"],
                "category_name": self.animation_config["category_name"],
                "duration": self.animation_config["animation_duration"],
                "id": self.animation_config["animation_id"],
                "material_type": "sticker",
                "name": self.animation_config["animation_name"],
                "panel": "",
                "path": f"C:/Users/Administrator/AppData/Local/JianyingPro/User Data/Cache/effect/{self.animation_config['animation_id']}/12196518b89652860631d196d19b6f45",
                "platform": "all",
                "request_id": "",
                "resource_id": self.animation_config["resource_id"],
                "start": 0,
                "type": "in"
            }]
        }
    
    def create_text_segment(self, text_material: Dict, animation_material: Dict, 
                           subtitle: Dict, render_index: int) -> Dict:
        """创建字幕轨道段"""
        return {
            "id": self._generate_uuid(),
            "material_id": text_material["id"],
            "target_timerange": {
                "start": subtitle['start'],
                "duration": subtitle['duration']
            },
            "source_timerange": None,
            "render_index": 14000 + render_index,
            "track_render_index": 2,
            "track_attribute": 0,
            "speed": 1.0,
            "volume": 1.0,
            "visible": True,
            "clip": {
                "alpha": 1.0,
                "flip": {"horizontal": False, "vertical": False},
                "rotation": 0.0,
                "scale": {"x": 1.0, "y": 1.0},
                "transform": {"x": 0.0, "y": self.subtitle_style["position_y"]}
            },
            "extra_material_refs": [animation_material["id"]],
            "enable_adjust": False,
            "enable_color_correct_adjust": False,
            "enable_color_curves": True,
            "enable_color_match_adjust": False,
            "enable_color_wheels": True,
            "enable_lut": False,
            "enable_smart_color_adjust": False,
            "common_keyframes": [],
            "keyframe_refs": [],
            "uniform_scale": {"on": True, "value": 1.0},
            "last_nonzero_volume": 1.0,
            "is_placeholder": False,
            "is_tone_modify": False,
            "cartoon": False,
            "caption_info": None,
            "intensifies_audio": False,
            "group_id": "",
            "hdr_settings": None,
            "reverse": False,
            "template_id": "",
            "template_scene": "default",
            "responsive_layout": {
                "enable": False,
                "horizontal_pos_layout": 0,
                "size_layout": 0,
                "target_follow": "",
                "vertical_pos_layout": 0
            }
        }
    
    def generate_draft(self, audio_path: str, srt_path: str, output_path: str = None):
        """
        生成剪映草稿文件
        
        Args:
            audio_path: 音频文件路径
            srt_path: 字幕文件路径
            output_path: 输出草稿文件路径
        """
        # 1. 校验文件
        if not self.validate_files(audio_path, srt_path):
            return None
        
        # 2. 读取并解析SRT文件
        with open(srt_path, 'r', encoding='utf-8-sig') as f:
            srt_content = f.read()
        
        subtitles = self.parse_srt(srt_content)
        print(f"解析到 {len(subtitles)} 条字幕")
        
        # 3. 获取音频时长
        audio_duration = max([s['end'] for s in subtitles]) if subtitles else 3000000
        
        # 4. 创建音频材料
        audio_material = self.create_audio_material(audio_path, audio_duration)
        
        # 5. 创建字幕材料和轨道段
        text_materials = []
        animation_materials = []
        text_segments = []
        
        for i, subtitle in enumerate(subtitles):
            text_material = self.create_text_material(subtitle)
            animation_material = self.create_animation_material()
            text_segment = self.create_text_segment(text_material, animation_material, subtitle, i)
            
            text_materials.append(text_material)
            animation_materials.append(animation_material)
            text_segments.append(text_segment)
        
        # 6. 构建完整的草稿JSON
        draft_id = self._generate_uuid()
        draft = {
            "canvas_config": {
                "height": self.project_config["canvas_height"],
                "width": self.project_config["canvas_width"],
                "ratio": self.project_config["canvas_ratio"]
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
                "video_mute": True,
                "zoom_info_params": None
            },
            "cover": None,
            "create_time": 0,
            "duration": audio_duration,
            "extra_info": None,
            "fps": self.project_config["fps"],
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
            "materials": {
                "ai_translates": [],
                "audio_balances": [],
                "audio_effects": [],
                "audio_fades": [{
                    "fade_in_duration": 0,
                    "fade_out_duration": 0,
                    "fade_type": 0,
                    "id": self._generate_uuid(),
                    "type": "audio_fade"
                }],
                "audio_track_indexes": [],
                "audios": [audio_material],
                "beats": [],
                "canvases": [{
                    "album_image": "",
                    "blur": 0.0,
                    "color": "",
                    "id": self._generate_uuid(),
                    "image": "",
                    "image_id": "",
                    "image_name": "",
                    "source_platform": 0,
                    "team_id": "",
                    "type": "canvas_color"
                }],
                "material_animations": animation_materials,
                "texts": text_materials,
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
                "material_colors": [],
                "multi_language_refs": [],
                "placeholders": [],
                "plugin_effects": [],
                "primary_color_wheels": [],
                "realtime_denoises": [],
                "shapes": [],
                "smart_crops": [],
                "smart_relights": [],
                "sound_channel_mappings": [],
                "speeds": [{
                    "curve_speed": None,
                    "id": self._generate_uuid(),
                    "mode": 0,
                    "speed": 1.0,
                    "type": "speed"
                }],
                "stickers": [],
                "tail_leaders": [],
                "text_templates": [],
                "time_marks": [],
                "transitions": [],
                "video_effects": [],
                "video_trackings": [],
                "videos": [],
                "vocal_beautifys": [],
                "vocal_separations": []
            },
            "mutable_config": None,
            "name": "",
            "new_version": "110.0.0",
            "platform": {
                "app_id": 3704,
                "app_source": "lv",
                "app_version": self.project_config["app_version"],
                "device_id": self._generate_uuid(),
                "hard_disk_id": "",
                "mac_address": "",
                "os": self.project_config["platform"],
                "os_version": "10.0.20348"
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
                    "id": self._generate_uuid(),
                    "is_default_name": True,
                    "name": "",
                    "segments": [{
                        "caption_info": None,
                        "cartoon": False,
                        "clip": None,
                        "common_keyframes": [],
                        "enable_adjust": False,
                        "enable_color_correct_adjust": False,
                        "enable_color_curves": True,
                        "enable_color_match_adjust": False,
                        "enable_color_wheels": True,
                        "enable_lut": False,
                        "enable_smart_color_adjust": False,
                        "extra_material_refs": [],
                        "group_id": "",
                        "hdr_settings": None,
                        "id": self._generate_uuid(),
                        "intensifies_audio": False,
                        "is_placeholder": False,
                        "is_tone_modify": False,
                        "keyframe_refs": [],
                        "last_nonzero_volume": 1.0,
                        "material_id": audio_material["id"],
                        "render_index": 0,
                        "responsive_layout": {
                            "enable": False,
                            "horizontal_pos_layout": 0,
                            "size_layout": 0,
                            "target_follow": "",
                            "vertical_pos_layout": 0
                        },
                        "reverse": False,
                        "source_timerange": {
                            "duration": audio_duration,
                            "start": 0
                        },
                        "speed": 1.0,
                        "target_timerange": {
                            "duration": audio_duration,
                            "start": 0
                        },
                        "template_id": "",
                        "template_scene": "default",
                        "track_attribute": 0,
                        "track_render_index": 0,
                        "uniform_scale": None,
                        "visible": True,
                        "volume": 1.0
                    }],
                    "type": "audio"
                },
                {
                    "attribute": 0,
                    "flag": 1,
                    "id": self._generate_uuid(),
                    "is_default_name": True,
                    "name": "",
                    "segments": text_segments,
                    "type": "text"
                }
            ],
            "update_time": 0,
            "version": 360000
        }
        
        # 7. 保存草稿文件
        if output_path is None:
            output_path = srt_path.replace('.srt', '_draft.json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 草稿生成完成：{output_path}")
        print(f"  - 音频时长：{audio_duration / 1000000:.2f} 秒")
        print(f"  - 字幕数量：{len(subtitles)} 条")
        
        return draft


def main():
    """主函数"""
    generator = JianyingDraftGenerator()
    
    # 测试文件路径
    audio_file = "/Users/pengfei.shi/workspace/youtube/story_generator/draft_gen/test_t54eELXWe4g_story.mp3"
    srt_file = "/Users/pengfei.shi/workspace/youtube/story_generator/draft_gen/test_t54eELXWe4g_story.srt"
    output_file = "/Users/pengfei.shi/workspace/youtube/story_generator/draft_gen/test_t54eELXWe4g_story_draft.json"
    
    # 生成草稿
    generator.generate_draft(audio_file, srt_file, output_file)


if __name__ == "__main__":
    main()