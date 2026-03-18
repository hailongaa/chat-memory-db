# Chat Memory Database Skill

## 概述
这是一个高性能的聊天记录记忆系统，使用数据库存储聊天记录，支持亿级数据秒查询，每天23点自动归档，对话时智能检索记忆。

## 核心特性
1. **高性能存储**: 使用SQLite + 向量索引，支持亿级数据秒级查询
2. **自动归档**: 每天23点自动将当天聊天数据归类存储至数据库
3. **智能检索**: 对话时根据上下文自动检索相关记忆
4. **语义搜索**: 支持向量相似度搜索，找到最相关的历史对话
5. **增量索引**: 实时更新向量索引，保证查询性能

## 技术架构
```
┌─────────────────────────────────────────────────────────────┐
│                     Chat Memory System                       │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: 会话层 (Session Layer)                            │
│    • 实时聊天记录捕获                                        │
│    • 上下文提取与预处理                                      │
│    • 语义向量生成                                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 存储层 (Storage Layer)                            │
│    • SQLite 数据库 (主存储)                                 │
│    • FAISS 向量索引 (语义搜索)                              │
│    • 分区表设计 (按日期分区)                                │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 检索层 (Retrieval Layer)                          │
│    • 关键词匹配                                             │
│    • 向量相似度搜索                                         │
│    • 混合检索策略                                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: 调度层 (Scheduler Layer)                          │
│    • 每日23点自动归档                                       │
│    • 增量索引构建                                           │
│    • 数据清理与优化                                         │
└─────────────────────────────────────────────────────────────┘
```

## 数据库设计

### 核心表结构
```sql
-- 聊天记录主表
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,           -- 会话ID
    message_id TEXT UNIQUE NOT NULL,    -- 消息ID
    sender_type TEXT NOT NULL,          -- 'user' 或 'assistant'
    content TEXT NOT NULL,              -- 消息内容
    timestamp DATETIME NOT NULL,        -- 时间戳
    channel TEXT,                       -- 渠道 (webchat, telegram等)
    metadata JSON,                      -- 元数据
    embedding BLOB,                     -- 向量嵌入 (用于语义搜索)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 会话摘要表
CREATE TABLE session_summaries (
    session_id TEXT PRIMARY KEY,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    message_count INTEGER DEFAULT 0,
    topics TEXT,                        -- 主题标签
    summary TEXT,                       -- 会话摘要
    embedding BLOB,                     -- 会话向量
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 向量索引表 (用于FAISS)
CREATE TABLE vector_index (
    id INTEGER PRIMARY KEY,
    message_id TEXT NOT NULL,
    embedding BLOB NOT NULL,
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (message_id) REFERENCES chat_messages(message_id)
);

-- 关键词索引表
CREATE TABLE keyword_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    message_id TEXT NOT NULL,
    frequency INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES chat_messages(message_id)
);
```

### 分区策略
```sql
-- 按日期分区视图
CREATE VIEW chat_messages_daily AS
SELECT * FROM chat_messages
WHERE DATE(timestamp) = DATE('now');

-- 按月分区表 (自动创建)
-- 每月1号自动创建新表: chat_messages_YYYY_MM
```

## 🚀 快速安装

### 方法1: 使用安装脚本（推荐）
```bash
# Linux/macOS
chmod +x install.sh
./install.sh

# Windows
install.bat
```

### 方法2: 手动安装
```bash
# 1. 安装依赖
pip install sentence-transformers faiss-cpu sqlite-utils numpy schedule

# 2. 初始化数据库
python init_db.py

# 3. 运行测试
python test_memory.py
```

### 方法3: 集成到OpenClaw技能目录
```bash
# 将整个技能目录复制到OpenClaw技能目录
cp -r chat-memory-db "C:\Users\Admin-YZ\.openclaw-autoclaw\skills\"

# 或创建符号链接
ln -s $(pwd)/chat-memory-db "C:\Users\Admin-YZ\.openclaw-autoclaw\skills\"
```

## ⚙️ 配置

### 环境变量配置
```bash
# 数据库路径
export CHAT_MEMORY_DB_PATH="~/.openclaw-autoclaw/data/chat_memory.db"

# 向量模型配置
export EMBEDDING_MODEL="all-MiniLM-L6-v2"  # 轻量级向量模型
export VECTOR_INDEX_PATH="~/.openclaw-autoclaw/data/vector_index.index"

# 性能配置
export MAX_MEMORY_ITEMS=1000      # 每次检索的最大记忆数量
export SIMILARITY_THRESHOLD=0.6   # 向量相似度阈值
export AUTO_ARCHIVE_HOUR=23       # 自动归档时间（小时）
```

