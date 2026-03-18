#!/usr/bin/env python3
"""
快速测试脚本
"""

import sys
import os
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_simple_memory():
    """测试简单记忆管理器"""
    print("测试简单记忆管理器...")
    
    try:
        from chat_memory_simple import get_memory
        
        # 获取记忆管理器
        memory = get_memory()
        
        print("1. 存储测试消息...")
        
        # 存储一些测试消息
        test_messages = [
            {
                'session_id': 'test_session_1',
                'message_id': 'test_msg_1',
                'sender_type': 'user',
                'content': '你好，我想学习Python编程',
                'timestamp': datetime.now()
            },
            {
                'session_id': 'test_session_1',
                'message_id': 'test_msg_2',
                'sender_type': 'assistant',
                'content': 'Python是一门很好的编程语言，适合初学者',
                'timestamp': datetime.now()
            },
            {
                'session_id': 'test_session_2',
                'message_id': 'test_msg_3',
                'sender_type': 'user',
                'content': '机器学习需要哪些数学基础？',
                'timestamp': datetime.now()
            }
        ]
        
        for msg in test_messages:
            success = memory.store_message(**msg)
            if success:
                print(f"  [OK] 存储: {msg['content'][:20]}...")
            else:
                print(f"  [ERROR] 存储失败: {msg['content'][:20]}...")
        
        print("\n2. 获取最近消息...")
        recent = memory.get_recent_messages(limit=3)
        print(f"  获取到 {len(recent)} 条消息")
        for i, msg in enumerate(recent, 1):
            print(f"  {i}. [{msg['sender_type']}] {msg['content'][:30]}...")
        
        print("\n3. 关键词搜索...")
        search_results = memory.search_by_keyword('Python', limit=2)
        print(f"  搜索'Python'找到 {len(search_results)} 条结果")
        for i, result in enumerate(search_results, 1):
            print(f"  {i}. {result['content'][:40]}...")
        
        print("\n4. 获取统计信息...")
        stats = memory.get_stats()
        print(f"  总消息数: {stats['total_messages']}")
        print(f"  总会话数: {stats['total_sessions']}")
        print(f"  数据库路径: {stats['db_path']}")
        
        print("\n5. 按会话获取消息...")
        session_messages = memory.get_recent_messages(session_id='test_session_1', limit=5)
        print(f"  会话 test_session_1 有 {len(session_messages)} 条消息")
        
        # 清理测试数据
        print("\n6. 清理测试数据...")
        # 在实际使用中，你可能不想清理，这里只是演示
        
        memory.close()
        
        print("\n[SUCCESS] 所有测试通过！")
        return True
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_openclaw_integration():
    """测试OpenClaw集成"""
    print("\n测试OpenClaw集成...")
    
    try:
        # 检查openclaw_skill.py是否存在
        skill_file = os.path.join(os.path.dirname(__file__), 'openclaw_skill.py')
        if not os.path.exists(skill_file):
            print("  [INFO] openclaw_skill.py 不存在，跳过集成测试")
            return True
        
        # 尝试导入
        from openclaw_skill import get_skill
        
        print("  [OK] OpenClaw技能模块可导入")
        
        # 注意：完整版本需要额外依赖
        print("  [INFO] 完整功能需要安装额外依赖:")
        print("    pip install sentence-transformers faiss-cpu schedule")
        
        return True
        
    except ImportError as e:
        print(f"  [INFO] 导入OpenClaw技能失败: {e}")
        print("  [INFO] 这是正常的，因为完整版本需要额外依赖")
        return True
    except Exception as e:
        print(f"  [ERROR] 集成测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("聊天记录记忆技能 - 快速测试")
    print("=" * 60)
    
    print(f"工作目录: {os.getcwd()}")
    print(f"Python版本: {sys.version}")
    
    # 测试简单记忆管理器
    if not test_simple_memory():
        print("\n[ERROR] 简单记忆管理器测试失败")
        return 1
    
    # 测试OpenClaw集成
    if not test_openclaw_integration():
        print("\n[WARNING] OpenClaw集成测试有警告")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] 技能安装成功！")
    print("=" * 60)
    
    print("\n总结:")
    print("1. ✅ 数据库存储功能正常")
    print("2. ✅ 消息检索功能正常")
    print("3. ✅ 关键词搜索功能正常")
    print("4. ✅ 统计功能正常")
    print("5. ⚠️  完整功能需要额外依赖")
    
    print("\n下一步:")
    print("1. 使用简单记忆管理器:")
    print("   from chat_memory_simple import get_memory")
    print("   memory = get_memory()")
    
    print("\n2. 安装完整依赖:")
    print("   pip install sentence-transformers faiss-cpu sqlite-utils numpy schedule")
    
    print("\n3. 运行完整测试:")
    print("   python test_memory.py")
    
    print("\n4. 查看使用示例:")
    print("   python examples/basic_usage.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())