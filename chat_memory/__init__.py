"""
聊天记录记忆系统
高性能的聊天记忆存储和检索系统
"""

from .database import ChatDatabase, get_database
from .vector_search import VectorSearch, get_vector_search
from .memory_manager import ChatMemoryManager, get_memory_manager
from .scheduler import MemoryScheduler, get_scheduler

__version__ = "1.0.0"
__author__ = "AutoClaw"
__all__ = [
    "ChatDatabase",
    "get_database",
    "VectorSearch", 
    "get_vector_search",
    "ChatMemoryManager",
    "get_memory_manager",
    "MemoryScheduler",
    "get_scheduler"
]
