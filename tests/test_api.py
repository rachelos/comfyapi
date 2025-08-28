#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import time
import os
import sys
from PIL import Image

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_api():
    """
    测试ComfyUI API服务
    """
    # API服务地址
    api_url = "http://localhost:8000"
    
    # 测试生成图像API
    print("测试生成图像API...")
    
    # 准备请求数据
    request_data = {
        "prompt": "beautiful mountain landscape with lake, sunset, photorealistic",
        "negative_prompt": "ugly, deformed",
        "width": 512,
        "height": 512,
        "steps": 4,
        "cfg": 7.0,
        "seed": -1,
        "model": "qwen-image-Q4_K_M.gguf",
        "extra_params": {
            "95.sampler_name": "euler_ancestral",
            "95.scheduler": "karras"
        }
    }
    
    # 发送请求
    response = requests.post(f"{api_url}/api/generate_image", json=request_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"任务提交成功: {result}")
        
        # 获取任务ID
        task_id = result["task_id"]
        
        # 轮询任务状态
        print("\n轮询任务状态...")
        completed = False
        while not completed:
            status_response = requests.get(f"{api_url}/api/task_status/{task_id}")
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"任务状态: {status['status']}")
                
                if status["status"] == "completed":
                    completed = True
                    print(f"任务完成，结果: {status['result']}")
                    
                    # 获取prompt_id（从文件路径中提取）
                    file_path = status["result"]
                    prompt_id = os.path.basename(file_path).replace(".png", "")
                    
                    # 测试获取文件路径API
                    print("\n测试获取文件路径API...")
                    file_response = requests.get(f"{api_url}/api/get_file/{prompt_id}")
                    
                    if file_response.status_code == 200:
                        file_result = file_response.json()
                        print(f"获取文件路径成功: {file_result}")
                        
                        # 测试下载图像API
                        print("\n测试下载图像API...")
                        download_response = requests.get(f"{api_url}/api/download_image/{prompt_id}")
                        
                        if download_response.status_code == 200:
                            # 保存下载的图像
                            download_path = f"./test_download_{prompt_id}.png"
                            with open(download_path, "wb") as f:
                                f.write(download_response.content)
                            print(f"图像下载成功，保存到: {download_path}")
                            
                            # 显示图像
                            try:
                                img = Image.open(download_path)
                                img.show()
                            except Exception as e:
                                print(f"无法显示图像: {e}")
                        else:
                            print(f"下载图像失败: {download_response.status_code} {download_response.text}")
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
        print(f"提交任务失败: {response.status_code} {response.text}")

if __name__ == "__main__":
    test_api()