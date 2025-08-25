#!/bin/bash

# 启动所有服务的脚本
# 包括后端API服务器和前端开发服务器

echo "==================================="
echo "   视频创作工作台 - 启动所有服务"
echo "==================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Python环境
echo -e "${BLUE}[1/3]${NC} 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}警告: Python3未安装${NC}"
    exit 1
fi

# 检查Node环境
echo -e "${BLUE}[2/3]${NC} 检查Node环境..."
if ! command -v npm &> /dev/null; then
    echo -e "${YELLOW}警告: Node.js/npm未安装${NC}"
    exit 1
fi

# 启动后端API服务器
echo -e "${BLUE}[3/3]${NC} 启动服务..."
echo ""

# 启动后端API
echo -e "${GREEN}→ 启动后端API服务器...${NC}"
echo "  地址: http://localhost:51082"
echo "  文档: http://localhost:51082/docs"
python3 api_simple.py &
API_PID=$!

# 等待API启动
sleep 3

# 启动前端开发服务器
echo ""
echo -e "${GREEN}→ 启动前端开发服务器...${NC}"
echo "  地址: http://localhost:3000"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# 显示成功信息
echo ""
echo "==================================="
echo -e "${GREEN}✓ 所有服务已启动${NC}"
echo ""
echo "访问地址:"
echo "  • 前端界面: http://localhost:3000"
echo "  • API文档:  http://localhost:51082/docs"
echo ""
echo "进程ID:"
echo "  • API服务器: $API_PID"
echo "  • 前端服务: $FRONTEND_PID"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "==================================="

# 等待用户中断
trap "echo '正在停止服务...'; kill $API_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait