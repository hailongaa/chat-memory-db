"""
调度器模块
负责定时任务，特别是每天23点的自动归档
"""
import schedule
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
import json
import os

from .memory_manager import get_memory_manager

logger = logging.getLogger(__name__)

class MemoryScheduler:
    """记忆系统调度器"""
    
    def __init__(self, 
                 auto_archive_hour: int = 23,
                 auto_archive_minute: int = 0):
        """
        初始化调度器
        
        Args:
            auto_archive_hour: 自动归档小时（23表示23点）
            auto_archive_minute: 自动归档分钟
        """
        self.auto_archive_hour = auto_archive_hour
        self.auto_archive_minute = auto_archive_minute
        self.memory_manager = get_memory_manager()
        self.scheduler_thread = None
        self.running = False
        
        # 加载调度状态
        self.state_file = os.path.expanduser("~/.openclaw-autoclaw/data/scheduler_state.json")
        self.state = self._load_state()
        
        logger.info(f"记忆调度器初始化完成，归档时间: {auto_archive_hour}:{auto_archive_minute:02d}")
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行")
            return
        
        self.running = True
        
        # 创建调度器线程
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("记忆调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        # 保存状态
        self._save_state()
        
        logger.info("记忆调度器已停止")
    
    def _run_scheduler(self):
        """运行调度器主循环"""
        try:
            # 设置定时任务
            self._setup_schedules()
            
            logger.info("调度器任务已设置，开始运行...")
            
            # 立即运行一次健康检查
            self._run_health_check()
            
            # 如果当前时间已过23点，立即运行归档
            now = datetime.now()
            if now.hour >= self.auto_archive_hour:
                logger.info("当前时间已过归档时间，立即运行归档")
                self._run_daily_archive()
            
            # 主循环
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            
        except Exception as e:
            logger.error(f"调度器运行失败: {e}")
            self.running = False
    
    def _setup_schedules(self):
        """设置定时任务"""
        # 每天23点运行归档
        schedule.every().day.at(f"{self.auto_archive_hour:02d}:{self.auto_archive_minute:02d}").do(
            self._run_daily_archive
        )
        
        # 每小时运行健康检查
        schedule.every().hour.do(self._run_health_check)
        
        # 每天凌晨2点运行数据库优化
        schedule.every().day.at("02:00").do(self._run_database_optimization)
        
        # 每周日凌晨3点运行完整维护
        schedule.every().sunday.at("03:00").do(self._run_weekly_maintenance)
        
        logger.info("定时任务设置完成")
    
    def _run_daily_archive(self):
        """运行每日归档"""
        try:
            logger.info("开始执行每日归档...")
            
            # 获取昨天的日期
            archive_date = datetime.now() - timedelta(days=1)
            
            # 运行归档
            report = self.memory_manager.daily_archive(archive_date)
            
            if report:
                # 更新状态
                self.state['last_archive'] = {
                    'date': archive_date.isoformat(),
                    'timestamp': datetime.now().isoformat(),
                    'message_count': report.get('total_messages', 0),
                    'session_count': report.get('total_sessions', 0)
                }
                self.state['archive_count'] = self.state.get('archive_count', 0) + 1
                
                # 保存状态
                self._save_state()
                
                # 发送通知（可选）
                self._send_archive_notification(report)
                
                logger.info(f"每日归档完成: {archive_date.date()}")
            else:
                logger.warning("每日归档未生成报告")
                
        except Exception as e:
            logger.error(f"每日归档执行失败: {e}")
            self.state['last_error'] = {
                'timestamp': datetime.now().isoformat(),
                'operation': 'daily_archive',
                'error': str(e)
            }
            self._save_state()
    
    def _run_health_check(self):
        """运行健康检查"""
        try:
            logger.debug("执行健康检查...")
            
            # 获取系统统计
            stats = self.memory_manager.get_stats()
            
            # 检查数据库连接
            db_ok = stats.get('database', {}).get('total_messages', -1) >= 0
            
            # 检查向量索引
            vector_ok = stats.get('vector_search', {}).get('has_index', False)
            
            # 更新状态
            self.state['last_health_check'] = {
                'timestamp': datetime.now().isoformat(),
                'database_ok': db_ok,
                'vector_index_ok': vector_ok,
                'total_messages': stats.get('database', {}).get('total_messages', 0),
                'db_size_mb': stats.get('database', {}).get('db_size', 0) / (1024 * 1024)
            }
            
            # 保存状态
            self._save_state()
            
            if not db_ok or not vector_ok:
                logger.warning(f"健康检查发现问题: db_ok={db_ok}, vector_ok={vector_ok}")
            
            logger.debug("健康检查完成")
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
    
    def _run_database_optimization(self):
        """运行数据库优化"""
        try:
            logger.info("开始数据库优化...")
            
            # 优化数据库
            self.memory_manager.db.optimize_database()
            
            # 更新状态
            self.state['last_optimization'] = datetime.now().isoformat()
            self._save_state()
            
            logger.info("数据库优化完成")
            
        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
    
    def _run_weekly_maintenance(self):
        """运行每周维护"""
        try:
            logger.info("开始每周维护...")
            
            # 1. 清理旧数据（保留90天）
            self.memory_manager.db.cleanup_old_data(days=90)
            
            # 2. 重建向量索引
            self._rebuild_vector_index()
            
            # 3. 备份数据库
            self._backup_database()
            
            # 更新状态
            self.state['last_weekly_maintenance'] = datetime.now().isoformat()
            self._save_state()
            
            logger.info("每周维护完成")
            
        except Exception as e:
            logger.error(f"每周维护失败: {e}")
    
    def _rebuild_vector_index(self):
        """重建向量索引"""
        try:
            logger.info("开始重建向量索引...")
            
            # 获取所有用户消息
            cursor = self.memory_manager.db.conn.cursor()
            cursor.execute("""
                SELECT message_id, content 
                FROM chat_messages 
                WHERE sender_type = 'user'
                ORDER BY timestamp DESC
                LIMIT 10000  -- 限制数量，避免内存不足
            """)
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'message_id': row['message_id'],
                    'text': row['content']
                })
            
            # 重建索引
            if messages:
                success = self.memory_manager.vector_search.rebuild_index(messages)
                if success:
                    self.memory_manager.vector_search.save_index()
                    logger.info(f"向量索引重建完成，包含 {len(messages)} 条消息")
                else:
                    logger.warning("向量索引重建失败")
            
        except Exception as e:
            logger.error(f"重建向量索引失败: {e}")
    
    def _backup_database(self):
        """备份数据库"""
        try:
            db_path = self.memory_manager.db.db_path
            if not os.path.exists(db_path):
                return
            
            # 创建备份目录
            backup_dir = os.path.expanduser("~/.openclaw-autoclaw/data/backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"chat_memory_backup_{timestamp}.db")
            
            # 复制数据库文件
            import shutil
            shutil.copy2(db_path, backup_path)
            
            # 保留最近7个备份
            self._cleanup_old_backups(backup_dir, keep_count=7)
            
            logger.info(f"数据库备份完成: {backup_path}")
            
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
    
    def _cleanup_old_backups(self, backup_dir: str, keep_count: int = 7):
        """清理旧的备份文件"""
        try:
            # 获取所有备份文件
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.startswith("chat_memory_backup_") and filename.endswith(".db"):
                    filepath = os.path.join(backup_dir, filename)
                    mtime = os.path.getmtime(filepath)
                    backup_files.append((mtime, filepath))
            
            # 按修改时间排序
            backup_files.sort(reverse=True)
            
            # 删除多余的备份
            for i in range(keep_count, len(backup_files)):
                old_file = backup_files[i][1]
                os.remove(old_file)
                logger.debug(f"删除旧备份: {old_file}")
                
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
    
    def _send_archive_notification(self, report: dict):
        """发送归档通知（可选）"""
        try:
            # 这里可以集成到消息系统，发送归档报告
            # 例如：发送到Telegram、Discord或保存到文件
            
            # 简单实现：保存到日志文件
            notification_dir = os.path.expanduser("~/.openclaw-autoclaw/data/notifications")
            os.makedirs(notification_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            notification_file = os.path.join(notification_dir, f"archive_{timestamp}.json")
            
            with open(notification_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"归档通知已保存: {notification_file}")
            
        except Exception as e:
            logger.error(f"发送归档通知失败: {e}")
    
    def _load_state(self) -> dict:
        """加载调度器状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载调度器状态失败: {e}")
        
        # 默认状态
        return {
            'initialized_at': datetime.now().isoformat(),
            'archive_count': 0,
            'last_archive': None,
            'last_health_check': None,
            'last_error': None
        }
    
    def _save_state(self):
        """保存调度器状态"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"保存调度器状态失败: {e}")
    
    def get_status(self) -> dict:
        """
        获取调度器状态
        
        Returns:
            状态信息字典
        """
        status = {
            'running': self.running,
            'auto_archive_time': f"{self.auto_archive_hour:02d}:{self.auto_archive_minute:02d}",
            'next_archive': self._get_next_archive_time(),
            'state': self.state.copy(),
            'timestamp': datetime.now().isoformat()
        }
        
        # 添加调度任务信息
        status['scheduled_jobs'] = []
        for job in schedule.get_jobs():
            status['scheduled_jobs'].append({
                'job_func': job.job_func.__name__,
                'next_run': job.next_run.isoformat() if job.next_run else None,
                'period': str(job.period)
            })
        
        return status
    
    def _get_next_archive_time(self) -> Optional[str]:
        """获取下一次归档时间"""
        try:
            for job in schedule.get_jobs():
                if job.job_func.__name__ == '_run_daily_archive' and job.next_run:
                    return job.next_run.isoformat()
        except:
            pass
        
        return None
    
    def run_manual_archive(self, date_str: Optional[str] = None):
        """
        手动运行归档
        
        Args:
            date_str: 归档日期字符串 (YYYY-MM-DD)，默认为昨天
        """
        try:
            if date_str:
                archive_date = datetime.fromisoformat(date_str)
            else:
                archive_date = datetime.now() - timedelta(days=1)
            
            logger.info(f"手动运行归档: {archive_date.date()}")
            
            report = self.memory_manager.daily_archive(archive_date)
            
            if report:
                logger.info(f"手动归档完成: {report.get('total_messages', 0)} 条消息")
                return report
            else:
                logger.warning("手动归档未生成报告")
                return None
                
        except Exception as e:
            logger.error(f"手动归档失败: {e}")
            return None


# 全局调度器实例
_scheduler_instance = None

def get_scheduler(auto_archive_hour: int = 23,
                  auto_archive_minute: int = 0) -> MemoryScheduler:
    """
    获取调度器实例（单例模式）
    
    Args:
        auto_archive_hour: 自动归档小时
        auto_archive_minute: 自动归档分钟
        
    Returns:
        MemoryScheduler实例
    """
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = MemoryScheduler(auto_archive_hour, auto_archive_minute)
    
    return _scheduler_instance