#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
独立的图片提示词生成模块
可以独立运行，不依赖完整的故事生成流程
"""

import os
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)

# Debug logger for AI conversations
debug_logger = logging.getLogger('debug_ai_conversation')
debug_logger.setLevel(logging.DEBUG)

class ImagePromptGenerator:
    """图片提示词生成器"""
    
    def __init__(self, 
                 creator_name: str,
                 video_id: str,
                 scene_extractor_prompt: str = "prompts/scene_extractor.md",
                 sd_generator_prompt: str = "prompts/sd_prompt_generator.md",
                 jimeng_generator_prompt: str = "prompts/jimeng_prompt_generator.md",
                 sd_prompt_file: str = "prompts/sd_image_generator_v2.md",
                 images_per_segment: int = 1,
                 generator_type: str = "sd",
                 art_style: Optional[str] = None):
        """
        初始化图片提示词生成器
        
        Args:
            creator_name: 创作者名称
            video_id: 视频ID
            scene_extractor_prompt: 场景提取提示词文件路径
            sd_generator_prompt: SD提示词生成提示词文件路径
            jimeng_generator_prompt: 即梦提示词生成文件路径
            sd_prompt_file: SD提示词优化的prompt文件路径
            images_per_segment: 每个片段生成的图片数量
            generator_type: 生成器类型 'sd' 或 'jimeng'
            art_style: 统一的艺术风格，可选值：
                - 超写实风格、写实摄影风格
                - 梦幻唯美风格、童话风格
                - 赛博朋克风格、蒸汽朋克风格
                - 中国水墨画风格、工笔画风格
                - 油画风格、水彩画风格
                - 动漫风格、二次元风格
                - 极简主义风格、现代艺术风格
                - 复古怀旧风格、老照片风格
                - 暗黑哥特风格、末世废土风格
        """
        self.creator_name = creator_name
        self.video_id = video_id
        self.images_per_segment = images_per_segment
        self.generator_type = generator_type
        self.art_style = art_style
        self.character_visual_map = {}  # 人物姓名到视觉特征的映射
        
        # 设置debug日志
        self._setup_debug_logging(creator_name, video_id)
        
        # 自动构建路径
        self.base_dir = Path("story_result") / creator_name / video_id
        self.segments_dir = self.base_dir / "segments"
        self.processing_dir = self.base_dir / "processing"
        self.final_dir = self.base_dir / "final"
        
        # 提示词模板文件
        project_root = Path(__file__).parent
        
        # 场景提取提示词
        self.scene_extractor_prompt = Path(scene_extractor_prompt)
        if not self.scene_extractor_prompt.exists():
            self.scene_extractor_prompt = project_root / scene_extractor_prompt
        
        # SD生成提示词
        self.sd_generator_prompt = Path(sd_generator_prompt)
        if not self.sd_generator_prompt.exists():
            self.sd_generator_prompt = project_root / sd_generator_prompt
        
        # 即梦生成提示词
        self.jimeng_generator_prompt = Path(jimeng_generator_prompt)
        if not self.jimeng_generator_prompt.exists():
            self.jimeng_generator_prompt = project_root / jimeng_generator_prompt
        
        # SD优化提示词
        self.sd_prompt_file = Path(sd_prompt_file)
        if not self.sd_prompt_file.exists():
            self.sd_prompt_file = project_root / sd_prompt_file
        
        # 验证路径存在
        self._validate_paths()
        
        # 加载SD提示词模板
        self.sd_prompt_template = self._load_sd_prompt_template()
        
        # 初始化Gemini客户端（如果需要）
        self.gemini_client = None
        
        logger.info(f"✅ ImagePromptGenerator初始化完成 - Creator: {creator_name}, Video: {video_id}, Type: {generator_type}")
    
    def _validate_paths(self):
        """验证必要的路径是否存在"""
        if not self.base_dir.exists():
            raise FileNotFoundError(f"项目目录不存在: {self.base_dir}")
        if not self.segments_dir.exists():
            raise FileNotFoundError(f"片段目录不存在: {self.segments_dir}")
        if not self.processing_dir.exists():
            logger.warning(f"处理目录不存在: {self.processing_dir}")
    
    def _load_sd_prompt_template(self) -> str:
        """加载SD提示词模板"""
        # 检查所有提示词文件
        prompt_files = [
            (self.scene_extractor_prompt, "场景提取提示词")
        ]
        
        if self.generator_type == "sd":
            prompt_files.extend([
                (self.sd_generator_prompt, "SD生成提示词"),
                (self.sd_prompt_file, "SD优化提示词")
            ])
        elif self.generator_type == "jimeng":
            prompt_files.append((self.jimeng_generator_prompt, "即梦生成提示词"))
        
        for prompt_file, name in prompt_files:
            if not prompt_file.exists():
                raise FileNotFoundError(f"{name}文件不存在: {prompt_file}")
        
        # 加载主要的SD提示词模板
        if self.sd_prompt_file.exists():
            with open(self.sd_prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return ""
    
    def _setup_debug_logging(self, creator_name: str, video_id: str):
        """设置debug日志"""
        # 创建logs目录
        log_dir = Path("logs") / creator_name / video_id
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"ai_conversation_{timestamp}.log"
        
        # 添加文件handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s\n' + '='*80,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 清除旧的handlers并添加新的
        debug_logger.handlers.clear()
        debug_logger.addHandler(file_handler)
        
        logger.info(f"Debug日志已启用: {log_file}")
        debug_logger.info(f"开始新的图片提示词生成会话 - Creator: {creator_name}, Video: {video_id}")
    
    def _init_gemini_client(self):
        """延迟初始化Gemini客户端"""
        if self.gemini_client is None:
            try:
                from gemini_client import GeminiClient
                gemini_api_key = os.getenv("NEWAPI_API_KEY", "sk-oFdSWMX8z3cAYYCrGYCcwAupxMdiErcOKBsfi5k0QdRxELCu")
                self.gemini_client = GeminiClient(api_key=gemini_api_key)
                logger.info("✅ Gemini客户端初始化成功")
            except Exception as e:
                logger.error(f"❌ Gemini客户端初始化失败: {e}")
                raise
    
    def generate_for_segment(self, segment_id: int) -> Dict[str, Any]:
        """
        为指定的segment生成图片提示词
        
        Args:
            segment_id: 片段编号 (1-30)
            
        Returns:
            包含场景分析和SD提示词的字典
        """
        logger.info(f"🎨 开始为片段 {segment_id} 生成图片提示词...")
        
        # 1. 读取segment文件
        segment_file = self.segments_dir / f"segment_{segment_id:02d}.txt"
        if not segment_file.exists():
            raise FileNotFoundError(f"片段文件不存在: {segment_file}")
        
        with open(segment_file, 'r', encoding='utf-8') as f:
            segment_content = f.read()
        
        logger.info(f"✅ 读取片段 {segment_id}, 长度: {len(segment_content)}字")
        
        # 2. 读取框架文件获取角色信息
        character_profiles = self._extract_character_profiles()
        
        # 3. 分析场景
        scenes = self._analyze_segment_scenes(segment_content, segment_id)
        
        # 4. 生成SD提示词
        prompts = self._generate_sd_prompts(scenes, character_profiles, segment_id)
        
        result = {
            "segment_id": segment_id,
            "segment_length": len(segment_content),
            "character_profiles": character_profiles,
            "scenes": scenes,
            "prompts": prompts
        }
        
        logger.info(f"✅ 片段 {segment_id} 处理完成，生成了 {len(prompts)} 个提示词")
        
        return result
    
    def generate_for_segments(self, segment_ids: List[int] = None) -> Dict[str, Any]:
        """
        批量生成多个segment的提示词
        
        Args:
            segment_ids: 片段编号列表，None表示处理所有存在的片段
        """
        if segment_ids is None:
            # 自动发现所有segment文件
            segment_ids = self._discover_segments()
            logger.info(f"🔍 自动发现 {len(segment_ids)} 个片段文件")
        
        results = {
            "creator_name": self.creator_name,
            "video_id": self.video_id,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_segments": len(segment_ids),
            "images_per_segment": self.images_per_segment,
            "segments": {}
        }
        
        # 提取一次角色信息（所有片段共用）
        character_profiles = self._extract_character_profiles()
        results["character_profiles"] = character_profiles
        
        for seg_id in segment_ids:
            try:
                logger.info(f"📝 处理片段 {seg_id}/{len(segment_ids)}...")
                segment_result = self.generate_for_segment(seg_id)
                results["segments"][f"segment_{seg_id:02d}"] = segment_result
            except Exception as e:
                logger.error(f"❌ 处理片段 {seg_id} 失败: {e}")
                results["segments"][f"segment_{seg_id:02d}"] = {
                    "error": str(e),
                    "segment_id": seg_id
                }
        
        # 统计信息
        total_prompts = sum(
            len(seg.get("prompts", [])) 
            for seg in results["segments"].values()
            if "prompts" in seg
        )
        results["total_prompts"] = total_prompts
        
        logger.info(f"✅ 批量处理完成，共生成 {total_prompts} 个提示词")
        
        return results
    
    def _discover_segments(self) -> List[int]:
        """自动发现所有存在的segment文件"""
        segment_files = list(self.segments_dir.glob("segment_*.txt"))
        segment_ids = []
        for f in segment_files:
            # 从文件名提取编号
            try:
                num = int(f.stem.split('_')[1])
                segment_ids.append(num)
            except (IndexError, ValueError):
                logger.warning(f"无法解析文件名: {f.name}")
        
        return sorted(segment_ids)
    
    def _extract_character_profiles(self) -> Dict[str, Any]:
        """从framework文件提取角色信息，只提取名称和视觉描述"""
        framework_file = self.processing_dir / "2_framework.txt"
        
        if not framework_file.exists():
            logger.warning(f"<未找到框架文件>: {framework_file}")
            sys.exit(1)
        
        with open(framework_file, 'r', encoding='utf-8') as f:
            framework_content = f.read()
        
        characters = self._extract_characters(framework_content)
        #logger.debug(f"framework_file = {framework_content}")

        logger.info(f" characters =  {characters} ")
        # 如果没找到，使用默认角色
        if not characters:
            logger.warning(f"<<未找到角色信息，退出>>: {characters}")
            sys.exit(1)
        
        logger.info(f"✅ 提取到 {len(characters)} 个角色信息")
        return characters

    import re

    def _extract_characters(self , framework_content: str):
        characters = {}
        # 匹配形如 "- **角色1：Name**" 的 header（支持无 - 或无 ** 的 fallback）
        role_pat = re.compile(r"^[ \t]*[-*]?\s*\*\*角色(\d+)[：:]\s*([^\*]+?)\*\*", re.MULTILINE)
        roles = list(role_pat.finditer(framework_content))

        # fallback（没有粗体时尽量也能匹配）
        if not roles:
            role_pat = re.compile(r"角色(\d+)[：:]\s*([^\n\[]+)")
            roles = list(role_pat.finditer(framework_content))

        for i, m in enumerate(roles):
            name = m.group(2).strip()
            # 取 header 到下一个 header 之间作为这个角色的块
            start = m.end()
            end = roles[i + 1].start() if i + 1 < len(roles) else len(framework_content)
            block = framework_content[start:end]

            visual = ""
            # 优先匹配形如 "**性别/...** 描述" 的那一行，取 ** 后面的内容
            bold_sex = re.search(r"^[ \t]*[-*]?\s*\*\*性别[^*]*\*\*\s*(.*)$", block, re.MULTILINE)
            if bold_sex:
                visual = bold_sex.group(1).strip()
            else:
                # 回退：找包含 "性别" 的任意行，做简易清洗后取性别之后的部分
                for line in block.splitlines():
                    if "性别" in line:
                        # 去掉行内的 - 和 *
                        clean_line = re.sub(r"[-*]", "", line).strip()
                        # 去掉粗体标记（若存在）
                        clean_line = clean_line.replace("**", "")
                        # 尝试按冒号分割，例如 "性别/..： 描述"
                        parts = re.split(r"[:：]\s*", clean_line, maxsplit=1)
                        if len(parts) == 2 and "性别" in parts[0]:
                            visual = parts[1].strip()
                        else:
                            # 常规：取 "性别" 后面的所有内容，去掉开头的标点和斜线
                            idx = clean_line.find("性别")
                            tail = clean_line[idx + len("性别"):].strip()
                            tail = re.sub(r"^[\s/:\-:：\.\…]*", "", tail)
                            visual = tail
                        break

            # 最终清理并合并成单行
            visual = visual.replace("**", "").strip()
            visual = re.sub(r"\s+", " ", visual)

            characters[name] = {
                "name": name,
                "visual_description": visual
            }

        return characters

    # --- 示例用法（把你的 framework_content 放进来） ---
    # result = extract_characters(framework_content)
    # print(result)


    def _get_default_characters(self) -> Dict[str, Any]:
        """获取默认角色配置"""
        return {
            "主角": {
                "name": "主角",
                "visual_description": "年轻人，坚定的眼神，普通装扮"
            }
        }
    
    def _build_character_visual_map(self, characters: Dict[str, Any]) -> None:
        """
        构建人物姓名到视觉特征的映射
        
        Args:
            characters: 人物信息字典
        """
        for char_name, char_info in characters.items():
            if isinstance(char_info, dict) and 'visual_description' in char_info:
                # 存储完整的视觉描述
                self.character_visual_map[char_name] = char_info['visual_description']
                
                # 为常见的姓名变体也创建映射
                if ' ' in char_name:
                    # 处理中英文混合名称，如 "艾拉拉·索恩 (Ailala Thorne)"
                    name_parts = char_name.split('(')
                    if len(name_parts) > 0:
                        chinese_name = name_parts[0].strip()
                        self.character_visual_map[chinese_name] = char_info['visual_description']
                    if len(name_parts) > 1:
                        english_name = name_parts[1].replace(')', '').strip()
                        self.character_visual_map[english_name] = char_info['visual_description']
                
                # 只取第一个名字
                first_name = char_name.split()[0].split('·')[0].split('(')[0]
                self.character_visual_map[first_name] = char_info['visual_description']
    
    def _replace_names_with_descriptions(self, text: str) -> str:
        """
        将文本中的人物姓名替换为视觉描述
        
        Args:
            text: 包含人物姓名的文本
            
        Returns:
            替换后的文本
        """
        result = text
        
        # 按姓名长度降序排序，先替换长的名字避免部分匹配问题
        sorted_names = sorted(self.character_visual_map.keys(), key=len, reverse=True)
        
        for name in sorted_names:
            if name in result:
                visual_desc = self.character_visual_map[name]
                # 提取关键视觉特征
                visual_features = self._extract_key_visual_features(visual_desc)
                result = result.replace(name, visual_features)
        
        return result
    
    def _extract_key_visual_features(self, description: str) -> str:
        """
        从完整描述中提取关键视觉特征
        
        Args:
            description: 完整的人物描述
            
        Returns:
            精简的视觉特征描述
        """
        # 提取关键词
        key_features = []
        
        # 性别和年龄
        if "女" in description:
            if "年轻" in description or "青年" in description:
                key_features.append("年轻女性")
            elif "中年" in description:
                key_features.append("中年女性")
            elif "老" in description:
                key_features.append("老年女性")
            else:
                key_features.append("女性")
        elif "男" in description:
            if "年轻" in description or "青年" in description:
                key_features.append("年轻男性")
            elif "中年" in description:
                key_features.append("中年男性")
            elif "老" in description:
                key_features.append("老年男性")
            else:
                key_features.append("男性")
        
        # 发色和发型
        hair_colors = ["黑发", "棕发", "金发", "红发", "白发", "灰发", "银发"]
        for color in hair_colors:
            if color in description:
                key_features.append(color)
                break
        
        hair_styles = ["长发", "短发", "卷发", "直发", "波浪发"]
        for style in hair_styles:
            if style in description:
                key_features.append(style)
                break
        
        # 其他明显特征
        if "眼镜" in description:
            key_features.append("戴眼镜")
        if "胡须" in description or "胡子" in description:
            key_features.append("有胡须")
        
        # 如果没有提取到特征，返回简化的原描述
        if not key_features:
            # 尝试返回前20个字作为简化描述
            return description[:20] if len(description) > 20 else description
        
        return "，".join(key_features[:3])  # 最多保留3个特征
    
    def _extract_sd_features(self, description: str) -> str:
        """从中文描述提取SD友好的特征"""
        features = []
        
        # 年龄特征
        if "年轻" in description or "青年" in description:
            features.append("young adult")
        elif "中年" in description:
            features.append("middle-aged")
        elif "老" in description or "年长" in description:
            features.append("elderly")
        
        # 性别特征
        if "女" in description:
            features.append("female")
        elif "男" in description:
            features.append("male")
        
        # 发型特征
        if "长发" in description:
            features.append("long hair")
        elif "短发" in description:
            features.append("short hair")
        elif "卷发" in description:
            features.append("curly hair")
        
        # 其他特征
        if "眼镜" in description:
            features.append("wearing glasses")
        if "微笑" in description:
            features.append("smiling")
        if "严肃" in description:
            features.append("serious expression")
        
        return ", ".join(features) if features else "person"
    
    def _analyze_segment_scenes(self, segment_content: str, segment_id: int) -> List[Dict[str, Any]]:
        """
        分析segment内容，提取关键场景（三步流程）
        
        Args:
            segment_content: 片段内容
            segment_id: 片段编号
            
        Returns:
            关键场景列表
        """
        # 步骤1: 使用场景提取提示词提取场景
        if self.scene_extractor_prompt.exists() and len(segment_content) > 100:
            try:
                self._init_gemini_client()
                if self.gemini_client:
                    return self._extract_scenes_with_prompt(segment_content, segment_id)
            except Exception as e:
                logger.error(f"场景提取失败: {e}")
                raise
    
    def _analyze_with_ai(self, segment_content: str, segment_id: int) -> List[Dict[str, Any]]:
        """使用AI分析提取场景"""
        prompt = f"""
