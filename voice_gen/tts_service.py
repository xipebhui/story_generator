#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS服务层
"""

import os
import json
import time
import requests
from typing import Optional, Dict, Literal
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class TTSServiceInterface(ABC):
    """TTS服务接口"""
    
    @abstractmethod
    def generate(self, text: str, voice: str, pitch: str, volume: str, rate: str) -> dict:
        pass
    
    @abstractmethod
    def check_status(self) -> str:
        pass
    
    @abstractmethod
    def get_voices(self, language: Optional[str] = None) -> dict:
        pass


class OldTTSService(TTSServiceInterface):
    """旧版TTS服务"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get('TTS_OLD_URL', 'http://localhost:3000')
        self.session = requests.Session()
        
    def generate(self, text: str, voice: str, pitch: str, volume: str, rate: str, force_async: bool = False) -> dict:
        """
        生成语音
        
        Args:
            text: 要转换的文本
            voice: 语音类型
            pitch: 音调
            volume: 音量
            rate: 语速
            force_async: 是否强制使用异步接口（批量处理时推荐设为True）
        """
        try:
            # 批量处理时应该强制使用异步接口，避免同步接口的限制
            if force_async or len(text) >= 200:
                logger.info(f"文本长度 {len(text)} 字符，使用异步接口...")
                return self._generate_async(text, voice, pitch, volume, rate)
            else:
                logger.info(f"文本长度 {len(text)} 字符，使用同步接口...")
                return self._generate_sync(text, voice, pitch, volume, rate)
        except Exception as e:
            logger.error(f"生成语音失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_sync(self, text: str, voice: str, pitch: str, volume: str, rate: str) -> dict:
        try:
            url = f"{self.base_url}/api/v1/tts/generate"
            payload = {
                'text': text,
                'voice': voice,
                'pitch': pitch,
                'volume': volume,
                'rate': rate
            }
            
            response = self.session.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                # 根据EasyVoice文档，同步接口返回JSON格式
                try:
                    result = response.json()
                    if result.get('success'):
                        # 获取音频文件路径
                        audio_file = result.get('data', {}).get('audio')
                        if audio_file:
                            # 下载音频文件
                            download_url = f"{self.base_url}/api/v1/tts/download/{audio_file.split('/')[-1]}"
                            audio_response = self.session.get(download_url, timeout=30)
                            if audio_response.status_code == 200:
                                return {
                                    'success': True,
                                    'audio_data': audio_response.content,
                                    'file_size': len(audio_response.content),
                                    'voice': voice,
                                    'file': result.get('data', {}).get('file'),
                                    'srt': result.get('data', {}).get('srt')
                                }
                        # 如果没有文件路径，尝试其他方式
                        return {
                            'success': True,
                            'data': result.get('data', {}),
                            'voice': voice
                        }
                    else:
                        return {
                            'success': False,
                            'error': result.get('message', '同步生成失败')
                        }
                except json.JSONDecodeError as e:
                    logger.error(f"解析响应失败: {e}")
                    logger.error(f"响应内容: {response.text[:500]}")
                    return {'success': False, 'error': '响应格式错误'}
            else:
                logger.error(f"HTTP错误状态码: {response.status_code}")
                logger.error(f"响应headers: {response.headers}")
                
                try:
                    error_body = response.text
                    logger.error(f"响应内容: {error_body}")
                    error_json = response.json()
                    logger.error(f"错误响应JSON: {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                    error_msg = error_json.get('message', '')
                    if 'errors' in error_json:
                        error_msg = error_json['errors'][0].get('message', error_msg)
                    return {
                        'success': False, 
                        'error': f"同步生成失败 - 状态码: {response.status_code} - 错误信息: {error_msg}"
                    }
                except Exception as parse_error:
                    logger.error(f"解析错误响应失败: {parse_error}")
                    logger.error(f"原始响应: {response.text[:1000]}")
                    
                return {
                    'success': False,
                    'error': f"同步生成失败 - 状态码: {response.status_code}"
                }
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接失败: {e}")
            logger.error(f"TTS服务URL: {self.base_url}")
            logger.error("请检查TTS服务是否启动")
            import traceback
            logger.error(f"完整错误栈:\n{traceback.format_exc()}")
            return {'success': False, 'error': f"连接TTS服务失败: {self.base_url}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            logger.error(f"请求URL: {url}")
            import traceback
            logger.error(f"完整错误栈:\n{traceback.format_exc()}")
            return {'success': False, 'error': f"网络请求失败: {e}"}
    
    def _generate_async(self, text: str, voice: str, pitch: str, volume: str, rate: str) -> dict:
        try:
            url = f"{self.base_url}/api/v1/tts/create"
            payload = {
                'text': text,
                'voice': voice,
                'pitch': pitch,
                'volume': volume,
                'rate': rate
            }
            
            logger.debug(f"请求URL: {url}")
            logger.debug(f"请求负载: {json.dumps(payload, ensure_ascii=False)[:500]}...")  # 只显示前500字符
            
            response = self.session.post(url, json=payload, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"创建任务失败，状态码: {response.status_code}")
                logger.error(f"响应headers: {dict(response.headers)}")
                try:
                    error_body = response.text
                    logger.error(f"响应内容: {error_body}")
                    # 尝试解析JSON错误
                    if error_body:
                        try:
                            error_json = response.json()
                            logger.error(f"错误JSON: {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                        except:
                            pass
                except Exception as parse_error:
                    logger.error(f"解析响应失败: {parse_error}")
                
                return {'success': False, 'error': f"创建任务失败: 状态码={response.status_code}, URL={url}"}
            
            try:
                task_data = response.json()
                logger.debug(f"创建任务响应: {json.dumps(task_data, indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                logger.error(f"响应内容: {response.text}")
                return {'success': False, 'error': f"响应解析失败: {response.text[:500]}"}
            
            # 尝试不同的字段名
            task_id = task_data.get('taskId') or task_data.get('data', {}).get('id')
            
            if not task_id:
                logger.error(f"未获取到任务ID，响应数据: {task_data}")
                return {'success': False, 'error': "未获取到任务ID"}
            
            logger.info(f"任务已创建，ID: {task_id}")
            
            status_url = f"{self.base_url}/api/v1/tts/task/{task_id}"
            max_wait = 120
            poll_interval = 2
            waited = 0
            
            while waited < max_wait:
                time.sleep(poll_interval)
                waited += poll_interval
                
                status_response = self.session.get(status_url, timeout=10)
                
                if status_response.status_code != 200:
                    logger.warning(f"获取任务状态失败: {status_response.status_code}")
                    continue
                
                try:
                    status_data = status_response.json()
                except json.JSONDecodeError:
                    logger.warning(f"状态响应不是JSON: {status_response.text[:200]}")
                    continue
                    
                # 根据EasyVoice文档，任务状态在 data.status 中
                task_info = status_data.get('data', {})
                status = task_info.get('status')
                
                logger.debug(f"任务状态: {status}, 任务信息: {json.dumps(task_info, ensure_ascii=False)[:500]}")
                
                if status == 'completed':
                    # 获取结果数据
                    result = task_info.get('result', {})
                    
                    # 尝试获取音频文件名并下载
                    audio_file = result.get('audio') or result.get('file')
                    if audio_file:
                        # 提取文件名
                        filename = audio_file.split('/')[-1] if '/' in audio_file else audio_file
                        download_url = f"{self.base_url}/api/v1/tts/download/{filename}"
                        logger.info(f"下载音频: {download_url}")
                        
                        audio_response = self.session.get(download_url, timeout=30)
                        if audio_response.status_code == 200:
                            return {
                                'success': True,
                                'audio_data': audio_response.content,
                                'file_size': len(audio_response.content),
                                'voice': voice,
                                'duration': result.get('duration'),
                                'subtitle_text': result.get('subtitleText'),
                                'srt': result.get('srt')
                            }
                        else:
                            logger.error(f"下载音频失败: {audio_response.status_code}")
                    
                    # 尝试其他可能的音频数据字段
                    audio_url = result.get('audioUrl')
                    if audio_url:
                        audio_response = self.session.get(audio_url, timeout=30)
                        if audio_response.status_code == 200:
                            return {
                                'success': True,
                                'audio_data': audio_response.content,
                                'file_size': len(audio_response.content),
                                'voice': voice,
                                'duration': result.get('duration'),
                                'subtitle_text': result.get('subtitleText')
                            }
                    
                    audio_data = result.get('audioData')
                    if audio_data:
                        import base64
                        audio_bytes = base64.b64decode(audio_data)
                        return {
                            'success': True,
                            'audio_data': audio_bytes,
                            'file_size': len(audio_bytes),
                            'voice': voice,
                            'duration': result.get('duration'),
                            'subtitle_text': result.get('subtitleText')
                        }
                    
                    logger.error(f"任务完成但无音频数据，结果: {json.dumps(result, ensure_ascii=False)[:500]}")
                    return {'success': False, 'error': "任务完成但无音频数据"}
                    
                elif status == 'failed':
                    error = status_data.get('error', '未知错误')
                    logger.error(f"任务失败: {error}")
                    return {'success': False, 'error': f"任务失败: {error}"}
                
                logger.debug(f"任务状态: {status} (已等待 {waited}秒)")
            
            logger.error(f"任务超时（{max_wait}秒）")
            return {'success': False, 'error': f"任务超时（{max_wait}秒）"}
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"连接失败: {e}")
            logger.error(f"TTS服务URL: {self.base_url}")
            logger.error("请检查TTS服务是否启动")
            import traceback
            logger.error(f"完整错误栈:\n{traceback.format_exc()}")
            return {'success': False, 'error': f"连接TTS服务失败: {self.base_url}"}
        except requests.exceptions.Timeout as e:
            logger.error(f"请求超时: {e}")
            logger.error(f"TTS服务URL: {self.base_url}")
            import traceback
            logger.error(f"完整错误栈:\n{traceback.format_exc()}")
            return {'success': False, 'error': f"请求TTS服务超时"}
        except Exception as e:
            logger.error(f"异步生成失败: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"完整错误栈:\n{traceback.format_exc()}")
            return {'success': False, 'error': f"异步生成失败: {e}"}
    
    def check_status(self) -> str:
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                return "healthy"
            return f"unhealthy (status: {response.status_code})"
        except:
            return "unreachable"
    
    def get_voices(self, language: Optional[str] = None) -> dict:
        try:
            url = f"{self.base_url}/api/v1/tts/voiceList"
            if language:
                url += f"?lang={language}"
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {'success': False, 'error': f"Status: {response.status_code}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class NewTTSService(TTSServiceInterface):
    """新版TTS服务"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get('TTS_NEW_URL', 'http://localhost:3031')
        self.session = requests.Session()
        
    def generate(self, text: str, voice: str, pitch: str, volume: str, rate: str) -> dict:
        try:
            url = f"{self.base_url}/api/v1/tts/generate"
            payload = {
                'text': text,
                'voice': voice,
                'pitch': pitch,
                'volume': volume,
                'rate': rate
            }
            
            response = self.session.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    import base64
                    audio_data = base64.b64decode(result['audioData'])
                    
                    return {
                        'success': True,
                        'audio_data': audio_data,
                        'file_size': len(audio_data),
                        'voice': result.get('voice', voice),
                        'duration': result.get('duration'),
                        'subtitle_text': result.get('subtitleText')
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('error', '生成失败')
                    }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"新版服务生成失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_status(self) -> str:
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('status', 'unknown')
            return f"unhealthy (status: {response.status_code})"
        except:
            return "unreachable"
    
    def get_voices(self, language: Optional[str] = None) -> dict:
        try:
            url = f"{self.base_url}/api/v1/tts/voiceList"
            params = {'language': language} if language else {}
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {'success': False, 'error': f"Status: {response.status_code}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class TTSServiceFactory:
    """TTS服务工厂"""
    
    @staticmethod
    def create_service(
        service_type: Literal["old", "new"] = "old",
        base_url: Optional[str] = None
    ) -> TTSServiceInterface:
        if service_type == "new":
            return NewTTSService(base_url)
        else:
            return OldTTSService(base_url)
