@echo off
REM 安全拉取代码的脚本，保护本地 .env 文件

echo ===================================
echo 安全同步代码（保护本地配置）
echo ===================================

REM 检查是否有 .env 文件
if exist .env (
    echo √ 检测到本地 .env 文件
    
    REM 备份 .env
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
    for /f "tokens=1-2 delims=/:" %%a in ("%TIME%") do (set mytime=%%a%%b)
    copy .env .env.backup.%mydate%_%mytime%
    echo √ 已备份 .env 文件
    
    REM 暂存本地修改
    git stash push -m "Auto stash before pull"
    echo √ 已暂存本地修改
)

REM 拉取最新代码
echo → 正在拉取最新代码...
git pull origin master

REM 恢复 .env 文件
if exist .env.backup.* (
    REM 找到最新的备份文件
    for /f "delims=" %%i in ('dir /b /o-d .env.backup.*') do (
        copy "%%i" .env
        echo √ 已恢复 .env 文件
        goto :restored
    )
    :restored
    
    REM 设置 Git 忽略 .env 的变化
    git update-index --skip-worktree .env 2>nul
    echo √ 已设置 Git 忽略 .env 文件变化
)

REM 尝试恢复其他暂存的修改
git stash list | findstr "Auto stash before pull" >nul
if %errorlevel%==0 (
    echo → 正在恢复其他本地修改...
    git stash pop
)

echo ===================================
echo √ 同步完成！
echo ===================================
echo.
echo 提示：
echo - 本地 .env 文件已保留
echo - 如有新配置项，请参考 .env.example