从以下故事片段中提取{self.images_per_segment}个最具视觉冲击力的关键场景，用于生成插画。

片段内容：
{segment_content[:2000]}...

请返回JSON格式：
[
  {{
    "description": "场景的视觉描述",
    "characters": ["出现的人物"],
    "emotion": "场景的情感氛围",
    "visual_elements": ["关键视觉元素"],
    "color_mood": "色调氛围"
  }}
]
"""
        
        try:
            response = self.gemini_client.generate_content(prompt)
            
            # 解析JSON
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                scenes = json.loads(json_match.group())
                # 添加scene_index
                for i, scene in enumerate(scenes[:self.images_per_segment], 1):
                    scene["scene_index"] = i
                return scenes[:self.images_per_segment]
        except Exception as e:
            logger.warning(f"AI场景分析失败: {e}")
        
        # 失败时返回默认场景
        return self._get_default_scenes(segment_id)
    
    def _extract_scenes_with_prompt(self, segment_content: str, segment_id: int) -> Optional[List[Dict[str, Any]]]:
        """使用场景提取提示词提取场景"""
        try:
            # 读取场景提取提示词
            prompt_template = self.scene_extractor_prompt.read_text(encoding='utf-8')
            
            # 获取角色信息 - 只传递名称和视觉描述
            characters = self._extract_character_profiles()
            
            # 格式化角色信息为简单的文本格式
            character_info_lines = []
            for char_name, char_info in characters.items():
                character_info_lines.append(f"- {char_info['name']}: {char_info['visual_description']}")
            character_info_text = "\n".join(character_info_lines)
            
            # 构建完整提示词
            prompt = f"""{prompt_template}

