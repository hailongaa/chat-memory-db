#!/usr/bin/env python3
"""
测试聊天记录记忆系统
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import json

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat_memory import get_memory_manager, get_scheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_basic_operations():
    """测试基本操作"""
    print("🧪 测试基本操作...")
    
    memory = get_memory_manager()
    
    # 测试存储消息
    test_session = "test_session_001"
    test_messages = [
        {
            "id": "msg_001",
            "role": "user",
            "content": "你好，我想学习Python编程",
            "timestamp": datetime.now().isoformat(),
            "channel": "webchat"
        },
        {
            "id": "msg_002", 
            "role": "assistant",
            "content": "Python是一门很好的编程语言，适合初学者",
            "timestamp": (datetime.now() + timedelta(seconds=1)).isoformat(),
            "channel": "webchat"
        },
        {
            "id": "msg_003",
            "role": "user",
            "content": "有什么推荐的Python学习资源吗？",
            "timestamp": (datetime.now() + timedelta(seconds=2)).isoformat(),
            "channel": "webchat"
        }
    ]
    
    # 存储对话
    success = memory.store_conversation(test_session, test_messages)
    print(f"  存储对话: {'✅' if success else '❌'}")
    
    # 获取会话历史
    history = memory.get_conversation_history(test_session, limit=10)
    print(f"  获取历史: {len(history)} 条消息")
    
    # 检索相关记忆
    query = "Python学习资源推荐"
    results = memory.retrieve_context(query, limit=3)
    print(f"  检索记忆 (查询: '{query}'): {len(results)} 条相关结果")
    
    if results:
        for i, result in enumerate(results[:2], 1):
            print(f"    结果{i}: {result.get('content', '')[:50]}...")
    
    return success

def test_search_functions():
    """测试搜索功能"""
    print("\n🔍 测试搜索功能...")
    
    memory = get_memory_manager()
    
    # 添加更多测试数据
    test_data = [
        {
            "session_id": "test_session_002",
            "message_id": "msg_ai_001",
            "sender_type": "user",
            "content": "人工智能和机器学习有什么区别？",
            "timestamp": datetime.now() - timedelta(hours=1)
        },
        {
            "session_id": "test_session_002",
            "message_id": "msg_ai_002",
            "sender_type": "assistant", 
            "content": "人工智能是更广泛的概念，机器学习是AI的一个子领域",
            "timestamp": datetime.now() - timedelta(hours=1) + timedelta(seconds=1)
        },
        {
            "session_id": "test_session_003",
            "message_id": "msg_web_001",
            "sender_type": "user",
            "content": "如何学习Web开发？需要掌握哪些技术？",
            "timestamp": datetime.now() - timedelta(hours=2)
        }
    ]
    
    # 存储测试数据
    for msg in test_data:
        memory.db.store_message(**msg)
    
    # 测试关键词搜索
    keyword_results = memory.db.search_by_keyword("学习", limit=3)
    print(f"  关键词搜索 ('学习'): {len(keyword_results)} 条结果")
    
    # 测试时间范围搜索
    start_time = datetime.now() - timedelta(hours=3)
    end_time = datetime.now()
    time_results = memory.db.search_by_time_range(start_time, end_time, limit=5)
    print(f"  时间范围搜索: {len(time_results)} 条结果")
    
    # 测试记忆搜索
    search_results = memory.search_memories(
        query="学习编程技术",
        search_type="hybrid",
        limit=5
    )
    print(f"  记忆搜索 (混合模式): {len(search_results.get('results', []))} 条结果")
    
    return True

def test_scheduler():
    """测试调度器"""
    print("\n⏰ 测试调度器...")
    
    scheduler = get_scheduler(auto_archive_hour=23)
    
    # 获取状态
    status = scheduler.get_status()
    print(f"  调度器状态: {'运行中' if status['running'] else '未运行'}")
    print(f"  自动归档时间: {status['auto_archive_time']}")
    print(f"  下次归档: {status.get('next_archive', 'N/A')}")
    
    # 测试手动归档
    print("  测试手动归档...")
    test_date = datetime.now() - timedelta(days=1)
    report = scheduler.run_manual_archive(test_date.strftime("%Y-%m-%d"))
    
    if report:
        print(f"    手动归档完成: {report.get('total_messages', 0)} 条消息")
    else:
        print("    手动归档未生成报告")
    
    return True

def test_performance():
    """测试性能"""
    print("\n⚡ 测试性能...")
    
    memory = get_memory_manager()
    
    import time
    
    # 测试检索性能
    test_queries = [
        "Python编程",
        "机器学习",
        "Web开发",
        "人工智能"
    ]
    
    for query in test_queries:
        start_time = time.time()
        results = memory.retrieve_context(query, limit=3)
        elapsed = (time.time() - start_time) * 1000  # 转换为毫秒
        
        print(f"  查询 '{query}': {len(results)} 结果, {elapsed:.1f}ms")
    
    # 获取统计信息
    stats = memory.get_stats()
    print(f"\n  系统统计:")
    print(f"    总消息数: {stats.get('database', {}).get('total_messages', 0)}")
    print(f"    总会话数: {stats.get('database', {}).get('total_sessions', 0)}")
    print(f"    数据库大小: {stats.get('database', {}).get('db_size', 0) / 1024:.1f} KB")
    print(f"    向量索引: {stats.get('vector_search', {}).get('total_vectors', 0)} 个向量")
    
    return True

def test_integration():
    """测试集成功能"""
    print("\n🔗 测试集成功能...")
    
    memory = get_memory_manager()
    
    # 模拟对话场景
    conversation_history = [
        {"role": "user", "content": "我想学习数据科学"},
        {"role": "assistant", "content": "数据科学需要掌握Python、统计学和机器学习"}
    ]
    
    current_user_input = "数据科学需要学习哪些Python库？"
    
    # 检索相关记忆
    relevant_memories = memory.retrieve_context(current_user_input, limit=3)
    
    # 构建增强上下文
    enhanced_context = f"""
