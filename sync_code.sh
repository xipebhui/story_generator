#!/bin/bash
# 安全拉取代码的脚本，保护本地 .env 文件

echo "==================================="
echo "安全同步代码（保护本地配置）"
echo "==================================="

# 检查是否有 .env 文件
if [ -f .env ]; then
    echo "✓ 检测到本地 .env 文件"
    
    # 备份 .env
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "✓ 已备份 .env 文件"
    
    # 暂存本地修改
    git stash push -m "Auto stash before pull $(date +%Y-%m-%d_%H:%M:%S)"
    echo "✓ 已暂存本地修改"
fi

# 拉取最新代码
echo "→ 正在拉取最新代码..."
git pull origin master

# 恢复 .env 文件
if [ -f .env.backup.* ]; then
    # 找到最新的备份文件
    latest_backup=$(ls -t .env.backup.* | head -1)
    cp "$latest_backup" .env
    echo "✓ 已恢复 .env 文件"
    
    # 设置 Git 忽略 .env 的变化
    git update-index --skip-worktree .env 2>/dev/null || true
    echo "✓ 已设置 Git 忽略 .env 文件变化"
fi

# 尝试恢复其他暂存的修改
if git stash list | grep -q "Auto stash before pull"; then
    echo "→ 正在恢复其他本地修改..."
    git stash pop
fi

echo "==================================="
echo "✅ 同步完成！"
echo "==================================="
echo ""
echo "提示："
echo "- 本地 .env 文件已保留"
echo "- 如有新配置项，请参考 .env.example"