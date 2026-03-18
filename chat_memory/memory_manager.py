"""
记忆管理器主类
整合数据库和向量搜索，提供完整的聊天记忆功能
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import hashlib
import re

from .database import get_database
from .vector_search import get_vector_search

logger = logging.getLogger(__name__)

class ChatMemoryManager:
    """聊天记忆管理器"""
    
    def __init__(self, 
                 db_path: Optional[str] = None,
                 vector_model: str = "all-MiniLM-L6-v2"):
        """
        初始化记忆管理器
        
        Args:
            db_path: 数据库文件路径
            vector_model: 向量模型名称
        """
        self.db = get_database(db_path)
        self.vector_search = get_vector_search(vector_model)
        
        # 配置参数
        self.config = {
            'max_context_length': 2000,  # 最大上下文长度
            'similarity_threshold': 0.6,  # 向量相似度阈值
            'max_retrieved_items': 10,    # 最大检索数量
            'cache_ttl': 300,             # 缓存TTL（秒）
            'auto_archive_hour': 23,      # 自动归档时间（小时）
        }
        
        # 内存缓存
        self.cache = {}
        
        logger.info("聊天记忆管理器初始化完成")
    
    def store_conversation(self, 
                          session_id: str,
                          messages: List[Dict[str, Any]]) -> bool:
        """
        存储完整对话
        
        Args:
            session_id: 会话ID
            messages: 消息列表
            
        Returns:
            是否存储成功
        """
        try:
            success_count = 0
            
            for msg in messages:
                message_id = msg.get('id') or self._generate_message_id(msg)
                
                # 提取必要字段
                sender_type = 'user' if msg.get('role') == 'user' else 'assistant'
                content = msg.get('content', '')
                timestamp = msg.get('timestamp')
                
                if timestamp:
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                # 存储到数据库
                success = self.db.store_message(
                    session_id=session_id,
                    message_id=message_id,
                    sender_type=sender_type,
                    content=content,
                    timestamp=timestamp,
                    channel=msg.get('channel'),
                    metadata={
                        'role': msg.get('role'),
                        'model': msg.get('model'),
                        'tokens': msg.get('tokens')
                    }
                )
                
                if success and sender_type == 'user':
                    # 添加到向量索引
                    self.vector_search.add_to_index(message_id, content)
                    success_count += 1
            
            logger.info(f"存储对话完成，成功 {success_count}/{len(messages)} 条消息")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"存储对话失败: {e}")
            return False
    
    def retrieve_context(self, 
                        query: str,
                        session_id: Optional[str] = None,
                        limit: int = 5) -> List[Dict[str, Any]]:
        """
        检索相关上下文
        
        Args:
            query: 查询文本
            session_id: 可选的会话ID
            limit: 返回结果数量
            
        Returns:
            相关上下文列表
        """
        try:
            # 1. 向量搜索（语义相似度）
            vector_results = self.vector_search.search_similar(
                query=query,
                top_k=limit,
                threshold=self.config['similarity_threshold']
            )
            
            # 2. 关键词搜索
            keywords = self._extract_keywords(query)
            keyword_results = []
            
            for keyword in keywords[:3]:  # 只使用前3个关键词
                results = self.db.search_by_keyword(keyword, limit=3)
                keyword_results.extend(results)
            
            # 3. 合并和去重
            all_results = []
            seen_ids = set()
            
            # 添加向量搜索结果
            for result in vector_results:
                msg_id = result['message_id']
                if msg_id not in seen_ids:
                    # 获取完整消息信息
                    full_msg = self._get_message_by_id(msg_id)
                    if full_msg:
                        full_msg['similarity'] = result['similarity']
                        full_msg['search_type'] = 'vector'
                        all_results.append(full_msg)
                        seen_ids.add(msg_id)
            
            # 添加关键词搜索结果
            for result in keyword_results:
                msg_id = result['message_id']
                if msg_id not in seen_ids:
                    result['search_type'] = 'keyword'
                    all_results.append(result)
                    seen_ids.add(msg_id)
            
            # 4. 按相关性排序
            all_results.sort(key=lambda x: (
                x.get('similarity', 0) if x.get('search_type') == 'vector' else 0,
                x.get('timestamp', '')
            ), reverse=True)
            
            # 5. 限制数量
            final_results = all_results[:self.config['max_retrieved_items']]
            
            logger.debug(f"检索到 {len(final_results)} 条相关上下文")
            return final_results
            
        except Exception as e:
            logger.error(f"检索上下文失败: {e}")
            return []
    
    def get_conversation_history(self,
                                session_id: str,
                                limit: int = 20,
                                offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取会话历史
        
        Args:
            session_id: 会话ID
            limit: 返回结果数量
            offset: 偏移量
            
        Returns:
            会话历史列表
        """
        try:
            # 获取最近的消息
            results = self.db.get_recent_messages(session_id=session_id, limit=limit)
            
            # 按时间排序
            results.sort(key=lambda x: x.get('timestamp', ''))
            
            return results
            
        except Exception as e:
            logger.error(f"获取会话历史失败: {e}")
            return []
    
    def summarize_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        生成会话摘要
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话摘要信息
        """
        try:
            # 获取会话所有消息
            messages = self.get_conversation_history(session_id, limit=1000)
            
            if not messages:
                return None
            
            # 提取关键信息
            user_messages = [m for m in messages if m.get('sender_type') == 'user']
            assistant_messages = [m for m in messages if m.get('sender_type') == 'assistant']
            
            # 提取主题
            topics = self._extract_topics(messages)
            
            # 生成简单摘要
            summary = self._generate_summary(messages)
            
            # 计算时间范围
            timestamps = [m.get('timestamp') for m in messages if m.get('timestamp')]
            if timestamps:
                start_time = min(timestamps)
                end_time = max(timestamps)
            else:
                start_time = end_time = datetime.now()
            
            session_summary = {
                'session_id': session_id,
                'start_time': start_time,
                'end_time': end_time,
                'message_count': len(messages),
                'user_message_count': len(user_messages),
                'assistant_message_count': len(assistant_messages),
                'topics': topics,
                'summary': summary,
                'created_at': datetime.now().isoformat()
            }
            
            # 存储到数据库
            self._store_session_summary(session_summary)
            
            logger.info(f"生成会话摘要: {session_id}")
            return session_summary
            
        except Exception as e:
            logger.error(f"生成会话摘要失败: {e}")
            return None
    
    def daily_archive(self, date: Optional[datetime] = None):
        """
        每日归档
        
        Args:
            date: 归档日期，默认为昨天
        """
        try:
            if date is None:
                date = datetime.now() - timedelta(days=1)
            
            logger.info(f"开始每日归档: {date.date()}")
            
            # 1. 获取当日统计
            stats = self.db.get_daily_stats(date)
            
            # 2. 获取当日所有会话
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            
            # 获取当日所有消息
            daily_messages = self.db.search_by_time_range(start_date, end_date, limit=10000)
            
            # 按会话分组
            sessions = {}
            for msg in daily_messages:
                session_id = msg.get('session_id')
                if session_id:
                    if session_id not in sessions:
                        sessions[session_id] = []
                    sessions[session_id].append(msg)
            
            # 3. 为每个会话生成摘要
            session_summaries = []
            for session_id, messages in sessions.items():
                summary = self.summarize_session(session_id)
                if summary:
                    session_summaries.append(summary)
            
            # 4. 更新向量索引
            self._update_vector_index(daily_messages)
            
            # 5. 生成归档报告
            archive_report = {
                'date': date.isoformat(),
                'total_messages': stats.get('total_messages', 0),
                'total_sessions': stats.get('total_sessions', 0),
                'session_summaries': session_summaries,
                'top_keywords': stats.get('top_keywords', []),
                'archived_at': datetime.now().isoformat()
            }
            
            # 6. 保存归档报告
            self._save_archive_report(archive_report)
            
            # 7. 清理临时数据
            self._cleanup_temporary_data()
            
            logger.info(f"每日归档完成: {date.date()}")
            return archive_report
            
        except Exception as e:
            logger.error(f"每日归档失败: {e}")
            return None
    
    def search_memories(self,
                       query: str,
                       search_type: str = 'hybrid',
                       limit: int = 10) -> Dict[str, Any]:
        """
        搜索记忆
        
        Args:
            query: 查询文本
            search_type: 搜索类型 ('keyword', 'vector', 'hybrid')
            limit: 返回结果数量
            
        Returns:
            搜索结果
        """
        try:
            results = {
                'query': query,
                'search_type': search_type,
                'timestamp': datetime.now().isoformat(),
                'results': []
            }
            
            if search_type in ['keyword', 'hybrid']:
                # 关键词搜索
                keywords = self._extract_keywords(query)
                keyword_results = []
                
                for keyword in keywords[:5]:
                    items = self.db.search_by_keyword(keyword, limit=5)
                    for item in items:
                        item['matched_keyword'] = keyword
                        item['search_score'] = 1.0
                    keyword_results.extend(items)
                
                # 去重和排序
                keyword_dict = {}
                for item in keyword_results:
                    msg_id = item['message_id']
                    if msg_id not in keyword_dict:
                        keyword_dict[msg_id] = item
                    else:
                        # 合并匹配的关键词
                        existing = keyword_dict[msg_id]
                        if 'matched_keywords' not in existing:
                            existing['matched_keywords'] = [existing.get('matched_keyword')]
                            del existing['matched_keyword']
                        existing['matched_keywords'].append(item.get('matched_keyword'))
                        existing['search_score'] += 1.0
                
                keyword_results = list(keyword_dict.values())
                keyword_results.sort(key=lambda x: x.get('search_score', 0), reverse=True)
                
                if search_type == 'keyword':
                    results['results'] = keyword_results[:limit]
                    return results
            
            if search_type in ['vector', 'hybrid']:
                # 向量搜索
                vector_results = self.vector_search.search_similar(
                    query=query,
                    top_k=limit * 2,
                    threshold=0.4
                )
                
                # 获取完整消息信息
                vector_items = []
                for vec_result in vector_results:
                    msg_id = vec_result['message_id']
                    full_msg = self._get_message_by_id(msg_id)
                    if full_msg:
                        full_msg['similarity'] = vec_result['similarity']
                        full_msg['search_score'] = vec_result['similarity']
                        vector_items.append(full_msg)
                
                if search_type == 'vector':
                    results['results'] = vector_items[:limit]
                    return results
            
            # 混合搜索：合并结果
            if search_type == 'hybrid':
                # 合并去重
                all_items = {}
                
                # 添加关键词结果
                for item in keyword_results[:limit]:
                    msg_id = item['message_id']
                    all_items[msg_id] = {
                        'item': item,
                        'score': item.get('search_score', 0),
                        'type': 'keyword'
                    }
                
                # 添加向量结果
                for item in vector_items[:limit]:
                    msg_id = item['message_id']
                    if msg_id in all_items:
                        # 合并分数
                        existing = all_items[msg_id]
                        existing['score'] = (existing['score'] + item.get('search_score', 0)) / 2
                        existing['type'] = 'hybrid'
                    else:
                        all_items[msg_id] = {
                            'item': item,
                            'score': item.get('search_score', 0),
                            'type': 'vector'
                        }
                
                # 按分数排序
                sorted_items = sorted(all_items.values(), key=lambda x: x['score'], reverse=True)
                results['results'] = [item['item'] for item in sorted_items[:limit]]
            
            return results
            
        except Exception as e:
            logger.error(f"搜索记忆失败: {e}")
            return {'query': query, 'error': str(e), 'results': []}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            统计信息字典
        """
        try:
            # 数据库统计
            db_stats = {
                'total_messages': self._count_messages(),
                'total_sessions': self._count_sessions(),
                'db_size': self._get_database_size(),
            }
            
            # 向量索引统计
            vector_stats = self.vector_search.get_stats()
            
            # 性能统计
            perf_stats = {
                'cache_size': len(self.cache),
                'config': self.config
            }
            
            stats = {
                'database': db_stats,
                'vector_search': vector_stats,
                'performance': perf_stats,
                'timestamp': datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    # 私有方法
    
    def _generate_message_id(self, message: Dict[str, Any]) -> str:
        """生成消息ID"""
        content = message.get('content', '')
        timestamp = message.get('timestamp', datetime.now().isoformat())
        
        # 使用内容和时间戳生成哈希ID
        hash_input = f"{content}_{timestamp}".encode('utf-8')
        message_hash = hashlib.md5(hash_input).hexdigest()[:16]
        
        return f"msg_{message_hash}"
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """提取关键词"""
        # 移除标点符号
        text = re.sub(r'[^\w\u4e00-\u9fff]+', ' ', text)
        
        # 分割单词
        words = text.split()
        
        # 中文停用词
        stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
            '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
            '没有', '看', '好', '自己', '这', '那', '就', '都', '还', '又', '什么'
        }
        
        keywords = [word for word in words 
                   if word not in stop_words 
                   and len(word) > 1 
                   and not word.isdigit()]
        
        # 按长度排序，取最重要的关键词
        keywords.sort(key=len, reverse=True)
        
        return keywords[:max_keywords]
    
    def _extract_topics(self, messages: List[Dict[str, Any]], max_topics: int = 5) -> List[str]:
        """提取主题"""
        # 收集所有用户消息
        user_texts = []
        for msg in messages:
            if msg.get('sender_type') == 'user':
                content = msg.get('content', '')
                if len(content) > 10:  # 只处理较长的消息
                    user_texts.append(content)
        
        if not user_texts:
            return []
        
        # 合并所有文本
        all_text = ' '.join(user_texts)
        
        # 提取关键词作为主题
        topics = self._extract_keywords(all_text, max_keywords=max_topics * 2)
        
        # 过滤掉太短的关键词
        topics = [t for t in topics if len(t) >= 2]
        
        return topics[:max_topics]
    
    def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """生成摘要"""
        if not messages:
            return "无聊天记录"
        
        # 提取用户的主要问题
        user_questions = []
        for msg in messages:
            if msg.get('sender_type') == 'user':
                content = msg.get('content', '')
                if '?' in content or '？' in content or len(content) > 20:
                    user_questions.append(content[:100])  # 截断
        
        if user_questions:
            questions_text = '；'.join(user_questions[:3])
            return f"讨论了: {questions_text}"
        
        # 如果没有明显的问题，使用第一个用户消息
        for msg in messages:
            if msg.get('sender_type') == 'user':
                content = msg.get('content', '')[:50]
                return f"对话内容: {content}..."
        
        return "常规对话"
    
    def _store_session_summary(self, summary: Dict[str, Any]) -> bool:
        """存储会话摘要"""
        try:
            cursor = self.db.conn.cursor()
            
            # 检查是否已存在
            cursor.execute("""
                SELECT session_id FROM session_summaries 
                WHERE session_id = ?
            """, (summary['session_id'],))
            
            if cursor.fetchone():
                # 更新
                cursor.execute("""
                    UPDATE session_summaries 
                    SET end_time = ?, message_count = ?, topics = ?, summary = ?
                    WHERE session_id = ?
                """, (
                    summary['end_time'].isoformat() if isinstance(summary['end_time'], datetime) else summary['end_time'],
                    summary['message_count'],
                    json.dumps(summary['topics'], ensure_ascii=False),
                    summary['summary'],
                    summary['session_id']
                ))
            else:
                # 插入
                cursor.execute("""
                    INSERT INTO session_summaries 
                    (session_id, start_time, end_time, message_count, topics, summary)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    summary['session_id'],
                    summary['start_time'].isoformat() if isinstance(summary['start_time'], datetime) else summary['start_time'],
                    summary['end_time'].isoformat() if isinstance(summary['end_time'], datetime) else summary['end_time'],
                    summary['message_count'],
                    json.dumps(summary['topics'], ensure_ascii=False),
                    summary['summary']
                ))
            
            self.db.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"存储会话摘要失败: {e}")
            self.db.conn.rollback()
            return False
    
    def _get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取消息"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT * FROM chat_messages 
                WHERE message_id = ?
            """, (message_id,))
            
            row = cursor.fetchone()
            if row:
                result = dict(row)
                if result.get('metadata'):
                    result['metadata'] = json.loads(result['metadata'])
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return None
    
    def _update_vector_index(self, messages: List[Dict[str, Any]]):
        """更新向量索引"""
        try:
            # 准备数据
            vector_data = []
            for msg in messages:
                if msg.get('sender_type') == 'user':
                    vector_data.append({
                        'message_id': msg['message_id'],
                        'text': msg['content']
                    })
            
            # 批量添加到向量索引
            if vector_data:
                self.vector_search.batch_add(vector_data)
                self.vector_search.save_index()
                
        except Exception as e:
            logger.error(f"更新向量索引失败: {e}")
    
    def _save_archive_report(self, report: Dict[str, Any]):
        """保存归档报告"""
        try:
            # 保存到文件
            base_dir = os.path.expanduser("~/.openclaw-autoclaw/data/archives")
            os.makedirs(base_dir, exist_ok=True)
            
            date_str = report['date'][:10]  # YYYY-MM-DD
            file_path = os.path.join(base_dir, f"archive_{date_str}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"归档报告已保存: {file_path}")
            
        except Exception as e:
            logger.error(f"保存归档报告失败: {e}")
    
    def _cleanup_temporary_data(self):
        """清理临时数据"""
        try:
            # 清理30天前的数据
            self.db.cleanup_old_data(days=30)
            
            # 清理缓存
            self.cache = {}
            
            # 优化数据库
            self.db.optimize_database()
            
            logger.info("临时数据清理完成")
            
        except Exception as e:
            logger.error(f"清理临时数据失败: {e}")
    
    def _count_messages(self) -> int:
        """统计消息总数"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM chat_messages")
            result = cursor.fetchone()
            return result['count'] if result else 0
        except:
            return 0
    
    def _count_sessions(self) -> int:
        """统计会话总数"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT session_id) as count FROM chat_messages")
            result = cursor.fetchone()
            return result['count'] if result else 0
        except:
            return 0
    
    def _get_database_size(self) -> int:
        """获取数据库文件大小"""
        try:
            if os.path.exists(self.db.db_path):
                return os.path.getsize(self.db.db_path)
            return 0
        except:
            return 0


# 全局记忆管理器实例
_memory_manager_instance = None

def get_memory_manager(db_path: Optional[str] = None,
                      vector_model: str = "all-MiniLM-L6-v2") -> ChatMemoryManager:
    """
    获取记忆管理器实例（单例模式）
    
    Args:
        db_path: 数据库文件路径
        vector_model: 向量模型名称
        
    Returns:
        ChatMemoryManager实例
    """
    global _memory_manager_instance
    
    if _memory_manager_instance is None:
        _memory_manager_instance = ChatMemoryManager(db_path, vector_model)
    
    return _memory_manager_instance