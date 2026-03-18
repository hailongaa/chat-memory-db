#!/usr/bin/env python3
"""
安装脚本 - 无Unicode字符版本
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
        
        print("[OK] 数据库设置完成")
        return True
        
    except Exception as e:
        print(f"[ERROR] 数据库设置失败: {e}")
        return False

def create_simple_manager():
    """创建简单管理器"""
    print("\n创建简单记忆管理器...")
    
    try:
        skill_dir = os.path.dirname(os.path.abspath(__file__))
        manager_path = os.path.join(skill_dir, "chat_memory_simple.py")
        
        manager_code = '''
import sqlite3
import json
import os
from datetime import datetime

class SimpleChatMemory:
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
                if result.get('metadata'):
                    try:
                        result['metadata'] = json.loads(result['metadata'])
                    except:
                        result['metadata'] = None
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"获取消息失败: {e}")
            return []
    
    def search_by_keyword(self, keyword, limit=5):
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
                if result.get('metadata'):
                    try:
                        result['metadata'] = json.loads(result['metadata'])
                    except:
                        result['metadata'] = None
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def get_stats(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM chat_messages")
            total = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(DISTINCT session_id) as count FROM chat_messages")
            sessions = cursor.fetchone()['count']
            
            return {
                'total_messages': total,
                'total_sessions': sessions,
                'db_path': self.db_path
            }
        except Exception as e:
            print(f"获取统计失败: {e}")
            return {}
    
    def close(self):
        if self.conn:
            self.conn.close()

# 全局实例
_memory_instance = None

def get_memory(db_path=None):
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = SimpleChatMemory(db_path)
    return _memory_instance
'''
        
        with open(manager_path, 'w', encoding='utf-8') as f:
            f.write(manager_code)
        
        print(f"[OK] 简单记忆管理器: {manager_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 创建记忆管理器失败: {e}")
        return False

def test_installation():
    """测试安装"""
    print("\n测试安装...")
    
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
            
            print(f"[OK] 数据库表: {tables}")
            
            # 检查消息数量
            cursor.execute("SELECT COUNT(*) FROM chat_messages")
            count = cursor.fetchone()[0]
            print(f"[OK] 消息数量: {count}")
            
            conn.close()
        else:
            print("[ERROR] 数据库文件不存在")
            return False
        
        # 测试管理器
        skill_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, skill_dir)
        
        try:
            from chat_memory_simple import get_memory
            memory = get_memory()
            
            # 测试插入
            from datetime import datetime
            test_success = memory.store_message(
                session_id="test_install",
                message_id="install_test_001",
                sender_type="user",
                content="安装测试消息 - 你好世界",
                timestamp=datetime.now(),
                channel="test"
            )
            
            if test_success:
                print("[OK] 记忆管理器测试通过")
            else:
                print("[ERROR] 记忆管理器测试失败")
            
            # 测试查询
            messages = memory.get_recent_messages(limit=2)
            print(f"[OK] 最近消息: {len(messages)} 条")
            
            # 测试统计
            stats = memory.get_stats()
            print(f"[OK] 统计: {stats['total_messages']} 条消息, {stats['total_sessions']} 个会话")
            
            memory.close()
            
        except ImportError as e:
            print(f"[ERROR] 导入失败: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("聊天记录记忆技能 - 安装")
    print("=" * 60)
    
    # 设置数据库
    if not setup_database():
        return 1
    
    # 创建管理器
    if not create_simple_manager():
        return 1
    
    # 测试
    if not test_installation():
        return 1
    
    print("\n" + "=" * 60)
    print("[SUCCESS] 安装完成！")
    print("=" * 60)
    
    print("\n已安装的功能:")
    print("1. [OK] 数据库存储 (SQLite)")
    print("2. [OK] 消息存储和检索")
    print("3. [OK] 关键词搜索")
    print("4. [OK] 统计功能")
    
    print("\n使用方法:")
    print("from chat_memory_simple import get_memory")
    print("")
    print("# 获取记忆管理器")
    print("memory = get_memory()")
    print("")
    print("# 存储消息")
    print("memory.store_message(")
    print("    session_id='my_session',")
    print("    message_id='msg_001',")
    print("    sender_type='user',")
    print("    content='你好'")
    print(")")
    print("")
    print("# 获取最近消息")
    print("messages = memory.get_recent_messages(limit=5)")
    print("")
    print("# 关键词搜索")
    print("results = memory.search_by_keyword('你好', limit=3)")
    print("")
    print("# 获取统计")
    print("stats = memory.get_stats()")
    print("")
    print("# 关闭连接")
    print("memory.close()")
    
    print("\n文件位置:")
    print(f"数据库: {os.path.expanduser('~/.openclaw-autoclaw/data/chat_memory.db')}")
    print(f"管理器: {os.path.dirname(os.path.abspath(__file__))}/chat_memory_simple.py")
    
    print("\n注意: 这是基础版本，包含核心功能。")
    print("要安装完整版本（包含向量搜索、自动归档等），请运行:")
    print("pip install sentence-transformers faiss-cpu sqlite-utils numpy schedule")
    
    print("\n然后运行完整测试:")
    print("python test_memory.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())