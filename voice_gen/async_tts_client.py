import requests
import json
import os
import time
from pathlib import Path

class AsyncTTSClient:
    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1/tts"
    
    def generate_speech_async(self, text, voice="zh-CN-XiaoxiaoNeural", 
                             pitch="+0Hz", volume="+0%", rate="+0%",
                             use_llm=False, save_path="./downloads", max_wait=300):
        """
        异步生成语音（适用于长文本）
        
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
        
        # 1. 创建任务
        create_url = f"{self.api_url}/create" 
        payload = {
            "text": text,
            "voice": voice,
            "pitch": pitch,
            "volume": volume,
            "rate": rate,
            "useLLM": use_llm
        }
        
        print(f"正在创建异步任务: {text[:50]}...")
        
        response = requests.post(create_url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if not result.get('success'):
            raise Exception(f"创建任务失败: {result.get('message')}")
        
        task_id = result['data']['id']
        print(f"任务已创建，ID: {task_id}")
        
        # 2. 轮询任务状态并下载文件
        return self.wait_for_task(task_id, save_path, max_wait)
    
    def generate_batch_speech(self, voice_data, save_path="./downloads", max_wait=600):
        """
        批量生成语音（多个不同语音片段合成一个文件）
        这是一个流式接口，适合处理多角色对话或长文本
        
        Args:
            voice_data: 语音数据数组，格式如：
            [
                {
                    "desc": "角色描述",
                    "text": "要转换的文本",
                    "voice": "语音类型",
                    "rate": "语速调整（可选）",
                    "pitch": "音调调整（可选）",
                    "volume": "音量调整（可选）"
                },
                ...
            ]
            save_path: 保存文件的目录
            max_wait: 最大等待时间（秒）
            
        Returns:
            str: 生成的音频文件路径
        """
        
        # 创建保存目录
        Path(save_path).mkdir(parents=True, exist_ok=True)
        
        # 生成输出文件名
        timestamp = int(time.time())
        output_filename = f"batch_audio_{timestamp}.mp3"
        output_path = os.path.join(save_path, output_filename)
        
        # 调用批量生成接口
        generate_url = f"{self.api_url}/generateJson"
        payload = {"data": voice_data}
        
        print(f"正在批量生成语音，共 {len(voice_data)} 个片段...")
        print("这是一个流式接口，可能需要较长时间...")
        
        try:
            # 流式下载
            response = requests.post(generate_url, json=payload, stream=True, timeout=max_wait)
            response.raise_for_status()
            
            # 检查响应类型
            content_type = response.headers.get('content-type', '')
            if 'audio' in content_type:
                # 直接返回音频流
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                print(f"批量语音生成成功，文件保存到: {output_path}")
                return output_path
            else:
                # 可能返回的是JSON响应（错误或任务ID）
                response_text = response.text
                try:
                    result = json.loads(response_text)
                    if result.get('success'):
                        print("任务创建成功，等待完成...")
                        # 这里可以实现任务状态轮询逻辑
                        return self._handle_batch_task_response(result, save_path, max_wait)
                    else:
                        raise Exception(f"批量生成失败: {result.get('message', '未知错误')}")
                except json.JSONDecodeError:
                    raise Exception(f"响应解析失败: {response_text}")
                    
        except requests.exceptions.RequestException as e:
            raise Exception(f"请求失败: {e}")
        except Exception as e:
            raise Exception(f"批量生成语音失败: {e}")
    
    def _handle_batch_task_response(self, result, save_path, max_wait):
        """处理批量任务的响应（如果返回的是任务ID而不是直接的音频流）"""
        # 这里可以根据实际API响应格式来实现
        # 目前假设直接返回音频流
        pass
    
    def wait_for_task(self, task_id, save_path="./downloads", max_wait=300):
        """
        等待任务完成并下载文件
        
        Args:
            task_id: 任务ID
            save_path: 保存目录
            max_wait: 最大等待时间（秒）
        
        Returns:
            dict: 包含文件路径等信息的结果
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # 检查任务状态
            try:
                status_response = requests.get(f"{self.api_url}/task/{task_id}")
                status_response.raise_for_status()
                
                task_data = status_response.json()['data']
                status = task_data['status']
                
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
                        'task_id': task_id
                    }
                
                elif status == 'failed':
                    error_info = task_data.get('error', {})
                    error_message = error_info.get('message', '未知错误')
                    raise Exception(f"任务失败: {error_message}")
                
                # 等待2秒后再次检查
                time.sleep(2)
                
            except requests.exceptions.RequestException as e:
                print(f"检查任务状态失败: {e}")
                time.sleep(5)  # 网络错误时等待更长时间
        
        raise Exception(f"任务超时，等待时间超过 {max_wait} 秒")
    
    def download_file(self, filename, save_path="./downloads"):
        """下载文件"""
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

    def get_task_stats(self):
        """获取任务统计信息"""
        try:
            response = requests.get(f"{self.api_url}/task/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取任务统计失败: {e}")
            return None

