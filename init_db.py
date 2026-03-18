#!/usr/bin/env python3
"""
初始化数据库脚本
创建数据库表结构和索引
"""

import os
import sys
import logging
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat_memory import get_database, get_vector_search

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database():
    """初始化数据库"""
    try:
        logger.info("开始初始化数据库...")
        
        # 获取数据库实例（会自动创建表结构）
        db = get_database()
        
        # 测试数据库连接
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM chat_messages")
        result = cursor.fetchone()
        logger.info(f"数据库初始化完成，当前消息数: {result['count']}")
        
        # 显示表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info("数据库表列表:")
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table['name']})")
            columns = cursor.fetchall()
            logger.info(f"  {table['name']}: {len(columns)} 列")
        
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False

def init_vector_index():
    """初始化向量索引"""
    try:
        logger.info("开始初始化向量索引...")
        
        # 获取向量搜索实例
        vector_search = get_vector_search()
        
        # 检查模型是否加载
        if vector_search.model is None:
            logger.warning("向量模型未加载，请安装依赖: pip install sentence-transformers faiss-cpu")
            return False
        
        # 检查索引状态
        stats = vector_search.get_stats()
        logger.info(f"向量索引状态: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"向量索引初始化失败: {e}")
        return False

def create_directories():
    """创建必要的目录"""
    try:
        base_dir = Path.home() / ".openclaw-autoclaw" / "data"
        directories = [
            base_dir,
            base_dir / "archives",
            base_dir / "backups",
            base_dir / "notifications"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建目录: {directory}")
        
        return True
        
    except Exception as e:
        logger.error(f"创建目录失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("聊天记录记忆系统 - 初始化脚本")
    print("=" * 60)
    
    # 创建目录
    if not create_directories():
        print("❌ 创建目录失败")
        return 1
    
    # 初始化数据库
    if not init_database():
        print("❌ 数据库初始化失败")
        return 1
    
    # 初始化向量索引
    if not init_vector_index():
        print("⚠️  向量索引初始化警告（可能需要安装依赖）")
    
    print("=" * 60)
    print("✅ 初始化完成！")
    print("")
    print("下一步:")
    print("1. 安装依赖: pip install sentence-transformers faiss-cpu sqlite-utils numpy schedule")
    print("2. 启动调度器: python -m chat_memory.scheduler")
    print("3. 测试功能: python test_memory.py")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())