### 配置文件（config.json）
```json
{
  "database": {
    "path": "~/.openclaw-autoclaw/data/chat_memory.db",
    "cleanup_days": 30,
    "optimize_interval_hours": 24
  },
  "vector_search": {
    "model": "all-MiniLM-L6-v2",
    "index_path": "~/.openclaw-autoclaw/data/vector_index.index",
    "similarity_threshold": 0.6
  },
  "scheduler": {
    "auto_archive_hour": 23,
    "auto_archive_minute": 0,
    "health_check_interval_minutes": 60
  },
  "integration": {
    "auto_store": true,
    "auto_retrieve": true,
    "max_context_items": 5,
    "enable_vector_search": true,
    "enable_keyword_search": true
  }
}
```

## 使用方法

### 基本使用
当用户提到需要记忆聊天记录、查询历史对话、或需要上下文记忆时，自动激活此skill。

### 1. 存储聊天记录
```python
# 自动捕获聊天记录
from chat_memory import ChatMemory

memory = ChatMemory()
memory.store_message(
    session_id="session_123",
    message_id="msg_456",
    sender="user",
    content="你好，我想了解AI编程",
    channel="webchat"
)
```

### 2. 检索相关记忆
```python
# 根据当前对话检索相关记忆
context = memory.retrieve_context(
    query="AI编程有什么好的学习资源？",
    limit=5,
    similarity_threshold=0.7
)
```

### 3. 自动归档
```python
# 每天23点自动运行
memory.daily_archive()
```

### 4. 手动查询
```python
# 关键词查询
results = memory.search_by_keyword("AI编程", limit=10)

# 时间范围查询
results = memory.search_by_time_range(
    start_date="2026-03-01",
    end_date="2026-03-19",
    limit=20
)

# 语义搜索
results = memory.semantic_search(
    query="如何学习机器学习",
    limit=5
)
```

## 性能优化

### 1. 索引策略
```sql
-- 创建性能索引
CREATE INDEX idx_timestamp ON chat_messages(timestamp);
CREATE INDEX idx_session ON chat_messages(session_id);
CREATE INDEX idx_sender ON chat_messages(sender_type);
CREATE INDEX idx_channel ON chat_messages(channel);
```

### 2. 查询优化
- **分区查询**: 按日期分区，减少扫描范围
- **向量缓存**: 缓存常用查询的向量结果
- **增量索引**: 只对新数据建立向量索引
- **批量操作**: 使用事务批量插入

### 3. 内存管理
```python
# 配置内存使用
config = {
    "max_cache_size": 10000,      # 最大缓存条目
    "vector_cache_ttl": 3600,     # 向量缓存TTL(秒)
    "batch_size": 100,            # 批量处理大小
    "cleanup_threshold": 1000000  # 清理阈值
}
```

## 调度任务

### 每日归档任务 (23:00)
```python
# 归档脚本
def daily_archive():
    # 1. 汇总当日聊天记录
    daily_summary = summarize_daily_chats()
    
    # 2. 更新向量索引
    update_vector_index()
    
    # 3. 清理临时数据
    cleanup_temporary_data()
    
    # 4. 备份数据库
    backup_database()
    
    # 5. 发送归档报告
    send_archive_report()
```

### 使用cron调度
```bash
# 每天23点执行归档
0 23 * * * python /path/to/chat_memory/daily_archive.py
```

## API接口

### REST API (可选)
```python
from flask import Flask, request, jsonify

app = Flask(__name__)
memory = ChatMemory()

@app.route('/api/memory/store', methods=['POST'])
def store_message():
    data = request.json
    memory.store_message(**data)
    return jsonify({"status": "success"})

@app.route('/api/memory/retrieve', methods=['GET'])
def retrieve_context():
    query = request.args.get('query')
    limit = int(request.args.get('limit', 5))
    results = memory.retrieve_context(query, limit)
    return jsonify(results)

@app.route('/api/memory/search', methods=['GET'])
def search():
    # 支持多种搜索方式
    pass
```

## 🔌 集成到OpenClaw

