#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client.comfyui_client import ComfyUIClient

def main():
    """
    命令行工具入口函数，用于生成图像
    """
    parser = argparse.ArgumentParser(description="ComfyUI图像生成工具")
    
    # 添加命令行参数
    parser.add_argument("--prompt", type=str, default="", help="正向提示词（描述你想要生成的内容）")
    parser.add_argument("--negative", type=str, default="", help="负向提示词（描述你不想在图像中出现的内容）")
    parser.add_argument("--width", type=int, default=640, help="图像宽度（像素）")
    parser.add_argument("--height", type=int, default=480, help="图像高度（像素）")
    parser.add_argument("--server", type=str, default="", help="ComfyUI服务器地址")
    parser.add_argument("--output", type=str, default=None, help="输出文件名")
    
    args = parser.parse_args()
    # 创建ComfyUI客户端
    client = ComfyUIClient(server_address=args.server)
    
    try:
        # 显示任务信息
        print("=" * 50)
        print("ComfyUI 图像生成任务")
        print("=" * 50)
        print(f"提示词: {args.prompt}")
        if args.negative:
            print(f"负面提示词: {args.negative}")
        print(f"图像尺寸: {args.width}x{args.height}")
        print(f"采样步数: {args.steps}")
        print(f"CFG比例: {args.cfg}")
        print(f"随机种子: {'随机' if args.seed == -1 else args.seed}")
        print(f"使用模型: {args.model}")
        print("=" * 50)
        print("开始生成图像...")
        
        # 生成图像
        output_file = client.generate_image(
            prompt=args.prompt,
            negative_prompt=args.negative,
            width=args.width,
            height=args.height,
            steps=args.steps,
            cfg=args.cfg,
            seed=args.seed,
            model=args.model,
            output_file=args.output
        )
        
        # 显示生成的图像
        client.display_image(output_file)
        
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())