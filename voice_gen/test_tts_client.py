#!/usr/bin/env python3
"""
TTS公开API客户端测试
测试TTS生成语音接口的完整功能
"""

import requests
import json
import base64
from pathlib import Path
import time
from typing import Optional, Dict, Any
import sys

class TTSClient:
    """TTS公开API客户端"""
    
    def __init__(self, base_url: str = 'http://localhost:18765/api/v1'):
        """
        初始化TTS客户端
        
        Args:
            base_url: API基础URL
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json; charset=utf-8'
        })
    
    def generate_tts(
        self,
        text: str,
        language: str = 'zh',
        voice: Optional[str] = None,
        rate: str = '+0%',
        pitch: str = '+0Hz',
        volume: str = '+0%',
        save_audio: Optional[str] = None,
        save_subtitle: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成TTS音频和字幕
        
        Args:
            text: 要转换的文本
            language: 语言代码 (zh/en/ja)
            voice: 指定语音，如 zh-CN-XiaoxiaoNeural
            rate: 语速 (-100% 到 +100%)
            pitch: 音调 (-100Hz 到 +100Hz)
            volume: 音量 (-100% 到 +100%)
            save_audio: 音频保存路径
            save_subtitle: 字幕保存路径
            
        Returns:
            包含音频数据、字幕、时长等信息的字典
        """
        url = f'{self.base_url}/tts-public/generate'
        
        # 构建请求payload
        payload = {
            'text': text,
            'language': language,
            'config': {
                'rate': rate,
                'pitch': pitch,
                'volume': volume
            }
        }
        
        # 如果指定了语音，添加到config中
        if voice:
            payload['config']['voice'] = voice
        
        print(f"🎤 正在生成语音...")
        print(f"   文本: {text[:50]}..." if len(text) > 50 else f"   文本: {text}")
        print(f"   语言: {language}")
        if voice:
            print(f"   语音: {voice}")
        print(f"   参数: 语速={rate}, 音调={pitch}, 音量={volume}")
        
        try:
            # 发送请求
            start_time = time.time()
            response = self.session.post(url, json=payload, timeout=30)
            elapsed_time = time.time() - start_time
            
            # 检查响应状态
            response.raise_for_status()
            result = response.json()
            
            if not result.get('success'):
                raise Exception(f"API返回错误: {result.get('error', '未知错误')}")
            
            data = result['data']
            
            # 解析音频数据
            audio_base64 = data['audio_base64']
            if not audio_base64.startswith('data:audio/mp3;base64,'):
                raise ValueError("音频数据格式错误")
            
            # 提取Base64数据部分
            audio_data = base64.b64decode(audio_base64.split(',')[1])
            
            print(f"✅ 语音生成成功!")
            print(f"   音频时长: {data['duration']:.2f}秒")
            print(f"   文件大小: {data['file_size']:,} 字节")
            print(f"   使用语音: {data['voice']}")
            print(f"   响应时间: {elapsed_time:.2f}秒")
            
            # 保存音频文件
            if save_audio:
                Path(save_audio).write_bytes(audio_data)
                print(f"   💾 音频已保存: {save_audio}")
            
            # 保存字幕文件
            if save_subtitle:
                Path(save_subtitle).write_text(
                    data['subtitle_text'],
                    encoding='utf-8'
                )
                print(f"   📝 字幕已保存: {save_subtitle}")
            
            return {
                'success': True,
                'audio_data': audio_data,
                'subtitle_text': data['subtitle_text'],
                'duration': data['duration'],
                'file_size': data['file_size'],
                'voice': data['voice']
            }
            
        except requests.exceptions.Timeout:
            raise Exception("请求超时，请稍后重试")
        except requests.exceptions.ConnectionError:
            raise Exception(f"无法连接到服务器: {self.base_url}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP错误: {e}")
        except Exception as e:
            raise Exception(f"生成失败: {str(e)}")
    
    def get_voices(self, language: Optional[str] = None) -> Dict[str, Any]:
        """
        获取可用语音列表
        
        Args:
            language: 语言代码，如果不指定则返回所有语言的语音
            
        Returns:
            语音列表
        """
        url = f'{self.base_url}/tts-public/voices'
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            voices_data = result.get('data', {})
            
            if language:
                return voices_data.get(language, [])
            return voices_data
            
        except Exception as e:
            raise Exception(f"获取语音列表失败: {str(e)}")
    
    def check_status(self) -> str:
        """
        检查TTS服务状态
        
        Returns:
            服务状态 (healthy/unhealthy/unknown)
        """
        url = f'{self.base_url}/tts-public/status'
        
        try:
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            result = response.json()
            return result['data']['service_status']
        except:
            return 'unknown'


