#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import shutil
from datetime import datetime, timedelta

class CacheCleaner:
    """
    缓存清理工具类，用于清理超过指定时间的缓存图片
    """
    
    def __init__(self, cache_root_dir="resources/img", days_threshold=1):
        """
        初始化缓存清理器
        
        Args:
            cache_root_dir (str): 缓存根目录，默认为 resources/img
            days_threshold (int): 清理阈值天数，默认为1天
        """
        self.cache_root_dir = cache_root_dir
        self.days_threshold = days_threshold
        self.cutoff_time = time.time() - (days_threshold * 24 * 60 * 60)
    
    def clean_old_cache(self, dry_run=False):
        """
        清理超过指定天数的缓存文件
        
        Args:
            dry_run (bool): 是否为试运行模式，True时只显示将要删除的文件，不实际删除
            
        Returns:
            dict: 清理统计信息
        """
        if not os.path.exists(self.cache_root_dir):
            print(f"缓存目录不存在: {self.cache_root_dir}")
            return {"deleted_files": 0, "deleted_dirs": 0, "freed_space": 0}
        
        deleted_files = 0
        deleted_dirs = 0
        freed_space = 0
        
        print(f"开始清理超过 {self.days_threshold} 天的缓存文件...")
        print(f"缓存目录: {self.cache_root_dir}")
        print(f"截止时间: {datetime.fromtimestamp(self.cutoff_time).strftime('%Y-%m-%d %H:%M:%S')}")
        
        if dry_run:
            print("=== 试运行模式 - 不会实际删除文件 ===")
        
        # 遍历所有月份目录
        for month_dir in os.listdir(self.cache_root_dir):
            month_path = os.path.join(self.cache_root_dir, month_dir)
            if not os.path.isdir(month_path):
                continue
            
            # 遍历任务目录
            for task_dir in os.listdir(month_path):
                task_path = os.path.join(month_path, task_dir)
                if not os.path.isdir(task_path):
                    continue
                
                # 检查任务目录的修改时间
                dir_mtime = os.path.getmtime(task_path)
                
                if dir_mtime < self.cutoff_time:
                    # 计算目录大小
                    dir_size = self._get_dir_size(task_path)
                    
                    if dry_run:
                        print(f"[试运行] 将删除目录: {task_path} (修改时间: {datetime.fromtimestamp(dir_mtime).strftime('%Y-%m-%d %H:%M:%S')}, 大小: {self._format_size(dir_size)})")
                    else:
                        try:
                            shutil.rmtree(task_path)
                            print(f"已删除目录: {task_path} (修改时间: {datetime.fromtimestamp(dir_mtime).strftime('%Y-%m-%d %H:%M:%S')}, 大小: {self._format_size(dir_size)})")
                            deleted_dirs += 1
                            freed_space += dir_size
                        except Exception as e:
                            print(f"删除目录失败 {task_path}: {e}")
                else:
                    # 检查目录内的单个文件
                    for file_name in os.listdir(task_path):
                        file_path = os.path.join(task_path, file_name)
                        if os.path.isfile(file_path):
                            file_mtime = os.path.getmtime(file_path)
                            file_size = os.path.getsize(file_path)
                            
                            if file_mtime < self.cutoff_time:
                                if dry_run:
                                    print(f"[试运行] 将删除文件: {file_path} (修改时间: {datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M:%S')}, 大小: {self._format_size(file_size)})")
                                else:
                                    try:
                                        os.remove(file_path)
                                        print(f"已删除文件: {file_path} (修改时间: {datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d %H:%M:%S')}, 大小: {self._format_size(file_size)})")
                                        deleted_files += 1
                                        freed_space += file_size
                                    except Exception as e:
                                        print(f"删除文件失败 {file_path}: {e}")
        
        # 清理空的月份目录
        for month_dir in os.listdir(self.cache_root_dir):
            month_path = os.path.join(self.cache_root_dir, month_dir)
            if os.path.isdir(month_path) and not os.listdir(month_path):
                if dry_run:
                    print(f"[试运行] 将删除空目录: {month_path}")
                else:
                    try:
                        os.rmdir(month_path)
                        print(f"已删除空目录: {month_path}")
                        deleted_dirs += 1
                    except Exception as e:
                        print(f"删除空目录失败 {month_path}: {e}")
        
        # 输出统计信息
        print("\n=== 清理统计 ===")
        if dry_run:
            print(f"试运行完成，实际未删除任何文件")
        else:
            print(f"已删除文件数: {deleted_files}")
            print(f"已删除目录数: {deleted_dirs}")
            print(f"释放空间: {self._format_size(freed_space)}")
        
        return {
            "deleted_files": deleted_files,
            "deleted_dirs": deleted_dirs,
            "freed_space": freed_space
        }
    
    def _get_dir_size(self, dir_path):
        """计算目录总大小"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(dir_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.isfile(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception:
            pass
        return total_size
    
    def _format_size(self, size_bytes):
        """格式化文件大小显示"""
        if size_bytes == 0:
            return "0B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.2f}{size_names[i]}"
    
    def get_cache_info(self):
        """
        获取缓存统计信息
        
        Returns:
            dict: 缓存统计信息
        """
        if not os.path.exists(self.cache_root_dir):
            return {"total_size": 0, "total_dirs": 0, "total_files": 0}
        
        total_size = 0
        total_dirs = 0
        total_files = 0
        old_files = 0
        old_dirs = 0
        
        for month_dir in os.listdir(self.cache_root_dir):
            month_path = os.path.join(self.cache_root_dir, month_dir)
            if not os.path.isdir(month_path):
                continue
            
            for task_dir in os.listdir(month_path):
                task_path = os.path.join(month_path, task_dir)
                if not os.path.isdir(task_path):
                    continue
                
                dir_mtime = os.path.getmtime(task_path)
                if dir_mtime < self.cutoff_time:
                    old_dirs += 1
                
                total_dirs += 1
                
                for file_name in os.listdir(task_path):
                    file_path = os.path.join(task_path, file_name)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        file_mtime = os.path.getmtime(file_path)
                        
                        total_size += file_size
                        total_files += 1
                        
                        if file_mtime < self.cutoff_time:
                            old_files += 1
        
        return {
            "total_size": total_size,
            "total_dirs": total_dirs,
            "total_files": total_files,
            "old_dirs": old_dirs,
            "old_files": old_files,
            "old_size": self._estimate_old_size()
        }
    
    def _estimate_old_size(self):
        """估算过期文件的大小"""
        old_size = 0
        try:
            for month_dir in os.listdir(self.cache_root_dir):
                month_path = os.path.join(self.cache_root_dir, month_dir)
                if not os.path.isdir(month_path):
                    continue
                
                for task_dir in os.listdir(month_path):
                    task_path = os.path.join(month_path, task_dir)
                    if not os.path.isdir(task_path):
                        continue
                    
                    dir_mtime = os.path.getmtime(task_path)
                    if dir_mtime < self.cutoff_time:
                        old_size += self._get_dir_size(task_path)
                    else:
                        for file_name in os.listdir(task_path):
                            file_path = os.path.join(task_path, file_name)
                            if os.path.isfile(file_path):
                                file_mtime = os.path.getmtime(file_path)
                                if file_mtime < self.cutoff_time:
                                    old_size += os.path.getsize(file_path)
        except Exception:
            pass
        return old_size


def clean_cache(days=1, dry_run=False):
    """
    便捷函数：清理缓存
    
    Args:
        days (int): 清理超过指定天数的缓存
        dry_run (bool): 是否为试运行模式
    """
    cleaner = CacheCleaner(days_threshold=days)
    return cleaner.clean_old_cache(dry_run=dry_run)


def show_cache_info(days=1):
    """
    便捷函数：显示缓存信息
    
    Args:
        days (int): 显示超过指定天数的过期缓存信息
    """
    cleaner = CacheCleaner(days_threshold=days)
    info = cleaner.get_cache_info()
    
    print("=== 缓存统计信息 ===")
    print(f"缓存目录: resources/img")
    print(f"总目录数: {info['total_dirs']}")
    print(f"总文件数: {info['total_files']}")
    print(f"总大小: {cleaner._format_size(info['total_size'])}")
    print(f"过期目录数 (> {days}天): {info['old_dirs']}")
    print(f"过期文件数 (> {days}天): {info['old_files']}")
    print(f"过期大小: {cleaner._format_size(info['old_size'])}")
    print(f"清理阈值: {datetime.fromtimestamp(cleaner.cutoff_time).strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="缓存清理工具")
    parser.add_argument("--days", type=int, default=1, help="清理超过指定天数的缓存 (默认: 1)")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不实际删除文件")
    parser.add_argument("--info", action="store_true", help="显示缓存统计信息")
    
    args = parser.parse_args()
    
    if args.info:
        show_cache_info(args.days)
    else:
        clean_cache(args.days, args.dry_run)