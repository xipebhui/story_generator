#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试视频拼接API
"""

import os
import sys
import json
import time
import shutil
import requests
from pathlib import Path
from datetime import datetime

# API配置
API_BASE_URL = "http://localhost:8000"
API_KEY = os.environ.get("API_KEY", "")  # 如果启用了认证，需要设置API_KEY

def setup_test_videos():
    """准备测试视频文件夹"""
    # 创建测试文件夹
    portrait_folder = Path("output/videos/portrait")
    landscape_folder = Path("output/videos/landscape")
    
    portrait_folder.mkdir(parents=True, exist_ok=True)
    landscape_folder.mkdir(parents=True, exist_ok=True)
    
    # 检查现有视频文件
    videos_dir = Path("output/videos")
    
    # 移动视频到相应文件夹
    for video_file in videos_dir.glob("*.mp4"):
        if video_file.is_file():
            # 简单判断：文件名包含某些关键词或通过ffprobe检查
            # 这里假设已知哪些是竖屏，哪些是横屏
            if "户晨风" in video_file.name or "9_16" in video_file.name:
                # 竖屏视频
                dest = portrait_folder / video_file.name
                if not dest.exists():
                    shutil.copy2(video_file, dest)
                    print(f"复制竖屏视频: {video_file.name}")
            elif "Sunset" in video_file.name or "16_9" in video_file.name:
                # 横屏视频
                dest = landscape_folder / video_file.name
                if not dest.exists():
                    shutil.copy2(video_file, dest)
                    print(f"复制横屏视频: {video_file.name}")
    
    # 检查是否有测试视频
    portrait_count = len(list(portrait_folder.glob("*.mp4")))
    landscape_count = len(list(landscape_folder.glob("*.mp4")))
    
    print(f"\n测试视频准备完成:")
    print(f"  竖屏视频: {portrait_count} 个 ({portrait_folder})")
    print(f"  横屏视频: {landscape_count} 个 ({landscape_folder})")
    
    if portrait_count == 0 or landscape_count == 0:
        print("\n⚠️ 警告：缺少测试视频文件！")
        print("请确保 output/videos 目录下有视频文件")
        return False
    
    return True

def test_video_merge_api():
    """测试视频拼接API"""
    print("=" * 60)
    print("测试视频拼接API")
    print("=" * 60)
    
    # 准备测试视频
    if not setup_test_videos():
        return
    
    # 构建请求数据
    request_data = {
        "portrait_folder": "output/videos/portrait",
        "landscape_folder": "output/videos/landscape",
        "custom_id": f"test_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }
    
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    print(f"\n1. 创建视频拼接任务...")
    print(f"   请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
    
    # 发送请求
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/video/merge",
            json=request_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get("task_id")
            print(f"\n✅ 任务创建成功!")
            print(f"   任务ID: {task_id}")
            print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 轮询任务状态
            print(f"\n2. 查询任务状态...")
            max_wait = 60  # 最多等待60秒
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                time.sleep(3)  # 每3秒查询一次
                
                status_response = requests.get(
                    f"{API_BASE_URL}/api/video/merge/{task_id}",
                    headers=headers
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data.get("status")
                    current_stage = status_data.get("current_stage", "")
                    
                    print(f"   状态: {current_status} - {current_stage}")
                    
                    if current_status == "已完成":
                        print(f"\n✅ 视频拼接完成!")
                        print(f"   草稿路径: {status_data.get('draft_path')}")
                        if status_data.get('result'):
                            print(f"   结果详情:")
                            print(json.dumps(status_data['result'], ensure_ascii=False, indent=2))
                        break
                    elif current_status == "失败":
                        print(f"\n❌ 视频拼接失败!")
                        print(f"   错误: {status_data.get('error')}")
                        break
                else:
                    print(f"   查询失败: {status_response.status_code}")
            
            else:
                print(f"\n⚠️ 等待超时，任务可能仍在运行")
                
        else:
            print(f"\n❌ 请求失败!")
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ 无法连接到API服务器: {API_BASE_URL}")
        print("请确保API服务器正在运行: python api_with_db.py")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

def test_direct_pipeline():
    """直接测试Pipeline（不通过API）"""
    print("=" * 60)
    print("直接测试视频拼接Pipeline")
    print("=" * 60)
    
    from pipeline_video_merge import VideoMergePipeline
    
    # 准备测试视频
    if not setup_test_videos():
        return
    
    # 创建pipeline实例
    pipeline = VideoMergePipeline()
    
    # 执行拼接
    result = pipeline.process(
        portrait_folder="output/videos/portrait",
        landscape_folder="output/videos/landscape",
        custom_id=f"test_direct_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    print("\n测试结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if result['success']:
        print(f"\n✅ 测试成功!")
        print(f"草稿文件: {result['draft_path']}")
    else:
        print(f"\n❌ 测试失败: {result.get('error')}")

def main():
    """主测试函数"""
    print("\n🎬 视频拼接服务测试")
    print("=" * 60)
    
    # 检查测试模式
    if len(sys.argv) > 1 and sys.argv[1] == "--direct":
        # 直接测试Pipeline
        test_direct_pipeline()
    else:
        # 测试API
        test_video_merge_api()
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()