## 输入信息

### 故事片段
{segment_content}

### 角色信息
{character_info_text}

### 需要提取的场景数量
{self.images_per_segment}

请分析上述故事片段，提取{self.images_per_segment}个最具视觉表现力的场景，以JSON格式输出。"""
            
            # 记录AI对话
            debug_logger.debug("="*80)
            debug_logger.debug("场景提取 - 输入")
            debug_logger.debug("="*80)
            debug_logger.debug(prompt)
            
            # 调用AI
            response = self.gemini_client.generate_content(prompt)
            
            # 解析返回的JSON（response可能是字符串或对象）
            response_text = response if isinstance(response, str) else response.text
            
            # 记录AI响应
            debug_logger.debug("="*80)
            debug_logger.debug("场景提取 - 输出")
            debug_logger.debug("="*80)
            debug_logger.debug(response_text)
            return self._parse_extracted_scenes(response_text, segment_id)
            
        except Exception as e:
            logger.warning(f"场景提取失败: {e}")
            return None
    
    def _parse_extracted_scenes(self, response_text: str, segment_id: int) -> Optional[List[Dict[str, Any]]]:
        """解析AI提取的场景JSON - 适配新格式"""
        try:
            # 提取JSON部分
            json_match = re.search(r'```json\s*(.+?)\s*```', response_text, re.DOTALL)
            if json_match:
                scenes_data = json.loads(json_match.group(1))
            else:
                # 尝试直接解析
                scenes_data = json.loads(response_text)
            
            # 新格式有 "角色" 和 "场景" 两个键
            characters_info = scenes_data.get("角色", [])
            scenes = scenes_data.get("场景", [])
            
            if not scenes:
                return None
            
            # 构建角色名称到描述的映射
            character_map = {}
            for char in characters_info:
                if isinstance(char, dict):
                    character_map[char.get("name", "")] = char.get("character", "")
            
            # 标准化场景数据
            standardized_scenes = []
            for scene in scenes[:self.images_per_segment]:
                # 从场景描述中提取角色名称
                scene_chars = []
                for char_name in character_map.keys():
                    if char_name in scene.get("scene_description", ""):
                        scene_chars.append(char_name)
                
                if not scene_chars and character_map:
                    # 如果没有明确提到角色，使用第一个角色
                    scene_chars = [list(character_map.keys())[0]]
                
                standardized_scene = {
                    "scene_index": scene.get("scene_num", 1),
                    "description": scene.get("scene_description", ""),
                    "characters": scene_chars,
                    "character_descriptions": character_map,  # 添加角色描述映射
                    "emotion": "neutral",  # 简化后的格式没有情感字段
                    "visual_elements": [],  # 简化后的格式没有视觉元素列表
                    "color_mood": "neutral"  # 简化后的格式没有色彩基调
                }
                standardized_scenes.append(standardized_scene)
            
            return standardized_scenes
            
        except Exception as e:
            logger.warning(f"场景JSON解析失败: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            return None
    
    def _extract_character_names(self, scene: Dict) -> List[str]:
        """从场景中提取角色名称"""
        characters = []
        if "characters" in scene:
            for char in scene["characters"]:
                if isinstance(char, dict):
                    characters.append(char.get("name", "人物"))
                elif isinstance(char, str):
                    characters.append(char)
        return characters if characters else ["人物"]
    
    def _extract_visual_elements_from_scene(self, scene: Dict) -> List[str]:
        """从场景中提取视觉元素"""
        elements = []
        
        # 从visual_composition中提取
        if "visual_composition" in scene:
            comp = scene["visual_composition"]
            elements.extend(comp.get("foreground", []))
            elements.extend(comp.get("midground", []))
            elements.extend(comp.get("background", []))
        
        # 从key_objects中提取
        if "key_objects" in scene:
            for obj in scene["key_objects"]:
                if isinstance(obj, dict):
                    elements.append(obj.get("object", ""))
                elif isinstance(obj, str):
                    elements.append(obj)
        
        # 从visual_elements中提取
        if "visual_elements" in scene:
            elements.extend(scene["visual_elements"])
        
        return elements[:5] if elements else ["场景"]
    
    def _analyze_with_rules(self, segment_content: str, segment_id: int) -> List[Dict[str, Any]]:
        """使用规则分析提取场景"""
        scenes = []
        
        # 将内容分段
        paragraphs = segment_content.split('\n\n')
        
        # 选择最有代表性的段落
        selected_paragraphs = []
        if len(paragraphs) >= self.images_per_segment:
            # 均匀选择段落
            step = len(paragraphs) // self.images_per_segment
            for i in range(self.images_per_segment):
                idx = i * step
                if idx < len(paragraphs):
                    selected_paragraphs.append(paragraphs[idx])
        else:
            selected_paragraphs = paragraphs[:self.images_per_segment]
        
        # 为每个段落生成场景
        for i, para in enumerate(selected_paragraphs, 1):
            scene = {
                "scene_index": i,
                "description": para[:100] + "..." if len(para) > 100 else para,
                "characters": self._extract_characters_from_text(para),
                "emotion": self._detect_emotion(para),
                "visual_elements": self._extract_visual_elements(para),
                "color_mood": self._detect_color_mood(para)
            }
            scenes.append(scene)
        
        # 如果场景不够，添加默认场景
        while len(scenes) < self.images_per_segment:
            scenes.extend(self._get_default_scenes(segment_id))
        
        return scenes[:self.images_per_segment]
    
    def _extract_characters_from_text(self, text: str) -> List[str]:
        """从文本中提取人物"""
        characters = []
        
        # 简单的人物识别规则
        character_keywords = ["他", "她", "我", "你", "男人", "女人", "孩子", "老人"]
        for keyword in character_keywords:
            if keyword in text:
                characters.append(keyword)
        
        return characters[:3] if characters else ["人物"]
    
    def _detect_emotion(self, text: str) -> str:
        """检测文本的情感氛围"""
        emotions = {
            "愤怒": ["愤怒", "生气", "怒", "恨"],
            "悲伤": ["悲", "哭", "泪", "伤心"],
            "快乐": ["笑", "乐", "喜", "开心"],
            "紧张": ["紧张", "焦虑", "担心", "害怕"],
            "平静": ["平静", "安静", "宁静", "淡然"]
        }
        
        for emotion, keywords in emotions.items():
            for keyword in keywords:
                if keyword in text:
                    return emotion
        
        return "平静"
    
    def _extract_visual_elements(self, text: str) -> List[str]:
        """提取视觉元素"""
        elements = []
        
        # 场景元素
        scene_keywords = ["海", "山", "树", "房", "路", "城", "天", "云", "雨", "雪"]
        for keyword in scene_keywords:
            if keyword in text:
                elements.append(keyword)
        
        # 物体元素
        object_keywords = ["车", "门", "窗", "桌", "椅", "床", "灯", "花"]
        for keyword in object_keywords:
            if keyword in text:
                elements.append(keyword)
        
        return elements[:5] if elements else ["场景"]
    
    def _detect_color_mood(self, text: str) -> str:
        """检测色调氛围"""
        if any(word in text for word in ["黑", "暗", "夜", "阴"]):
            return "dark"
        elif any(word in text for word in ["白", "亮", "光", "明"]):
            return "bright"
        elif any(word in text for word in ["红", "火", "血"]):
            return "warm"
        elif any(word in text for word in ["蓝", "冷", "冰"]):
            return "cold"
        else:
            return "neutral"
    
    def _get_default_scenes(self, segment_id: int) -> List[Dict[str, Any]]:
        """获取默认场景"""
        return [{
            "scene_index": 1,
            "description": f"片段{segment_id}的关键时刻",
            "characters": ["主角"],
            "emotion": "dramatic",
            "visual_elements": ["场景", "人物"],
            "color_mood": "moody"
        }]
    
    def _generate_sd_prompts(self, scenes: List[Dict[str, Any]], 
                           character_profiles: Dict[str, Any],
                           segment_id: int) -> List[Dict[str, Any]]:
        """
        根据场景信息生成提示词
        
        Args:
            scenes: 场景列表
            character_profiles: 角色信息
            segment_id: 片段编号
            
        Returns:
            SD提示词列表
        """
        prompts = []
        
        # 根据生成器类型选择不同的生成方法
        if self.generator_type == "jimeng":
            # 使用即梦生成器
            if self.jimeng_generator_prompt.exists() and self.gemini_client:
                for scene in scenes:
                    prompt = self._generate_jimeng_with_prompt(scene, character_profiles)
                    prompts.append(prompt)
            else:
                raise RuntimeError("即梦生成器需要AI支持")
        else:
            # 使用SD生成器
            if self.sd_generator_prompt.exists() and self.gemini_client:
                for scene in scenes:
                    prompt = self._generate_sd_with_prompt(scene, character_profiles)
                    prompts.append(prompt)
            else:
                raise RuntimeError("SD生成器需要AI支持")
        
        return prompts
    
    def _build_sd_prompt(self, scene: Dict[str, Any], 
                        character_profiles: Dict[str, Any]) -> Dict[str, str]:
        """构建单个场景的SD提示词"""
        # 基础质量词
        positive_parts = ["masterpiece", "best quality", "ultra-detailed", "8k uhd"]
        
        # 添加角色特征
        if character_profiles:
            # 使用第一个主要角色的特征
            main_char = list(character_profiles.values())[0]
            if main_char.get("sd_features"):
                positive_parts.append(main_char["sd_features"])
        
        # 添加场景描述（转换为英文风格）
        scene_desc = self._translate_scene_to_sd(scene)
        if scene_desc:
            positive_parts.append(scene_desc)
        
        # 添加情感氛围
        emotion = scene.get("emotion", "")
        emotion_mapping = {
            "愤怒": "angry expression, intense atmosphere",
            "悲伤": "sad mood, melancholic atmosphere",
            "快乐": "happy, cheerful atmosphere",
            "紧张": "tense, dramatic atmosphere",
            "平静": "calm, peaceful atmosphere",
            "dramatic": "dramatic lighting, intense atmosphere"
        }
        if emotion in emotion_mapping:
            positive_parts.append(emotion_mapping[emotion])
        
        # 添加色调
        color_mood = scene.get("color_mood", "")
        color_mapping = {
            "dark": "dark atmosphere, low key lighting",
            "bright": "bright colors, high key lighting",
            "warm": "warm color palette",
            "cold": "cold color palette",
            "moody": "moody atmosphere",
            "neutral": "balanced colors"
        }
        if color_mood in color_mapping:
            positive_parts.append(color_mapping[color_mood])
        
        # 添加构图风格
        positive_parts.append("cinematic composition")
        positive_parts.append("professional photography")
        
        # 负面提示词
        negative_prompt = "low quality, blurry, deformed, ugly, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers"
        
        return {
            "positive": ", ".join(positive_parts),
            "negative": negative_prompt
        }
    
    def _generate_sd_with_prompt(self, scene: Dict[str, Any], 
                                character_profiles: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """使用SD生成提示词转换场景"""
        try:
            # 读取SD生成提示词
            prompt_template = self.sd_generator_prompt.read_text(encoding='utf-8')
            
            # 构建人物视觉映射（如果还没有构建）
            if not self.character_visual_map and character_profiles:
                self._build_character_visual_map(character_profiles)
            
            # 替换场景描述中的人物姓名为视觉特征
            scene_copy = scene.copy()
            if 'description' in scene_copy:
                scene_copy['description'] = self._replace_names_with_descriptions(scene_copy['description'])
            if 'characters' in scene_copy and isinstance(scene_copy['characters'], list):
                scene_copy['characters'] = [
                    self._replace_names_with_descriptions(char) if isinstance(char, str) else char
                    for char in scene_copy['characters']
                ]
            
            # 构建场景信息JSON
            scene_info = {
                "scene": scene_copy,  # 使用替换后的场景
                "characters": character_profiles
            }
            scene_json = json.dumps(scene_info, ensure_ascii=False, indent=2)
            
            # 构建完整提示词
            prompt = f"""{prompt_template}

