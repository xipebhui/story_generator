#!/usr/bin/env python3
"""
SRT字幕转剪映字幕格式转换器
将SRT字幕文件转换为剪映项目中的字幕格式，并应用样式和动画效果
"""

import re
import json
import uuid
from typing import List, Dict, Tuple
from pathlib import Path


class SRTToJianyingConverter:
    """SRT到剪映字幕格式转换器"""
    
    def __init__(self):
        # 默认字幕样式配置
        self.default_style = {
            "font_path": "D:/tmp/jy/JianyingPro/5.9.0.11632/Resources/Font/后现代体.otf",
            "font_id": "6740435494053614093",
            "font_title": "后现代体",
            "font_size": 13.0,
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
            "category_name": "入场"
        }
    
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
                    index = int(lines[0])
                    
                    # 提取时间戳
                    time_match = re.match(
                        r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
                        lines[1]
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
                except (ValueError, IndexError):
                    continue
        
        return subtitles
    
    def _time_to_microseconds(self, hours: int, minutes: int, seconds: int, milliseconds: int) -> int:
        """将时间转换为微秒"""
        total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
        return total_ms * 1000  # 转换为微秒
    
    def create_text_material(self, subtitle: Dict, render_index: int) -> Dict:
        """创建剪映文本材料对象"""
        material_id = str(uuid.uuid4()).upper().replace('-', '')
        animation_id = str(uuid.uuid4()).upper().replace('-', '')
        
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
                    "id": self.default_style["font_id"],
                    "path": self.default_style["font_path"]
                },
                "range": [0, len(subtitle['text'])],
                "size": self.default_style["font_size"],
                "strokes": [{
                    "alpha": self.default_style["border_alpha"],
                    "content": {
                        "render_type": "solid",
                        "solid": {
                            "alpha": 1.0,
                            "color": [0.0, 0.0, 0.0]  # 黑色描边
                        }
                    },
                    "width": self.default_style["border_width"]
                }],
                "useLetterColor": True
            }],
            "text": subtitle['text']
        }
        
        # 创建文本材料
        text_material = {
            "id": material_id,
            "type": "subtitle",
            "content": json.dumps(content, ensure_ascii=False),
            "text_color": self.default_style["text_color"],
            "text_alpha": self.default_style["text_alpha"],
            "text_size": 30,
            "font_path": self.default_style["font_path"],
            "font_resource_id": self.default_style["font_id"],
            "font_title": self.default_style["font_title"],
            "font_size": self.default_style["font_size"],
            "border_color": self.default_style["border_color"],
            "border_width": self.default_style["border_width"],
            "border_alpha": self.default_style["border_alpha"],
            "shadow_alpha": self.default_style["shadow_alpha"],
            "shadow_angle": self.default_style["shadow_angle"],
            "shadow_distance": self.default_style["shadow_distance"],
            "shadow_point": {
                "x": 0.6363961030678928,
                "y": -0.6363961030678928
            },
            "alignment": self.default_style["alignment"],
            "background_alpha": 1.0,
            "background_color": "#000000",
            "background_style": 0,
            "bold_width": 0.0,
            "check_flag": 15,
            "fixed_height": -1.0,
            "fixed_width": -1.0,
            "force_apply_line_max_width": False,
            "global_alpha": 1.0,
            "has_shadow": False,
            "initial_scale": 1.0,
            "inner_padding": -1.0,
            "is_rich_text": False,
            "italic_degree": 0,
            "layer_weight": 1,
            "letter_spacing": 0.0,
            "line_feed": 1,
            "line_max_width": 0.82,
            "line_spacing": 0.02,
            "multi_language_current": "none",
            "preset_has_set_alignment": False,
            "recognize_type": 0,
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
            }
        }
        
        # 创建动画材料
        animation_material = {
            "id": animation_id,
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
                "resource_id": "7237411357514011192",
                "start": 0,
                "type": "in"
            }]
        }
        
        # 创建轨道段
        segment = {
            "id": str(uuid.uuid4()).upper().replace('-', ''),
            "material_id": material_id,
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
                "transform": {"x": 0.0, "y": self.default_style["position_y"]}
            },
            "extra_material_refs": [animation_id],
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
        
        return {
            'text_material': text_material,
            'animation_material': animation_material,
            'segment': segment
        }
    
    def convert_to_jianying(self, srt_file_path: str, output_path: str = None):
        """将SRT文件转换为剪映字幕数据"""
        # 读取SRT文件
        with open(srt_file_path, 'r', encoding='utf-8-sig') as f:
            srt_content = f.read()
        
        # 解析字幕
        subtitles = self.parse_srt(srt_content)
        print(f"解析到 {len(subtitles)} 条字幕")
        
        # 创建剪映字幕数据
        text_materials = []
        animation_materials = []
        segments = []
        
        for i, subtitle in enumerate(subtitles):
            result = self.create_text_material(subtitle, i)
            text_materials.append(result['text_material'])
            animation_materials.append(result['animation_material'])
            segments.append(result['segment'])
        
        # 构建输出数据
        output_data = {
            'text_materials': text_materials,
            'animation_materials': animation_materials,
            'segments': segments,
            'subtitle_count': len(subtitles),
            'total_duration': max([s['end'] for s in subtitles]) if subtitles else 0
        }
        
        # 保存输出
        if output_path is None:
            output_path = srt_file_path.replace('.srt', '_jianying_subtitles.json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"转换完成！输出文件：{output_path}")
        print(f"总时长：{output_data['total_duration'] / 1000000:.2f} 秒")
        
        return output_data


def main():
    """主函数"""
    converter = SRTToJianyingConverter()
    
    # 转换SRT文件
    srt_file = "/Users/pengfei.shi/workspace/youtube/story_generator/draft_gen/test_t54eELXWe4g_story.srt"
    output_file = "/Users/pengfei.shi/workspace/youtube/story_generator/draft_gen/test_t54eELXWe4g_story_jianying.json"
    
    converter.convert_to_jianying(srt_file, output_file)


if __name__ == "__main__":
    main()