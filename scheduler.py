#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import schedule
import logging
from datetime import datetime
from client.comfyui_client import ComfyUIClient
from utils.cache_cleaner import CacheCleaner

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cache_cleaner.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class CacheScheduler:
    """
    缓存清理调度器，用于定期执行缓存清理任务
    """
    
    def __init__(self, clean_days=1, schedule_time="02:00"):
        """
        初始化调度器
        
        Args:
            clean_days (int): 清理超过指定天数的缓存
            schedule_time (str): 每天执行清理的时间，格式为 "HH:MM"
        """
        self.clean_days = clean_days
        self.schedule_time = schedule_time
        self.client = ComfyUIClient()
        self.cache_cleaner = CacheCleaner(days_threshold=clean_days)
    
    def run_cache_cleanup(self):
        """
        执行缓存清理任务
        """
        try:
            logger.info("开始执行定期缓存清理任务")
            logger.info(f"清理阈值: {self.clean_days} 天")
            
            # 显示清理前的缓存信息
            info = self.client.get_cache_info(self.clean_days)
            logger.info(f"清理前缓存状态 - 总文件: {info['total_files']}, 过期文件: {info['old_files']}, 总大小: {self.client._format_size(info['total_size'])}")
            
            # 执行清理
            result = self.client.clean_old_cache(self.clean_days)
            
            if result:
                logger.info(f"清理完成 - 删除文件: {result['deleted_files']}, 删除目录: {result['deleted_dirs']}, 释放空间: {self.client._format_size(result['freed_space'])}")
            else:
                logger.warning("清理任务执行失败")
                
        except Exception as e:
            logger.error(f"缓存清理任务执行出错: {e}")
    
    def run_auto_cleanup_check(self):
        """
        执行自动清理检查（基于时间间隔）
        """
        try:
            logger.info("执行自动清理检查")
            result = self.client.auto_clean_cache(self.clean_days, 24)  # 24小时间隔
            
            if result:
                logger.info(f"自动清理完成 - 删除文件: {result['deleted_files']}, 删除目录: {result['deleted_dirs']}, 释放空间: {self.client._format_size(result['freed_space'])}")
            else:
                logger.info("无需执行清理")
                
        except Exception as e:
            logger.error(f"自动清理检查出错: {e}")
    
    def start_scheduler(self):
        """
        启动调度器
        """
        logger.info(f"启动缓存清理调度器")
        logger.info(f"每天 {self.schedule_time} 执行清理任务")
        logger.info(f"清理超过 {self.clean_days} 天的缓存文件")
        
        # 设置定时任务
        schedule.every().day.at(self.schedule_time).do(self.run_cache_cleanup)
        
        # 每6小时检查一次是否需要自动清理
        schedule.every(6).hours.do(self.run_auto_cleanup_check)
        
        logger.info("调度器已启动，等待执行任务...")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("调度器已停止")
        except Exception as e:
            logger.error(f"调度器运行出错: {e}")
    
    def run_once(self):
        """
        立即执行一次清理任务
        """
        logger.info("立即执行缓存清理任务")
        self.run_cache_cleanup()


def main():
    """
    主函数，用于启动调度器
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="缓存清理调度器")
    parser.add_argument("--days", type=int, default=1, help="清理超过指定天数的缓存 (默认: 1)")
    parser.add_argument("--time", type=str, default="02:00", help="每天执行清理的时间 (默认: 02:00)")
    parser.add_argument("--run-once", action="store_true", help="立即执行一次清理任务后退出")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不实际删除文件")
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("=== 试运行模式 ===")
        cleaner = CacheCleaner(days_threshold=args.days)
        cleaner.clean_old_cache(dry_run=True)
        return
    
    if args.run_once:
        scheduler = CacheScheduler(clean_days=args.days, schedule_time=args.time)
        scheduler.run_once()
    else:
        scheduler = CacheScheduler(clean_days=args.days, schedule_time=args.time)
        scheduler.start_scheduler()


if __name__ == "__main__":
    main()