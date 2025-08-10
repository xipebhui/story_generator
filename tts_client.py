#!/usr/bin/env python3
"""
TTS (Text-to-Speech) Client Script
用于调用本地TTS服务，将文本转换为MP3音频文件
"""

import requests
import json
import argparse
import sys
from pathlib import Path
from typing import Optional
import time


class TTSClient:
    """TTS客户端类，封装所有TTS相关的参数和请求逻辑"""

    def __init__(self,
                 text: Optional[str] = None,
                 text_file: Optional[str] = None,
                 output_file: str = "output.mp3",
                 voice: str = "en-US-AriaNeural",
                 rate: str = "+25%",
                 pitch: str = "0Hz",
                 volume: str = "0%",
                 api_url: str = "http://localhost:3000/api/v1/tts/generate"):
        """
        初始化TTS客户端

        Args:
            text: 要转换的文本内容
            text_file: 包含文本的文件路径
            output_file: 输出MP3文件的名称
            voice: 语音类型（如 en-US-AriaNeural, zh-CN-XiaoxiaoNeural 等）
            rate: 语速（如 +25% 表示加快25%，-25% 表示减慢25%）
            pitch: 音调（如 +5Hz 表示提高音调，-5Hz 表示降低音调）
            volume: 音量（如 +50% 表示增大音量，-50% 表示减小音量）
            api_url: TTS API的URL地址
        """
        self.text = text
        self.text_file = text_file
        self.output_file = output_file
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.volume = volume
        self.api_url = api_url

    def get_text(self) -> str:
        """获取要转换的文本内容"""
        if self.text:
            return self.text
        elif self.text_file:
            try:
                with open(self.text_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except FileNotFoundError:
                raise FileNotFoundError(f"文件未找到: {self.text_file}")
            except Exception as e:
                raise Exception(f"读取文件失败: {e}")
        else:
            raise ValueError("必须提供文本内容或文本文件路径")

    def create_tts_request(self) -> dict:
        """创建TTS请求的JSON数据"""
        text_content = self.get_text()

        return {
            "text": text_content,
            "voice": self.voice,
            "rate": self.rate,
            "pitch": self.pitch,
            "volume": self.volume
        }

    def send_request(self) -> requests.Response:
        """发送TTS请求"""
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:3000',
            'Referer': 'http://localhost:3000/generate',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }

        # Cookie可选，根据需要可以添加
        cookies = {
            '_locale': 'en-us'
        }

        data = self.create_tts_request()

        print(f"发送TTS请求...")
        print(f"文本长度: {len(data['text'])} 字符")
        print(f"语音: {self.voice}")
        print(f"语速: {self.rate}")
        print(f"音调: {self.pitch}")
        print(f"音量: {self.volume}")

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                cookies=cookies,
                json=data,
                stream=True  # 使用流式下载
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise e

    def save_audio(self, response: requests.Response):
        """保存音频文件"""
        # 确保输出文件以.mp3结尾
        if not self.output_file.endswith('.mp3'):
            self.output_file += '.mp3'

        output_path = Path(self.output_file)

        # 创建输出目录（如果不存在）
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"保存音频到: {output_path}")

        # 流式写入文件
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # 获取文件大小
        file_size = output_path.stat().st_size
        print(f"音频文件已保存: {output_path} (大小: {file_size:,} 字节)")

    def convert(self):
        """执行TTS转换的主方法"""
        try:
            start_time = time.time()

            # 发送请求
            response = self.send_request()

            # 保存音频
            self.save_audio(response)

            elapsed_time = time.time() - start_time
            print(f"转换完成！用时: {elapsed_time:.2f} 秒")

        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(
        description='TTS文本转语音工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 直接指定文本
  python tts_client.py -t "Hello, world!" -o hello.mp3

  # 从文件读取文本
  python tts_client.py -f story.txt -o story.mp3

  # 使用中文语音
  python tts_client.py -t "你好，世界！" -v zh-CN-XiaoxiaoNeural -o chinese.mp3

  # 调整语速和音量
  python tts_client.py -t "Faster speech" -r "+50%" -vol "+20%" -o fast.mp3

常用语音选项:
  英语: en-US-AriaNeural, en-US-JennyNeural, en-US-GuyNeural
  中文: zh-CN-XiaoxiaoNeural, zh-CN-YunxiNeural, zh-CN-YunjianNeural
        """
    )

    # 文本输入参数（二选一）
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-t', '--text',
                             help='要转换的文本内容')
    input_group.add_argument('-f', '--file',
                             help='包含文本的文件路径')

    # 输出参数
    parser.add_argument('-o', '--output',
                        default='output.mp3',
                        help='输出MP3文件名 (默认: output.mp3)')

    # 语音参数
    parser.add_argument('-v', '--voice',
                        default='en-US-AriaNeural',
                        help='语音类型 (默认: en-US-AriaNeural)')

    parser.add_argument('-r', '--rate',
                        default='+25%%',
                        help='语速，如 +25%% 或 -25%% (默认: +25%%)')

    parser.add_argument('-p', '--pitch',
                        default='0Hz',
                        help='音调，如 +5Hz 或 -5Hz (默认: 0Hz)')

    parser.add_argument('-vol', '--volume',
                        default='0%%',
                        help='音量，如 +50%% 或 -50%% (默认: 0%%)')

    # API URL（可选）
    parser.add_argument('--api-url',
                        default='http://localhost:3000/api/v1/tts/generate',
                        help='TTS API URL (默认: http://localhost:3000/api/v1/tts/generate)')

    args = parser.parse_args()

    # 创建TTS客户端
    client = TTSClient(
        text=args.text,
        text_file=args.file,
        output_file=args.output,
        voice=args.voice,
        rate=args.rate,
        pitch=args.pitch,
        volume=args.volume,
        api_url=args.api_url
    )

    # 执行转换
    client.convert()


if __name__ == "__main__":
    main()