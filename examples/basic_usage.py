#!/usr/bin/env python3
"""
基本使用示例
展示如何在OpenClaw中使用聊天记忆技能
"""

import os
import sys
import logging
from datetime import datetime

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw_skill import get_skill

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def example_1_basic_conversation():
    """示例1: 基本对话记忆"""
    print("=" * 60)
    print("示例1: 基本对话记忆")
    print("=" * 60)
    
    skill = get_skill()
    
    # 激活技能
    skill.activate()
    
    # 模拟对话
    session_id = "example_session_001"
    
    # 第一轮对话
    user_message_1 = {
        "id": "msg_001",
        "role": "user",
        "content": "你好，我想学习Python编程",
        "timestamp": datetime.now().isoformat(),
        "channel": "webchat"
    }
    
    # 处理用户消息
    result_1 = skill.process_message(session_id, user_message_1)
    print(f"处理用户消息: {result_1['processed']}")
    
    # 增强上下文
    enhanced_context = skill.enhance_conversation(
        session_id=session_id,
        user_input=user_message_1['content'],
        conversation_history=[user_message_1]
    )
    print(f"增强上下文长度: {len(enhanced_context)} 字符")
    
    # 模拟助手回复
    assistant_response_1 = {
        "id": "msg_002",
        "role": "assistant",
        "content": "Python是一门很好的编程语言，适合初学者学习。",
        "timestamp": datetime.now().isoformat(),
        "model": "gpt-4",
        "tokens": 50
    }
    
    # 存储对话轮次
    skill.store_conversation(
        session_id=session_id,
        user_message=user_message_1,
        assistant_response=assistant_response_1
    )
    
    # 第二轮对话
    user_message_2 = {
        "id": "msg_003",
        "role": "user",
        "content": "有什么推荐的Python学习资源吗？",
        "timestamp": datetime.now().isoformat(),
        "channel": "webchat"
    }
    
    # 处理第二用户消息
    result_2 = skill.process_message(session_id, user_message_2)
    
    # 增强上下文（包含历史记忆）
    conversation_history = [user_message_1, assistant_response_1, user_message_2]
    enhanced_context_2 = skill.enhance_conversation(
        session_id=session_id,
        user_input=user_message_2['content'],
        conversation_history=conversation_history
    )
    
    print(f"第二轮增强上下文长度: {len(enhanced_context_2)} 字符")
    print("\n增强上下文预览:")
    print("-" * 40)
    print(enhanced_context_2[:500] + "...")
    print("-" * 40)
    
    return True

def example_2_memory_search():
    """示例2: 记忆搜索"""
    print("\n" + "=" * 60)
    print("示例2: 记忆搜索")
    print("=" * 60)
    
    skill = get_skill()
    
    # 添加一些测试数据
    test_session = "search_test_session"
    test_messages = [
        {
            "session_id": test_session,
            "message_id": "test_msg_001",
            "sender_type": "user",
            "content": "机器学习需要掌握哪些数学知识？",
            "timestamp": datetime.now().isoformat(),
            "channel": "webchat"
        },
        {
            "session_id": test_session,
            "message_id": "test_msg_002",
            "sender_type": "assistant",
            "content": "机器学习需要线性代数、概率论和微积分基础。",
            "timestamp": datetime.now().isoformat(),
            "channel": "webchat"
        },
        {
            "session_id": test_session,
            "message_id": "test_msg_003",
            "sender_type": "user",
            "content": "深度学习框架哪个比较好？",
            "timestamp": datetime.now().isoformat(),
            "channel": "webchat"
        }
    ]
    
    # 存储测试数据
    for msg in test_messages:
        skill.memory.db.store_message(**msg)
    
    # 搜索记忆
    print("搜索 '机器学习':")
    search_result = skill.search_memory("机器学习", limit=5)
    
    if search_result['success']:
        print(f"找到 {search_result['total']} 条结果:")
        for i, result in enumerate(search_result['results'][:3], 1):
            content = result.get('content', '')[:80]
            print(f"  {i}. {content}...")
    else:
        print(f"搜索失败: {search_result.get('error')}")
    
    # 关键词搜索
    print("\n关键词搜索 '深度学习':")
    keyword_result = skill.search_memory("深度学习", search_type='keyword', limit=3)
    
    if keyword_result['success']:
        print(f"找到 {keyword_result['total']} 条结果")
    
    return True