## 场景信息
{scene_json}

请将上述场景描述转换为Stable Diffusion提示词，以JSON格式输出。"""
            
            # 记录AI对话
            debug_logger.debug("="*80)
            debug_logger.debug("SD提示词生成 - 输入")
            debug_logger.debug("="*80)
            debug_logger.debug(prompt)
            
            # 调用AI
            response = self.gemini_client.generate_content(prompt)
            
            # 解析返回的SD提示词
            # 处理response可能是字符串或对象的情况
            response_text = response if isinstance(response, str) else response.text
            
            # 记录AI响应
            debug_logger.debug("="*80)
            debug_logger.debug("SD提示词生成 - 输出")
            debug_logger.debug("="*80)
            debug_logger.debug(response_text)
            return self._parse_sd_prompt(response_text, scene)
            
        except Exception as e:
            logger.error(f"SD提示词生成失败: {e}")
            raise
    
    def _parse_sd_prompt(self, response_text: str, original_scene: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析AI生成的SD提示词"""
        try:
            # 提取JSON
            json_match = re.search(r'```json\s*(.+?)\s*```', response_text, re.DOTALL)
            if json_match:
                sd_data = json.loads(json_match.group(1))
            else:
                sd_data = json.loads(response_text)
            
            # 构建标准格式
            positive_prompt = ""
            negative_prompt = ""
            
            # 提取正面提示词
            if "prompts" in sd_data:
                prompts = sd_data["prompts"]
                if "positive" in prompts:
                    if isinstance(prompts["positive"], dict):
                        positive_prompt = prompts["positive"].get("full_prompt", "")
                    else:
                        positive_prompt = prompts["positive"]
                if "negative" in prompts:
                    if isinstance(prompts["negative"], dict):
                        negative_prompt = prompts["negative"].get("full_prompt", "")
                    else:
                        negative_prompt = prompts["negative"]
            elif "positive_prompt" in sd_data:
                positive_prompt = sd_data["positive_prompt"]
                negative_prompt = sd_data.get("negative_prompt", "")
            
            return {
                "scene_index": original_scene.get("scene_index", 1),
                "scene_description": original_scene.get("description", ""),
                "emotion": original_scene.get("emotion", ""),
                "sd_prompt": {
                    "positive": positive_prompt,
                    "negative": negative_prompt
                }
            }
            
        except Exception as e:
            logger.error(f"SD提示词JSON解析失败: {e}")
            raise
    
    def _translate_scene_to_sd(self, scene: Dict[str, Any]) -> str:
        """将场景描述转换为SD风格（简化版）"""
        elements = []
        
        # 添加视觉元素
        visual_elements = scene.get("visual_elements", [])
        element_mapping = {
            "海": "ocean",
            "山": "mountain",
            "树": "trees",
            "房": "house",
            "路": "road",
            "城": "city",
            "天": "sky",
            "云": "clouds",
            "雨": "rain",
            "雪": "snow",
            "场景": "scenery",
            "人物": "character"
        }
        
        for element in visual_elements[:3]:
            if element in element_mapping:
                elements.append(element_mapping[element])
            else:
                elements.append("detailed background")
                break
        
        return ", ".join(elements) if elements else "detailed scene"
    
    def save_results(self, results: Dict[str, Any], single: bool = False):
        """
        保存结果到文件
        
        Args:
            results: 生成的结果
            single: 是否为单个segment的结果
        """
        # 确保输出目录存在
        self.final_dir.mkdir(parents=True, exist_ok=True)
        
        # 根据生成器类型确定文件前缀
        prefix = "jimeng" if self.generator_type == "jimeng" else "sd"
        
        # 确定输出文件名
        if single:
            segment_id = results.get("segment_id", 0)
            json_file = self.final_dir / f"{prefix}_prompt_segment_{segment_id:02d}.json"
            md_file = self.final_dir / f"{prefix}_prompt_segment_{segment_id:02d}.md"
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_file = self.final_dir / f"{prefix}_prompts_batch_{timestamp}.json"
            md_file = self.final_dir / f"{prefix}_prompts_batch_{timestamp}.md"
        
        # 保存JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 JSON结果已保存到: {json_file}")
        
        # 保存Markdown
        self._save_as_markdown(results, md_file, single)
        logger.info(f"📝 Markdown结果已保存到: {md_file}")
    
    def _save_as_markdown(self, results: Dict[str, Any], output_file: Path, single: bool = False):
        """将结果保存为Markdown格式"""
        with open(output_file, 'w', encoding='utf-8') as f:
            title = "即梦图片提示词生成结果" if self.generator_type == "jimeng" else "SD图片提示词生成结果"
            f.write(f"# {title}\n\n")
            f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if single:
                # 单个segment的结果
                self._write_single_segment_markdown(f, results)
            else:
                # 批量结果
                self._write_batch_markdown(f, results)
    
    def _write_single_segment_markdown(self, f, results: Dict[str, Any]):
        """写入单个segment的Markdown"""
        f.write(f"## 片段 {results.get('segment_id', 0)}\n\n")
        
        # 角色信息
        if "character_profiles" in results:
            f.write("### 角色信息\n\n")
            for name, profile in results["character_profiles"].items():
                f.write(f"- **{name}**: {profile.get('visual_description', '')}\n")
            f.write("\n")
        
        # 场景分析
        if "scenes" in results:
            f.write("### 场景分析\n\n")
            for scene in results["scenes"]:
                f.write(f"#### 场景 {scene.get('scene_index', '')}\n")
                f.write(f"- **描述**: {scene.get('description', '')}\n")
                f.write(f"- **情感**: {scene.get('emotion', '')}\n")
                f.write(f"- **视觉元素**: {', '.join(scene.get('visual_elements', []))}\n\n")
        
        # 根据生成器类型输出不同格式
        if "prompts" in results:
            if self.generator_type == "jimeng":
                f.write("### 即梦提示词\n\n")
                for prompt in results["prompts"]:
                    f.write(f"#### 场景 {prompt.get('scene_index', '')}\n")
                    f.write(f"- **标题**: {prompt.get('scene_title', '')}\n")
                    if "jimeng_prompt" in prompt and "full_prompt" in prompt["jimeng_prompt"]:
                        f.write(f"**提示词**:\n```\n{prompt['jimeng_prompt']['full_prompt']}\n```\n\n")
            else:
                f.write("### SD提示词\n\n")
                for prompt in results["prompts"]:
                    f.write(f"#### 场景 {prompt.get('scene_index', '')}\n")
                    if "sd_prompt" in prompt:
                        f.write(f"**正面提示词**:\n```\n{prompt['sd_prompt']['positive']}\n```\n")
                        f.write(f"**负面提示词**:\n```\n{prompt['sd_prompt']['negative']}\n```\n\n")
    
    def _write_batch_markdown(self, f, results: Dict[str, Any]):
        """写入批量结果的Markdown"""
        f.write(f"## 项目信息\n\n")
        f.write(f"- **创作者**: {results.get('creator_name', '')}\n")
        f.write(f"- **视频ID**: {results.get('video_id', '')}\n")
        f.write(f"- **片段总数**: {results.get('total_segments', 0)}\n")
        f.write(f"- **提示词总数**: {results.get('total_prompts', 0)}\n")
        f.write(f"- **每片段图片数**: {results.get('images_per_segment', 1)}\n\n")
        
        # 角色信息
        if "character_profiles" in results:
            f.write("## 角色信息\n\n")
            for name, profile in results["character_profiles"].items():
                f.write(f"### {name}\n")
                f.write(f"- **视觉描述**: {profile.get('visual_description', '')}\n")
                f.write(f"- **SD特征**: {profile.get('sd_features', '')}\n\n")
        
        # 各片段的提示词
        if "segments" in results:
            f.write("## 片段提示词\n\n")
            for segment_key, segment_data in results["segments"].items():
                if "error" in segment_data:
                    f.write(f"### {segment_key}\n")
                    f.write(f"❌ 错误: {segment_data['error']}\n\n")
                    continue
                
                f.write(f"### {segment_key}\n\n")
                
                if "prompts" in segment_data:
                    for prompt in segment_data["prompts"]:
                        f.write(f"#### 场景 {prompt.get('scene_index', '')}\n")
                        if self.generator_type == "jimeng":
                            f.write(f"- **标题**: {prompt.get('scene_title', '')}\n")
                            if "jimeng_prompt" in prompt and "full_prompt" in prompt["jimeng_prompt"]:
                                f.write(f"**提示词**:\n```\n{prompt['jimeng_prompt']['full_prompt']}\n```\n\n")
                        else:
                            f.write(f"- **描述**: {prompt.get('scene_description', '')}\n")
                            f.write(f"- **情感**: {prompt.get('emotion', '')}\n")
                            if "sd_prompt" in prompt:
                                f.write(f"**提示词**:\n```\n{prompt['sd_prompt']['positive']}\n```\n\n")
    
    def _generate_jimeng_with_prompt(self, scene: Dict[str, Any], 
                                    character_profiles: Dict[str, Any]) -> Dict[str, Any]:
        """使用即梦生成器生成中文提示词 - 直接拼接场景提取结果"""
        try:
            # 读取即梦生成提示词
            prompt_template = self.jimeng_generator_prompt.read_text(encoding='utf-8')
            
            # 将场景信息转换为JSON字符串，直接拼接
            scene_json = json.dumps(scene, ensure_ascii=False, indent=2)
            
            # 添加艺术风格指示
            style_instruction = ""
            if self.art_style:
                style_instruction = f"""
## 重要：统一艺术风格
本故事的统一艺术风格为：**{self.art_style}**
请确保所有生成的提示词都采用此艺术风格，以保持整个故事的视觉一致性。
在生成提示词时，必须在开头明确包含此艺术风格。
"""
            
            # 直接拼接：提示词模板 + 场景JSON
            prompt = f"""{prompt_template}
{style_instruction}
## 场景信息（从场景提取直接获得）
{scene_json}

请基于上述场景信息生成即梦AI的中文提示词，以JSON格式输出。
注意：必须使用指定的艺术风格：{self.art_style if self.art_style else '根据场景自由选择合适的风格'}"""
            
            # 记录AI对话
            debug_logger.debug("="*80)
            debug_logger.debug("即梦提示词生成 - 输入")
            debug_logger.debug("="*80)
            debug_logger.debug(prompt)
            
            # 调用AI
            response = self.gemini_client.generate_content(prompt)
            
            # 解析返回的即梦提示词（response可能是字符串或对象）
            response_text = response if isinstance(response, str) else response.text
            
            # 记录AI响应
            debug_logger.debug("="*80)
            debug_logger.debug("即梦提示词生成 - 输出")
            debug_logger.debug("="*80)
            debug_logger.debug(response_text)
            return self._parse_jimeng_prompt(response_text, scene)
            
        except Exception as e:
            logger.error(f"即梦提示词生成失败: {e}")
            raise
    
    def _parse_jimeng_prompt(self, response_text: str, original_scene: Dict[str, Any]) -> Dict[str, Any]:
        """解析AI生成的即梦提示词 - 适配新格式"""
        try:
            # 提取JSON
            json_match = re.search(r'```json\s*(.+?)\s*```', response_text, re.DOTALL)
            if json_match:
                jimeng_data = json.loads(json_match.group(1))
            else:
                jimeng_data = json.loads(response_text)
            
            # 新格式只包含这些字段
            result = {
                "scene_index": jimeng_data.get("scene_index", original_scene.get("scene_index", 1)),
                "scene_title": jimeng_data.get("scene_title", ""),
                "jimeng_prompt": {}
            }
            
            # 提取jimeng_prompt
            if "jimeng_prompt" in jimeng_data:
                result["jimeng_prompt"] = {
                    "full_prompt": jimeng_data["jimeng_prompt"].get("full_prompt", "")
                }
            elif "full_prompt" in jimeng_data:
                result["jimeng_prompt"] = {
                    "full_prompt": jimeng_data["full_prompt"]
                }
            
            return result
            
        except Exception as e:
            logger.error(f"即梦提示词JSON解析失败: {e}")
            raise