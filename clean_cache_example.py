#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
缓存清理使用示例
"""

from client.comfyui_client import ComfyUIClient
from utils.cache_cleaner import CacheCleaner, clean_cache, show_cache_info

def example_manual_clean():
    """
    手动清理缓存示例
    """
    print("=== 手动清理缓存示例 ===")
    
    # 创建客户端
    client = ComfyUIClient()
    
    # 显示当前缓存状态
    print("\n1. 当前缓存状态:")
    info = client.get_cache_info(days_threshold=1)
    print(f"   总目录数: {info['total_dirs']}")
    print(f"   总文件数: {info['total_files']}")
    print(f"   总大小: {client._format_size(info['total_size'])}")
    print(f"   过期目录数 (>1天): {info['old_dirs']}")
    print(f"   过期文件数 (>1天): {info['old_files']}")
    print(f"   过期大小: {client._format_size(info['old_size'])}")
    
    # 试运行清理
    print("\n2. 试运行清理 (不会实际删除文件):")
    result = client.clean_old_cache(days_threshold=1, dry_run=True)
    
    # 实际清理
    print("\n3. 实际清理缓存:")
    confirm = input("是否继续执行实际清理? (y/N): ")
    if confirm.lower() == 'y':
        result = client.clean_old_cache(days_threshold=1, dry_run=False)
        print(f"清理完成: {result}")
    else:
        print("已取消清理")

def example_auto_clean():
    """
    自动清理示例
    """
    print("\n=== 自动清理示例 ===")
    
    # 创建客户端
    client = ComfyUIClient()
    
    # 执行自动清理检查
    print("执行自动清理检查:")
    result = client.auto_clean_cache(days_threshold=1, check_interval_hours=24)
    
    if result:
        print(f"自动清理完成: {result}")
    else:
        print("无需执行清理或清理失败")

def example_standalone_cleaner():
    """
    独立清理工具示例
    """
    print("\n=== 独立清理工具示例 ===")
    
    # 显示缓存信息
    print("1. 显示缓存信息:")
    show_cache_info(days=1)
    
    # 使用便捷函数清理
    print("\n2. 使用便捷函数清理:")
    result = clean_cache(days=1, dry_run=True)
    print(f"试运行结果: {result}")

def example_generate_with_auto_clean():
    """
    生成图像时自动清理示例
    """
    print("\n=== 生成图像时自动清理示例 ===")
    
    try:
        # 创建客户端
        client = ComfyUIClient()
        
        # 设置工作流
        client.set_workflow("1.yaml")
        
        # 生成图像（会自动触发缓存清理检查）
        print("生成图像，会自动检查并清理过期缓存...")
        prompt_id = client.generate_image(
            prompt="a beautiful landscape",
            negative_prompt="blurry, low quality",
            width=512,
            height=512,
            batch_size=1,
            steps=20,
            cfg=7.5,
            seed=-1
        )
        
        print(f"图像生成请求已发送，Prompt ID: {prompt_id}")
        
    except Exception as e:
        print(f"生成图像失败: {e}")

def main():
    """
    主函数
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="缓存清理使用示例")
    parser.add_argument("--example", type=str, choices=["manual", "auto", "standalone", "generate"], 
                       default="manual", help="选择要运行的示例")
    
    args = parser.parse_args()
    
    if args.example == "manual":
        example_manual_clean()
    elif args.example == "auto":
        example_auto_clean()
    elif args.example == "standalone":
        example_standalone_cleaner()
    elif args.example == "generate":
        example_generate_with_auto_clean()

if __name__ == "__main__":
    main()