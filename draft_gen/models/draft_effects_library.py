"""
剪映特效和转场库
包含预定义的特效和转场信息，这些信息对应剪映服务端资源
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from enum import Enum


@dataclass
class TransitionInfo:
    """转场信息"""
    effect_id: str
    name: str
    resource_id: str
    category_id: str = "39663"
    category_name: str = "热门"
    is_overlap: bool = True
    default_duration: int = 466666  # 默认转场时长（微秒）
    path_template: str = "C:/Users/Administrator/AppData/Local/JianyingPro/User Data/Cache/effect/{effect_id}/{hash}"
    
    def get_path(self, hash_value: str = "") -> str:
        """获取转场文件路径"""
        if not hash_value:
            # 使用默认的hash值
            if self.effect_id == "26135688":
                hash_value = "94815943a86e741a5fec1737fbb46d60"
            elif self.effect_id == "359527":
                hash_value = "55af58a9b04ff458c3a9ae3ddb358152"
            else:
                hash_value = "default_hash"
        return self.path_template.format(effect_id=self.effect_id, hash=hash_value)


@dataclass
class VideoEffectInfo:
    """视频特效信息"""
    effect_id: str
    name: str
    resource_id: str
    category_id: str = "heycan_search_special_effect"
    category_name: str = "heycan_search_special_effect"
    default_value: float = 1.0
    adjust_params: List[Dict[str, Any]] = None
    path_template: str = "C:/Users/Administrator/AppData/Local/JianyingPro/User Data/Cache/effect/{effect_id}/{hash}"
    
    def __post_init__(self):
        if self.adjust_params is None:
            self.adjust_params = []
    
    def get_path(self, hash_value: str = "") -> str:
        """获取特效文件路径"""
        if not hash_value:
            # 使用默认的hash值
            if self.effect_id == "1441796":
                hash_value = "aa711f9666bdc3e51ff72de0d7c073a8"
            else:
                hash_value = "default_hash"
        return self.path_template.format(effect_id=self.effect_id, hash=hash_value)


class Transitions:
    """预定义转场库"""
    
    # 推近 II - 重叠转场
    PUSH_IN_II = TransitionInfo(
        effect_id="26135688",
        name="推近 II",
        resource_id="7290852476259930685",
        is_overlap=True
    )
    
    # 向右 - 非重叠转场
    SLIDE_RIGHT = TransitionInfo(
        effect_id="359527",
        name="向右",
        resource_id="6724227599616184836",
        is_overlap=False
    )

    
    @classmethod
    def get_all(cls) -> List[TransitionInfo]:
        """获取所有转场"""
        return [
            cls.PUSH_IN_II,
            cls.SLIDE_RIGHT
        ]
    
    @classmethod
    def get_by_name(cls, name: str) -> TransitionInfo:
        """根据名称获取转场"""
        for transition in cls.get_all():
            if transition.name == name:
                return transition
        raise ValueError(f"未找到名为 '{name}' 的转场")


class VideoEffects:
    """预定义视频特效库"""
    
    # 雪花特效
    SNOW = VideoEffectInfo(
        effect_id="1441796",
        name="雪花",
        resource_id="7030728702258319909",
        adjust_params=[
            {
                "name": "effects_adjust_background_animation",
                "default_value": 1.0,
                "value": 0.36
            },
            {
                "name": "effects_adjust_speed",
                "default_value": 0.3361999988555908,
                "value": 0.3361999988555908
            }
        ]
    )
    

    

    
    @classmethod
    def get_all(cls) -> List[VideoEffectInfo]:
        """获取所有特效"""
        return [
            cls.SNOW
        ]
    
    @classmethod
    def get_by_name(cls, name: str) -> VideoEffectInfo:
        """根据名称获取特效"""
        for effect in cls.get_all():
            if effect.name == name:
                return effect
        raise ValueError(f"未找到名为 '{name}' 的特效")


class SpeedInfo:
    """速度调节信息"""
    
    @staticmethod
    def create_speed_dict(speed: float = 1.0, mode: int = 0) -> Dict[str, Any]:
        """
        创建速度调节字典
        
        Args:
            speed: 速度值 (0.1-10.0, 1.0为正常速度)
            mode: 速度模式 (0=常规)
        """
        import uuid
        return {
            "id": str(uuid.uuid4()).upper().replace('-', ''),
            "type": "speed",
            "mode": mode,
            "speed": speed,
            "curve_speed": None
        }


class CanvasInfo:
    """画布信息"""
    
    @staticmethod
    def create_canvas_dict(canvas_type: str = "canvas_color") -> Dict[str, Any]:
        """
        创建画布字典
        
        Args:
            canvas_type: 画布类型 (canvas_color=纯色)
        """
        import uuid
        return {
            "id": str(uuid.uuid4()).upper().replace('-', ''),
            "type": canvas_type,
            "album_image": "",
            "blur": 0.0,
            "color": "",
            "image": "",
            "image_id": "",
            "image_name": "",
            "source_platform": 0,
            "team_id": ""
        }


class MaterialAnimationInfo:
    """素材动画信息"""
    
    @staticmethod
    def create_animation_dict(animation_type: str = "sticker_animation") -> Dict[str, Any]:
        """
        创建素材动画字典
        
        Args:
            animation_type: 动画类型 (sticker_animation=贴纸动画)
        """
        import uuid
        return {
            "id": str(uuid.uuid4()).upper().replace('-', ''),
            "type": animation_type,
            "animations": [],
            "multi_language_current": "none"
        }