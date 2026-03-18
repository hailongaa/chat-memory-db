"""
向量搜索模块
使用sentence-transformers生成文本向量，使用FAISS进行相似度搜索
"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
import pickle
import os
from datetime import datetime
import json

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_VECTOR_DEPS = True
except ImportError:
    HAS_VECTOR_DEPS = False
    logging.warning("向量搜索依赖未安装，请运行: pip install sentence-transformers faiss-cpu")

logger = logging.getLogger(__name__)

class VectorSearch:
    """向量搜索管理器"""
    
    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 index_path: Optional[str] = None,
                 dimension: int = 384):
        """
        初始化向量搜索
        
        Args:
            model_name: 句子转换模型名称
            index_path: FAISS索引文件路径
            dimension: 向量维度
        """
        self.model_name = model_name
        self.dimension = dimension
        self.index_path = index_path
        
        # 初始化模型
        self.model = None
        self.index = None
        self.id_to_message = {}  # 向量ID到消息的映射
        self.message_to_id = {}  # 消息到向量ID的映射
        
        if HAS_VECTOR_DEPS:
            self._init_model()
            self._init_index()
        else:
            logger.warning("向量搜索功能不可用，请安装依赖")
    
    def _init_model(self):
        """初始化句子转换模型"""
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"加载向量模型: {self.model_name}")
        except Exception as e:
            logger.error(f"加载向量模型失败: {e}")
            self.model = None
    
    def _init_index(self):
        """初始化FAISS索引"""
        try:
            if self.index_path and os.path.exists(self.index_path):
                # 从文件加载索引
                self.index = faiss.read_index(self.index_path)
                
                # 加载映射文件
                map_path = self.index_path.replace('.index', '_map.json')
                if os.path.exists(map_path):
                    with open(map_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.id_to_message = data.get('id_to_message', {})
                        self.message_to_id = data.get('message_to_id', {})
                
                logger.info(f"从文件加载FAISS索引: {self.index_path}")
            else:
                # 创建新索引
                self.index = faiss.IndexFlatIP(self.dimension)  # 内积相似度
                logger.info(f"创建新的FAISS索引，维度: {self.dimension}")
                
        except Exception as e:
            logger.error(f"初始化FAISS索引失败: {e}")
            self.index = faiss.IndexFlatIP(self.dimension)
    
    def encode_text(self, text: str) -> Optional[np.ndarray]:
        """
        将文本编码为向量
        
        Args:
            text: 文本内容
            
        Returns:
            向量数组或None
        """
        if not self.model or not text:
            return None
        
        try:
            # 编码文本
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # 归一化向量（用于内积相似度）
            embedding = embedding / np.linalg.norm(embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"文本编码失败: {e}")
            return None
    
    def add_to_index(self, message_id: str, text: str, embedding: Optional[np.ndarray] = None) -> bool:
        """
        添加文本到向量索引
        
        Args:
            message_id: 消息ID
            text: 文本内容
            embedding: 可选的预计算向量
            
        Returns:
            是否添加成功
        """
        if not self.index:
            return False
        
        try:
            # 如果消息已存在，先删除
            if message_id in self.message_to_id:
                self.remove_from_index(message_id)
            
            # 获取向量
            if embedding is None:
                embedding = self.encode_text(text)
            
            if embedding is None:
                return False
            
            # 添加到FAISS索引
            vector_id = self.index.ntotal
            self.index.add(embedding.reshape(1, -1))
            
            # 更新映射
            self.id_to_message[str(vector_id)] = {
                'message_id': message_id,
                'text': text,
                'added_at': datetime.now().isoformat()
            }
            self.message_to_id[message_id] = vector_id
            
            logger.debug(f"添加到向量索引: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加到向量索引失败: {e}")
            return False
    
    def remove_from_index(self, message_id: str) -> bool:
        """
        从向量索引中移除消息
        
        Args:
            message_id: 消息ID
            
        Returns:
            是否移除成功
        """
        if not self.index or message_id not in self.message_to_id:
            return False
        
        try:
            # FAISS不支持直接删除，标记为删除
            vector_id = self.message_to_id[message_id]
            
            # 从映射中移除
            del self.id_to_message[str(vector_id)]
            del self.message_to_id[message_id]
            
            logger.debug(f"从向量索引移除: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"从向量索引移除失败: {e}")
            return False
    
    def search_similar(self, 
                      query: str, 
                      top_k: int = 5,
                      threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        搜索相似的文本
        
        Args:
            query: 查询文本
            top_k: 返回最相似的数量
            threshold: 相似度阈值
            
        Returns:
            相似结果列表
        """
        if not self.index or not self.model:
            return []
        
        try:
            # 编码查询文本
            query_embedding = self.encode_text(query)
            if query_embedding is None:
                return []
            
            # 搜索相似向量
            distances, indices = self.index.search(
                query_embedding.reshape(1, -1), 
                min(top_k * 2, self.index.ntotal)  # 搜索更多结果用于过滤
            )
            
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:  # FAISS返回-1表示没有结果
                    continue
                
                # 检查向量是否有效
                idx_str = str(idx)
                if idx_str not in self.id_to_message:
                    continue
                
                # 检查相似度阈值
                if distance < threshold:
                    continue
                
                message_info = self.id_to_message[idx_str]
                results.append({
                    'message_id': message_info['message_id'],
                    'text': message_info['text'],
                    'similarity': float(distance),
                    'rank': i + 1
                })
                
                if len(results) >= top_k:
                    break
            
            # 按相似度排序
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []
    
    def batch_add(self, messages: List[Dict[str, Any]]) -> int:
        """
        批量添加消息到向量索引
        
        Args:
            messages: 消息列表，每个消息包含message_id和text
            
        Returns:
            成功添加的数量
        """
        if not self.index or not self.model:
            return 0
        
        try:
            texts = []
            valid_messages = []
            
            # 准备数据
            for msg in messages:
                message_id = msg.get('message_id')
                text = msg.get('text')
                
                if message_id and text and message_id not in self.message_to_id:
                    texts.append(text)
                    valid_messages.append(msg)
            
            if not texts:
                return 0
            
            # 批量编码
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            
            # 归一化
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms
            
            # 批量添加到索引
            start_id = self.index.ntotal
            self.index.add(embeddings)
            
            # 更新映射
            added_count = 0
            for i, msg in enumerate(valid_messages):
                vector_id = start_id + i
                
                self.id_to_message[str(vector_id)] = {
                    'message_id': msg['message_id'],
                    'text': msg['text'],
                    'added_at': datetime.now().isoformat()
                }
                self.message_to_id[msg['message_id']] = vector_id
                added_count += 1
            
            logger.info(f"批量添加 {added_count} 条消息到向量索引")
            return added_count
            
        except Exception as e:
            logger.error(f"批量添加失败: {e}")
            return 0
    
    def rebuild_index(self, messages: List[Dict[str, Any]]) -> bool:
        """
        重建向量索引
        
        Args:
            messages: 所有消息列表
            
        Returns:
            是否重建成功
        """
        try:
            # 创建新索引
            self.index = faiss.IndexFlatIP(self.dimension)
            self.id_to_message = {}
            self.message_to_id = {}
            
            # 批量添加
            added = self.batch_add(messages)
            
            logger.info(f"重建向量索引完成，添加 {added} 条消息")
            return added > 0
            
        except Exception as e:
            logger.error(f"重建向量索引失败: {e}")
            return False
    
    def save_index(self, path: Optional[str] = None):
        """
        保存向量索引到文件
        
        Args:
            path: 保存路径
        """
        if not self.index:
            return
        
        try:
            save_path = path or self.index_path
            if not save_path:
                logger.warning("未指定索引保存路径")
                return
            
            # 保存FAISS索引
            faiss.write_index(self.index, save_path)
            
            # 保存映射
            map_path = save_path.replace('.index', '_map.json')
            map_data = {
                'id_to_message': self.id_to_message,
                'message_to_id': self.message_to_id,
                'saved_at': datetime.now().isoformat(),
                'total_vectors': self.index.ntotal
            }
            
            with open(map_path, 'w', encoding='utf-8') as f:
                json.dump(map_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"向量索引已保存到: {save_path}")
            
        except Exception as e:
            logger.error(f"保存向量索引失败: {e}")
    
    def load_index(self, path: str) -> bool:
        """
        从文件加载向量索引
        
        Args:
            path: 索引文件路径
            
        Returns:
            是否加载成功
        """
        try:
            if not os.path.exists(path):
                logger.warning(f"索引文件不存在: {path}")
                return False
            
            # 加载FAISS索引
            self.index = faiss.read_index(path)
            
            # 加载映射
            map_path = path.replace('.index', '_map.json')
            if os.path.exists(map_path):
                with open(map_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.id_to_message = data.get('id_to_message', {})
                    self.message_to_id = data.get('message_to_id', {})
            
            self.index_path = path
            logger.info(f"向量索引已加载，包含 {self.index.ntotal} 个向量")
            return True
            
        except Exception as e:
            logger.error(f"加载向量索引失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取向量索引统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'has_model': self.model is not None,
            'has_index': self.index is not None,
            'total_vectors': self.index.ntotal if self.index else 0,
            'total_messages': len(self.message_to_id),
            'model_name': self.model_name,
            'dimension': self.dimension
        }
        return stats
    
    def cleanup(self):
        """清理资源"""
        if self.model:
            # 释放模型资源
            pass
        
        if self.index:
            # 保存索引
            if self.index_path:
                self.save_index(self.index_path)


# 全局向量搜索实例
_vector_search_instance = None

def get_vector_search(model_name: str = "all-MiniLM-L6-v2",
                     index_path: Optional[str] = None) -> VectorSearch:
    """
    获取向量搜索实例（单例模式）
    
    Args:
        model_name: 模型名称
        index_path: 索引文件路径
        
    Returns:
        VectorSearch实例
    """
    global _vector_search_instance
    
    if _vector_search_instance is None:
        if index_path is None:
            # 默认索引路径
            base_dir = os.path.expanduser("~/.openclaw-autoclaw/data")
            os.makedirs(base_dir, exist_ok=True)
            index_path = os.path.join(base_dir, "vector_index.index")
        
        _vector_search_instance = VectorSearch(
            model_name=model_name,
            index_path=index_path
        )
    
    return _vector_search_instance