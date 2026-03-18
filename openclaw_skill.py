#!/usr/bin/env python3
"""
OpenClaw聊天记忆技能
在OpenClaw中激活和使用聊天记忆系统
"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat_memory import get_memory_manager, get_scheduler, get_integration

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatMemorySkill:
    """聊天记忆技能类"""
    
    def __init__(self):
        """初始化技能"""
        self.memory = get_memory_manager()
        self.scheduler = get_scheduler(auto_archive_hour=23)
        self.integration = get_integration()
        
        # 技能配置
        self.config = {
            'skill_name': 'chat-memory-db',
            'version': '1.0.0',
            'description': '高性能聊天记录记忆系统',
            'author': 'AutoClaw',
            'enabled': True,
            'auto_start_scheduler': True,
            'max_memory_context': 5,
            'enable_auto_archive': True
        }
        
        # 技能状态
        self.status = {
            'initialized': False,
            'scheduler_running': False,
            'last_operation': None,
            'error_count': 0
        }
        
        logger.info(f"聊天记忆技能初始化: {self.config['skill_name']} v{self.config['version']}")
    
    def activate(self):
        """激活技能"""
        try:
            logger.info("激活聊天记忆技能...")
            
            # 启动调度器
            if self.config['auto_start_scheduler']:
                self.scheduler.start()
                self.status['scheduler_running'] = True
                logger.info("调度器已启动")
            
            # 更新状态
            self.status['initialized'] = True
            self.status['last_operation'] = datetime.now().isoformat()
            
            logger.info("聊天记忆技能激活完成")
            return True
            
        except Exception as e:
            logger.error(f"激活技能失败: {e}")
            self.status['error_count'] += 1
            return False
    
    def deactivate(self):
        """停用技能"""
        try:
            logger.info("停用聊天记忆技能...")
            
            # 停止调度器
            if self.status['scheduler_running']:
                self.scheduler.stop()
                self.status['scheduler_running'] = False
                logger.info("调度器已停止")
            
            # 清理资源
            self.integration.clear_cache()
            
            logger.info("聊天记忆技能已停用")
            return True
            
        except Exception as e:
            logger.error(f"停用技能失败: {e}")
            return False
    
    def process_message(self, 
                       session_id: str,
                       message: Dict[str, Any],
                       channel: str = "webchat") -> Dict[str, Any]:
        """
        处理消息（OpenClaw技能接口）
        
        Args:
            session_id: 会话ID
            message: 消息字典
            channel: 渠道名称
            
        Returns:
            处理结果
        """
        try:
            # 检查技能是否激活
            if not self.status['initialized']:
                return {
                    'processed': False,
                    'reason': '技能未激活',
                    'original_message': message
                }
            
            # 使用集成器处理消息
            result = self.integration.process_incoming_message(
                session_id=session_id,
                message=message,
                channel=channel
            )
            
            # 更新状态
            self.status['last_operation'] = datetime.now().isoformat()
            
            return {
                'processed': True,
                'skill': self.config['skill_name'],
                'result': result
            }
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            self.status['error_count'] += 1
            
            return {
                'processed': False,
                'error': str(e),
                'original_message': message
            }
    
    def enhance_conversation(self,
                            session_id: str,
                            user_input: str,
                            conversation_history: List[Dict[str, Any]]) -> str:
        """
        增强对话上下文
        
        Args:
            session_id: 会话ID
            user_input: 用户输入
            conversation_history: 对话历史
            
        Returns:
            增强的上下文字符串
        """
        try:
            # 使用集成器增强上下文
            enhanced_context = self.integration.enhance_model_context(
                session_id=session_id,
                user_input=user_input,
                conversation_history=conversation_history
            )
            
            return enhanced_context
            
        except Exception as e:
            logger.error(f"增强对话失败: {e}")
            # 返回原始上下文
            return self._format_history(conversation_history)
    
    def store_conversation(self,
                          session_id: str,
                          user_message: Dict[str, Any],
                          assistant_response: Dict[str, Any],
                          channel: str = "webchat"):
        """
        存储对话
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            assistant_response: 助手回复
            channel: 渠道名称
        """
        try:
            self.integration.store_conversation_turn(
                session_id=session_id,
                user_message=user_message,
                assistant_response=assistant_response,
                channel=channel
            )
            
        except Exception as e:
            logger.error(f"存储对话失败: {e}")
    
    def search_memory(self,
                     query: str,
                     search_type: str = 'hybrid',
                     limit: int = 10,
                     session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        搜索记忆
        
        Args:
            query: 搜索查询
            search_type: 搜索类型
            limit: 返回数量
            session_id: 会话ID
            
        Returns:
            搜索结果
        """
        try:
            results = self.integration.search_chat_history(
                query=query,
                search_type=search_type,
                limit=limit,
                session_id=session_id
            )
            
            return {
                'success': True,
                'query': query,
                'results': results.get('results', []),
                'total': len(results.get('results', [])),
                'search_type': search_type
            }
            
        except Exception as e:
            logger.error(f"搜索记忆失败: {e}")
            return {
                'success': False,
                'query': query,
                'error': str(e),
                'results': []
            }
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话信息
        """
        try:
            # 获取会话摘要
            summary = self.integration.get_session_summary(session_id)
            
            # 获取会话历史
            history = self.memory.get_conversation_history(session_id, limit=20)
            
            return {
                'session_id': session_id,
                'summary': summary,
                'message_count': len(history),
                'history_preview': [{
                    'role': 'user' if msg.get('sender_type') == 'user' else 'assistant',
                    'content': msg.get('content', '')[:100],
                    'timestamp': msg.get('timestamp')
                } for msg in history[:5]]
            }
            
        except Exception as e:
            logger.error(f"获取会话信息失败: {e}")
            return {
                'session_id': session_id,
                'error': str(e)
            }
    
    def run_manual_archive(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        手动运行归档
        
        Args:
            date_str: 日期字符串 (YYYY-MM-DD)
            
        Returns:
            归档结果
        """
        try:
            report = self.scheduler.run_manual_archive(date_str)
            
            if report:
                return {
                    'success': True,
                    'operation': 'manual_archive',
                    'date': report.get('date'),
                    'total_messages': report.get('total_messages', 0),
                    'total_sessions': report.get('total_sessions', 0),
                    'report': report
                }
            else:
                return {
                    'success': False,
                    'operation': 'manual_archive',
                    'error': '归档未生成报告'
                }
                
        except Exception as e:
            logger.error(f"手动归档失败: {e}")
            return {
                'success': False,
                'operation': 'manual_archive',
                'error': str(e)
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            状态信息
        """
        try:
            # 获取记忆系统统计
            memory_stats = self.memory.get_stats()
            
            # 获取调度器状态
            scheduler_status = self.scheduler.get_status()
            
            # 获取集成器统计
            integration_stats = self.integration.get_system_stats()
            
            status = {
                'skill': self.config,
                'status': self.status,
                'memory_system': memory_stats,
                'scheduler': scheduler_status,
                'integration': integration_stats.get('integration', {}),
                'timestamp': datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                'skill': self.config,
                'status': self.status,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def handle_command(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理技能命令
        
        Args:
            command: 命令名称
            args: 命令参数
            
        Returns:
            命令结果
        """
        try:
            if command == 'status':
                return {
                    'command': command,
                    'result': self.get_system_status()
                }
            
            elif command == 'search':
                query = args.get('query', '')
                search_type = args.get('type', 'hybrid')
                limit = args.get('limit', 10)
                session_id = args.get('session_id')
                
                return {
                    'command': command,
                    'result': self.search_memory(query, search_type, limit, session_id)
                }
            
            elif command == 'archive':
                date_str = args.get('date')
                return {
                    'command': command,
                    'result': self.run_manual_archive(date_str)
                }
            
            elif command == 'session_info':
                session_id = args.get('session_id', '')
                return {
                    'command': command,
                    'result': self.get_session_info(session_id)
                }
            
            elif command == 'stats':
                return {
                    'command': command,
                    'result': self.memory.get_stats()
                }
            
            elif command == 'clear_cache':
                self.integration.clear_cache()
                return {
                    'command': command,
                    'result': {'success': True, 'message': '缓存已清理'}
                }
            
            else:
                return {
                    'command': command,
                    'error': f'未知命令: {command}',
                    'available_commands': [
                        'status', 'search', 'archive', 'session_info', 
                        'stats', 'clear_cache'
                    ]
                }
                
        except Exception as e:
            logger.error(f"处理命令失败: {command} - {e}")
            return {
                'command': command,
                'error': str(e)
            }
    
    def _format_history(self, history: List[Dict[str, Any]]) -> str:
        """格式化历史记录"""
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
        
        return "\n".join(formatted)
    
    def __del__(self):
        """析构函数"""
        try:
            self.deactivate()
        except:
            pass


# 全局技能实例
_skill_instance = None

def get_skill() -> ChatMemorySkill:
    """
    获取技能实例（单例模式）
    
    Returns:
        ChatMemorySkill实例
    """
    global _skill_instance
    
    if _skill_instance is None:
        _skill_instance = ChatMemorySkill()
    
    return _skill_instance