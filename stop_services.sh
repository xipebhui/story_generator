#!/bin/bash
echo "停止自动发布系统..."

# 查找并停止Python进程
pkill -f "api_with_db.py"
pkill -f "start_auto_publish.py"

echo "服务已停止"
