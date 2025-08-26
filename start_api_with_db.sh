#!/bin/bash
# 启动增强版API服务器（带数据库支持）

echo "启动增强版Pipeline API服务器..."
echo "================================"

# 设置环境变量
export DB_PATH="./data/pipeline_tasks.db"
export USE_MOCK_UPLOAD="true"  # 使用Mock接口测试，改为false使用真实接口
export YTENGINE_HOST="http://localhost:51077"
export LOG_LEVEL="INFO"

# 创建数据目录
mkdir -p data

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: Python3未安装"
    exit 1
fi

# 安装依赖（如果需要）
echo "检查依赖..."
pip3 install -q sqlalchemy aiohttp

# 启动服务器
echo "启动服务器..."
echo "访问 http://localhost:51082 查看API"
echo "访问 http://localhost:51082/docs 查看交互式文档"
echo "================================"

python3 api_with_db.py