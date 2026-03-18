
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
