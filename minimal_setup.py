#!/usr/bin/env python3
"""
最小化安装 - 只安装核心功能
"""

import os
import sys
import sqlite3

def setup_database():
    """设置数据库"""
    print("设置数据库...")
    
    try:
        # 创建数据目录
        data_dir = os.path.expanduser("~/.openclaw-autoclaw/data")
        os.makedirs(data_dir, exist_ok=True)
        
        db_path = os.path.join(data_dir, "chat_memory.db")
        print(f"数据库路径: {db_path}")
        
        # 创建数据库连接
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建基本表结构
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_id TEXT UNIQUE NOT NULL,
                sender_type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                channel TEXT,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON chat_messages(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON chat_messages(session_id)")
        
        conn.commit()
        conn.close()
        
        print("✅ 数据库设置完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据库设置失败: {e}")
        return False

def setup_config():
    """设置配置文件"""
    print("\n设置配置文件...")
    
    try:
        # 创建配置目录
        config_dir = os.path.expanduser("~/.openclaw-autoclaw/config")
        os.makedirs(config_dir, exist_ok=True)
        
        # 简单配置文件
        config_content = """# 聊天记录记忆技能 - 最小配置
[database]
path = ~/.openclaw-autoclaw/data/chat_memory.db

[basic]
auto_store = true
max_messages = 1000
"""
        
        config_file = os.path.join(config_dir, "chat_memory_simple.conf")
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"✅ 配置文件: {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ 配置设置失败: {e}")
        return False

def create_simple_memory_manager():
    """创建简单的记忆管理器"""
    print("\n创建简单记忆管理器...")
    
    try:
        skill_dir = os.path.dirname(os.path.abspath(__file__))
        simple_manager_path = os.path.join(skill_dir, "simple_memory.py")
        
        simple_code = '''"""
简单的记忆管理器 - 不依赖外部库
"""
import sqlite3
import json
import os
from datetime import datetime

class SimpleChatMemory:
    """简单的聊天记忆管理器"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            data_dir = os.path.expanduser("~/.openclaw-autoclaw/data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "chat_memory.db")
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def store_message(self, session_id, message_id, sender_type, content, 
                     timestamp=None, channel=None, metadata=None):
        """存储消息"""
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            metadata_str = json.dumps(metadata) if metadata else None
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO chat_messages 
                (session_id, message_id, sender_type, content, timestamp, channel, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, message_id, sender_type, content, 
                  timestamp.isoformat(), channel, metadata_str))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"存储消息失败: {e}")
            return False
    
    def get_recent_messages(self, session_id=None, limit=10):
        """获取最近消息"""
        try:
            cursor = self.conn.cursor()
            
            if session_id:
                cursor.execute("""
                    SELECT * FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (session_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM chat_messages
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"获取消息失败: {e}")
            return []
    
    def search_by_keyword(self, keyword, limit=5):
        """关键词搜索"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM chat_messages
                WHERE content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f'%{keyword}%', limit))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()

# 全局实例
_memory_instance = None

def get_simple_memory(db_path=None):
    """获取简单记忆管理器实例"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = SimpleChatMemory(db_path)
    return _memory_instance
'''
        
        with open(simple_manager_path, 'w', encoding='utf-8') as f:
            f.write(simple_code)
        
        print(f"✅ 简单记忆管理器: {simple_manager_path}")
        return True
        
    except Exception as e:
        print(f"❌ 创建记忆管理器失败: {e}")
        return False

def test_setup():
    """测试设置"""
    print("\n测试设置...")
    
    try:
        # 测试数据库
        data_dir = os.path.expanduser("~/.openclaw-autoclaw/data")
        db_path = os.path.join(data_dir, "chat_memory.db")
        
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"✅ 数据库表: {tables}")
            
            # 检查消息数量
            cursor.execute("SELECT COUNT(*) FROM chat_messages")
            count = cursor.fetchone()[0]
            print(f"✅ 消息数量: {count}")
            
            conn.close()
        else:
            print("❌ 数据库文件不存在")
            return False
        
        # 测试简单管理器
        skill_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, skill_dir)
        
        try:
            from simple_memory import get_simple_memory
            memory = get_simple_memory()
            
            # 测试插入
            from datetime import datetime
            test_success = memory.store_message(
                session_id="test_setup",
                message_id="setup_test_001",
                sender_type="user",
                content="安装测试消息",
                timestamp=datetime.now(),
                channel="setup"
            )
            
            if test_success:
                print("✅ 记忆管理器测试通过")
            else:
                print("❌ 记忆管理器测试失败")
            
            memory.close()
            
        except ImportError:
            print("⚠️  简单记忆管理器导入失败，但数据库已设置")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("聊天记录记忆技能 - 最小化安装")
    print("=" * 60)
    
    # 设置数据库
    if not setup_database():
        return 1
    
    # 设置配置
    if not setup_config():
        return 1
    
    # 创建简单管理器
    if not create_simple_memory_manager():
        return 1
    
    # 测试
    if not test_setup():
        return 1
    
    print("\n" + "=" * 60)
    print("✅ 最小化安装完成！")
    print("=" * 60)
    
    print("\n已安装的功能:")
    print("1. ✅ 数据库存储 (SQLite)")
    print("2. ✅ 基本消息存储和检索")
    print("3. ✅ 关键词搜索")
    print("4. ✅ 简单配置")
    
    print("\n使用简单记忆管理器:")
    print("```python")
    print("from simple_memory import get_simple_memory")
    print("")
    print("memory = get_simple_memory()")
    print("memory.store_message(")
    print("    session_id='my_session',")
    print("    message_id='msg_001',")
    print("    sender_type='user',")
    print("    content='你好'")
    print(")")
    print("")
    print("messages = memory.get_recent_messages(limit=5)")
    print("memory.close()")
    print("```")
    
    print("\n文件位置:")
    print(f"数据库: ~/.openclaw-autoclaw/data/chat_memory.db")
    print(f"配置: ~/.openclaw-autoclaw/config/chat_memory_simple.conf")
    print(f"简单管理器: {os.path.dirname(os.path.abspath(__file__))}/simple_memory.py")
    
    print("\n注意: 这是最小化版本，缺少:")
    print("- 向量搜索 (需要FAISS)")
    print("- 自动归档调度 (需要schedule)")
    print("- 高级语义搜索 (需要sentence-transformers)")
    
    print("\n要安装完整版本，请运行:")
    print("pip install sentence-transformers faiss-cpu sqlite-utils numpy schedule")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())