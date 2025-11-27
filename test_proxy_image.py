#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试图片代理功能
"""

import requests
import json

def test_proxy_image():
    """测试图片代理API"""
    base_url = "http://localhost:8081"
    
    # 测试用的远程图片URL
    test_urls = [
        "https://picsum.photos/200/300",
        "https://via.placeholder.com/150x150/0000FF/808080?text=Test",
        "https://httpbin.org/image/png"
    ]
    
    for i, url in enumerate(test_urls):
        print(f"\n测试图片 {i+1}: {url}")
        
        try:
            # 调用代理API
            response = requests.get(
                f"{base_url}/api/proxy_image",
                params={"url": url},
                timeout=30
            )
            
            print(f"状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                # 保存代理后的图片
                with open(f"proxied_image_{i+1}.jpg", "wb") as f:
                    f.write(response.content)
                print(f"图片已保存为: proxied_image_{i+1}.jpg")
                print(f"图片大小: {len(response.content)} bytes")
            else:
                print(f"错误: {response.text}")
                
        except Exception as e:
            print(f"请求失败: {e}")

if __name__ == "__main__":
    print("开始测试图片代理功能...")
    print("请确保服务器运行在 http://localhost:8081")
    test_proxy_image()