当前对话历史:
{json.dumps(conversation_history, ensure_ascii=False, indent=2)}

相关历史记忆:
{json.dumps([{
    'content': m.get('content', ''),
    'timestamp': m.get('timestamp', ''),
    'similarity': m.get('similarity', 0)
} for m in relevant_memories], ensure_ascii=False, indent=2)}

用户当前问题:
{current_user_input}
"""
    
    print(f"  增强上下文长度: {len(enhanced_context)} 字符")
    print(f"  相关记忆数量: {len(relevant_memories)}")
    
    if relevant_memories:
        print("  相关记忆示例:")
        for i, memory in enumerate(relevant_memories[:2], 1):
            content = memory.get('content', '')
            similarity = memory.get('similarity', 0)
            print(f"    {i}. {content[:60]}... (相似度: {similarity:.2f})")
    
    return True

def cleanup_test_data():
    """清理测试数据"""
    print("\n🧹 清理测试数据...")
    
    memory = get_memory_manager()
    
    # 删除测试会话
    test_sessions = ["test_session_001", "test_session_002", "test_session_003"]
    
    for session_id in test_sessions:
        cursor = memory.db.conn.cursor()
        cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        memory.db.conn.commit()
    
    print("  测试数据已清理")
    return True

def main():
    """主测试函数"""
    print("=" * 60)
    print("聊天记录记忆系统 - 功能测试")
    print("=" * 60)
    
    tests = [
        ("基本操作", test_basic_operations),
        ("搜索功能", test_search_functions),
        ("调度器", test_scheduler),
        ("性能测试", test_performance),
        ("集成功能", test_integration),
        ("清理数据", cleanup_test_data)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
            status = "✅ 通过" if success else "❌ 失败"
            print(f"{status}: {test_name}")
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ 异常: {test_name} - {e}")
            logger.error(f"测试失败: {test_name}", exc_info=True)
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}")
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())