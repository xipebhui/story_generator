#!/usr/bin/env python3
"""
独立的视频导出脚本
用于将剪映草稿导出为视频文件

使用方法:
    python export_video.py <draft_id>
    python export_video.py <draft_id> --output-dir /path/to/output
    python export_video.py <draft_id> --export-url http://custom-url/api/export_draft
"""

import os
import sys
import argparse
import json
import time
from typing import Optional
import requests

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import config
from utils import http_utils
import logger

# 获取logger
log = logger.get_logger("VideoExporter")


class VideoExporter:
    """视频导出器类"""
    
    def __init__(self, export_url: Optional[str] = None):
        """
        初始化视频导出器
        
        Args:
            export_url: 导出服务URL，如果不提供则使用config中的默认值
        """
        self.export_url = export_url or config.EXPORT_VIDEO_URL
        log.info(f"VideoExporter initialized with URL: {self.export_url}")
    
    def export_video(self, draft_id: str, output_dir: Optional[str] = None) -> str:
        """
        导出视频
        
        Args:
            draft_id: 草稿ID
            output_dir: 输出目录，如果不提供则使用默认目录
            
        Returns:
            导出的视频文件路径
            
        Raises:
            Exception: 导出失败时抛出异常
        """
        log.info(f"Starting video export for draft: {draft_id}")
        
        # 验证草稿是否存在
        draft_path = os.path.join(config.FINAL_JIANYING_DRAFTS_PATH, draft_id)
        if not os.path.exists(draft_path):
            error_msg = f"Draft not found: {draft_id} at path: {draft_path}"
            log.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # 检查草稿必需文件
        required_files = ["draft_meta_info.json", "draft_content.json"]
        for file_name in required_files:
            file_path = os.path.join(draft_path, file_name)
            if not os.path.exists(file_path):
                log.warning(f"Required file not found: {file_path}")
        
        # 请求导出视频
        try:
            log.info(f"Sending export request to: {self.export_url}")
            video_path = http_utils.reuqset_export_video(draft_id, self.export_url)
            log.info(f"Video exported successfully: {video_path}")
            
            # 如果指定了输出目录，复制文件到该目录
            if output_dir:
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                    log.info(f"Created output directory: {output_dir}")
                
                import shutil
                video_filename = os.path.basename(video_path)
                new_video_path = os.path.join(output_dir, video_filename)
                shutil.copy2(video_path, new_video_path)
                log.info(f"Video copied to: {new_video_path}")
                return new_video_path
            
            return video_path
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error during video export: {str(e)}"
            log.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Failed to export video: {str(e)}"
            log.error(error_msg)
            raise
    
    def batch_export(self, draft_ids: list, output_dir: Optional[str] = None) -> dict:
        """
        批量导出视频
        
        Args:
            draft_ids: 草稿ID列表
            output_dir: 输出目录
            
        Returns:
            导出结果字典，格式: {draft_id: video_path or error_message}
        """
        results = {}
        total = len(draft_ids)
        
        log.info(f"Starting batch export for {total} drafts")
        
        for index, draft_id in enumerate(draft_ids, 1):
            log.info(f"Processing {index}/{total}: {draft_id}")
            try:
                video_path = self.export_video(draft_id, output_dir)
                results[draft_id] = {
                    "status": "success",
                    "video_path": video_path
                }
                log.info(f"Successfully exported {draft_id}")
            except Exception as e:
                results[draft_id] = {
                    "status": "failed",
                    "error": str(e)
                }
                log.error(f"Failed to export {draft_id}: {str(e)}")
            
            # 避免过于频繁的请求
            if index < total:
                time.sleep(1)
        
        # 统计结果
        success_count = sum(1 for r in results.values() if r["status"] == "success")
        failed_count = total - success_count
        
        log.info(f"Batch export completed: {success_count} success, {failed_count} failed")
        
        return results
    
    def get_draft_info(self, draft_id: str) -> dict:
        """
        获取草稿信息
        
        Args:
            draft_id: 草稿ID
            
        Returns:
            草稿信息字典
        """
        draft_path = os.path.join(config.FINAL_JIANYING_DRAFTS_PATH, draft_id)
        
        info = {
            "draft_id": draft_id,
            "draft_path": draft_path,
            "exists": os.path.exists(draft_path)
        }
        
        if info["exists"]:
            # 读取草稿元信息
            meta_info_path = os.path.join(draft_path, "draft_meta_info.json")
            if os.path.exists(meta_info_path):
                try:
                    with open(meta_info_path, 'r', encoding='utf-8') as f:
                        meta_info = json.load(f)
                        info["meta_info"] = meta_info
                except Exception as e:
                    log.error(f"Failed to read meta info: {str(e)}")
            
            # 读取请求信息（如果存在）
            request_json_path = os.path.join(config.FINAL_ONLINE_DRAFT_PATH, f"{draft_id}_request.json")
            if os.path.exists(request_json_path):
                try:
                    with open(request_json_path, 'r', encoding='utf-8') as f:
                        request_info = json.load(f)
                        info["request_info"] = request_info
                except Exception as e:
                    log.error(f"Failed to read request info: {str(e)}")
            
            # 获取材料信息
            materials_path = os.path.join(draft_path, "materials")
            if os.path.exists(materials_path):
                materials = os.listdir(materials_path)
                info["materials"] = {
                    "count": len(materials),
                    "files": materials
                }
        
        return info


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="剪映草稿视频导出工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  导出单个视频:
    python export_video.py draft_123456
    
  导出到指定目录:
    python export_video.py draft_123456 --output-dir /path/to/output
    
  使用自定义导出URL:
    python export_video.py draft_123456 --export-url http://localhost:8080/api/export
    
  批量导出:
    python export_video.py draft_1 draft_2 draft_3 --batch
    
  获取草稿信息:
    python export_video.py draft_123456 --info
        """
    )
    
    parser.add_argument(
        "draft_ids",
        nargs="+",
        help="草稿ID（可以是一个或多个）"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        help="输出目录路径"
    )
    
    parser.add_argument(
        "--export-url",
        type=str,
        help=f"导出服务URL (默认: {config.EXPORT_VIDEO_URL})"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量导出模式"
    )
    
    parser.add_argument(
        "--info",
        action="store_true",
        help="仅显示草稿信息，不导出"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志"
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建导出器
    exporter = VideoExporter(export_url=args.export_url)
    
    try:
        if args.info:
            # 显示草稿信息
            for draft_id in args.draft_ids:
                info = exporter.get_draft_info(draft_id)
                print(f"\n草稿信息: {draft_id}")
                print("-" * 50)
                print(json.dumps(info, indent=2, ensure_ascii=False))
        
        elif args.batch or len(args.draft_ids) > 1:
            # 批量导出
            results = exporter.batch_export(args.draft_ids, args.output_dir)
            
            print("\n批量导出结果:")
            print("-" * 50)
            for draft_id, result in results.items():
                if result["status"] == "success":
                    print(f"[OK] {draft_id}: {result['video_path']}")
                else:
                    print(f"[ERROR] {draft_id}: {result['error']}")
        
        else:
            # 单个导出
            draft_id = args.draft_ids[0]
            video_path = exporter.export_video(draft_id, args.output_dir)
            print(f"\n[OK] 视频导出成功!")
            print(f"草稿ID: {draft_id}")
            print(f"视频路径: {video_path}")
            
    except KeyboardInterrupt:
        print("\n[WARNING] 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 导出失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()