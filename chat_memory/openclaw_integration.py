"""
OpenClaw集成模块
将聊天记忆系统集成到OpenClaw工作流中
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import re

from .memory_manager import get_memory_manager

logger = logging.getLogger(__name__)

class OpenClawMemoryIntegration:
    """OpenClaw记忆集成器"""
    
    def __init__(self):
        """初始化集成器"""
        self.memory = get_memory_manager()
        self.session_cache = {}
        
        # 配置
        self.config = {
            'auto_store': True,  # 自动存储对话
            'auto_retrieve': True,  # 自动检索记忆
            'max_context_tokens': 2000,  # 最大上下文token数
            'similarity_threshold': 0.6,  # 相似度阈值
            'max_retrieved_items': 5,  # 最大检索数量
            'enable_vector_search': True,  # 启用向量搜索
            'enable_keyword_search': True,  # 启用关键词搜索
        }
        
        logger.info("OpenClaw记忆集成器初始化完成")
    
    def process_incoming_message(self,
                                session_id: str,
                                message: Dict[str, Any],
                                channel: str = "webchat") -> Dict[str, Any]:
        """
        处理接收到的消息
        
        Args:
            session_id: 会话ID
            message: 消息字典
            channel: 渠道名称
            
        Returns:
            处理后的消息，包含增强的上下文
        """
        try:
            # 提取消息信息
            message_id = message.get('id') or self._generate_message_id(message)
            role = message.get('role', 'user')
            content = message.get('content', '')
            timestamp = message.get('timestamp', datetime.now().isoformat())
            
            # 如果是用户消息，存储到记忆系统
            if role == 'user' and self.config['auto_store']:
                self._store_message(
                    session_id=session_id,
                    message_id=message_id,
                    role=role,
                    content=content,
                    timestamp=timestamp,
                    channel=channel,
                    metadata=message.get('metadata')
                )
            
            # 如果是用户消息，检索相关记忆
            enhanced_context = None
            if role == 'user' and self.config['auto_retrieve']:
                enhanced_context = self._retrieve_and_build_context(
                    session_id=session_id,
                    user_input=content,
                    current_messages=self._get_session_messages(session_id)
                )
            
            # 返回增强的消息
            result = {
                'original_message': message,
                'message_id': message_id,
                'enhanced_context': enhanced_context,
                'has_memory_context': enhanced_context is not None
            }
            
            return result
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return {'original_message': message, 'error': str(e)}
    
    def enhance_model_context(self,
                             session_id: str,
                             user_input: str,
                             conversation_history: List[Dict[str, Any]]) -> str:
        """
        增强模型上下文
        
        Args:
            session_id: 会话ID
            user_input: 用户输入
            conversation_history: 当前会话历史
            
        Returns:
            增强的上下文字符串
        """
        try:
            # 检索相关记忆
            relevant_memories = self._retrieve_relevant_memories(
                session_id=session_id,
                user_input=user_input
            )
            
            if not relevant_memories:
                # 没有相关记忆，返回原始上下文
                return self._format_conversation_history(conversation_history)
            
            # 构建增强上下文
            enhanced_context = self._build_enhanced_context(
                conversation_history=conversation_history,
                relevant_memories=relevant_memories,
                current_query=user_input
            )
            
            logger.debug(f"上下文增强完成，添加 {len(relevant_memories)} 条相关记忆")
            return enhanced_context
            
        except Exception as e:
            logger.error(f"增强上下文失败: {e}")
            return self._format_conversation_history(conversation_history)
    
    def store_conversation_turn(self,
                               session_id: str,
                               user_message: Dict[str, Any],
                               assistant_response: Dict[str, Any],
                               channel: str = "webchat"):
        """
        存储完整的对话轮次
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            assistant_response: 助手回复
            channel: 渠道名称
        """
        try:
            messages = []
            
            # 用户消息
            if user_message:
                user_msg_id = user_message.get('id') or self._generate_message_id(user_message)
                messages.append({
                    'id': user_msg_id,
                    'role': 'user',
                    'content': user_message.get('content', ''),
                    'timestamp': user_message.get('timestamp', datetime.now().isoformat()),
                    'channel': channel,
                    'metadata': user_message.get('metadata')
                })
            
            # 助手回复
            if assistant_response:
                assistant_msg_id = assistant_response.get('id') or self._generate_message_id(assistant_response)
                messages.append({
                    'id': assistant_msg_id,
                    'role': 'assistant',
                    'content': assistant_response.get('content', ''),
                    'timestamp': assistant_response.get('timestamp', datetime.now().isoformat()),
                    'channel': channel,
                    'metadata': {
                        'model': assistant_response.get('model'),
                        'tokens': assistant_response.get('tokens'),
                        'finish_reason': assistant_response.get('finish_reason')
                    }
                })
            
            # 存储到记忆系统
            if messages:
                success = self.memory.store_conversation(session_id, messages)
                if success:
                    logger.debug(f"存储对话轮次: {session_id}, {len(messages)} 条消息")
                else:
                    logger.warning(f"存储对话轮次失败: {session_id}")
            
        except Exception as e:
            logger.error(f"存储对话轮次失败: {e}")
    
    def search_chat_history(self,
                           query: str,
                           search_type: str = 'hybrid',
                           limit: int = 10,
                           session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        搜索聊天历史
        
        Args:
            query: 搜索查询
            search_type: 搜索类型 ('keyword', 'vector', 'hybrid')
            limit: 返回结果数量
            session_id: 可选的会话ID
            
        Returns:
            搜索结果
        """
        try:
            results = self.memory.search_memories(
                query=query,
                search_type=search_type,
                limit=limit
            )
            
            # 如果指定了会话ID，过滤结果
            if session_id and results.get('results'):
                filtered_results = [
                    r for r in results['results']
                    if r.get('session_id') == session_id
                ]
                results['results'] = filtered_results
                results['filtered_by_session'] = session_id
            
            return results
            
        except Exception as e:
            logger.error(f"搜索聊天历史失败: {e}")
            return {'query': query, 'error': str(e), 'results': []}
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话摘要
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话摘要信息
        """
        try:
            return self.memory.summarize_session(session_id)
        except Exception as e:
            logger.error(f"获取会话摘要失败: {e}")
            return None
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            统计信息字典
        """
        try:
            stats = self.memory.get_stats()
            
            # 添加集成器特定统计
            stats['integration'] = {
                'session_cache_size': len(self.session_cache),
                'config': self.config,
                'timestamp': datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {}
    
    # 私有方法
    
    def _store_message(self,
                      session_id: str,
                      message_id: str,
                      role: str,
                      content: str,
                      timestamp: str,
                      channel: str,
                      metadata: Optional[Dict] = None):
        """存储单条消息"""
        try:
            sender_type = 'user' if role == 'user' else 'assistant'
            
            # 解析时间戳
            if isinstance(timestamp, str):
                from datetime import datetime
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # 存储到数据库
            success = self.memory.db.store_message(
                session_id=session_id,
                message_id=message_id,
                sender_type=sender_type,
                content=content,
                timestamp=timestamp,
                channel=channel,
                metadata=metadata
            )
            
            # 如果是用户消息，添加到向量索引
            if success and role == 'user' and self.config['enable_vector_search']:
                self.memory.vector_search.add_to_index(message_id, content)
            
            return success
            
        except Exception as e:
            logger.error(f"存储消息失败: {e}")
            return False
    
    def _retrieve_relevant_memories(self,
                                   session_id: str,
                                   user_input: str) -> List[Dict[str, Any]]:
        """检索相关记忆"""
        try:
            relevant_memories = []
            
            # 向量搜索
            if self.config['enable_vector_search']:
                vector_results = self.memory.retrieve_context(
                    query=user_input,
                    session_id=session_id,
                    limit=self.config['max_retrieved_items']
                )
                relevant_memories.extend(vector_results)
            
            # 关键词搜索
            if self.config['enable_keyword_search'] and len(relevant_memories) < self.config['max_retrieved_items']:
                # 提取关键词
                keywords = self._extract_keywords(user_input)
                
                for keyword in keywords[:3]:  # 使用前3个关键词
                    keyword_results = self.memory.db.search_by_keyword(
                        keyword=keyword,
                        limit=3
                    )
                    
                    # 过滤当前会话的结果
                    filtered_results = [
                        r for r in keyword_results
                        if r.get('session_id') == session_id
                    ]
                    
                    relevant_memories.extend(filtered_results)
            
            # 去重和排序
            unique_memories = []
            seen_ids = set()
            
            for memory in relevant_memories:
                msg_id = memory.get('message_id')
                if msg_id and msg_id not in seen_ids:
                    seen_ids.add(msg_id)
                    unique_memories.append(memory)
            
            # 按相关性排序
            unique_memories.sort(key=lambda x: (
                x.get('similarity', 0) if x.get('similarity') else 0,
                x.get('timestamp', '')
            ), reverse=True)
            
            # 限制数量
            return unique_memories[:self.config['max_retrieved_items']]
            
        except Exception as e:
            logger.error(f"检索相关记忆失败: {e}")
            return []
    
    def _build_enhanced_context(self,
                               conversation_history: List[Dict[str, Any]],
                               relevant_memories: List[Dict[str, Any]],
                               current_query: str) -> str:
        """构建增强上下文"""
        try:
            # 格式化当前对话历史
            history_text = self._format_conversation_history(conversation_history)
            
            # 格式化相关记忆
            memories_text = "相关历史记忆:\n"
            for i, memory in enumerate(relevant_memories, 1):
                role = "用户" if memory.get('sender_type') == 'user' else "助手"
                content = memory.get('content', '')
                timestamp = memory.get('timestamp', '')
                
                # 格式化时间
                if timestamp:
                    if isinstance(timestamp, str):
                        timestamp = timestamp[:19]  # 保留到秒
                
                memories_text += f"{i}. [{role}] {content}\n"
                if timestamp:
                    memories_text += f"   时间: {timestamp}\n"
                
                # 添加相似度（如果有）
                similarity = memory.get('similarity')
                if similarity:
                    memories_text += f"   相关性: {similarity:.2f}\n"
                
                memories_text += "\n"
            
            # 构建完整上下文
            enhanced_context = f"""当前对话历史:
{history_text}

{memories_text}

当前用户问题:
{current_query}

请基于以上对话历史和相关信息回答用户问题。"""
            
            return enhanced_context
            
        except Exception as e:
            logger.error(f"构建增强上下文失败: {e}")
            return self._format_conversation_history(conversation_history)
    
    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        if not history:
            return "无对话历史"
        
        formatted = []
        for msg in history[-10:]:  # 只保留最近10条
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            if role == 'user':
                formatted.append(f"用户: {content}")
            elif role == 'assistant':
                formatted.append(f"助手: {content}")
            else:
                formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话消息（带缓存）"""
        try:
            # 检查缓存
            cache_key = f"session_messages_{session_id}"
            if cache_key in self.session_cache:
                return self.session_cache[cache_key]
            
            # 从数据库获取
            messages = self.memory.get_conversation_history(session_id, limit=50)
            
            # 缓存结果
            self.session_cache[cache_key] = messages
            
            return messages
            
        except Exception as e:
            logger.error(f"获取会话消息失败: {e}")
            return []
    
    def _generate_message_id(self, message: Dict[str, Any]) -> str:
        """生成消息ID"""
        import hashlib
        import time
        
        content = message.get('content', '')
        timestamp = message.get('timestamp', str(time.time()))
        
        hash_input = f"{content}_{timestamp}".encode('utf-8')
        message_hash = hashlib.md5(hash_input).hexdigest()[:12]
        
        return f"msg_{message_hash}"
    
    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """提取关键词"""
        # 简单的中文关键词提取
        import re
        
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
        
        # 按长度排序
        keywords.sort(key=len, reverse=True)
        
        return keywords[:max_keywords]
    
    def clear_cache(self):
        """清理缓存"""
        self.session_cache = {}
        logger.info("集成器缓存已清理")


# 全局集成器实例
_integration_instance = None

def get_integration() -> OpenClawMemoryIntegration:
    """
    获取集成器实例（单例模式）
    
    Returns:
        OpenClawMemoryIntegration实例
    """
    global _integration_instance
    
    if _integration_instance is None:
        _integration_instance = OpenClawMemoryIntegration()
    
    return _integration_instance