### 1. 自动激活条件
当检测到以下关键词时自动激活技能：
```python
activation_keywords = [
    # 中文关键词
    "聊天记录", "历史对话", "之前说过", "记得吗", "查一下",
    "搜索聊天", "对话历史", "记忆", "上下文",
    
    # 英文关键词  
    "memory", "chat history", "recall", "remember", "search chat",
    "conversation history", "context", "previous discussion"
]
```

### 2. 完整的OpenClaw集成示例
```python
# openclaw_integration.py
from chat_memory.openclaw_integration import get_integration

class OpenClawWithMemory:
    def __init__(self):
        self.memory_integration = get_integration()
        
    def process_user_message(self, session_id, user_message, conversation_history):
        """
        处理用户消息的完整流程
        """
        # 1. 处理消息（自动存储）
        processed = self.memory_integration.process_incoming_message(
            session_id=session_id,
            message=user_message,
            channel="webchat"  # 或其他渠道
        )
        
        # 2. 增强上下文
        enhanced_context = self.memory_integration.enhance_model_context(
            session_id=session_id,
            user_input=user_message['content'],
            conversation_history=conversation_history
        )
        
        # 3. 调用大模型（使用增强的上下文）
        llm_response = self.call_llm_with_context(enhanced_context)
        
        # 4. 存储完整的对话轮次
        self.memory_integration.store_conversation_turn(
            session_id=session_id,
            user_message=user_message,
            assistant_response=llm_response,
            channel="webchat"
        )
        
        return llm_response
    
    def call_llm_with_context(self, context):
        """调用大模型（示例）"""
        # 这里集成你的LLM调用逻辑
        # 例如: OpenAI API, Claude API, 本地模型等
        pass
```

### 3. 技能命令接口
技能提供以下命令供OpenClaw调用：

```python
from openclaw_skill import get_skill

skill = get_skill()
skill.activate()  # 激活技能

# 获取系统状态
status = skill.handle_command('status', {})

# 搜索记忆
search_results = skill.handle_command('search', {
    'query': 'Python编程',
    'type': 'hybrid',
    'limit': 5
})

# 手动归档
archive_result = skill.handle_command('archive', {
    'date': '2026-03-18'  # 可选，默认为昨天
})

# 获取会话信息
session_info = skill.handle_command('session_info', {
    'session_id': 'your_session_id'
})

# 清理缓存
skill.handle_command('clear_cache', {})
```

### 4. 对话流程优化
```
用户输入
    ↓
[技能激活检查] → 如果包含记忆相关关键词 → [记忆检索]
    ↓
[消息预处理] → 提取关键信息
    ↓
[记忆检索] → 向量搜索 + 关键词搜索
    ↓
[上下文构建] → 当前对话 + 相关记忆
    ↓
[大模型调用] → 使用增强上下文
    ↓
[回复生成] → 生成个性化回复
    ↓
[记忆存储] → 存储本轮对话
```

### 5. 上下文增强模板
```python
def build_enhanced_context_template(session_id, user_input, conversation_history):
    """
    构建增强上下文的模板函数
    """
    from chat_memory import get_memory_manager
    
    memory = get_memory_manager()
    
    # 检索相关记忆
    relevant_memories = memory.retrieve_context(
        query=user_input,
        session_id=session_id,
        limit=5
    )
    
    # 构建模板
    template = f"""# 对话上下文

## 当前会话历史
{format_conversation_history(conversation_history)}

## 相关历史记忆
{format_relevant_memories(relevant_memories)}

## 用户当前问题
{user_input}

## 回复要求
请基于以上完整的对话历史和相关信息，回答用户的问题。
如果历史记忆中有相关信息，请参考并整合到回答中。
保持回答自然、连贯，避免简单重复历史内容。"""
    
    return template
```

### 6. 实时监控和调试
```python
# 实时查看系统状态
def monitor_system():
    skill = get_skill()
    
    while True:
        status = skill.get_system_status()
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 系统状态:")
        print(f"  消息总数: {status['memory_system']['database']['total_messages']}")
        print(f"  向量数量: {status['memory_system']['vector_search']['total_vectors']}")
        print(f"  缓存大小: {status['integration']['session_cache_size']}")
        print(f"  最后操作: {status['status']['last_operation']}")
        
        time.sleep(60)  # 每分钟更新一次
```