def run_comprehensive_test():
    """运行综合测试用例"""
    
    print("=" * 60)
    print("TTS公开API客户端测试")
    print("=" * 60)
    
    # 创建客户端
    client = TTSClient()
    
    # 测试1: 检查服务状态
    print("\n📊 测试1: 检查服务状态")
    print("-" * 40)
    try:
        status = client.check_status()
        print(f"服务状态: {status}")
        if status != 'healthy':
            print("⚠️  警告: 服务状态异常")
    except Exception as e:
        print(f"❌ 错误: {e}")
        return
    
    # 测试2: 获取语音列表
    print("\n📋 测试2: 获取可用语音列表")
    print("-" * 40)
    try:
        all_voices = client.get_voices()
        for lang, voices in all_voices.items():
            print(f"\n{lang} 语言 ({len(voices)} 个语音):")
            for voice in voices[:3]:  # 只显示前3个
                gender = voice.get('gender', 'unknown')
                print(f"  • {voice['label']} ({voice['value']}) - {gender}")
                if voice.get('description'):
                    print(f"    {voice['description']}")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    # 测试3: 中文语音生成
    print("\n🇨🇳 测试3: 中文语音生成")
    print("-" * 40)
    test_cases = [
        {
            'text': '你好，欢迎使用语音合成服务。这是一个测试。',
            'language': 'zh',
            'voice': 'zh-CN-XiaoxiaoNeural',
            'rate': '+0%',
            'pitch': '+0Hz',
            'volume': '+0%',
            'save_audio': 'test_zh_xiaoxiao.mp3',
            'save_subtitle': 'test_zh_xiaoxiao.srt'
        },
        {
            'text': '今天天气真好，适合出去散步。',
            'language': 'zh',
            'voice': 'zh-CN-YunxiNeural',
            'rate': '+20%',  # 加快语速
            'pitch': '-10Hz',  # 降低音调
            'volume': '+10%',  # 增加音量
            'save_audio': 'test_zh_yunxi.mp3',
            'save_subtitle': 'test_zh_yunxi.srt'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 3.{i}:")
        try:
            result = client.generate_tts(**test_case)
            print(f"  ✅ 测试通过")
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
    
    # 测试4: 英文语音生成
    print("\n🇺🇸 测试4: 英文语音生成")
    print("-" * 40)
    try:
        result = client.generate_tts(
            text="Hello! Welcome to the Text-to-Speech service. This is a test message.",
            language='en',
            voice='en-US-JennyNeural',
            save_audio='test_en_jenny.mp3',
            save_subtitle='test_en_jenny.srt'
        )
        print("  ✅ 测试通过")
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
    
    # 测试5: 日文语音生成
    print("\n🇯🇵 测试5: 日文语音生成")
    print("-" * 40)
    try:
        result = client.generate_tts(
            text="こんにちは。音声合成サービスへようこそ。",
            language='ja',
            voice='ja-JP-NanamiNeural',
            save_audio='test_ja_nanami.mp3',
            save_subtitle='test_ja_nanami.srt'
        )
        print("  ✅ 测试通过")
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
    
    # 测试6: 长文本测试
    print("\n📝 测试6: 长文本生成测试")
    print("-" * 40)
    long_text = """
    人工智能正在改变我们的生活方式。从智能手机的语音助手，到自动驾驶汽车，
    再到医疗诊断系统，AI技术已经渗透到生活的方方面面。未来，随着技术的不断进步，
    我们将看到更多创新的应用场景。然而，在享受技术带来便利的同时，
    我们也需要关注隐私保护、伦理道德等重要议题。
    """
    try:
        result = client.generate_tts(
            text=long_text.strip(),
            language='zh',
            voice='zh-CN-XiaoxiaoNeural',
            rate='+10%',
            save_audio='test_long_text.mp3',
            save_subtitle='test_long_text.srt'
        )
        print("  ✅ 测试通过")
        
        # 显示字幕内容预览
        print("\n  字幕预览:")
        subtitle_lines = result['subtitle_text'].split('\n')
        for line in subtitle_lines[:12]:  # 显示前12行
            if line.strip():
                print(f"    {line}")
        if len(subtitle_lines) > 12:
            print(f"    ... (共 {len(subtitle_lines)} 行)")
            
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
    
    # 测试7: 错误处理测试
    print("\n⚠️  测试7: 错误处理测试")
    print("-" * 40)
    
    # 测试无效语言
    print("测试无效语言代码:")
    try:
        result = client.generate_tts(
            text="Test",
            language='invalid_lang'
        )
        print("  ❌ 应该抛出错误但没有")
    except Exception as e:
        print(f"  ✅ 正确捕获错误: {e}")
    
    # 测试空文本
    print("\n测试空文本:")
    try:
        result = client.generate_tts(
            text="",
            language='zh'
        )
        print("  ❌ 应该抛出错误但没有")
    except Exception as e:
        print(f"  ✅ 正确捕获错误: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    
    # 列出生成的文件
    print("\n📁 生成的文件:")
    from pathlib import Path
    audio_files = list(Path('.').glob('test_*.mp3'))
    subtitle_files = list(Path('.').glob('test_*.srt'))
    
    if audio_files:
        print("\n音频文件:")
        for f in audio_files:
            size = f.stat().st_size
            print(f"  • {f.name} ({size:,} 字节)")
    
    if subtitle_files:
        print("\n字幕文件:")
        for f in subtitle_files:
            print(f"  • {f.name}")


def run_simple_test():
    """运行简单测试用例"""
    
    print("TTS API 简单测试")
    print("-" * 40)
    
    client = TTSClient()
    
    # 简单的中文测试
    try:
        result = client.generate_tts(
            text="你好，这是一个简单的测试。",
            language='zh',
            save_audio='simple_test.mp3',
            save_subtitle='simple_test.srt'
        )
        
        print(f"\n✅ 测试成功!")
        print(f"音频文件: simple_test.mp3")
        print(f"字幕文件: simple_test.srt")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='TTS公开API客户端测试')
    parser.add_argument(
        '--simple',
        action='store_true',
        help='运行简单测试'
    )
    parser.add_argument(
        '--text',
        type=str,
        help='指定要转换的文本'
    )
    parser.add_argument(
        '--lang',
        type=str,
        default='zh',
        choices=['zh', 'en', 'ja'],
        help='语言代码'
    )
    parser.add_argument(
        '--voice',
        type=str,
        help='指定语音'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='output',
        help='输出文件名前缀（不含扩展名）'
    )
    
    args = parser.parse_args()
    
    if args.text:
        # 自定义文本测试
        client = TTSClient()
        try:
            result = client.generate_tts(
                text=args.text,
                language=args.lang,
                voice=args.voice,
                save_audio=f'{args.output}.mp3',
                save_subtitle=f'{args.output}.srt'
            )
            print(f"\n✅ 生成成功!")
            print(f"音频: {args.output}.mp3")
            print(f"字幕: {args.output}.srt")
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            sys.exit(1)
    elif args.simple:
        run_simple_test()
    else:
        run_comprehensive_test()