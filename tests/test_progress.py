#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import sys

def simulate_task_with_progress():
    """
    模拟一个有进度显示的任务
    """
    total_steps = 10
    progress_chars = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    progress_idx = 0
    
    print("开始执行模拟任务...")
    start_time = time.time()
    
    # 模拟任务节点
    nodes = [
        {"id": "1", "name": "加载模型", "duration": 2},
        {"id": "2", "name": "处理提示词", "duration": 1},
        {"id": "3", "name": "生成潜空间", "duration": 0.5},
        {"id": "4", "name": "采样过程", "duration": 3},
        {"id": "5", "name": "解码图像", "duration": 1.5}
    ]
    
    node_stats = {}
    
    # 执行每个节点
    for node in nodes:
        node_start = time.time()
        node_stats[node["id"]] = {"name": node["name"], "start": node_start, "status": "执行中"}
        
        # 模拟节点执行过程
        steps_for_node = int(node["duration"] * 2)
        for step in range(steps_for_node):
            current_time = time.time()
            elapsed_time = int(current_time - start_time)
            progress_char = progress_chars[progress_idx]
            progress_idx = (progress_idx + 1) % len(progress_chars)
            
            # 计算总体进度
            total_progress = int((sum(n["duration"] for n in nodes[:nodes.index(node)]) + 
                               (step / steps_for_node) * node["duration"]) / 
                              sum(n["duration"] for n in nodes) * 100)
            
            # 构建进度条
            bar_length = 20
            filled_length = int(bar_length * total_progress / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # 显示基本进度信息
            status_display = f"进度: {total_progress}% | 当前节点: {node['name']} | [{bar}]"
            print(f"\r{progress_char} 正在执行任务... {status_display}", end="", flush=True)
            
            # 每5步显示一次详细节点状态
            if step % 5 == 0 and step > 0:
                # 清除当前行
                print("\r" + " " * 100, end="\r", flush=True)
                print(f"{progress_char} 正在执行任务... {status_display}")
                
                # 打印节点执行状态
                print("\n节点执行状态:")
                for node_id, data in node_stats.items():
                    status_icon = "⏳" if data["status"] == "执行中" else "✓"
                    if data["status"] == "执行中":
                        time_info = f"{time.time() - data['start']:.2f}秒 (进行中...)"
                    else:
                        time_info = f"{data['time']:.2f}秒 (完成)"
                    print(f"  {status_icon} {data['name']}: {time_info}")
                
                # 移动光标回到进度行
                print("\033[A" * (len(node_stats) + 2), end="", flush=True)
            
            time.sleep(0.5)
        
        # 节点完成
        node_end = time.time()
        node_stats[node["id"]]["status"] = "已完成"
        node_stats[node["id"]]["time"] = node_end - node_start
    
    # 任务完成
    elapsed_time = time.time() - start_time
    print(f"\r✅ 任务执行完成！耗时: {elapsed_time:.2f}秒" + " " * 50)
    
    # 打印任务摘要
    print("\n" + "=" * 50)
    print(f"任务执行摘要 (总耗时: {elapsed_time:.2f}秒)")
    print("-" * 50)
    
    for node_id, data in node_stats.items():
        print(f"{data['name']}: {data['time']:.2f}秒 ({data['status']})")
        
    print("=" * 50)

if __name__ == "__main__":
    simulate_task_with_progress()