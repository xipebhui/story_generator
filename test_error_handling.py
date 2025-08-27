#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试错误处理脚本
用于验证pipeline错误信息能正确传递到前端
"""

import requests
import json
import time
import sys

# API基础URL
BASE_URL = "http://localhost:8000"

def test_subtitle_error():
    """测试字幕获取失败的错误处理"""
    print("="*60)
    print("测试字幕获取失败的错误处理")
    print("="*60)
    
    # 1. 创建一个会失败的任务（使用一个没有字幕的视频ID或假的视频ID）
    request_data = {
        "video_id": "INVALID_VIDEO_ID_FOR_TEST",  # 使用一个无效的视频ID来触发字幕获取失败
        "creator_id": "test_creator",
        "gender": 1,
        "duration": 60,
        "export_video": False,
        "enable_subtitle": True
    }
    
    print(f"\n1. 创建测试任务...")
    print(f"   请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
    
    try:
        # 发送创建任务请求
        response = requests.post(f"{BASE_URL}/api/pipeline/execute", json=request_data)
        response.raise_for_status()
        
        result = response.json()
        task_id = result.get("task_id")
        print(f"   ✅ 任务创建成功: {task_id}")
        
        # 2. 等待一段时间让任务执行并失败
        print(f"\n2. 等待任务执行（30秒）...")
        for i in range(30):
            time.sleep(1)
            print(".", end="", flush=True)
            
            # 检查任务状态
            status_response = requests.get(f"{BASE_URL}/api/pipeline/status/{task_id}")
            if status_response.ok:
                status_data = status_response.json()
                if status_data.get("status") == "failed":
                    print(f"\n   任务已失败")
                    break
        
        # 3. 获取任务状态，检查错误信息
        print(f"\n3. 获取任务状态...")
        status_response = requests.get(f"{BASE_URL}/api/pipeline/status/{task_id}")
        status_response.raise_for_status()
        
        status_data = status_response.json()
        print(f"   任务状态: {status_data.get('status')}")
        print(f"   当前阶段: {status_data.get('current_stage')}")
        print(f"   进度信息: {json.dumps(status_data.get('progress', {}), ensure_ascii=False)}")
        
        # 检查错误信息
        error_msg = status_data.get("error")
        if error_msg:
            print(f"\n   ✅ 错误信息成功返回:")
            print(f"   {error_msg}")
            
            # 检查是否包含字幕相关的错误提示
            if "字幕" in error_msg or "subtitle" in error_msg.lower() or "transcript" in error_msg.lower():
                print(f"\n   ✅ 错误信息正确识别为字幕获取失败!")
                
                # 检查是否包含上传提示
                if "手动上传" in error_msg or "upload" in error_msg.lower():
                    print(f"   ✅ 包含手动上传字幕的提示!")
                else:
                    print(f"   ⚠️ 缺少手动上传字幕的提示")
            else:
                print(f"   ⚠️ 错误信息未明确标识为字幕问题")
        else:
            print(f"\n   ❌ 未返回错误信息!")
            print(f"   完整响应: {json.dumps(status_data, ensure_ascii=False, indent=2)}")
        
        return task_id
        
    except requests.exceptions.RequestException as e:
        print(f"\n   ❌ 请求失败: {e}")
        return None
    except Exception as e:
        print(f"\n   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_manual_subtitle_upload(task_id):
    """测试手动上传字幕功能"""
    if not task_id:
        print("\n跳过字幕上传测试（无有效任务ID）")
        return
    
    print("\n" + "="*60)
    print("测试手动上传字幕功能")
    print("="*60)
    
    # 创建测试字幕文件
    test_subtitle = """这是测试字幕内容
第一行字幕
第二行字幕
第三行字幕
用于测试手动上传功能"""
    
    # 准备上传数据
    files = {
        'file': ('subtitle.txt', test_subtitle.encode('utf-8'), 'text/plain')
    }
    data = {
        'task_id': task_id
    }
    
    print(f"\n上传测试字幕文件...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/pipeline/upload-subtitle",
            data=data,
            files=files
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"   ✅ 字幕上传成功!")
        print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 上传失败: {e}")
        if hasattr(e.response, 'text'):
            print(f"   错误详情: {e.response.text}")
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("Pipeline 错误处理测试")
    print("="*60)
    
    print(f"\n测试服务器: {BASE_URL}")
    print("请确保API服务已启动在 http://localhost:8000")
    
    input("\n按Enter键开始测试...")
    
    # 测试字幕错误处理
    task_id = test_subtitle_error()
    
    # 测试手动上传字幕
    if task_id:
        input("\n按Enter键测试手动上传字幕...")
        test_manual_subtitle_upload(task_id)
    
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)

if __name__ == "__main__":
    main()