def example_3_system_status():
    """示例3: 系统状态查看"""
    print("\n" + "=" * 60)
    print("示例3: 系统状态查看")
    print("=" * 60)
    
    skill = get_skill()
    
    # 获取系统状态
    status = skill.get_system_status()
    
    print("系统状态概览:")
    print(f"  技能名称: {status['skill']['skill_name']}")
    print(f"  版本: {status['skill']['version']}")
    print(f"  是否激活: {status['status']['initialized']}")
    print(f"  调度器运行: {status['status']['scheduler_running']}")
    
    print("\n记忆系统统计:")
    memory_stats = status['memory_system']['database']
    print(f"  总消息数: {memory_stats.get('total_messages', 0)}")
    print(f"  总会话数: {memory_stats.get('total_sessions', 0)}")
    print(f"  数据库大小: {memory_stats.get('db_size', 0) / 1024:.1f} KB")
    
    print("\n向量搜索统计:")
    vector_stats = status['memory_system']['vector_search']
    print(f"  模型加载: {vector_stats.get('has_model', False)}")
    print(f"  索引加载: {vector_stats.get('has_index', False)}")
    print(f"  向量数量: {vector_stats.get('total_vectors', 0)}")
    
    return True

def example_4_command_interface():
    """示例4: 命令接口"""
    print("\n" + "=" * 60)
    print("示例4: 命令接口")
    print("=" * 60)
    
    skill = get_skill()
    
    # 测试命令
    commands = [
        ("status", {}),
        ("search", {"query": "Python", "limit": 3}),
        ("stats", {}),
        ("clear_cache", {})
    ]
    
    for command, args in commands:
        print(f"\n执行命令: {command}")
        result = skill.handle_command(command, args)
        
        if 'error' in result:
            print(f"  错误: {result['error']}")
        else:
            print(f"  成功: {command}")
            
            # 显示简要结果
            if command == 'search':
                search_data = result['result']
                if search_data['success']:
                    print(f"  找到 {search_data['total']} 条结果")
            
            elif command == 'stats':
                stats = result['result']
                print(f"  消息总数: {stats.get('database', {}).get('total_messages', 0)}")
    
    return True

def example_5_integration_with_openclaw():
    """示例5: 与OpenClaw集成"""
    print("\n" + "=" * 60)
    print("示例5: 与OpenClaw集成")
    print("=" * 60)
    
    print("""
在OpenClaw中使用聊天记忆技能的典型流程:

1. 初始化技能:
   ```python
   from openclaw_skill import get_skill
   skill = get_skill()
   skill.activate()
   ```

2. 处理用户消息时增强上下文:
   ```python
   def process_user_input(session_id, user_input, history):
       # 增强上下文
       enhanced_context = skill.enhance_conversation(
           session_id=session_id,
           user_input=user_input,
           conversation_history=history
       )
       
       # 调用大模型
       response = call_llm(enhanced_context)
       
       # 存储对话
       skill.store_conversation(
           session_id=session_id,
           user_message={"content": user_input},
           assistant_response={"content": response}
       )
       
       return response
   ```

3. 定期运行归档:
   ```python
   # 手动运行归档
   skill.run_manual_archive()
   
   # 或使用调度器自动归档（每天23点）
   ```

4. 搜索历史记忆:
   ```python
   # 搜索相关对话
   results = skill.search_memory("Python编程", limit=5)
   
   # 获取会话摘要
   session_info = skill.get_session_info(session_id)
   ```

5. 监控系统状态:
   ```python
   status = skill.get_system_status()
   print(f"系统状态: {status['status']['initialized']}")
   ```
""")
    
    return True

def main():
    """运行所有示例"""
    print("聊天记录记忆技能 - 使用示例")
    print("=" * 60)
    
    examples = [
        ("基本对话记忆", example_1_basic_conversation),
        ("记忆搜索", example_2_memory_search),
        ("系统状态查看", example_3_system_status),
        ("命令接口", example_4_command_interface),
        ("OpenClaw集成", example_5_integration_with_openclaw)
    ]
    
    results = []
    
    for example_name, example_func in examples:
        try:
            print(f"\n▶️  运行: {example_name}")
            success = example_func()
            results.append((example_name, success))
            
            if success:
                print(f"✅ {example_name} - 完成")
            else:
                print(f"❌ {example_name} - 失败")
                
        except Exception as e:
            print(f"❌ {example_name} - 异常: {e}")
            results.append((example_name, False))
    
    print("\n" + "=" * 60)
    print("示例运行结果:")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for example_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {example_name}")
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 所有示例运行成功！")
    else:
        print(f"\n⚠️  {total - passed} 个示例失败")
    
    print("\n下一步:")
    print("1. 安装依赖: pip install sentence-transformers faiss-cpu sqlite-utils numpy schedule")
    print("2. 初始化数据库: python init_db.py")
    print("3. 运行测试: python test_memory.py")
    print("4. 集成到OpenClaw工作流")

if __name__ == "__main__":
    main()
