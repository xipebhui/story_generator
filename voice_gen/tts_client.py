import requests
import json
import os
import time
import re
import string
import logging
import traceback
from pathlib import Path
from pydub import AudioSegment
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class TTSClient:
    def __init__(self, base_url="https://easyvoice.ioplus.tech"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1/tts"
    
    def generate_speech(self, text, voice="zh-CN-XiaoxiaoNeural", 
                       pitch="0Hz", volume="0%", rate="0%", 
                       use_llm=False, save_path="./downloads"):
        """
        生成语音并下载MP3文件（根据文本长度自动选择同步或异步接口）
        
        Args:
            text: 要转换的文本内容
            voice: 语音类型
            pitch: 音调调整
            volume: 音量调整  
            rate: 语速调整
            use_llm: 是否使用LLM处理文本
            save_path: 保存文件的目录
        
        Returns:
            dict: 包含文件路径等信息的结果
        """
        
        # 检查文本长度，超过200字符使用异步接口
        if len(text) > 200:
            logger.info(f"文本长度 {len(text)} 字符，使用异步接口...")
            return self._generate_speech_async(text, voice, pitch, volume, rate, use_llm, save_path)
        
        # 1. 发送生成请求（同步接口）
        generate_url = f"{self.api_url}/generate"
        payload = {
            "text": text,
            "voice": voice,
            "pitch": pitch,
            "volume": volume,
            "rate": rate
        }
        
        # 只在需要时添加 useLLM 参数
        if use_llm:
            payload["useLLM"] = use_llm
        
        print(f"正在生成语音: {text[:50]}...")
        
        try:
            # 添加必要的请求头
            headers = {
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json',
                'origin': self.base_url,
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
            }
            
            # 发送POST请求生成音频
            response = requests.post(generate_url, json=payload, headers=headers, timeout=60)
            
            # 如果请求失败，打印详细错误信息
            if response.status_code != 200:
                print(f"错误状态码: {response.status_code}")
                print(f"错误响应: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            
            if not result.get('success'):
                raise Exception(f"生成失败: {result.get('message', '未知错误')}")
            
            # 获取文件信息
            data = result['data']
            audio_file = data['file']  # MP3文件名
            srt_file = data.get('srt')  # 字幕文件名（如果有）
            
            print(f"生成成功，音频文件: {audio_file}")
            
            # 2. 下载音频文件
            audio_path = self.download_file(audio_file, save_path)
            
            # 3. 下载字幕文件（如果存在）
            srt_path = None
            if srt_file:
                try:
                    srt_path = self.download_file(srt_file, save_path)
                except Exception as e:
                    print(f"下载字幕文件失败: {e}")
            
            return {
                'success': True,
                'audio_path': audio_path,
                'srt_path': srt_path,
                'text': text,
                'voice': voice
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求失败: {e}")
        except Exception as e:
            raise Exception(f"生成语音失败: {e}")
    
    def download_file(self, filename, save_path="./downloads"):
        """
        下载文件
        
        Args:
            filename: 要下载的文件名
            save_path: 保存目录
        
        Returns:
            str: 保存的文件完整路径
        """
        download_url = f"{self.api_url}/download/{filename}"
        
        # 创建保存目录
        Path(save_path).mkdir(parents=True, exist_ok=True)
        
        # 下载文件
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        # 保存到本地
        file_path = os.path.join(save_path, filename)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"文件已保存到: {file_path}")
        return file_path

    def get_voice_list(self):
        """获取可用语音列表"""
        try:
            response = requests.get(f"{self.api_url}/voiceList")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取语音列表失败: {e}")
            return None

    def get_engines(self):
        """获取可用的TTS引擎"""
        try:
            response = requests.get(f"{self.api_url}/engines")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取引擎列表失败: {e}")
            return None
    
    def _generate_speech_async(self, text, voice, pitch, volume, rate, use_llm, save_path, max_wait=300):
        """
        异步生成语音（用于长文本）
        
        Args:
            text: 要转换的文本内容
            voice: 语音类型
            pitch: 音调调整
            volume: 音量调整
            rate: 语速调整
            use_llm: 是否使用LLM处理文本
            save_path: 保存文件的目录
            max_wait: 最大等待时间（秒）
        
        Returns:
            dict: 包含文件路径等信息的结果
        """
        
        # 处理服务端路径问题：确保文本开头不包含特殊字符
        text = self._prepare_text_for_async_api(text)
        
        # 1. 创建任务
        create_url = f"{self.api_url}/create"
        payload = {
            "text": text,
            "voice": voice,
            "pitch": pitch,
            "volume": volume,
            "rate": rate
        }
        
        if use_llm:
            payload["useLLM"] = use_llm
        
        print(f"正在创建异步任务...")
        
        headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'origin': self.base_url,
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }
        
        response = requests.post(create_url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"创建任务失败: {result.get('message')}")
        
        task_id = result['data']['id']
        print(f"任务已创建，ID: {task_id}")
        
        # 2. 轮询任务状态
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # 检查任务状态
            try:
                status_response = requests.get(f"{self.api_url}/task/{task_id}", headers=headers)
                status_response.raise_for_status()
                
                # 获取完整响应数据
                full_response = status_response.json()
                
                # 检查响应是否成功
                if not full_response.get('success', False):
                    print(f"API响应失败:")
                    print(f"  完整响应: {json.dumps(full_response, ensure_ascii=False, indent=2)}")
                    raise Exception(f"API响应失败: {full_response.get('message', '未知错误')}")
                
                task_data = full_response.get('data', {})
                status = task_data.get('status', 'unknown')
                
                print(f"任务状态: {status}")
                
                if status == 'completed':
                    # 任务完成，下载文件
                    result = task_data['result']
                    audio_file = result['file']
                    srt_file = result.get('srt')
                    
                    audio_path = self.download_file(audio_file, save_path)
                    
                    # 下载字幕文件（如果存在）
                    srt_path = None
                    if srt_file:
                        try:
                            srt_path = self.download_file(srt_file, save_path)
                        except Exception as e:
                            print(f"下载字幕文件失败: {e}")
                    
                    return {
                        'success': True,
                        'audio_path': audio_path,
                        'srt_path': srt_path,
                        'text': text,
                        'voice': voice
                    }
                
                elif status == 'failed':
                    error_info = task_data.get('error', {})
                    error_message = error_info.get('message', '未知错误')
                    # 打印完整的错误信息用于调试
                    print(f"任务失败详情:")
                    print(f"  错误信息: {error_message}")
                    print(f"  完整错误数据: {json.dumps(error_info, ensure_ascii=False, indent=2)}")
                    print(f"  完整任务数据: {json.dumps(task_data, ensure_ascii=False, indent=2)}")
                    raise Exception(f"任务失败: {error_message}")
                
                # 等待2秒后再次检查
                time.sleep(2)
                
            except requests.exceptions.RequestException as e:
                print(f"检查任务状态失败: {e}")
                time.sleep(5)  # 网络错误时等待更长时间
        
        raise Exception(f"任务超时，等待时间超过 {max_wait} 秒")
    
    def _parse_srt_time(self, time_str):
        """
        解析SRT时间格式 (00:00:00,000) 为毫秒
        """
        time_parts = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_str)
        if time_parts:
            hours = int(time_parts.group(1))
            minutes = int(time_parts.group(2))
            seconds = int(time_parts.group(3))
            milliseconds = int(time_parts.group(4))
            total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
            return total_ms
        return 0
    
    def _format_srt_time(self, milliseconds):
        """
        将毫秒转换为SRT时间格式 (00:00:00,000)
        """
        hours = milliseconds // 3600000
        minutes = (milliseconds % 3600000) // 60000
        seconds = (milliseconds % 60000) // 1000
        ms = milliseconds % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"
    
    def generate_speech_with_line_num(self, text, voice, pitch, volume, rate, save_path, line_num, use_llm=False):
        """
        生成语音并使用行号命名文件
        
        Args:
            text: 要转换的文本内容
            voice: 语音类型
            pitch: 音调调整
            volume: 音量调整  
            rate: 语速调整
            save_path: 保存文件的目录
            line_num: 行号
            use_llm: 是否使用LLM处理文本
        
        Returns:
            dict: 包含文件路径等信息的结果
        """
        
        # 如果是英文语音，清理文本
        if 'en-' in voice.lower():
            original_text = text
            text = self._clean_text_for_english_tts(text)
            if original_text != text:
                logger.debug(f"文本已清理 - 行号: {line_num}")
                logger.debug(f"原始文本: {original_text[:100]}...")
                logger.debug(f"清理后文本: {text[:100]}...")
        
        # 检查文本长度，超过200字符使用异步接口
        if len(text) > 200:
            logger.info(f"文本长度 {len(text)} 字符，使用异步接口...")
            return self._generate_speech_async_with_line_num(text, voice, pitch, volume, rate, use_llm, save_path, line_num)
        
        # 1. 发送生成请求（同步接口）
        generate_url = f"{self.api_url}/generate"
        payload = {
            "text": text,
            "voice": voice,
            "pitch": pitch,
            "volume": volume,
            "rate": rate
        }
        
        # 只在需要时添加 useLLM 参数
        if use_llm:
            payload["useLLM"] = use_llm
        
        print(f"正在生成语音: {text[:50]}...")
        
        try:
            # 添加必要的请求头
            headers = {
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json',
                'origin': self.base_url,
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
            }
            
            # 发送POST请求生成音频
            response = requests.post(generate_url, json=payload, headers=headers, timeout=60)
            
            # 如果请求失败，打印详细错误信息
            if response.status_code != 200:
                print(f"错误状态码: {response.status_code}")
                print(f"错误响应: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            
            if not result.get('success'):
                raise Exception(f"生成失败: {result.get('message', '未知错误')}")
            
            # 获取文件信息
            data = result['data']
            audio_file = data['file']  # MP3文件名
            srt_file = data.get('srt')  # 字幕文件名（如果有）
            
            print(f"生成成功，音频文件: {audio_file}")
            
            # 2. 下载音频文件并重命名
            audio_filename = f"line_{line_num:04d}.mp3"
            audio_path = self.download_file_with_rename(audio_file, save_path, audio_filename)
            
            # 3. 下载字幕文件（如果存在）并重命名
            srt_path = None
            if srt_file:
                try:
                    srt_filename = f"line_{line_num:04d}.srt"
                    srt_path = self.download_file_with_rename(srt_file, save_path, srt_filename)
                except Exception as e:
                    print(f"下载字幕文件失败: {e}")
            
            return {
                'success': True,
                'audio_path': audio_path,
                'srt_path': srt_path,
                'text': text,
                'voice': voice
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求失败: {e}")
        except Exception as e:
            raise Exception(f"生成语音失败: {e}")
    
    def _generate_speech_async_with_line_num(self, text, voice, pitch, volume, rate, use_llm, save_path, line_num, max_wait=300):
        """
        异步生成语音并使用行号命名（用于长文本）
        """
        
        # 处理服务端路径问题：确保文本开头不包含特殊字符
        text = self._prepare_text_for_async_api(text)
        
        # 1. 创建任务
        create_url = f"{self.api_url}/create"
        payload = {
            "text": text,
            "voice": voice,
            "pitch": pitch,
            "volume": volume,
            "rate": rate
        }
        
        if use_llm:
            payload["useLLM"] = use_llm
        
        logger.info(f"正在创建异步任务，行号: {line_num}")
        logger.debug(f"请求数据: {json.dumps(payload, ensure_ascii=False)}")
        
        headers = {
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json',
            'origin': self.base_url,
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }
        
        try:
            response = requests.post(create_url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('success'):
                logger.error(f"创建任务失败: {result}")
                raise Exception(f"创建任务失败: {result.get('message')}")
            
            task_id = result['data']['id']
            logger.info(f"任务已创建，ID: {task_id}")
            
        except Exception as e:
            logger.error(f"创建任务异常: {str(e)}")
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
            raise
        
        # 2. 轮询任务状态
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # 检查任务状态
            try:
                status_response = requests.get(f"{self.api_url}/task/{task_id}", headers=headers)
                status_response.raise_for_status()
                
                # 获取完整响应数据
                full_response = status_response.json()
                
                # 检查响应是否成功
                if not full_response.get('success', False):
                    logger.error(f"API响应失败:")
                    logger.error(f"完整响应: {json.dumps(full_response, ensure_ascii=False, indent=2)}")
                    raise Exception(f"API响应失败: {full_response.get('message', '未知错误')}")
                
                task_data = full_response.get('data', {})
                status = task_data.get('status', 'unknown')
                
                logger.debug(f"任务状态: {status}")
                
                if status == 'completed':
                    # 任务完成，下载文件
                    result = task_data['result']
                    audio_file = result['file']
                    srt_file = result.get('srt')
                    
                    # 使用行号命名
                    audio_filename = f"line_{line_num:04d}.mp3"
                    audio_path = self.download_file_with_rename(audio_file, save_path, audio_filename)
                    
                    # 下载字幕文件（如果存在）
                    srt_path = None
                    if srt_file:
                        try:
                            srt_filename = f"line_{line_num:04d}.srt"
                            srt_path = self.download_file_with_rename(srt_file, save_path, srt_filename)
                        except Exception as e:
                            logger.warning(f"下载字幕文件失败: {e}")
                    
                    return {
                        'success': True,
                        'audio_path': audio_path,
                        'srt_path': srt_path,
                        'text': text,
                        'voice': voice
                    }
                
                elif status == 'failed':
                    # 尝试从不同位置获取错误信息
                    error_message = task_data.get('message', '')  # 首先尝试从task_data获取
                    if not error_message:
                        error_info = task_data.get('error', {})
                        error_message = error_info.get('message', '未知错误')
                    
                    # 记录详细错误信息
                    logger.error(f"任务失败 - 文本行号: {line_num}")
                    logger.error(f"文本内容: {text[:100]}...")
                    logger.error(f"错误信息: {error_message}")
                    logger.error(f"完整任务数据: {json.dumps(task_data, ensure_ascii=False, indent=2)}")
                    
                    raise Exception(f"任务失败 (文本行号: {line_num}): {error_message}")
                
                # 等待2秒后再次检查
                time.sleep(2)
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"检查任务状态失败: {e}")
                logger.debug(f"异常堆栈:\n{traceback.format_exc()}")
                time.sleep(5)  # 网络错误时等待更长时间
            except Exception as e:
                logger.error(f"处理任务状态时异常: {str(e)}")
                logger.error(f"异常堆栈:\n{traceback.format_exc()}")
                raise
        
        raise Exception(f"任务超时，等待时间超过 {max_wait} 秒")
    
    def download_file_with_rename(self, filename, save_path, new_filename):
        """
        下载文件并重命名
        
        Args:
            filename: 要下载的文件名
            save_path: 保存目录
            new_filename: 新文件名
        
        Returns:
            str: 保存的文件完整路径
        """
        download_url = f"{self.api_url}/download/{filename}"
        
        # 创建保存目录
        Path(save_path).mkdir(parents=True, exist_ok=True)
        
        # 下载文件
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        
        # 保存到本地（使用新文件名）
        file_path = os.path.join(save_path, new_filename)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"文件已保存到: {file_path}")
        return file_path
    
    def _prepare_text_for_async_api(self, text):
        """
        为异步API准备文本，避免服务端文件路径问题
        
        服务端bug：使用文本开头作为文件夹名，如果包含特殊字符会导致ffmpeg失败
        解决方案：直接清理前10个单词中的所有特殊字符
        """
        import re
        
        # 分割出前10个单词
        words = text.split()
        if not words:
            return text
        
        # 取前10个单词（或更少，如果文本较短）
        first_words = words[:10] if len(words) >= 10 else words
        remaining_text = words[10:] if len(words) > 10 else []
        
        # 定义要替换的特殊字符及其替换值
        replacements = {
            "'": "",  # 撇号直接删除（如 Sera's -> Seras）
            "'": "",  # 智能单引号
            '"': "",  # 双引号删除
            '"': "",  # 左智能双引号
            '"': "",  # 右智能双引号
            '/': " ",  # 斜杠替换为空格
            '\\': " ",  # 反斜杠替换为空格
            ':': "",  # 冒号删除
            '*': "",  # 星号删除
            '?': "",  # 问号删除
            '<': "",  # 小于号删除
            '>': "",  # 大于号删除
            '|': "",  # 管道符删除
            '&': " and ",  # &符号替换为and
            ';': "",  # 分号删除
            '(': "",  # 左括号删除
            ')': "",  # 右括号删除
            '[': "",  # 左方括号删除
            ']': "",  # 右方括号删除
            '{': "",  # 左花括号删除
            '}': "",  # 右花括号删除
            ',': "",  # 逗号删除
            '.': "",  # 句号删除
            '!': "",  # 感叹号删除
            '—': "",  # em dash删除
            '–': "",  # en dash删除
            '…': "",  # 省略号删除
        }
        
        # 清理前10个单词
        cleaned_first_words = []
        modified = False
        
        for word in first_words:
            original_word = word
            cleaned_word = word
            
            # 应用所有替换
            for char, replacement in replacements.items():
                if char in cleaned_word:
                    cleaned_word = cleaned_word.replace(char, replacement)
                    modified = True
            
            # 清理多余的空格
            cleaned_word = ' '.join(cleaned_word.split())
            
            # 如果清理后单词为空，跳过
            if cleaned_word.strip():
                cleaned_first_words.append(cleaned_word)
            elif original_word:  # 如果原单词不为空但清理后为空
                modified = True
        
        if modified:
            logger.info(f"清理了前10个单词中的特殊字符")
            logger.debug(f"原始: {' '.join(first_words[:5])}...")
            logger.debug(f"清理后: {' '.join(cleaned_first_words[:5])}...")
        
        # 重新组合文本
        if remaining_text:
            # 前10个单词被清理，其余保持原样
            result = ' '.join(cleaned_first_words + remaining_text)
        else:
            # 整个文本少于10个单词
            result = ' '.join(cleaned_first_words)
        
        return result
    
    def _clean_text_for_english_tts(self, text):
        """
        清理文本，只保留英文字符和基本标点符号
        使用 ftfy 库智能处理文本编码问题
        """
        try:
            import ftfy
            # 使用 ftfy 自动修复文本编码问题
            # 它会智能地将各种Unicode字符转换为最合适的ASCII等效字符
            cleaned_text = ftfy.fix_text(text)
            
            # ftfy 已经处理了大部分问题，但为了确保万无一失
            # 我们仍然过滤掉任何剩余的非ASCII字符
            cleaned_text = ''.join(char for char in cleaned_text if ord(char) < 128)
            
        except ImportError:
            # 如果 ftfy 未安装，使用备用方案
            logger.warning("ftfy 库未安装，使用备用文本清理方案")
            import unicodedata
            
            # 备用方案：手动替换常见特殊字符
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
    
    def _remove_punctuation(self, text):
        """
        去除文本中的所有标点符号
        """
        # 定义要去除的标点符号（包括中英文标点）
        punctuation = string.punctuation + '，。！？；：""''（）【】《》、…—·'
        # 创建翻译表
        translator = str.maketrans('', '', punctuation)
        # 去除标点符号
        return text.translate(translator)
    
    def _merge_srt_files(self, srt_files, audio_durations, output_path):
        """
        合并多个SRT字幕文件
        
        Args:
            srt_files: SRT文件路径列表
            audio_durations: 对应音频文件的时长列表（毫秒）
            output_path: 输出的合并SRT文件路径
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
                            
                            # 处理文本：去除标点符号
                            cleaned_text_lines = []
                            for text_line in text_lines:
                                cleaned_text = self._remove_punctuation(text_line)
                                if cleaned_text.strip():  # 只保留非空行
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
            print(f"字幕文件已合并: {output_path}")
            return output_path
        
        return None
    
    def generate_story_audio(self, c_id, v_id, gender):
        """
        读取故事文件并生成完整音频
        
        Args:
            c_id: creator_id
            v_id: voice_id
            gender: 性别 ('male' 或 'female')
        
        Returns:
            dict: 包含音频和字幕文件路径
        """
        # 构建故事文件路径
        story_path = f"./story_result/{c_id}/{v_id}/final/story.txt"
        
        # 检查文件是否存在
        if not os.path.exists(story_path):
            raise Exception(f"故事文件不存在: {story_path}")
        
        # 选择语音
        voice = "en-US-BrianNeural" if gender == "male" else "en-US-AvaNeural"
        
        # 创建临时目录（使用cid和vid作为子目录，避免多任务冲突）
        tmp_dir = f"./output/tmp/{c_id}_{v_id}"
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        
        # 读取故事文件
        with open(story_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        logger.info(f"开始生成音频，共 {len(lines)} 行")
        
        # 检查已存在的文件，支持断点续传
        audio_files = []
        srt_files = []
        audio_durations = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line:  # 跳过空行
                # 使用行号作为文件名
                line_num = i + 1
                audio_filename = f"line_{line_num:04d}.mp3"
                srt_filename = f"line_{line_num:04d}.srt"
                audio_path = os.path.join(tmp_dir, audio_filename)
                srt_path = os.path.join(tmp_dir, srt_filename)
                
                # 检查文件是否已存在（支持断点续传）
                if os.path.exists(audio_path):
                    logger.debug(f"第 {line_num}/{len(lines)} 行已存在，跳过...")
                    audio_files.append(audio_path)
                    if os.path.exists(srt_path):
                        srt_files.append(srt_path)
                    else:
                        srt_files.append(None)
                else:
                    logger.info(f"正在处理第 {line_num}/{len(lines)} 行...")
                    
                    # 生成语音，但先保存到临时文件
                    result = self.generate_speech_with_line_num(
                        text=line,
                        voice=voice,
                        pitch="0Hz",
                        volume="0%", 
                        rate="0%",
                        save_path=tmp_dir,
                        line_num=line_num
                    )
                    
                    if result['success']:
                        audio_files.append(result['audio_path'])
                        # 收集SRT文件路径
                        if result.get('srt_path'):
                            srt_files.append(result['srt_path'])
                        else:
                            srt_files.append(None)
        
        # 合并音频文件
        if not audio_files:
            raise Exception("没有生成任何音频文件")
        
        print("开始合并音频文件...")
        combined = AudioSegment.empty()
        
        for audio_file in audio_files:
            audio = AudioSegment.from_mp3(audio_file)
            audio_durations.append(len(audio))  # 记录每个音频的时长（毫秒）
            combined += audio
        
        # 保存合并后的音频
        output_path = f"./output/{c_id}_{v_id}_story.mp3"
        combined.export(output_path, format="mp3")
        
        print(f"音频合并完成: {output_path}")
        
        # 合并字幕文件
        srt_output_path = None
        if any(srt_files):
            srt_output_path = f"./output/{c_id}_{v_id}_story.srt"
            self._merge_srt_files(srt_files, audio_durations, srt_output_path)
        
        # 清理临时文件
        for file in Path(tmp_dir).glob("*.mp3"):
            file.unlink()
        for file in Path(tmp_dir).glob("*.srt"):
            file.unlink()
        
        return {
            'audio_path': output_path,
            'srt_path': srt_output_path
        }

# 使用示例
if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='生成故事音频')
    parser.add_argument('--cid', type=str, required=True, help='Creator ID')
    parser.add_argument('--vid', type=str, required=True, help='Voice ID')
    parser.add_argument('--gender', type=int, required=True, choices=[0, 1], 
                       help='性别: 0=女声, 1=男声')
    
    # 解析参数
    args = parser.parse_args()
    
    # 转换性别参数
    gender = "male" if args.gender == 1 else "female"
    
    # 创建客户端实例
    client = TTSClient("http://localhost:3000")
    
    try:
        print(f"开始生成故事音频...")
        print(f"Creator ID: {args.cid}")
        print(f"Voice ID: {args.vid}")
        print(f"性别: {'男声' if args.gender == 1 else '女声'}")
        
        # 调用生成方法
        result = client.generate_story_audio(
            c_id=args.cid,
            v_id=args.vid,
            gender=gender
        )
        
        print(f"\n✅ 音频生成成功！")
        print(f"音频文件: {result['audio_path']}")
        if result.get('srt_path'):
            print(f"字幕文件: {result['srt_path']}")
        
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")