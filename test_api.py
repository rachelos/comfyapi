#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import time
import os
from PIL import Image

def test_api():
    """
    测试ComfyUI API服务
    """
    # API服务地址
    api_url = "http://localhost:8081/api/"
    
    # 测试生成图像API
    print("测试生成图像API...")
    
    # 准备请求数据
    request_data = {
        "prompt": "beautiful mountain landscape with lake, sunset, photorealistic",
        "negative_prompt": "ugly, deformed",
        "width": 512,
        "height": 512,
    }
    
    # 发送请求
    response = requests.post(f"{api_url}generate_image", json=request_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"任务提交成功: {result}")
        
        # 获取任务ID
        task_id = result["task_id"]
        
        # 轮询任务状态
        print("\n轮询任务状态...")
        completed = False
        while not completed:
            status_response = requests.get(f"{api_url}task_status/{task_id}")
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"任务状态: {status['status']}")
                
                if status["status"] == "completed":
                    completed = True
                    print(f"任务完成，结果: {status['result']}")
                    
                    # 获取prompt_id（从文件路径中提取）
                    file_path = status["result"]
                    prompt_id = status["task_id"]
                    # 测试获取文件路径API
                    print("\n测试获取文件路径API...")
                    file_response = requests.get(f"{api_url}get_file/{prompt_id}")
                    
                    if file_response.status_code == 200:
                        file_result = file_response.json()
                        print(f"获取文件路径成功: {file_result}")
                    else:
                        print(f"获取文件路径失败: {file_response.status_code} {file_response.text}")
                elif status["status"] == "failed":
                    completed = True
                    print(f"任务失败，错误: {status.get('error', '未知错误')}")
                else:
                    # 等待一段时间后再次查询
                    time.sleep(2)
            else:
                print(f"获取任务状态失败: {status_response.status_code} {status_response.text}")
                break
    else:
        print(f"任务提交失败: {response.status_code} {response.text}")

if __name__ == "__main__":
    test_api()