### 7. 错误处理和恢复
```python
def safe_memory_operation(operation_func, *args, **kwargs):
    """
    安全执行记忆操作，带有错误处理和恢复
    """
    try:
        return operation_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"记忆操作失败: {e}")
        
        # 尝试恢复
        try:
            # 重新初始化记忆系统
            from chat_memory import get_memory_manager
            memory = get_memory_manager()
            
            # 记录错误
            error_log = {
                'timestamp': datetime.now().isoformat(),
                'operation': operation_func.__name__,
                'error': str(e),
                'recovered': True
            }
            
            # 保存错误日志
            save_error_log(error_log)
            
            return None  # 或返回默认值
            
        except Exception as recovery_error:
            logger.error(f"恢复失败: {recovery_error}")
            return None
```

### 8. 性能优化配置
```python
# 针对不同场景的性能优化配置
performance_profiles = {
    'development': {
        'max_retrieved_items': 3,
        'similarity_threshold': 0.5,
        'cache_ttl': 300,
        'enable_vector_search': True
    },
    'production': {
        'max_retrieved_items': 5,
        'similarity_threshold': 0.6,
        'cache_ttl': 600,
        'enable_vector_search': True,
        'enable_keyword_search': True
    },
    'high_performance': {
        'max_retrieved_items': 10,
        'similarity_threshold': 0.7,
        'cache_ttl': 900,
        'enable_vector_search': True,
        'enable_keyword_search': True,
        'batch_size': 100
    }
}

# 根据环境选择配置
def get_performance_profile(env='production'):
    return performance_profiles.get(env, performance_profiles['production'])
```

## 监控与维护

### 1. 健康检查
```python
def health_check():
    metrics = {
        "db_size": get_database_size(),
        "row_count": get_row_count(),
        "index_status": check_index_status(),
        "query_performance": measure_query_performance(),
        "vector_index_size": get_vector_index_size()
    }
    return metrics
```

### 2. 性能监控
- 查询响应时间 < 100ms
- 向量搜索时间 < 50ms
- 存储吞吐量 > 1000条/秒
- 内存使用 < 1GB

### 3. 维护任务
```bash
# 每周优化数据库
python -m chat_memory.optimize_db

# 每月重建索引
python -m chat_memory.rebuild_index

# 季度数据清理
python -m chat_memory.cleanup_old_data
```

## 故障排除

### 常见问题
1. **查询慢**: 检查索引状态，重建索引
2. **内存不足**: 调整缓存大小，清理旧数据
3. **向量搜索不准**: 更新嵌入模型，重新训练
4. **归档失败**: 检查磁盘空间，查看日志

### 日志配置
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chat_memory.log'),
        logging.StreamHandler()
    ]
)
```

## 扩展功能

### 1. 多语言支持
```python
# 支持中文、英文等多种语言
memory.set_language("zh-CN")
```

### 2. 情感分析
```python
# 分析对话情感
sentiment = analyze_sentiment(message_content)
memory.store_with_sentiment(message, sentiment)
```

### 3. 主题聚类
```python
# 自动聚类相关话题
topics = cluster_topics(chat_history)
memory.tag_with_topics(message_id, topics)
```

### 4. 知识图谱
```python
# 构建对话知识图谱
graph = build_knowledge_graph(chat_history)
memory.store_knowledge_graph(graph)
```

## 安全与隐私

### 1. 数据加密
```python
# 敏感数据加密存储
encrypted_content = encrypt_sensitive_data(content)
```

### 2. 访问控制
```python
# 基于角色的访问控制
if user.has_permission("read_chat_history"):
    results = memory.search(user_query)
```

### 3. 数据清理
```python
# 自动清理过期数据
memory.cleanup_expired_data(days=30)
```

## 部署指南

### 开发环境
```bash
# 克隆代码
git clone https://github.com/your-repo/chat-memory-db.git

# 安装依赖
pip install -r requirements.txt

# 初始化
python setup.py
```

### 生产环境
```bash
# 使用Docker部署
docker build -t chat-memory-db .
docker run -d -p 8000:8000 chat-memory-db

# 使用Kubernetes
kubectl apply -f k8s-deployment.yaml
```

## 版本历史
- v1.0.0: 初始版本，基础存储和检索功能
- v1.1.0: 添加向量搜索和自动归档
- v1.2.0: 性能优化和监控功能
- v1.3.0: 多语言支持和扩展API

---

**注意**: 这是一个高性能的聊天记忆系统，需要根据实际使用情况调整配置参数。建议在生产环境前进行充分的测试和性能调优。