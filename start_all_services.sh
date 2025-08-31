#!/bin/bash

# 自动发布系统启动脚本
# 包括数据库迁移、后端API和自动发布服务

echo "======================================"
echo "启动自动发布系统"
echo "======================================"

# 设置环境变量
export LOG_LEVEL=INFO
export DB_PATH=./data/pipeline_tasks.db
export CORS_ENABLED=true
export CORS_ORIGIN=http://localhost:3000

# 检查Python环境
echo "检查Python环境..."
python3 --version

# 安装依赖（如果需要）
echo "检查依赖..."
pip3 install -q fastapi uvicorn aiohttp scipy numpy

# 执行数据库迁移
echo ""
echo "执行数据库迁移..."
python3 migrate_database.py
if [ $? -ne 0 ]; then
    echo "数据库迁移失败，请检查错误信息"
    exit 1
fi

# 启动后端API服务
echo ""
echo "启动后端API服务..."
python3 api_with_db.py &
API_PID=$!
echo "API服务已启动 (PID: $API_PID)"

# 等待API服务启动
sleep 3

# 启动自动发布服务
echo ""
echo "启动自动发布服务..."
python3 start_auto_publish.py &
AUTO_PID=$!
echo "自动发布服务已启动 (PID: $AUTO_PID)"

# 创建停止脚本
cat > stop_services.sh << 'EOF'
#!/bin/bash
echo "停止自动发布系统..."

# 查找并停止Python进程
pkill -f "api_with_db.py"
pkill -f "start_auto_publish.py"

echo "服务已停止"
EOF

chmod +x stop_services.sh

echo ""
echo "======================================"
echo "✅ 所有服务已启动"
echo "======================================"
echo ""
echo "服务状态:"
echo "- API服务: http://localhost:51082"
echo "- 前端界面: http://localhost:3000"
echo ""
echo "使用说明:"
echo "1. 打开前端界面，点击'自动发布'标签"
echo "2. 创建账号组和发布配置"
echo "3. 生成调度槽位"
echo "4. 启动执行器开始自动发布"
echo ""
echo "停止服务: ./stop_services.sh"
echo ""
echo "按 Ctrl+C 停止所有服务..."

# 等待用户中断
wait $API_PID $AUTO_PID