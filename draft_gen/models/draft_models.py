from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Timerange:
    start: int = 0
    duration: int = 0
    def to_dict(self) -> Dict[str, int]:
        return {"start": self.start, "duration": self.duration}


@dataclass
class Clip:
    alpha: float = 1.0
    rotation: float = 0.0
    scale: Dict[str, float] = field(default_factory=lambda: {"x": 1.0, "y": 1.0})
    transform: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    flip: Dict[str, bool] = field(default_factory=lambda: {"horizontal": False, "vertical": False})
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha": self.alpha,
            "rotation": self.rotation,
            "scale": self.scale,
            "transform": self.transform,
            "flip": self.flip,
        }


@dataclass
class Keyframe:
    """关键帧数据"""
    id: str
    time_offset: int  # 时间偏移（微秒）
    values: List[float]  # 属性值
    curveType: str = "Line"  # 曲线类型
    graphID: str = ""
    left_control: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    right_control: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "time_offset": self.time_offset,
            "values": self.values,
            "curveType": self.curveType,
            "graphID": self.graphID,
            "left_control": self.left_control,
            "right_control": self.right_control
        }


@dataclass
class CommonKeyframe:
    """通用关键帧容器"""
    id: str
    property_type: str  # KFTypePositionX, KFTypePositionY, KFTypeScaleX, KFTypeRotation等
    keyframe_list: List[Keyframe]
    material_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "property_type": self.property_type,
            "keyframe_list": [kf.to_dict() for kf in self.keyframe_list],
            "material_id": self.material_id
        }


@dataclass
class Segment:
    id: str
    material_id: str
    target: Timerange
    source: Timerange
    speed: float = 1.0
    volume: float = 1.0
    clip: Optional[Clip] = None  # 允许为None，音频segment不需要clip
    extra_refs: List[str] = field(default_factory=list)
    common_keyframes: List[CommonKeyframe] = field(default_factory=list)  # 添加关键帧支持
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "material_id": self.material_id,
            "target_timerange": self.target.to_dict(),
            "source_timerange": self.source.to_dict(),
            "speed": self.speed,
            "volume": self.volume,
            "clip": self.clip.to_dict() if self.clip else None,
            "extra_material_refs": list(self.extra_refs),
            "reverse": False,
            "template_id": "",
            "template_scene": "default",
            "common_keyframes": [kf.to_dict() for kf in self.common_keyframes],
            "keyframe_refs": [],
            "visible": True,
            "is_placeholder": False,
            "track_attribute": 0,
        }


@dataclass
class Track:
    id: str
    type: str  # "video" | "audio" | "text" | "effect"
    segments: List[Segment] = field(default_factory=list)
    render_index: int = 0
    attribute: int = 0
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "segments": [s.to_dict() for s in self.segments],
            "name": "",
            "is_default_name": True,
            "flag": 0,
            "attribute": self.attribute,
            "track_render_index": self.render_index,
        }


@dataclass
class VideoMaterial:
    id: str
    path: str
    duration: int
    width: int = 1080
    height: int = 1920
    material_name: str = ""
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": "video",
            "path": self.path,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "has_audio": True,
            "crop_ratio": "free",
            "crop_scale": 1.0,
            "material_name": self.material_name,
        }


@dataclass
class AudioMaterial:
    id: str
    path: str
    duration: int
    material_name: str = ""
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": "music",
            "path": self.path,
            "duration": self.duration,
            "name": self.material_name,
        }


@dataclass
class Transition:
    """转场效果"""
    id: str
    effect_id: str
    name: str
    duration: int  # 微秒
    is_overlap: bool = True  # 是否重叠
    category_id: str = ""
    category_name: str = ""
    path: str = ""
    resource_id: str = ""
    platform: str = "all"
    request_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "effect_id": self.effect_id,
            "name": self.name,
            "duration": self.duration,
            "is_overlap": self.is_overlap,
            "category_id": self.category_id,
            "category_name": self.category_name,
            "path": self.path,
            "platform": self.platform,
            "request_id": self.request_id,
            "resource_id": self.resource_id,
            "type": "transition"
        }


@dataclass
class VideoEffect:
    """视频特效"""
    id: str
    effect_id: str
    name: str
    category_id: str = ""
    category_name: str = ""
    path: str = ""
    resource_id: str = ""
    adjust_params: List[Dict[str, Any]] = field(default_factory=list)
    value: float = 1.0
    render_index: int = 0
    track_render_index: int = 0
    apply_target_type: int = 2
    platform: str = "all"
    request_id: str = ""
    source_platform: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "effect_id": self.effect_id,
            "name": self.name,
            "category_id": self.category_id,
            "category_name": self.category_name,
            "path": self.path,
            "platform": self.platform,
            "request_id": self.request_id,
            "resource_id": self.resource_id,
            "type": "video_effect",
            "adjust_params": self.adjust_params,
            "value": self.value,
            "render_index": self.render_index,
            "track_render_index": self.track_render_index,
            "apply_target_type": self.apply_target_type,
            "apply_time_range": None,
            "algorithm_artifact_path": "",
            "common_keyframes": [],
            "disable_effect_faces": [],
            "formula_id": "",
            "source_platform": self.source_platform,
            "time_range": None,
            "version": ""
        }


