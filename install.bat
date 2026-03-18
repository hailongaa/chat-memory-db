@echo off
REM 聊天记录记忆技能安装脚本（Windows）

echo ==========================================
echo 聊天记录记忆技能安装脚本
echo ==========================================

REM 检查Python版本
echo 检查Python版本...
python --version
if errorlevel 1 (
    echo ❌ 需要Python 3.7或更高版本
    pause
    exit /b 1
)

REM 创建虚拟环境（可选）
set /p create_venv="是否创建虚拟环境？(y/n): "
if /i "%create_venv%"=="y" (
    echo 创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo 虚拟环境已激活
)

REM 安装依赖
echo 安装依赖...
pip install --upgrade pip
pip install -r requirements.txt

REM 检查是否安装成功
echo 检查依赖安装...
python -c "import sentence_transformers; import faiss; import schedule; print('✅ 核心依赖安装成功')"
if errorlevel 1 (
    echo ❌ 依赖安装失败，请手动安装: pip install sentence-transformers faiss-cpu schedule
    pause
    exit /b 1
)

REM 初始化数据库
echo 初始化数据库...
python init_db.py

REM 运行测试
echo 运行功能测试...
python test_memory.py

echo.
echo ==========================================
echo ✅ 安装完成！
echo ==========================================
echo.
echo 下一步:
echo 1. 查看使用示例: python examples\basic_usage.py
echo 2. 集成到OpenClaw: 参考 examples\basic_usage.py 中的集成示例
echo 3. 启动调度器: python -m chat_memory.scheduler
echo.
echo 技能目录: %CD%
echo 数据库位置: %USERPROFILE%\.openclaw-autoclaw\data\chat_memory.db
echo ==========================================
pause