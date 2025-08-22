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
        
    def generate(self, text: str, voice: str, pitch: str, volume: str, rate: str) -> dict:
        try:
            if len(text) < 200:
                logger.info(f"文本长度 {len(text)} 字符，使用同步接口...")
                return self._generate_sync(text, voice, pitch, volume, rate)
            else:
                logger.info(f"文本长度 {len(text)} 字符，使用异步接口...")
                return self._generate_async(text, voice, pitch, volume, rate)
        except Exception as e:
            logger.error(f"生成语音失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_sync(self, text: str, voice: str, pitch: str, volume: str, rate: str) -> dict:
        try:
            url = f"{self.base_url}/api/tts/sync"
            payload = {
                'text': text,
                'voice': voice,
                'pitch': pitch,
                'volume': volume,
                'rate': rate
            }
            
            response = self.session.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'audio_data': response.content,
                    'file_size': len(response.content),
                    'voice': voice
                }
            else:
                logger.error(f"HTTP错误状态码: {response.status_code}")
                logger.error(f"响应headers: {response.headers}")
                
                try:
                    error_json = response.json()
                    logger.error(f"错误响应JSON: {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                    error_msg = error_json.get('message', '')
                    if 'errors' in error_json:
                        error_msg = error_json['errors'][0].get('message', error_msg)
                    return {
                        'success': False, 
                        'error': f"同步生成失败 - 状态码: {response.status_code} - 错误信息: {error_msg}"
                    }
                except:
                    pass
                    
                return {
                    'success': False,
                    'error': f"同步生成失败 - 状态码: {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            return {'success': False, 'error': f"网络请求失败: {e}"}
    
    def _generate_async(self, text: str, voice: str, pitch: str, volume: str, rate: str) -> dict:
        try:
            url = f"{self.base_url}/api/tts/async"
            payload = {
                'text': text,
                'voice': voice,
                'pitch': pitch,
                'volume': volume,
                'rate': rate
            }
            
            response = self.session.post(url, json=payload, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"创建任务失败，状态码: {response.status_code}")
                return {'success': False, 'error': f"创建任务失败: {response.status_code}"}
            
            task_data = response.json()
            task_id = task_data.get('taskId')
            
            if not task_id:
                logger.error("未获取到任务ID")
                return {'success': False, 'error': "未获取到任务ID"}
            
            logger.info(f"任务已创建，ID: {task_id}")
            
            status_url = f"{self.base_url}/api/tts/async/{task_id}"
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
                
                status_data = status_response.json()
                status = status_data.get('status')
                
                if status == 'completed':
                    audio_url = status_data.get('result', {}).get('audioUrl')
                    if audio_url:
                        audio_response = self.session.get(audio_url, timeout=30)
                        if audio_response.status_code == 200:
                            return {
                                'success': True,
                                'audio_data': audio_response.content,
                                'file_size': len(audio_response.content),
                                'voice': voice,
                                'duration': status_data.get('result', {}).get('duration'),
                                'subtitle_text': status_data.get('result', {}).get('subtitleText')
                            }
                    
                    audio_data = status_data.get('result', {}).get('audioData')
                    if audio_data:
                        import base64
                        audio_bytes = base64.b64decode(audio_data)
                        return {
                            'success': True,
                            'audio_data': audio_bytes,
                            'file_size': len(audio_bytes),
                            'voice': voice,
                            'duration': status_data.get('result', {}).get('duration'),
                            'subtitle_text': status_data.get('result', {}).get('subtitleText')
                        }
                    
                    logger.error("任务完成但无音频数据")
                    return {'success': False, 'error': "任务完成但无音频数据"}
                    
                elif status == 'failed':
                    error = status_data.get('error', '未知错误')
                    logger.error(f"任务失败: {error}")
                    return {'success': False, 'error': f"任务失败: {error}"}
                
                logger.debug(f"任务状态: {status} (已等待 {waited}秒)")
            
            logger.error(f"任务超时（{max_wait}秒）")
            return {'success': False, 'error': f"任务超时（{max_wait}秒）"}
            
        except Exception as e:
            logger.error(f"异步生成失败: {e}")
            return {'success': False, 'error': f"异步生成失败: {e}"}
    
    def check_status(self) -> str:
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                return "healthy"
            return f"unhealthy (status: {response.status_code})"
        except:
            return "unreachable"
    
    def get_voices(self, language: Optional[str] = None) -> dict:
        try:
            url = f"{self.base_url}/api/voices"
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
            response = self.session.get(f"{self.base_url}/api/v1/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('status', 'unknown')
            return f"unhealthy (status: {response.status_code})"
        except:
            return "unreachable"
    
    def get_voices(self, language: Optional[str] = None) -> dict:
        try:
            url = f"{self.base_url}/api/v1/voices"
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
