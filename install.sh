#!/bin/bash
# 聊天记录记忆技能安装脚本

set -e

echo "=========================================="
echo "聊天记录记忆技能安装脚本"
echo "=========================================="

# 检查Python版本
echo "检查Python版本..."
python3 --version || { echo "❌ 需要Python 3.7或更高版本"; exit 1; }

# 创建虚拟环境（可选）
read -p "是否创建虚拟环境？(y/n): " create_venv
if [[ "$create_venv" == "y" || "$create_venv" == "Y" ]]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    echo "虚拟环境已激活"
fi

# 安装依赖
echo "安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 检查是否安装成功
echo "检查依赖安装..."
python3 -c "import sentence_transformers; import faiss; import schedule; print('✅ 核心依赖安装成功')" || {
    echo "❌ 依赖安装失败，请手动安装: pip install sentence-transformers faiss-cpu schedule"
    exit 1
}

# 初始化数据库
echo "初始化数据库..."
python3 init_db.py

# 运行测试
echo "运行功能测试..."
python3 test_memory.py

echo ""
echo "=========================================="
echo "✅ 安装完成！"
echo "=========================================="
echo ""
echo "下一步:"
echo "1. 查看使用示例: python3 examples/basic_usage.py"
echo "2. 集成到OpenClaw: 参考 examples/basic_usage.py 中的集成示例"
echo "3. 启动调度器: python3 -m chat_memory.scheduler"
echo ""
echo "技能目录: $(pwd)"
echo "数据库位置: ~/.openclaw-autoclaw/data/chat_memory.db"
echo "=========================================="