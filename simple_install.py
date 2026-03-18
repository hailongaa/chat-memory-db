#!/usr/bin/env python3
"""
简化安装脚本 - 不依赖外部pip
"""

import sys
import os
import subprocess
import importlib

def check_and_install_deps():
    """检查并安装依赖"""
    deps = [
        ('numpy', 'numpy'),
        ('schedule', 'schedule'),
        ('sentence_transformers', 'sentence-transformers'),
        ('faiss', 'faiss-cpu'),
        ('sqlite_utils', 'sqlite-utils')
    ]
    
    missing_deps = []
    
    print("检查依赖...")
    for import_name, pip_name in deps:
        try:
            importlib.import_module(import_name)
            print(f"✅ {import_name} 已安装")
        except ImportError:
            print(f"❌ {import_name} 未安装")
            missing_deps.append(pip_name)
    
    if missing_deps:
        print(f"\n需要安装的依赖: {missing_deps}")
        print("请运行以下命令安装:")
        print(f"pip install {' '.join(missing_deps)}")
        return False
    else:
        print("\n✅ 所有依赖已安装")
        return True

def init_database():
    """初始化数据库"""
    print("\n初始化数据库...")
    try:
        # 创建数据目录
        data_dir = os.path.expanduser("~/.openclaw-autoclaw/data")
        os.makedirs(data_dir, exist_ok=True)
        print(f"✅ 创建数据目录: {data_dir}")
        
        # 导入数据库模块
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from chat_memory.database import ChatDatabase
        
        # 初始化数据库
        db = ChatDatabase()
        print("✅ 数据库初始化完成")
        
        # 显示表结构
        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✅ 创建了 {len(tables)} 个表:")
        for table in tables:
            print(f"  - {table[0]}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False

def create_config_files():
    """创建配置文件"""
    print("\n创建配置文件...")
    
    try:
        # 创建配置目录
        config_dir = os.path.expanduser("~/.openclaw-autoclaw/config")
        os.makedirs(config_dir, exist_ok=True)
        
        # 创建技能配置文件
        config_content = """# 聊天记录记忆技能配置

[database]
path = ~/.openclaw-autoclaw/data/chat_memory.db
cleanup_days = 30

[vector_search]
model = all-MiniLM-L6-v2
similarity_threshold = 0.6

[scheduler]
auto_archive_hour = 23
auto_archive_minute = 0

[integration]
auto_store = true
auto_retrieve = true
max_context_items = 5
"""
        
        config_file = os.path.join(config_dir, "chat_memory.conf")
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"✅ 配置文件已创建: {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        return False

def test_basic_functionality():
    """测试基本功能"""
    print("\n测试基本功能...")
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from chat_memory.database import ChatDatabase
        
        # 测试数据库连接
        db = ChatDatabase()
        
        # 测试插入数据
        from datetime import datetime
        test_data = {
            'session_id': 'test_session',
            'message_id': 'test_msg_001',
            'sender_type': 'user',
            'content': '测试消息',
            'timestamp': datetime.now(),
            'channel': 'webchat'
        }
        
        success = db.store_message(**test_data)
        if success:
            print("✅ 数据库写入测试通过")
        else:
            print("❌ 数据库写入测试失败")
        
        # 测试查询
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chat_messages")
        count = cursor.fetchone()[0]
        print(f"✅ 数据库中有 {count} 条消息")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("聊天记录记忆技能 - 简化安装")
    print("=" * 60)
    
    # 检查依赖
    if not check_and_install_deps():
        print("\n⚠️  请先安装依赖，然后重新运行此脚本")
        print("或者使用以下命令安装:")
        print("python -m pip install sentence-transformers faiss-cpu sqlite-utils numpy schedule")
        return 1
    
    # 初始化数据库
    if not init_database():
        return 1
    
    # 创建配置文件
    if not create_config_files():
        return 1
    
    # 测试功能
    if not test_basic_functionality():
        return 1
    
    print("\n" + "=" * 60)
    print("✅ 安装完成！")
    print("=" * 60)
    print("\n技能已安装到:")
    print(f"  技能目录: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"  数据库: ~/.openclaw-autoclaw/data/chat_memory.db")
    print(f"  配置文件: ~/.openclaw-autoclaw/config/chat_memory.conf")
    
    print("\n使用方法:")
    print("1. 在OpenClaw中导入技能:")
    print("   from openclaw_skill import get_skill")
    print("   skill = get_skill()")
    print("   skill.activate()")
    
    print("\n2. 运行完整测试:")
    print("   python test_memory.py")
    
    print("\n3. 查看使用示例:")
    print("   python examples/basic_usage.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())