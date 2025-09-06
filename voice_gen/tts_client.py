#!/usr/bin/env python3
"""
TTS客户端
负责业务逻辑（如故事音频生成、文件管理等）
"""

import os
import re
import string
import logging
import traceback
from pathlib import Path
from typing import Optional, Literal
from pydub import AudioSegment
import argparse
import platform

# 导入TTS服务
from tts_service import TTSServiceFactory, TTSServiceInterface

# 导入工具函数处理Windows编码问题
try:
    from utils import safe_print, setup_console_encoding
    # 设置控制台编码
    setup_console_encoding()
    use_safe_print = True
except ImportError:
    # 如果导入失败，定义一个简单的 safe_print
    def safe_print(message: str, file=None):
        if platform.system() == 'Windows':
            # 替换emoji字符
            message = message.replace('✅', '[OK]').replace('❌', '[ERROR]').replace('⚠️', '[WARNING]')
        try:
            print(message, file=file)
        except UnicodeEncodeError:
            # 移除所有非 ASCII 字符
            message_ascii = message.encode('ascii', 'replace').decode('ascii')
            print(message_ascii, file=file)
    use_safe_print = True

# 配置日志
import os
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class TTSClient:
    """TTS客户端类，负责业务逻辑"""
    
    def __init__(
        self, 
        service_type: Literal["old", "new"] = "old",
        base_url: Optional[str] = None
    ):
        """
        初始化TTS客户端
        
        Args:
            service_type: 使用的服务类型 ("old" 或 "new")，默认使用旧服务
            base_url: 服务基础URL（可选）
        """
        self.service = TTSServiceFactory.create_service(service_type, base_url)
        self.service_type = service_type
        logger.info(f"使用 {service_type} TTS服务")
    
    def generate_speech(
        self, 
        text: str, 
        voice: str = "zh-CN-XiaoxiaoNeural",
        pitch: str = "+0Hz",
        volume: str = "+0%",
        rate: str = "+0%",
        save_path: str = "./downloads"
    ) -> dict:
        """
        生成语音并保存文件
        
        Args:
            text: 要转换的文本
            voice: 语音类型
            pitch: 音调调整
            volume: 音量调整
            rate: 语速调整
            save_path: 保存路径
            
        Returns:
            包含文件路径等信息的字典
        """
        try:
            # 调用服务生成语音
            # 批量处理时强制使用异步接口，避免同步接口的限制
            result = self.service.generate(text, voice, pitch, volume, rate, force_async=True)
            
            if not result.get('success'):
                raise Exception("生成失败")
            
            # 创建保存目录
            Path(save_path).mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            audio_filename = f"tts_{text_hash}.mp3"
            audio_path = os.path.join(save_path, audio_filename)
            
            # 保存音频文件
            with open(audio_path, 'wb') as f:
                f.write(result['audio_data'])
            
            safe_print(f"生成成功，音频文件已保存: {audio_path}")
            if result.get('duration'):
                safe_print(f"音频时长: {result['duration']:.2f}秒")
            safe_print(f"文件大小: {result['file_size']:,} 字节")
            
            # 保存字幕文件（如果有）
            srt_path = None
            if result.get('subtitle_text'):
                srt_filename = f"tts_{text_hash}.srt"
                srt_path = os.path.join(save_path, srt_filename)
                with open(srt_path, 'w', encoding='utf-8') as f:
                    f.write(result['subtitle_text'])
                safe_print(f"字幕文件已保存: {srt_path}")
            
            return {
                'success': True,
                'audio_path': audio_path,
                'srt_path': srt_path,
                'text': text,
                'voice': result.get('voice', voice),
                'duration': result.get('duration', 0),
                'file_size': result.get('file_size', 0)
            }
            
        except Exception as e:
            logger.error(f"生成语音失败: {e}")
            raise
    
    def generate_speech_with_line_num(
        self,
        text: str,
        voice: str,
        pitch: str,
        volume: str,
        rate: str,
        save_path: str,
        line_num: int
    ) -> dict:
        """
        生成语音并使用行号命名文件
        
        Args:
            text: 要转换的文本
            voice: 语音类型
            pitch: 音调调整
            volume: 音量调整
            rate: 语速调整
            save_path: 保存路径
            line_num: 行号
            
        Returns:
            包含文件路径等信息的字典
        """
        try:
            # 如果是英文语音，清理文本
            if 'en-' in voice.lower():
                original_text = text
                text = self._clean_text_for_english_tts(text)
                if original_text != text:
                    logger.debug(f"文本已清理 - 行号: {line_num}")
                    logger.debug(f"原始文本: {original_text[:100]}...")
                    logger.debug(f"清理后文本: {text[:100]}...")
            
            safe_print(f"正在生成语音 (行号: {line_num}): {text[:50]}...")
            
            # 调用服务生成语音
            # 批量处理时强制使用异步接口，避免同步接口的限制
            result = self.service.generate(text, voice, pitch, volume, rate, force_async=True)
            
            if not result.get('success'):
                raise Exception("生成失败")
            
            # 创建保存目录
            Path(save_path).mkdir(parents=True, exist_ok=True)
            
            # 使用行号命名文件
            audio_filename = f"line_{line_num:04d}.mp3"
            audio_path = os.path.join(save_path, audio_filename)
            
            # 保存音频文件
            with open(audio_path, 'wb') as f:
                f.write(result['audio_data'])
            
            safe_print(f"生成成功，音频文件已保存: {audio_path}")
            
            # 保存字幕文件（如果服务返回了字幕）
            srt_path = None
            if result.get('subtitle_text'):
                srt_filename = f"line_{line_num:04d}.srt"
                srt_path = os.path.join(save_path, srt_filename)
                with open(srt_path, 'w', encoding='utf-8') as f:
                    f.write(result['subtitle_text'])
                safe_print(f"字幕文件已保存: {srt_path}")
            else:
                logger.info(f"第 {line_num} 行没有返回字幕数据")
            
            return {
                'success': True,
                'audio_path': audio_path,
                'srt_path': srt_path,
                'text': text,
                'voice': result.get('voice', voice),
                'duration': result.get('duration', 0),
                'file_size': result.get('file_size', 0)
            }
            
        except Exception as e:
            logger.error(f"生成语音失败（行号: {line_num}）: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(f"TTS服务返回: {result if 'result' in locals() else 'No result'}")
            import traceback
            logger.error(f"完整错误栈:\n{traceback.format_exc()}")
            raise Exception(f"生成语音失败（行号: {line_num}）: {e}")
    
    def generate_story_audio(self, c_id: str, v_id: str, gender: str) -> dict:
        """
        读取故事文件并生成完整音频
        
        Args:
            c_id: creator_id
            v_id: voice_id
            gender: 性别 ('male' 或 'female')
        
        Returns:
            包含音频和字幕文件路径的字典
        """
        # 构建故事文件路径
        story_path = f"./story_result/{c_id}/{v_id}/final/story.txt"
        
        # 检查文件是否存在
        if not os.path.exists(story_path):
            raise Exception(f"故事文件不存在: {story_path}")
        
        # 选择语音
        voice = "en-US-BrianNeural" if gender == "male" else "en-US-AvaNeural"
        
        # 创建临时目录
        tmp_dir = f"./output/tmp/{c_id}_{v_id}"
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        
        # 读取故事文件
        with open(story_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 过滤掉空行，只保留有内容的行
        content_lines = [(i+1, line.strip()) for i, line in enumerate(lines) if line.strip()]
        
        logger.info(f"开始生成音频，共 {len(content_lines)} 行有效内容（原始 {len(lines)} 行）")
        
        # 生成每批次的音频（3行一批）
        audio_files = []
        srt_files = []
        audio_durations = []
        batch_size = 3  # 每批处理3行
        
        # 记录状态文件路径
        status_file = os.path.join(tmp_dir, "progress.txt")
        
        # 读取已处理的最后行号（支持断点续传）
        last_processed_line = 0
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r') as f:
                    last_processed_line = int(f.read().strip())
                logger.info(f"从上次处理的第 {last_processed_line} 行后继续...")
            except:
                pass
        
        # 按批次处理文本
        for batch_start in range(0, len(content_lines), batch_size):
            batch_end = min(batch_start + batch_size, len(content_lines))
            batch_lines = content_lines[batch_start:batch_end]
            
            # 获取批次中最后一行的行号
            last_line_num = batch_lines[-1][0]
            
            # 如果这批已经处理过，跳过
            if last_line_num <= last_processed_line:
                # 添加已存在的文件到列表
                for line_num, _ in batch_lines:
                    audio_filename = f"line_{line_num:04d}.mp3"
                    srt_filename = f"line_{line_num:04d}.srt"
                    audio_path = os.path.join(tmp_dir, audio_filename)
                    srt_path = os.path.join(tmp_dir, srt_filename)
                    
                    if os.path.exists(audio_path):
                        audio_files.append(audio_path)
                        if os.path.exists(srt_path):
                            srt_files.append(srt_path)
                        else:
                            srt_files.append(None)
                continue
            
            # 合并批次中的文本
            batch_text = " ".join([text for _, text in batch_lines])
            batch_line_nums = [line_num for line_num, _ in batch_lines]
            
            logger.info(f"正在处理第 {batch_line_nums[0]}-{batch_line_nums[-1]} 行 (批次 {batch_start//batch_size + 1}/{(len(content_lines) + batch_size - 1)//batch_size})...")
            logger.debug(f"批次文本长度: {len(batch_text)} 字符")
            
            # 生成批次音频（使用最后一行的行号作为文件名）
            audio_filename = f"line_{last_line_num:04d}.mp3"
            srt_filename = f"line_{last_line_num:04d}.srt"
            audio_path = os.path.join(tmp_dir, audio_filename)
            srt_path = os.path.join(tmp_dir, srt_filename)
            
            try:
                # 生成语音
                result = self.generate_speech_with_line_num(
                    text=batch_text,
                    voice=voice,
                    pitch="+0Hz",
                    volume="+0%",
                    rate="+0%",
                    save_path=tmp_dir,
                    line_num=last_line_num
                )
                
                if result['success']:
                    audio_files.append(result['audio_path'])
                    # 添加字幕文件（如果存在）
                    if result.get('srt_path') and os.path.exists(result['srt_path']):
                        srt_files.append(result['srt_path'])
                    else:
                        srt_files.append(None)
                    
                    # 更新状态文件，记录最后处理的行号
                    with open(status_file, 'w') as f:
                        f.write(str(last_line_num))
                    
                    logger.info(f"批次处理成功，已保存到第 {last_line_num} 行")
                else:
                    logger.error(f"批次处理失败（行 {batch_line_nums[0]}-{batch_line_nums[-1]}）")
                    
            except Exception as e:
                logger.error(f"批次处理出错（行 {batch_line_nums[0]}-{batch_line_nums[-1]}）: {e}")
                # 即使失败也继续处理下一批
        
        # 合并音频文件
        if not audio_files:
            raise Exception("没有生成任何音频文件")
        
        logger.info(f"开始合并 {len(audio_files)} 个音频文件...")
        safe_print(f"开始合并 {len(audio_files)} 个音频文件...")
        
        # 分批合并，避免内存占用过大
        batch_size = 5  # 减小批次大小，每批合并5个文件
        temp_files = []
        total_batches = (len(audio_files) + batch_size - 1) // batch_size
        
        for batch_idx, i in enumerate(range(0, len(audio_files), batch_size)):
            batch_files = audio_files[i:i+batch_size]
            current_batch = batch_idx + 1
            logger.info(f"合并批次 {current_batch}/{total_batches} (文件 {i+1}-{min(i+batch_size, len(audio_files))})")
            safe_print(f"合并进度: {current_batch}/{total_batches} 批次")
            
            # 合并当前批次
            batch_combined = AudioSegment.empty()
            for j, audio_file in enumerate(batch_files):
                try:
                    logger.debug(f"  加载文件 {j+1}/{len(batch_files)}: {audio_file}")
                    audio = AudioSegment.from_mp3(audio_file)
                    audio_durations.append(len(audio))  # 记录每个音频的时长（毫秒）
                    batch_combined += audio
                    # 释放单个音频占用的内存
                    del audio
                except Exception as e:
                    logger.error(f"加载音频文件失败 {audio_file}: {e}")
                    continue
            
            # 保存批次结果
            if len(batch_combined) > 0:
                temp_file = os.path.join(tmp_dir, f"batch_{batch_idx:03d}.mp3")
                logger.debug(f"  保存批次文件: {temp_file}")
                batch_combined.export(temp_file, format="mp3", bitrate="128k")  # 指定比特率
                temp_files.append(temp_file)
                logger.info(f"批次 {current_batch} 合并完成，临时文件: {temp_file}")
                # 释放批次音频占用的内存
                del batch_combined
            else:
                logger.warning(f"批次 {current_batch} 没有有效音频")
        
        # 最终合并所有批次
        logger.info(f"开始最终合并 {len(temp_files)} 个批次文件...")
        safe_print(f"最终合并: {len(temp_files)} 个批次文件")
        
        combined = AudioSegment.empty()
        for idx, temp_file in enumerate(temp_files, 1):
            logger.info(f"合并批次文件 {idx}/{len(temp_files)}: {temp_file}")
            try:
                audio = AudioSegment.from_mp3(temp_file)
                combined += audio
                # 释放内存
                del audio
                # 删除临时批次文件
                os.unlink(temp_file)
                logger.debug(f"已删除临时文件: {temp_file}")
            except Exception as e:
                logger.error(f"合并批次文件失败 {temp_file}: {e}")
                continue
        
        # 保存合并后的音频
        output_path = f"./output/{c_id}_{v_id}_story.mp3"
        logger.info(f"正在保存最终音频文件: {output_path}")
        safe_print(f"保存最终音频: {output_path}")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 导出最终音频，使用合理的比特率
        combined.export(output_path, format="mp3", bitrate="128k")
        logger.info(f"[OK] 音频合并完成: {output_path}")
        
        # 获取音频信息
        total_duration = len(combined) / 1000.0  # 转换为秒
        file_size = os.path.getsize(output_path)
        logger.info(f"音频总时长: {total_duration:.2f} 秒")
        logger.info(f"文件大小: {file_size:,} 字节 ({file_size/1024/1024:.2f} MB)")
        
        safe_print(f"音频合并完成: {output_path}")
        
        # 合并字幕文件
        srt_output_path = None
        if any(srt_files):  # 只有当有非None值时才合并
            srt_output_path = f"./output/{c_id}_{v_id}_story.srt"
            merged_srt = self._merge_srt_files(srt_files, audio_durations, srt_output_path)
            if not merged_srt:
                srt_output_path = None
        else:
            logger.warning("没有任何字幕文件可合并")
        
        # 清理临时文件
        for file in Path(tmp_dir).glob("*.mp3"):
            file.unlink()
        for file in Path(tmp_dir).glob("*.srt"):
            file.unlink()
        
        return {
            'audio_path': output_path,
            'srt_path': srt_output_path
        }
    
    def check_status(self) -> str:
        """检查TTS服务状态"""
        return self.service.check_status()
    
    def get_voices(self, language: Optional[str] = None) -> dict:
        """获取可用语音列表"""
        return self.service.get_voices(language)
    
    def _clean_text_for_english_tts(self, text: str) -> str:
        """清理文本，只保留英文字符和基本标点符号"""
        try:
            import ftfy
            # 使用 ftfy 自动修复文本编码问题
            cleaned_text = ftfy.fix_text(text)
            # 过滤掉非ASCII字符
            cleaned_text = ''.join(char for char in cleaned_text if ord(char) < 128)
            
        except ImportError:
            # 如果 ftfy 未安装，使用备用方案
            logger.warning("ftfy 库未安装，使用备用文本清理方案")
            import unicodedata
            
            # 手动替换常见特殊字符
            text = text.replace('\u201c', '"').replace('\u201d', '"')  # 智能双引号
            text = text.replace('\u2018', "'").replace('\u2019', "'")  # 智能单引号
            text = text.replace('\u2014', '--').replace('\u2013', '-')  # 破折号
            text = text.replace('\u2026', '...')  # 省略号
            text = text.replace('\u00a0', ' ')  # 不间断空格
            
            # NFKD 规范化
            text = unicodedata.normalize('NFKD', text)
            
            # 只保留ASCII字符
            cleaned_text = ''.join(char for char in text if ord(char) < 128)
        
        # 清理多余的空格
        cleaned_text = ' '.join(cleaned_text.split())
        
        # 确保文本不为空
        if not cleaned_text.strip():
            cleaned_text = "Text content"
            logger.warning("文本清理后为空，使用默认值")
        
        return cleaned_text
    
    def _parse_srt_time(self, time_str: str) -> int:
        """解析SRT时间格式 (00:00:00,000) 为毫秒"""
        time_parts = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str)
        if time_parts:
            hours = int(time_parts.group(1))
            minutes = int(time_parts.group(2))
            seconds = int(time_parts.group(3))
            milliseconds = int(time_parts.group(4))
            total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
            return total_ms
        return 0
    
    def _format_srt_time(self, milliseconds: int) -> str:
        """将毫秒转换为SRT时间格式 (00:00:00,000)"""
        hours = milliseconds // 3600000
        minutes = (milliseconds % 3600000) // 60000
        seconds = (milliseconds % 60000) // 1000
        ms = milliseconds % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"
    
    def _remove_punctuation(self, text: str) -> str:
        """去除文本中的所有标点符号"""
        punctuation = string.punctuation + '，。！？；：""''（）【】《》、…—·'
        translator = str.maketrans('', '', punctuation)
        return text.translate(translator)
    
    def _merge_srt_files(self, srt_files: list, audio_durations: list, output_path: str) -> Optional[str]:
        """
        合并多个SRT字幕文件
        
        Args:
            srt_files: SRT文件路径列表
            audio_durations: 对应音频文件的时长列表（毫秒）
            output_path: 输出的合并SRT文件路径
            
        Returns:
            合并后的文件路径，如果没有字幕则返回None
        """
        merged_content = []
        subtitle_index = 1
        time_offset = 0
        
        for i, srt_file in enumerate(srt_files):
            if srt_file and os.path.exists(srt_file):
                with open(srt_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # 解析SRT内容
                subtitles = content.split('\n\n')
                
                for subtitle in subtitles:
                    if not subtitle.strip():
                        continue
                    
                    lines = subtitle.strip().split('\n')
                    if len(lines) >= 3:
                        # 跳过原始序号，使用新的连续序号
                        time_line = lines[1]
                        text_lines = lines[2:]
                        
                        # 解析时间
                        time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', time_line)
                        if time_match:
                            start_time = self._parse_srt_time(time_match.group(1))
                            end_time = self._parse_srt_time(time_match.group(2))
                            
                            # 添加时间偏移
                            new_start = start_time + time_offset
                            new_end = end_time + time_offset
                            
                            # 处理文本：去除标点符号并转换为小写
                            cleaned_text_lines = []
                            for text_line in text_lines:
                                cleaned_text = self._remove_punctuation(text_line)
                                # 转换为小写
                                cleaned_text = cleaned_text.lower()
                                if cleaned_text.strip():
                                    cleaned_text_lines.append(cleaned_text)
                            
                            # 只有当有文本内容时才添加字幕
                            if cleaned_text_lines:
                                # 格式化新的字幕块
                                new_subtitle = f"{subtitle_index}\n"
                                new_subtitle += f"{self._format_srt_time(new_start)} --> {self._format_srt_time(new_end)}\n"
                                new_subtitle += '\n'.join(cleaned_text_lines)
                                
                                merged_content.append(new_subtitle)
                                subtitle_index += 1
                
                # 更新时间偏移（使用音频实际时长）
                if i < len(audio_durations):
                    time_offset += audio_durations[i]
        
        # 保存合并的SRT文件
        if merged_content:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(merged_content))
            safe_print(f"字幕文件已合并: {output_path}")
            return output_path
        
        return None


# 命令行接口
if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='生成故事音频')
    parser.add_argument('--cid', type=str, required=True, help='Creator ID')
    parser.add_argument('--vid', type=str, required=True, help='Voice ID')
    parser.add_argument('--gender', type=int, required=True, choices=[0, 1],
                       help='性别: 0=女声, 1=男声')
    parser.add_argument('--service', type=str, default='old', choices=['old', 'new'],
                       help='TTS服务类型: old=旧版EasyVoice(默认), new=新版公开API')
    parser.add_argument('--url', type=str, help='自定义服务URL')
    parser.add_argument('--account', type=str, help='发布账号')
    
    # 解析参数
    args = parser.parse_args()
    
    # 转换性别参数
    gender = "male" if args.gender == 1 else "female"
    
    # 创建客户端实例
    client = TTSClient(service_type=args.service, base_url=args.url)
    
    try:
        safe_print(f"开始生成故事音频...")
        safe_print(f"Creator ID: {args.cid}")
        safe_print(f"Voice ID: {args.vid}")
        safe_print(f"性别: {'男声' if args.gender == 1 else '女声'}")
        safe_print(f"使用服务: {args.service}")
        if args.url:
            safe_print(f"服务URL: {args.url}")
        
        # 调用生成方法
        result = client.generate_story_audio(
            c_id=args.cid,
            v_id=args.vid,
            gender=gender
        )
        
        safe_print(f"\n[OK] 音频生成成功！")
        safe_print(f"音频文件: {result['audio_path']}")
        if result.get('srt_path'):
            safe_print(f"字幕文件: {result['srt_path']}")
        
    except Exception as e:
        safe_print(f"\n[ERROR] 生成失败: {e}")
        import sys
        sys.exit(1)