"""
数据库管理模块
负责SQLite数据库的创建、连接、表结构和索引管理
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ChatDatabase:
    """聊天记录数据库管理类"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，默认为 ~/.openclaw-autoclaw/data/chat_memory.db
        """
        if db_path is None:
            base_dir = os.path.expanduser("~/.openclaw-autoclaw/data")
            os.makedirs(base_dir, exist_ok=True)
            db_path = os.path.join(base_dir, "chat_memory.db")
        
        self.db_path = db_path
        self.conn = None
        self.connect()
        self.init_tables()
        
    def connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # 返回字典格式的结果
            # 启用WAL模式提高并发性能
            self.conn.execute("PRAGMA journal_mode=WAL")
            # 设置缓存大小
            self.conn.execute("PRAGMA cache_size=-2000")  # 2MB缓存
            # 设置同步模式为NORMAL提高性能
            self.conn.execute("PRAGMA synchronous=NORMAL")
            logger.info(f"数据库连接成功: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def init_tables(self):
        """初始化数据库表结构"""
        try:
            cursor = self.conn.cursor()
            
            # 聊天记录主表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    message_id TEXT UNIQUE NOT NULL,
                    sender_type TEXT NOT NULL CHECK(sender_type IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    channel TEXT,
                    metadata TEXT,  -- JSON格式的元数据
                    embedding BLOB,  -- 向量嵌入
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 会话摘要表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_summaries (
                    session_id TEXT PRIMARY KEY,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    topics TEXT,
                    summary TEXT,
                    embedding BLOB,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 关键词索引表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keyword_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES chat_messages(message_id)
                )
            """)
            
            # 向量索引元数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vector_index_meta (
                    id INTEGER PRIMARY KEY,
                    index_version TEXT NOT NULL,
                    total_vectors INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    index_path TEXT
                )
            """)
            
            # 创建性能索引
            self.create_indexes()
            
            self.conn.commit()
            logger.info("数据库表结构初始化完成")
            
        except Exception as e:
            logger.error(f"初始化表结构失败: {e}")
            self.conn.rollback()
            raise
    
    def create_indexes(self):
        """创建性能索引"""
        try:
            cursor = self.conn.cursor()
            
            # 时间戳索引 - 最常用的查询条件
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp 
                ON chat_messages(timestamp)
            """)
            
            # 会话ID索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session 
                ON chat_messages(session_id)
            """)
            
            # 发送者类型索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_sender 
                ON chat_messages(sender_type)
            """)
            
            # 渠道索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_channel 
                ON chat_messages(channel)
            """)
            
            # 关键词索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_keyword_index_keyword 
                ON keyword_index(keyword)
            """)
            
            # 消息ID索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_keyword_index_message 
                ON keyword_index(message_id)
            """)
            
            # 复合索引：时间戳+会话
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp_session 
                ON chat_messages(timestamp, session_id)
            """)
            
            self.conn.commit()
            logger.info("数据库索引创建完成")
            
        except Exception as e:
            logger.error(f"创建索引失败: {e}")
            self.conn.rollback()
    
    def store_message(self, 
                     session_id: str,
                     message_id: str,
                     sender_type: str,
                     content: str,
                     timestamp: Optional[datetime] = None,
                     channel: Optional[str] = None,
                     metadata: Optional[Dict] = None,
                     embedding: Optional[bytes] = None) -> bool:
        """
        存储聊天消息
        
        Args:
            session_id: 会话ID
            message_id: 消息ID
            sender_type: 发送者类型 ('user' 或 'assistant')
            content: 消息内容
            timestamp: 时间戳，默认为当前时间
            channel: 渠道
            metadata: 元数据字典
            embedding: 向量嵌入的字节数据
            
        Returns:
            bool: 是否存储成功
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            metadata_str = json.dumps(metadata) if metadata else None
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO chat_messages 
                (session_id, message_id, sender_type, content, timestamp, channel, metadata, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, message_id, sender_type, content, 
                  timestamp.isoformat(), channel, metadata_str, embedding))
            
            self.conn.commit()
            
            # 提取关键词并更新关键词索引
            if sender_type == 'user':
                self._update_keyword_index(message_id, content)
            
            logger.debug(f"消息存储成功: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"存储消息失败: {e}")
            self.conn.rollback()
            return False
    
    def _update_keyword_index(self, message_id: str, content: str):
        """更新关键词索引"""
        try:
            # 简单的中文分词（实际应用中可以使用jieba等分词库）
            keywords = self._extract_keywords(content)
            
            cursor = self.conn.cursor()
            for keyword in keywords:
                # 检查关键词是否已存在
                cursor.execute("""
                    SELECT id, frequency FROM keyword_index 
                    WHERE keyword = ? AND message_id = ?
                """, (keyword, message_id))
                
                result = cursor.fetchone()
                if result:
                    # 更新频率
                    cursor.execute("""
                        UPDATE keyword_index 
                        SET frequency = frequency + 1, created_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (result['id'],))
                else:
                    # 插入新记录
                    cursor.execute("""
                        INSERT INTO keyword_index (keyword, message_id)
                        VALUES (?, ?)
                    """, (keyword, message_id))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"更新关键词索引失败: {e}")
            self.conn.rollback()
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        从文本中提取关键词
        
        Args:
            text: 文本内容
            max_keywords: 最大关键词数量
            
        Returns:
            关键词列表
        """
        # 简单的关键词提取逻辑
        # 实际应用中可以使用TF-IDF、TextRank等算法
        import re
        
        # 移除标点符号
        text = re.sub(r'[^\w\u4e00-\u9fff]+', ' ', text)
        
        # 分割单词
        words = text.split()
        
        # 过滤停用词（简单示例）
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        
        keywords = [word for word in words if word not in stop_words and len(word) > 1]
        
        # 按长度排序，取最重要的关键词
        keywords.sort(key=len, reverse=True)
        
        return keywords[:max_keywords]
    
    def search_by_keyword(self, 
                         keyword: str, 
                         limit: int = 10,
                         offset: int = 0) -> List[Dict]:
        """
        按关键词搜索聊天记录
        
        Args:
            keyword: 关键词
            limit: 返回结果数量
            offset: 偏移量
            
        Returns:
            聊天记录列表
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT cm.*, ki.frequency
                FROM chat_messages cm
                JOIN keyword_index ki ON cm.message_id = ki.message_id
                WHERE ki.keyword = ?
                ORDER BY ki.frequency DESC, cm.timestamp DESC
                LIMIT ? OFFSET ?
            """, (keyword, limit, offset))
            
            results = [dict(row) for row in cursor.fetchall()]
            
            # 解析metadata
            for result in results:
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
            
            return results
            
        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            return []
    
    def search_by_time_range(self,
                            start_date: datetime,
                            end_date: datetime,
                            session_id: Optional[str] = None,
                            limit: int = 20,
                            offset: int = 0) -> List[Dict]:
        """
        按时间范围搜索聊天记录
        
        Args:
            start_date: 开始时间
            end_date: 结束时间
            session_id: 可选的会话ID
            limit: 返回结果数量
            offset: 偏移量
            
        Returns:
            聊天记录列表
        """
        try:
            cursor = self.conn.cursor()
            
            if session_id:
                cursor.execute("""
                    SELECT * FROM chat_messages
                    WHERE timestamp BETWEEN ? AND ?
                    AND session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (start_date.isoformat(), end_date.isoformat(), 
                      session_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM chat_messages
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (start_date.isoformat(), end_date.isoformat(), 
                      limit, offset))
            
            results = [dict(row) for row in cursor.fetchall()]
            
            # 解析metadata
            for result in results:
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
            
            return results
            
        except Exception as e:
            logger.error(f"时间范围搜索失败: {e}")
            return []
    
    def get_recent_messages(self,
                           session_id: Optional[str] = None,
                           limit: int = 10) -> List[Dict]:
        """
        获取最近的聊天记录
        
        Args:
            session_id: 可选的会话ID
            limit: 返回结果数量
            
        Returns:
            聊天记录列表
        """
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
            
            results = [dict(row) for row in cursor.fetchall()]
            
            # 解析metadata
            for result in results:
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
            
            return results
            
        except Exception as e:
            logger.error(f"获取最近消息失败: {e}")
            return []
    
    def get_daily_stats(self, date: datetime) -> Dict[str, Any]:
        """
        获取每日统计信息
        
        Args:
            date: 日期
            
        Returns:
            统计信息字典
        """
        try:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            
            cursor = self.conn.cursor()
            
            # 消息总数
            cursor.execute("""
                SELECT COUNT(*) as total_messages,
                       COUNT(DISTINCT session_id) as total_sessions,
                       SUM(CASE WHEN sender_type = 'user' THEN 1 ELSE 0 END) as user_messages,
                       SUM(CASE WHEN sender_type = 'assistant' THEN 1 ELSE 0 END) as assistant_messages
                FROM chat_messages
                WHERE timestamp BETWEEN ? AND ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            stats = dict(cursor.fetchone())
            
            # 热门关键词
            cursor.execute("""
                SELECT keyword, COUNT(*) as count
                FROM keyword_index ki
                JOIN chat_messages cm ON ki.message_id = cm.message_id
                WHERE cm.timestamp BETWEEN ? AND ?
                GROUP BY keyword
                ORDER BY count DESC
                LIMIT 10
            """, (start_date.isoformat(), end_date.isoformat()))
            
            stats['top_keywords'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
            
        except Exception as e:
            logger.error(f"获取每日统计失败: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 30):
        """
        清理旧数据
        
        Args:
            days: 保留最近多少天的数据
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor = self.conn.cursor()
            
            # 删除旧聊天记录
            cursor.execute("""
                DELETE FROM chat_messages
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            # 删除相关的关键词索引
            cursor.execute("""
                DELETE FROM keyword_index
                WHERE message_id NOT IN (SELECT message_id FROM chat_messages)
            """)
            
            # 删除旧的会话摘要
            cursor.execute("""
                DELETE FROM session_summaries
                WHERE end_time < ?
            """, (cutoff_date.isoformat(),))
            
            self.conn.commit()
            
            # 执行VACUUM回收空间
            cursor.execute("VACUUM")
            
            logger.info(f"已清理{cutoff_date}之前的数据")
            
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            self.conn.rollback()
    
    def optimize_database(self):
        """优化数据库性能"""
        try:
            cursor = self.conn.cursor()
            
            # 重新分析统计信息
            cursor.execute("ANALYZE")
            
            # 重新构建索引
            cursor.execute("REINDEX")
            
            # 更新数据库统计
            cursor.execute("PRAGMA optimize")
            
            self.conn.commit()
            logger.info("数据库优化完成")
            
        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 单例模式，全局共享一个数据库实例
_db_instance = None

def get_database(db_path: Optional[str] = None) -> ChatDatabase:
    """
    获取数据库实例（单例模式）
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        ChatDatabase实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = ChatDatabase(db_path)
    return _db_instance