# 使用示例
if __name__ == "__main__":
    # 创建异步客户端实例
    client = AsyncTTSClient("http://localhost:3000")
    
    try:
        print("=== 异步TTS客户端测试 ===")
        
        # 示例1: 长文本异步生成
        print("\n1. 长文本异步生成测试...")
        long_text = """
        这是一段比较长的文本，用来测试异步语音生成功能。
        异步生成适合处理较长的文本内容，可以避免请求超时的问题。
        在实际使用中，如果文本内容超过200个字符，建议使用异步接口。
        异步接口会创建一个后台任务，然后定期检查任务状态，直到生成完成。
        """.strip()
        
        result = client.generate_speech_async(
            text=long_text,
            voice="zh-CN-XiaoxiaoNeural",
            rate="+5%",
            save_path="./output"
        )
        print("长文本异步生成成功:", result)
        
        # 示例2: 批量多角色语音生成（官方示例）
        print("\n2. 批量多角色语音生成测试...")
        voice_data = [
            {
                "desc": "徐凤年",
                "text": "你敢动他，我会穷尽一生毁掉卢家，说到做到",
                "voice": "zh-CN-YunjianNeural",
                "volume": "40%"
            },
            {
                "desc": "姜泥", 
                "text": "徐凤年，你快走，你打不过的",
                "voice": "zh-CN-XiaoyiNeural"
            },
            {
                "desc": "路人甲",
                "text": "他可是堂堂棠溪剑仙，这小子真是遇到强敌了",
                "voice": "zh-CN-XiaoniNeural",
                "volume": "-20%"
            },
            {
                "desc": "路人乙",
                "text": "这小子真是不知死活，竟然敢挑战卢白撷",
                "voice": "zh-TW-HsiaoChenNeural",
                "volume": "-20%"
            },
            {
                "desc": "旁白",
                "text": "面对棠溪剑仙卢白撷的杀意，徐凤年按住剑柄蓄势待发，他将姜泥放在心尖上，话锋一句比一句犀利，威逼利诱的要求卢白撷放姜泥一条生路。",
                "voice": "zh-CN-YunxiNeural",
                "rate": "0%",
                "pitch": "0Hz", 
                "volume": "0%"
            },
            {
                "desc": "卢白撷",
                "text": "人心入局，观子无敌，棋局未央，棋子难逃。你是！？ 曹长卿！",
                "voice": "zh-CN-YunyangNeural",
                "rate": "-2%",
                "pitch": "2Hz",
                "volume": "10%"
            }
        ]
        
        batch_result = client.generate_batch_speech(
            voice_data=voice_data,
            save_path="./output"
        )
        print(f"批量语音生成成功，文件路径: {batch_result}")
        
        # 获取任务统计
        print("\n3. 获取任务统计信息...")
        stats = client.get_task_stats()
        if stats and stats.get('success'):
            print("任务统计:", stats['data'])
        
        print("\n=== 所有测试完成 ===")
        print("请检查 ./output 目录下的MP3文件")
        
    except Exception as e:
        print(f"错误: {e}") 