@dataclass
class TextMaterial:
    id: str
    font_path: str
    content: Dict[str, Any]
    def to_dict(self) -> Dict[str, Any]:
        import json
        return {
            "id": self.id,
            "type": "text",
            "font_path": self.font_path,
            "content": json.dumps(self.content, ensure_ascii=False),
        }


@dataclass
class DraftContainer:
    id: str
    combination_id: str
    draft: Dict[str, Any]
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": "combination",
            "formula_id": "",
            "name": "",
            "precompile_combination": False,
            "combination_id": self.combination_id,
            "draft": self.draft,
        }


@dataclass
class Materials:
    videos: List[Dict[str, Any]] = field(default_factory=list)
    audios: List[Dict[str, Any]] = field(default_factory=list)
    texts: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)  # 添加images字段
    canvases: List[Dict[str, Any]] = field(default_factory=list)
    transitions: List[Dict[str, Any]] = field(default_factory=list)
    video_effects: List[Dict[str, Any]] = field(default_factory=list)  # 添加视频特效
    speeds: List[Dict[str, Any]] = field(default_factory=list)
    material_animations: List[Dict[str, Any]] = field(default_factory=list)
    drafts: List[Dict[str, Any]] = field(default_factory=list)
    sound_channel_mappings: List[Dict[str, Any]] = field(default_factory=list)
    vocal_separations: List[Dict[str, Any]] = field(default_factory=list)
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ai_translates": [],
            "audio_balances": [],
            "audio_effects": [],
            "audio_fades": [],
            "audio_track_indexes": [],
            "audios": self.audios,
            "beats": [],
            "canvases": self.canvases,
            "chromas": [],
            "color_curves": [],
            "digital_humans": [],
            "drafts": self.drafts,
            "effects": [],
            "flowers": [],
            "green_screens": [],
            "handwrites": [],
            "hsl": [],
            "images": self.images,  # 使用实际的images列表
            "log_color_wheels": [],
            "loudnesses": [],
            "manual_deformations": [],
            "masks": [],
            "material_animations": self.material_animations,
            "material_colors": [],
            "multi_language_refs": [],
            "placeholders": [],
            "plugin_effects": [],
            "primary_color_wheels": [],
            "realtime_denoises": [],
            "shapes": [],
            "smart_crops": [],
            "smart_relights": [],
            "sound_channel_mappings": self.sound_channel_mappings,
            "speeds": self.speeds,
            "stickers": [],
            "tail_leaders": [],
            "text_templates": [],
            "texts": self.texts,
            "time_marks": [],
            "transitions": self.transitions,
            "video_effects": self.video_effects,
            "video_trackings": [],
            "videos": self.videos,
            "vocal_beautifys": [],
            "vocal_separations": self.vocal_separations,
        }


@dataclass
class Draft:
    id: str
    duration: int = 0
    fps: float = 30.0
    canvas_config: Dict[str, Any] = field(default_factory=lambda: {"height": 1080, "width": 1920, "ratio": "original"})
    config: Dict[str, Any] = field(default_factory=lambda: {"video_mute": True})
    materials: Materials = field(default_factory=Materials)
    tracks: List[Track] = field(default_factory=list)
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "duration": self.duration,
            "fps": self.fps,
            "canvas_config": self.canvas_config,
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
                "video_mute": self.config.get("video_mute", True),
                "zoom_info_params": None,
            },
            "cover": None,
            "create_time": 0,
            "extra_info": None,
            "free_render_index_mode_on": False,
            "group_container": None,
            "keyframe_graph_list": [],
            "keyframes": {k: [] for k in ["adjusts", "audios", "effects", "filters", "handwrites", "stickers", "texts", "videos"]},
            "last_modified_platform": {
                "app_id": 3704,
                "app_source": "lv",
                "app_version": "5.9.0",
                "device_id": "",
                "hard_disk_id": "",
                "mac_address": "",
                "os": "windows",
                "os_version": "10.0.20348",
            },
            "materials": self.materials.to_dict(),
            "mutable_config": None,
            "name": "",
            "new_version": "110.0.0",
            "platform": {
                "app_id": 3704,
                "app_source": "lv",
                "app_version": "5.9.0",
                "device_id": "",
                "hard_disk_id": "",
                "mac_address": "",
                "os": "windows",
                "os_version": "10.0.20348",
            },
            "relationships": [],
            "render_index_track_mode_on": True,
            "retouch_cover": None,
            "source": "default",
            "static_cover_image_path": "",
            "time_marks": None,
            "tracks": [t.to_dict() for t in self.tracks],
            "update_time": 0,
            "version": 360000,
        } 