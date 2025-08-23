#!/usr/bin/env python3
"""
剪映字幕服务 - 用于在现有草稿生成服务中添加字幕支持
"""

import re
import json
import uuid
import os
from typing import List, Dict, Optional
from pathlib import Path

# 导入安全打印函数
try:
    from utils import safe_print
except ImportError:
    # 如果导入失败，定义一个简单的 safe_print
    import platform
    def safe_print(message: str, file=None):
        if platform.system() == 'Windows':
            message = message.replace('✅', '[OK]').replace('❌', '[ERROR]').replace('⚠️', '[WARNING]').replace('ℹ️', '[INFO]')
        print(message, file=file)


class JianyingSubtitleService:
    """剪映字幕服务"""
    
    def __init__(self):
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
    
    def validate_subtitle_file(self, audio_path: str, srt_path: Optional[str] = None) -> Optional[str]:
        """
        校验字幕文件是否存在且名称匹配
        
        Args:
            audio_path: 音频文件路径
            srt_path: 字幕文件路径（可选）
            
        Returns:
            有效的字幕文件路径，如果不存在或不匹配则返回None
        """
        if srt_path:
            # 如果提供了字幕路径，验证文件名是否匹配
            audio_name = Path(audio_path).stem
            srt_name = Path(srt_path).stem
            
            if audio_name != srt_name:
                safe_print(f"⚠️ 警告：音频文件名 '{audio_name}' 与字幕文件名 '{srt_name}' 不匹配")
                return None
            
            if os.path.exists(srt_path):
                safe_print(f"✓ 找到字幕文件：{os.path.basename(srt_path)}")
                return srt_path
        else:
            # 自动查找同名的SRT文件
            audio_dir = os.path.dirname(audio_path)
            audio_name = Path(audio_path).stem
            srt_path = os.path.join(audio_dir, f"{audio_name}.srt")
            
            if os.path.exists(srt_path):
                safe_print(f"✓ 自动检测到字幕文件：{os.path.basename(srt_path)}")
                return srt_path
        
        safe_print("ℹ️ 未找到匹配的字幕文件，将不添加字幕")
        return None
    
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
                    continue
        
        return subtitles
    
    def _time_to_microseconds(self, hours: int, minutes: int, seconds: int, milliseconds: int) -> int:
        """将时间转换为微秒"""
        total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
        return total_ms * 1000  # 转换为微秒
    
    def _generate_uuid(self) -> str:
        """生成UUID"""
        return str(uuid.uuid4()).upper().replace('-', '')
    
    def create_subtitle_materials(self, srt_path: str) -> Dict:
        """
        创建字幕相关的所有材料
        
        Args:
            srt_path: SRT文件路径
            
        Returns:
            包含所有字幕材料的字典
        """
        # 读取并解析SRT文件
        with open(srt_path, 'r', encoding='utf-8-sig') as f:
            srt_content = f.read()
        
        subtitles = self.parse_srt(srt_content)
        print(f"  解析到 {len(subtitles)} 条字幕")
        
        # 创建字幕材料
        text_materials = []
        animation_materials = []
        text_segments = []
        
        for i, subtitle in enumerate(subtitles):
            # 创建文本材料
            text_material = self._create_text_material(subtitle)
            text_materials.append(text_material)
            
            # 创建动画材料
            animation_material = self._create_animation_material()
            animation_materials.append(animation_material)
            
            # 创建字幕片段
            text_segment = self._create_text_segment(
                text_material, 
                animation_material, 
                subtitle, 
                i
            )
            text_segments.append(text_segment)
        
        return {
            'text_materials': text_materials,
            'animation_materials': animation_materials,
            'text_segments': text_segments,
            'subtitle_count': len(subtitles)
        }
    
    def _create_text_material(self, subtitle: Dict) -> Dict:
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
        
        material = {
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
        
        # 添加所有其他必要字段
        for key in ["caption_template_info", "font_category_id", "font_category_name", 
                   "font_id", "font_name", "font_source_platform", "font_team_id", 
                   "font_url", "group_id", "preset_category", "preset_category_id", 
                   "preset_id", "preset_index", "preset_name", "recognize_task_id", 
                   "source_from", "style_name", "subtitle_keywords", 
                   "text_curve", "text_preset_resource_id", "text_to_audio_ids"]:
            if key not in material:
                material[key] = "" if isinstance(key, str) else None
        
        return material
    
    def _create_animation_material(self) -> Dict:
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
    
    def _create_text_segment(self, text_material: Dict, animation_material: Dict, 
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
    
    def create_subtitle_track(self, text_segments: List[Dict]) -> Dict:
        """
        创建字幕轨道
        
        Args:
            text_segments: 字幕片段列表
            
        Returns:
            字幕轨道字典
        """
        return {
            "id": self._generate_uuid(),
            "type": "text",
            "segments": text_segments,
            "attribute": 0,
            "flag": 1,
            "is_default_name": True,
            "name": ""
        }


# 单例模式
_subtitle_service = None

def get_subtitle_service() -> JianyingSubtitleService:
    """获取字幕服务实例（单例）"""
    global _subtitle_service
    if _subtitle_service is None:
        _subtitle_service = JianyingSubtitleService()
    return _subtitle_service