#!/usr/bin/env python3
"""
配置文件
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 草稿相关路径 - 从环境变量读取，如果没有则使用默认值
FINAL_JIANYING_DRAFTS_PATH = os.getenv("DRAFT_LOCAL_DIR", 
                                        os.path.join(PROJECT_ROOT, "final_drafts", "jianying"))
FINAL_ONLINE_DRAFT_PATH = os.getenv("DRAFT_ONLINE_DIR", 
                                    os.path.join(PROJECT_ROOT, "final_drafts", "online"))

# 视频输出目录
VIDEO_OUTPUT_DIR = os.getenv("VIDEO_OUTPUT_DIR", 
                             os.path.join(PROJECT_ROOT, "output", "videos"))

# 导出相关配置
EXPORT_VIDEO_URL = os.getenv("EXPORT_VIDEO_URL", "http://localhost:8080/api/export_draft")

# 确保目录存在
os.makedirs(FINAL_JIANYING_DRAFTS_PATH, exist_ok=True)
os.makedirs(FINAL_ONLINE_DRAFT_PATH, exist_ok=True)
os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)