#!/bin/bash
# 发布任务重试和删除功能测试运行脚本

set -e  # 错误时退出

echo "🚀 发布任务重试和删除功能测试"
echo "================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 设置环境变量
export API_BASE_URL=${API_BASE_URL:-"http://localhost:51082"}
export API_KEY=${API_KEY:-"test-api-key-12345"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}

echo "📋 测试配置:"
echo "   API服务器: $API_BASE_URL"
echo "   API密钥: $API_KEY"
echo "   日志级别: $LOG_LEVEL"
echo ""

# 检查API服务器是否运行
echo "🔍 检查API服务器连接..."
if curl -f -s "$API_BASE_URL/health" > /dev/null 2>&1; then
    echo "✅ API服务器连接正常"
else
    echo "⚠️  警告: 无法连接到API服务器，测试可能会失败"
    echo "   请确保API服务器在 $API_BASE_URL 上运行"
    echo ""
fi

# 安装依赖 (如果需要)
if [ -f "requirements.txt" ]; then
    echo "📦 检查Python依赖..."
    pip3 install -r requirements.txt
fi

# 运行测试
echo "🧪 开始运行测试..."
echo ""

python3 test_publish_retry_delete.py

# 检查测试结果
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 所有测试通过!"
    echo "📄 详细日志请查看: test_results.log"
else
    echo ""
    echo "💥 测试失败!"
    echo "📄 错误详情请查看: test_results.log"
    exit 1
fi