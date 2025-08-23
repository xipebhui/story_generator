#!/usr/bin/env python3
"""
剪映草稿生成服务
综合音频、多图片、转场和特效的完整草稿生成服务
"""

import os
import sys
import json
import shutil
import random
import argparse
import zipfile
import logging
from typing import List, Optional
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入安全打印函数
try:
    from utils import safe_print
except ImportError:
    # 如果导入失败，定义一个简单的 safe_print
    import platform
    def safe_print(message: str, file=None):
        if platform.system() == 'Windows':
            message = message.replace('✅', '[OK]').replace('❌', '[ERROR]').replace('⚠️', '[WARNING]')
        try:
            print(message, file=file)
        except UnicodeEncodeError:
            message_ascii = message.encode('ascii', 'replace').decode('ascii')
            print(message_ascii, file=file)

from pydub import AudioSegment
from models.draft_models import (
    Draft, Track, Segment, VideoMaterial, AudioMaterial, Materials,
    Timerange, Clip, Transition, VideoEffect, Keyframe, CommonKeyframe
)
from models.draft_effects_library import (
    Transitions, VideoEffects, SpeedInfo, CanvasInfo, MaterialAnimationInfo
)
from jianying_subtitle_service import get_subtitle_service
import uuid

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def gen_upper_uuid():
    """生成大写UUID"""
    return str(uuid.uuid4()).upper().replace('-', '')


class DraftGeneratorService:
    """剪映草稿生成服务"""

    def __init__(self):
        """初始化服务"""
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        self.supported_audio_formats = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']

        # 可用的转场列表（用于随机选择）
        self.available_transitions = [
            Transitions.PUSH_IN_II,
            Transitions.SLIDE_RIGHT
        ]

        # 可用的特效列表（用于随机选择）
        self.available_effects = [
            VideoEffects.SNOW
        ]
        
        # 默认图片缩放比例
        self.default_image_scale = 1.8

    def get_audio_duration_ms(self, audio_path: str) -> int:
        """获取音频时长（毫秒）"""
        audio = AudioSegment.from_file(audio_path)
        return len(audio)

    def scan_images(self, images_dir: str) -> List[str]:
        """扫描目录下的所有图片文件"""
        images = []
        for file_path in Path(images_dir).iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_image_formats:
                images.append(str(file_path))

        # 按文件名排序
        images.sort()
        return images

    def create_keyframes_for_segment(self, segment_duration_us: int, segment_index: int, image_scale: float = 1.8) -> List[CommonKeyframe]:
        """
        为片段创建关键帧动画
        
        Args:
            segment_duration_us: 片段时长（微秒）
            segment_index: 片段索引（用于决定动画方向）
            image_scale: 图片缩放比例（默认1.8）
            
        Returns:
            关键帧列表
        """
        keyframes = []
        
        # 根据片段索引决定动画类型
        if segment_index % 2 == 0:
            # 偶数索引：从上到下移动
            # Y轴位置关键帧
            keyframes.append(CommonKeyframe(
                id=gen_upper_uuid(),
                property_type="KFTypePositionY",
                keyframe_list=[
                    Keyframe(
                        id=gen_upper_uuid(),
                        time_offset=0,
                        values=[0.8]  # 起始位置：上方
                    ),
                    Keyframe(
                        id=gen_upper_uuid(),
                        time_offset=segment_duration_us,
                        values=[-0.8]  # 结束位置：下方
                    )
                ]
            ))
        else:
            # 奇数索引：从下到上移动
            # Y轴位置关键帧
            keyframes.append(CommonKeyframe(
                id=gen_upper_uuid(),
                property_type="KFTypePositionY",
                keyframe_list=[
                    Keyframe(
                        id=gen_upper_uuid(),
                        time_offset=0,
                        values=[-0.8]  # 起始位置：下方
                    ),
                    Keyframe(
                        id=gen_upper_uuid(),
                        time_offset=segment_duration_us,
                        values=[0.8]  # 结束位置：上方
                    )
                ]
            ))
        
        # 添加X轴位置关键帧（保持不变）
        keyframes.append(CommonKeyframe(
            id=gen_upper_uuid(),
            property_type="KFTypePositionX",
            keyframe_list=[
                Keyframe(
                    id=gen_upper_uuid(),
                    time_offset=0,
                    values=[0.0]
                ),
                Keyframe(
                    id=gen_upper_uuid(),
                    time_offset=segment_duration_us,
                    values=[0.0]
                )
            ]
        ))
        
        # 添加缩放关键帧（使用传入的缩放比例）
        keyframes.append(CommonKeyframe(
            id=gen_upper_uuid(),
            property_type="KFTypeScaleX",
            keyframe_list=[
                Keyframe(
                    id=gen_upper_uuid(),
                    time_offset=0,
                    values=[image_scale]
                ),
                Keyframe(
                    id=gen_upper_uuid(),
                    time_offset=segment_duration_us,
                    values=[image_scale]
                )
            ]
        ))
        
        # 添加旋转关键帧（保持不旋转）
        keyframes.append(CommonKeyframe(
            id=gen_upper_uuid(),
            property_type="KFTypeRotation",
            keyframe_list=[
                Keyframe(
                    id=gen_upper_uuid(),
                    time_offset=0,
                    values=[0.0]
                ),
                Keyframe(
                    id=gen_upper_uuid(),
                    time_offset=segment_duration_us,
                    values=[0.0]
                )
            ]
        ))
        
        return keyframes

    def select_random_images(self, all_images: List[str], total_duration_ms: int, image_duration_ms: int) -> List[str]:
        """
        根据音频时长和图片显示时长，随机选择并排列图片

        Args:
            all_images: 所有可用的图片路径
            total_duration_ms: 总时长（毫秒）
            image_duration_ms: 每张图片显示时长（毫秒）

        Returns:
            选中的图片路径列表（可能有重复）
        """
        if not all_images:
            return []

        # 计算需要多少张图片
        num_images_needed = total_duration_ms // image_duration_ms
        if total_duration_ms % image_duration_ms > 0:
            num_images_needed += 1

        selected_images = []

        # 如果图片数量不够，需要重复使用
        if len(all_images) >= num_images_needed:
            # 随机选择不重复的图片
            selected_images = random.sample(all_images, num_images_needed)
        else:
            # 需要重复使用图片
            # 先用完所有图片
            selected_images = all_images.copy()
            random.shuffle(selected_images)

            # 补充剩余的
            remaining = num_images_needed - len(all_images)
            for _ in range(remaining):
                selected_images.append(random.choice(all_images))

        return selected_images

    def generate_draft(
            self,
            images_dir: str,
            audio_path: str,
            image_duration_seconds: float,
            video_title: str,
            output_dir: str,
            enable_transitions: bool = True,
            enable_effects: bool = True,
            enable_keyframes: bool = True,  # 默认启用关键帧
            image_scale: float = 1.8,  # 图片缩放比例
            random_seed: Optional[int] = None
    ) -> str:
        """
        生成剪映草稿

        Args:
            images_dir: 图片目录路径
            audio_path: 音频文件路径
            image_duration_seconds: 每张图片显示时长（秒）
            video_title: 视频标题（用作草稿目录名）
            output_dir: 输出目录路径
            enable_transitions: 是否启用转场
            enable_effects: 是否启用特效
            enable_keyframes: 是否启用关键帧动画（默认启用）
            image_scale: 图片缩放比例（默认1.8）
            random_seed: 随机种子（用于复现结果）

        Returns:
            生成的草稿目录路径
        """

        # 设置随机种子
        if random_seed is not None:
            random.seed(random_seed)

        print(f"\n{'=' * 60}")
        print(f"开始生成剪映草稿")
        print(f"视频标题: {video_title}")
        print(f"{'=' * 60}\n")

        # 1. 验证输入
        if not os.path.exists(images_dir):
            raise ValueError(f"图片目录不存在: {images_dir}")
        if not os.path.exists(audio_path):
            raise ValueError(f"音频文件不存在: {audio_path}")

        # 2. 扫描图片
        print("扫描图片文件...")
        all_images = self.scan_images(images_dir)
        if not all_images:
            raise ValueError(f"目录中没有找到图片文件: {images_dir}")
        print(f"找到 {len(all_images)} 张图片")

        # 3. 获取音频时长
        print("\n分析音频文件...")
        audio_duration_ms = self.get_audio_duration_ms(audio_path)
        audio_duration_us = audio_duration_ms * 1000  # 转换为微秒
        print(f"音频时长: {audio_duration_ms / 1000:.2f} 秒")

        # 4. 计算图片配置
        image_duration_ms = int(image_duration_seconds * 1000)
        image_duration_us = image_duration_ms * 1000  # 转换为微秒

        # 5. 选择图片
        print(f"\n选择图片（每张显示 {image_duration_seconds} 秒）...")
        selected_images = self.select_random_images(all_images, audio_duration_ms, image_duration_ms)
        print(f"将使用 {len(selected_images)} 张图片")

        # 6. 创建输出目录
        draft_dir = os.path.join(output_dir, video_title)
        materials_dir = os.path.join(draft_dir, "materials")
        os.makedirs(materials_dir, exist_ok=True)
        print(f"\n创建输出目录: {draft_dir}")

        # 7. 复制素材文件
        print("\n复制素材文件...")

        # 复制音频
        audio_filename = f"audio_{os.path.basename(audio_path)}"
        audio_dest = os.path.join(materials_dir, audio_filename)
        shutil.copy(audio_path, audio_dest)
        audio_relative_path = f"##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##/materials/{audio_filename}"
        print(f"复制音频: {os.path.basename(audio_path)}")
        
        # 检查并复制字幕文件
        subtitle_service = get_subtitle_service()
        audio_dir = os.path.dirname(audio_path)
        audio_name = Path(audio_path).stem
        srt_path = os.path.join(audio_dir, f"{audio_name}.srt")
        srt_dest = None
        
        # 验证字幕文件是否存在
        srt_file_path = None
        if subtitle_service.validate_subtitle_file(audio_path):
            srt_filename = f"subtitle_{os.path.basename(srt_path)}"
            srt_dest = os.path.join(materials_dir, srt_filename)
            shutil.copy(srt_path, srt_dest)
            print(f"复制字幕: {os.path.basename(srt_path)}")
            # 保存原始srt路径用于后续处理
            srt_file_path = srt_path

        # 复制图片
        image_relative_paths = []
        for i, image_path in enumerate(selected_images):
            ext = os.path.splitext(image_path)[1]
            image_filename = f"image_{i:03d}{ext}"
            image_dest = os.path.join(materials_dir, image_filename)
            shutil.copy(image_path, image_dest)
            relative_path = f"##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##/materials/{image_filename}"
            image_relative_paths.append(relative_path)
            if i < 10:  # 只显示前10个
                print(f"复制图片 {i + 1}: {os.path.basename(image_path)}")
        if len(selected_images) > 10:
            print(f"... 和其他 {len(selected_images) - 10} 张图片")

        # 8. 创建草稿对象
        print("\n创建草稿对象...")
        draft = self._create_draft_object(
            audio_relative_path,
            image_relative_paths,
            audio_duration_us,
            image_duration_us,
            enable_transitions,
            enable_effects,
            enable_keyframes,
            image_scale,
            srt_file_path  # 传递原始字幕文件路径（可能为None）
        )

        # 9. 复制元信息文件
        print("\n复制元信息文件...")
        self._copy_meta_files(draft_dir)

        # 10. 保存草稿
        print("\n保存草稿文件...")
        self._save_draft(draft, draft_dir)

        # 11. 创建 ZIP 包
        print("\n创建 ZIP 包...")
        zip_path = self._create_zip_package(draft_dir)
        
        # 12. 不再在此处移动到本地剪映目录，由 pipeline_core.py 统一处理
        # 这样避免重复移动的问题
        logger.info("草稿生成完成，跳过本地目录移动（由pipeline处理）")
        final_path = draft_dir

        print(f"\n{'=' * 60}")
        safe_print(f"✅ 生成完成!")
        print(f"草稿目录: {draft_dir}")
        print(f"ZIP 包: {zip_path}")
        print(f"总时长: {audio_duration_ms / 1000:.2f} 秒")
        print(f"图片数量: {len(selected_images)}")
        if enable_transitions:
            print(f"包含转场: {len(selected_images) - 1} 个")
        if enable_effects:
            print(f"包含特效: 已添加随机特效")
        if enable_keyframes:
            print(f"包含关键帧: 已添加动画效果（缩放: {image_scale}x）")
        print(f"画布比例: 16:9 (1920x1080)")
        print(f"\n📌 草稿将由pipeline移动到本地剪映目录（如果配置）")
        print(f"{'=' * 60}\n")

        return final_path

    def _create_draft_object(
            self,
            audio_relative_path: str,
            image_relative_paths: List[str],
            audio_duration_us: int,
            image_duration_us: int,
            enable_transitions: bool,
            enable_effects: bool,
            enable_keyframes: bool = True,  # 默认启用
            image_scale: float = 1.8,  # 图片缩放比例
            srt_path: Optional[str] = None  # 字幕文件路径
    ) -> Draft:
        """创建草稿对象（内部方法）"""

        materials = Materials()
        draft_id = gen_upper_uuid()

        # 1. 创建音频素材
        audio_material = AudioMaterial(
            id=gen_upper_uuid(),
            path=audio_relative_path,
            duration=audio_duration_us,
            material_name="背景音乐"
        )
        materials.audios = [audio_material.to_dict()]

        # 2. 创建视频素材（图片）
        video_materials = []
        for i, image_path in enumerate(image_relative_paths):
            video_material = VideoMaterial(
                id=gen_upper_uuid(),
                path=image_path,
                duration=image_duration_us,
                width=1920,
                height=1080,
                material_name=f"图片{i + 1}"
            )
            video_materials.append(video_material)
            materials.videos.append(video_material.to_dict())

        # 3. 创建转场（如果启用）
        transitions = []
        if enable_transitions and len(video_materials) > 1:
            for i in range(len(video_materials) - 1):
                # 随机选择一个转场
                transition_info = random.choice(self.available_transitions)
                transition = Transition(
                    id=gen_upper_uuid(),
                    effect_id=transition_info.effect_id,
                    name=transition_info.name,
                    duration=466666,  # 约0.47秒
                    is_overlap=transition_info.is_overlap,
                    category_id=transition_info.category_id,
                    category_name=transition_info.category_name,
                    path=transition_info.get_path(),
                    resource_id=transition_info.resource_id
                )
                transitions.append(transition)
                materials.transitions.append(transition.to_dict())

        # 4. 创建特效（如果启用）
        video_effect = None
        if enable_effects:
            # 随机选择一个特效
            effect_info = random.choice(self.available_effects)
            video_effect = VideoEffect(
                id=gen_upper_uuid(),
                effect_id=effect_info.effect_id,
                name=effect_info.name,
                category_id=effect_info.category_id,
                category_name=effect_info.category_name,
                path=effect_info.get_path(),
                resource_id=effect_info.resource_id,
                adjust_params=effect_info.adjust_params,
                value=effect_info.default_value,
                render_index=0,
                track_render_index=0
            )
            materials.video_effects.append(video_effect.to_dict())

        # 5. 创建辅助素材
        for i in range(len(video_materials)):
            materials.speeds.append(SpeedInfo.create_speed_dict())
            materials.canvases.append(CanvasInfo.create_canvas_dict())
            materials.sound_channel_mappings.append({
                "id": gen_upper_uuid(),
                "audio_channel_mapping": 0,
                "is_config_open": False,
                "type": ""
            })
            materials.vocal_separations.append({
                "id": gen_upper_uuid(),
                "choice": 0,
                "production_path": "",
                "time_range": None,
                "type": "vocal_separation"
            })

        # 添加素材动画
        for _ in range(len(transitions)):
            materials.material_animations.append(MaterialAnimationInfo.create_animation_dict())

        # 6. 创建视频轨道
        video_track = Track(
            id=gen_upper_uuid(),
            type="video",
            segments=[],
            attribute=1
        )

        # 创建视频片段
        current_time = 0
        for i, video_material in enumerate(video_materials):
            # 确保不超过音频时长
            if current_time >= audio_duration_us:
                break

            # 计算片段时长
            segment_duration = min(image_duration_us, audio_duration_us - current_time)

            # 创建额外引用
            extra_refs = []
            if i < len(materials.speeds):
                extra_refs.append(materials.speeds[i]["id"])
            if enable_transitions and i < len(transitions):
                extra_refs.append(transitions[i].id)
            if i < len(materials.canvases):
                extra_refs.append(materials.canvases[i]["id"])
            if i < len(materials.material_animations):
                extra_refs.append(materials.material_animations[i]["id"])
            if i < len(materials.sound_channel_mappings):
                extra_refs.append(materials.sound_channel_mappings[i]["id"])
            if i < len(materials.vocal_separations):
                extra_refs.append(materials.vocal_separations[i]["id"])

            # 创建片段
            video_segment = Segment(
                id=gen_upper_uuid(),
                material_id=video_material.id,
                target=Timerange(start=current_time, duration=segment_duration),
                source=Timerange(start=0, duration=segment_duration),
                speed=1.0,
                volume=0.0,
                clip=Clip(
                    alpha=1.0,
                    rotation=0.0,
                    scale={"x": image_scale if enable_keyframes else 1.0, "y": image_scale if enable_keyframes else 1.0},
                    transform={"x": 0.0, "y": 0.8 if enable_keyframes and i % 2 == 0 else -0.8 if enable_keyframes and i % 2 == 1 else 0.0}
                ),
                extra_refs=extra_refs
            )
            
            # 如果启用关键帧，添加动画
            if enable_keyframes:
                video_segment.common_keyframes = self.create_keyframes_for_segment(segment_duration, i, image_scale)
            video_track.segments.append(video_segment)
            current_time += segment_duration

        # 7. 创建音频轨道
        audio_track = Track(
            id=gen_upper_uuid(),
            type="audio",
            segments=[],
            attribute=0
        )

        audio_segment = Segment(
            id=gen_upper_uuid(),
            material_id=audio_material.id,
            target=Timerange(start=0, duration=audio_duration_us),
            source=Timerange(start=0, duration=audio_duration_us),
            speed=1.0,
            volume=1.0,
            clip=None,
            extra_refs=[
                materials.speeds[0]["id"] if materials.speeds else gen_upper_uuid(),
                materials.sound_channel_mappings[0]["id"] if materials.sound_channel_mappings else gen_upper_uuid(),
                materials.vocal_separations[0]["id"] if materials.vocal_separations else gen_upper_uuid()
            ]
        )
        audio_track.segments.append(audio_segment)

        # 8. 创建特效轨道（如果启用）
        tracks = [video_track, audio_track]
        if enable_effects and video_effect:
            effect_track = Track(
                id=gen_upper_uuid(),
                type="effect",
                segments=[],
                attribute=0
            )

            effect_segment = Segment(
                id=gen_upper_uuid(),
                material_id=video_effect.id,
                target=Timerange(start=0, duration=audio_duration_us),
                source=Timerange(start=0, duration=0),
                speed=1.0,
                volume=1.0,
                clip=None
            )
            effect_track.segments.append(effect_segment)
            tracks.append(effect_track)

        # 9. 处理字幕（如果提供了SRT文件）
        if srt_path and os.path.exists(srt_path):
            print("添加字幕轨道...")
            subtitle_service = get_subtitle_service()
            
            # 创建字幕材料
            subtitle_materials = subtitle_service.create_subtitle_materials(srt_path)
            
            # 添加字幕材料到materials
            materials.texts = subtitle_materials['text_materials']
            materials.material_animations.extend(subtitle_materials['animation_materials'])
            
            # 创建字幕轨道（转换为Track对象）
            subtitle_track_dict = subtitle_service.create_subtitle_track(subtitle_materials['text_segments'])
            
            # 转换segments为Segment对象
            subtitle_segments = []
            for seg_dict in subtitle_track_dict['segments']:
                # 处理source_timerange，如果为None则使用默认值
                source_timerange = seg_dict.get('source_timerange')
                if source_timerange is None:
                    source = Timerange(start=0, duration=0)
                else:
                    source = Timerange(
                        start=source_timerange.get('start', 0),
                        duration=source_timerange.get('duration', 0)
                    )
                
                # 处理clip
                clip_data = seg_dict.get('clip')
                if clip_data and isinstance(clip_data, dict):
                    clip = Clip(
                        alpha=clip_data.get('alpha', 1.0),
                        rotation=clip_data.get('rotation', 0.0),
                        scale=clip_data.get('scale', {"x": 1.0, "y": 1.0}),
                        transform=clip_data.get('transform', {"x": 0.0, "y": 0.0}),
                        flip=clip_data.get('flip', {"horizontal": False, "vertical": False})
                    )
                else:
                    clip = None
                
                segment = Segment(
                    id=seg_dict['id'],
                    material_id=seg_dict['material_id'],
                    target=Timerange(
                        start=seg_dict['target_timerange']['start'],
                        duration=seg_dict['target_timerange']['duration']
                    ),
                    source=source,
                    speed=seg_dict.get('speed', 1.0),
                    volume=seg_dict.get('volume', 1.0),
                    clip=clip
                )
                # 添加其他必要的字段
                segment.render_index = seg_dict.get('render_index', 14000)
                segment.track_render_index = seg_dict.get('track_render_index', 2)
                segment.track_attribute = seg_dict.get('track_attribute', 0)
                segment.visible = seg_dict.get('visible', True)
                segment.extra_material_refs = seg_dict.get('extra_material_refs', [])
                subtitle_segments.append(segment)
            
            subtitle_track = Track(
                id=subtitle_track_dict['id'],
                type=subtitle_track_dict['type'],
                segments=subtitle_segments,
                attribute=subtitle_track_dict.get('attribute', 0)
            )
            tracks.append(subtitle_track)
            
            print(f"  添加了 {subtitle_materials['subtitle_count']} 条字幕")
        
        # 10. 创建草稿
        draft = Draft(
            id=draft_id,
            duration=audio_duration_us,
            canvas_config={
                "height": 1080,
                "width": 1920,
                "ratio": "16:9"
            },
            materials=materials,
            tracks=tracks
        )

        return draft

    def _copy_meta_files(self, draft_dir: str):
        """复制元信息文件（内部方法）"""
        # 获取配置文件所在目录（与当前脚本同目录）
        config_dir = os.path.dirname(__file__)
        
        # 复制 draft_meta_info.json
        meta_info_src = os.path.join(config_dir, "draft_meta_info.json")
        meta_info_dst = os.path.join(draft_dir, "draft_meta_info.json")
        if os.path.exists(meta_info_src):
            shutil.copy(meta_info_src, meta_info_dst)
            print("复制元信息: draft_meta_info.json")
        else:
            print(f"警告：找不到元信息文件: {meta_info_src}")
            # 如果找不到文件，创建一个基础的
            meta_info = {
                "draft_materials": [],
                "draft_id": gen_upper_uuid(),
                "draft_name": os.path.basename(draft_dir)
            }
            with open(meta_info_dst, 'w', encoding='utf-8') as f:
                json.dump(meta_info, f, indent=4, ensure_ascii=False)
            print("创建基础元信息: draft_meta_info.json")

        # 复制 draft_settings
        settings_src = os.path.join(config_dir, "draft_settings")
        settings_dst = os.path.join(draft_dir, "draft_settings")
        if os.path.exists(settings_src):
            shutil.copy(settings_src, settings_dst)
            print("复制设置文件: draft_settings")
        else:
            print(f"警告：找不到设置文件: {settings_src}")
            # 如果找不到文件，创建一个基础的
            settings_content = "[General]\n"
            with open(settings_dst, 'w', encoding='utf-8') as f:
                f.write(settings_content)
            print("创建基础设置文件: draft_settings")

    def _move_to_local_dir(self, draft_dir: str, video_title: str) -> Optional[str]:
        """
        移动草稿到本地剪映目录
        
        Args:
            draft_dir: 生成的草稿目录路径
            video_title: 视频标题（用作目标文件夹名）
        
        Returns:
            移动后的目标路径，如果跳过则返回 None
        """
        # 读取环境变量
        local_dir = os.environ.get('DRAFT_LOCAL_DIR', '').strip()
        
        # 如果是 test 或未设置，跳过移动
        if not local_dir or local_dir.lower() == 'test':
            logger.debug(f"DRAFT_LOCAL_DIR 未设置或为 test，跳过移动")
            return None
        
        # 验证目标目录
        if not os.path.exists(local_dir):
            logger.warning(f"本地目录不存在，跳过移动: {local_dir}")
            return None
        
        # 构建目标路径
        target_path = os.path.join(local_dir, video_title)
        
        try:
            # 如果目标已存在，先删除
            if os.path.exists(target_path):
                logger.info(f"删除已存在的目录: {target_path}")
                shutil.rmtree(target_path)
            
            # 移动整个文件夹
            shutil.move(draft_dir, target_path)
            logger.info(f"成功移动到本地剪映目录: {target_path}")
            
            return target_path
        except Exception as e:
            logger.error(f"移动到本地目录失败: {str(e)}")
            return None
    
    def _create_zip_package(self, draft_dir: str) -> str:
        """创建 ZIP 包（内部方法）"""
        zip_path = f"{draft_dir}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 遍历草稿目录中的所有文件
            for root, dirs, files in os.walk(draft_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 计算在 ZIP 中的相对路径，不包含顶层目录名
                    arcname = os.path.relpath(file_path, draft_dir)
                    zipf.write(file_path, arcname)
                    
        # 获取 ZIP 文件大小
        zip_size = os.path.getsize(zip_path) / (1024 * 1024)  # 转换为 MB
        print(f"ZIP 包创建完成: {os.path.basename(zip_path)} ({zip_size:.2f} MB)")
        
        return zip_path

    def _save_draft(self, draft: Draft, draft_dir: str):
        """保存草稿（内部方法）"""
        draft_content_path = os.path.join(draft_dir, "draft_content.json")
        draft_dict = draft.to_dict()

        # 确保所有轨道的segment有正确的字段
        for track in draft_dict.get("tracks", []):
            for segment in track.get("segments", []):
                if track["type"] == "video":
                    segment.update({
                        "enable_adjust": True,
                        "enable_color_correct_adjust": False,
                        "enable_color_curves": True,
                        "enable_color_match_adjust": False,
                        "enable_color_wheels": True,
                        "enable_lut": True,
                        "enable_smart_color_adjust": False,
                        "caption_info": None,
                        "cartoon": False,
                        "group_id": "",
                        "hdr_settings": None,
                        "intensifies_audio": False,
                        "is_tone_modify": False,
                        "last_nonzero_volume": 1.0,
                        "render_index": 0,
                        "responsive_layout": {
                            "enable": False,
                            "horizontal_pos_layout": 0,
                            "size_layout": 0,
                            "target_follow": "",
                            "vertical_pos_layout": 0
                        },
                        "track_render_index": 0,
                        "uniform_scale": {
                            "on": True,
                            "value": 1.0
                        }
                    })
                elif track["type"] == "audio":
                    if "clip" not in segment:
                        segment["clip"] = None
                    segment.update({
                        "enable_adjust": False,
                        "enable_color_correct_adjust": False,
                        "enable_color_curves": True,
                        "enable_color_match_adjust": False,
                        "enable_color_wheels": True,
                        "enable_lut": False,
                        "enable_smart_color_adjust": False,
                        "caption_info": None,
                        "cartoon": False,
                        "group_id": "",
                        "hdr_settings": None,
                        "intensifies_audio": False,
                        "is_tone_modify": False,
                        "last_nonzero_volume": 1.0,
                        "render_index": 0,
                        "responsive_layout": {
                            "enable": False,
                            "horizontal_pos_layout": 0,
                            "size_layout": 0,
                            "target_follow": "",
                            "vertical_pos_layout": 0
                        },
                        "track_render_index": 0,
                        "uniform_scale": None
                    })
                elif track["type"] == "effect":
                    segment["source_timerange"] = None
                    segment.update({
                        "render_index": 11000,
                        "track_render_index": 1,
                        "caption_info": None,
                        "cartoon": False,
                        "enable_adjust": False,
                        "enable_color_correct_adjust": False,
                        "enable_color_curves": True,
                        "enable_color_match_adjust": False,
                        "enable_color_wheels": True,
                        "enable_lut": False,
                        "enable_smart_color_adjust": False,
                        "group_id": "",
                        "hdr_settings": None,
                        "intensifies_audio": False,
                        "is_tone_modify": False,
                        "last_nonzero_volume": 1.0,
                        "responsive_layout": {
                            "enable": False,
                            "horizontal_pos_layout": 0,
                            "size_layout": 0,
                            "target_follow": "",
                            "vertical_pos_layout": 0
                        },
                        "uniform_scale": None
                    })

        with open(draft_content_path, 'w', encoding='utf-8') as f:
            json.dump(draft_dict, f, indent=4, ensure_ascii=False)
        print("保存草稿: draft_content.json")


def generate_draft_from_story(cid: str, vid: str, 
                             image_duration_seconds: float = 3.0,
                             enable_transitions: bool = True,
                             enable_effects: bool = True,
                             enable_keyframes: bool = True,  # 默认启用
                             image_scale: float = 1.8,  # 图片缩放比例
                             random_seed: Optional[int] = 42):
    """
    根据故事ID生成剪映草稿
    
    Args:
        cid: Creator ID
        vid: Voice ID
        image_duration_seconds: 每张图片显示时长（秒）
        enable_transitions: 是否启用转场
        enable_effects: 是否启用特效
        enable_keyframes: 是否启用关键帧动画（默认启用）
        image_scale: 图片缩放比例（默认1.8）
        random_seed: 随机种子
    
    Returns:
        生成的草稿目录路径
    """
    
    # 构建路径
    audio_path = f"./output/{cid}_{vid}_story.mp3"
    images_dir = "./output/images"
    video_title = f"{cid}_{vid}_story"
    output_dir = "./output/drafts"
    
    # 验证文件存在
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")
    
    if not os.path.exists(images_dir):
        raise FileNotFoundError(f"图片目录不存在: {images_dir}")
    
    # 创建服务实例
    service = DraftGeneratorService()
    
    try:
        # 生成草稿
        draft_dir = service.generate_draft(
            images_dir=images_dir,
            audio_path=audio_path,
            image_duration_seconds=image_duration_seconds,
            video_title=video_title,
            output_dir=output_dir,
            enable_transitions=enable_transitions,
            enable_effects=enable_effects,
            enable_keyframes=enable_keyframes,
            image_scale=image_scale,
            random_seed=random_seed
        )
        
        return draft_dir
        
    except Exception as e:
        safe_print(f"\n❌ 生成失败: {str(e)}")
        raise


def main():
    """命令行入口"""
    
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='生成剪映草稿')
    parser.add_argument('--cid', type=str, required=True, help='Creator ID')
    parser.add_argument('--vid', type=str, required=True, help='Voice ID')
    parser.add_argument('--duration', type=float, default=3.0, 
                       help='每张图片显示时长（秒），默认3秒')
    parser.add_argument('--no-transitions', action='store_true',
                       help='禁用转场效果')
    parser.add_argument('--no-effects', action='store_true',
                       help='禁用视频特效')
    parser.add_argument('--no-keyframes', action='store_true',
                       help='禁用关键帧动画（默认启用）')
    parser.add_argument('--scale', type=float, default=1.8,
                       help='图片缩放比例，默认1.8')
    parser.add_argument('--seed', type=int, default=42,
                       help='随机种子，用于复现结果')
    
    # 解析参数
    args = parser.parse_args()
    
    print(f"\n{'=' * 60}")
    print(f"剪映草稿生成工具")
    print(f"{'=' * 60}")
    print(f"Creator ID: {args.cid}")
    print(f"Voice ID: {args.vid}")
    print(f"图片显示时长: {args.duration} 秒")
    print(f"转场效果: {'启用' if not args.no_transitions else '禁用'}")
    print(f"视频特效: {'启用' if not args.no_effects else '禁用'}")
    print(f"关键帧动画: {'启用' if not args.no_keyframes else '禁用'}")
    print(f"图片缩放比例: {args.scale}x")
    print(f"{'=' * 60}\n")
    
    try:
        # 生成草稿
        draft_dir = generate_draft_from_story(
            cid=args.cid,
            vid=args.vid,
            image_duration_seconds=args.duration,
            enable_transitions=not args.no_transitions,
            enable_effects=not args.no_effects,
            enable_keyframes=not args.no_keyframes,  # 注意：使用 not args.no_keyframes
            image_scale=args.scale,
            random_seed=args.seed
        )
        
        print(f"\n✨ 草稿已生成到: {draft_dir}")
        print("\n下一步操作：")
        print("1. 打开剪映专业版")
        print("2. 选择'导入草稿'")
        print("3. 选择生成的草稿文件夹")
        print("4. 开始编辑你的视频！")
        
    except FileNotFoundError as e:
        safe_print(f"\n❌ 文件未找到: {str(e)}")
        print("\n请确保已经完成以下步骤：")
        print("1. 生成故事音频: python voice_gen/tts_client.py --cid <cid> --vid <vid> --gender <0|1>")
        print("2. 生成图片: python image_generator.py")
        
    except Exception as e:
        safe_print(f"\n❌ 生成失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()