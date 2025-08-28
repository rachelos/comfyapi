#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ComfyUI 项目主入口文件
"""

import os
import sys
import argparse

def main():
    """
    主入口函数
    """
    parser = argparse.ArgumentParser(description="ComfyUI 工具集")
    parser.add_argument("action", choices=["api", "generate", "test"], help="要执行的操作")
    parser.add_argument("--server", type=str, default="http://10.10.10.59:6700", help="ComfyUI服务器地址")
    parser.add_argument("--port", type=int, default=8000, help="API服务端口")
    
    # 解析命令行参数
    args, unknown_args = parser.parse_known_args()
    
    # 根据操作类型执行不同的功能
    if args.action == "api":
        # 启动API服务
        import uvicorn
        print("启动 ComfyUI API 服务...")
        uvicorn.run("api.fastapi_app:app", host="0.0.0.0", port=args.port, reload=True)
    
    elif args.action == "generate":
        # 生成图像
        from utils.generate_image import main as generate_main
        sys.argv = [sys.argv[0]] + unknown_args
        return generate_main()
    
    elif args.action == "test":
        # 运行测试
        from tests.test_api import test_api
        test_api()
    
    return 0

if __name__ == "__main__":
    exit(main())