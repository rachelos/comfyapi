#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import uuid
import requests
from PIL import Image
from io import BytesIO

class ComfyUIClient:
    """
    ComfyUI客户端类，用于与ComfyUI服务器进行交互，发送工作流请求并获取生成的图像结果。
    """
    
    def __init__(self, server_address="http://10.10.10.59:6700"):
        """
        初始化ComfyUI客户端
        
        Args:
            server_address (str): ComfyUI服务器地址，默认为http://10.10.10.59:6700
        """
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.node_execution_times = {}  # 记录节点执行时间
        self.task_start_time = None     # 任务开始时间
        
    def get_workflow_template(self):
        """
        获取基本的工作流模板
        
        Returns:
            dict: 工作流模板
        """
        import json
        import os
        
        # 从配置文件中读取模板
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "/resource/templates", "qwen-image-workflowAPI4.json")
        with open(template_path, "r", encoding="utf-8") as f:
            workflow_template = json.load(f)
        
        return workflow_template
    
    def generate_image(self, prompt="", negative_prompt="", width=512, height=512, 
                    batch_size=2,
                    output_file=None, **kwargs):
        """
        生成图像
        
        Args:
            prompt (str): 正向提示词
            negative_prompt (str): 负向提示词
            width (int): 图像宽度
            height (int): 图像高度
            batch_size(int):生成数量
            steps (int): 采样步数
            cfg (float): CFG比例
            seed (int): 随机种子，-1表示随机
            model (str): 模型名称
            output_file (str): 输出文件名，如果为None则自动生成
            **kwargs: 其他工作流参数，可以使用节点ID和参数名称的组合作为键，例如：
                     "95.sampler_name": "euler_ancestral" 将设置节点95的sampler_name参数
            
        Returns:
            str: 生成的图像文件路径
        """
        # 准备工作流
        workflow = self.get_workflow_template()
        
        
        # 默认参数映射
        default_params = {
            "100.text": prompt,                # 正向提示词
            "93.text": negative_prompt,        # 负向提示词
            "97.width": width,                 # 图像宽度
            "97.height": height,               # 图像高度
            "97.batch_size":batch_size,         # 生成数量
            # "95.steps": steps,                 # 采样步数
            # "95.cfg": cfg,                     # CFG比例
            # "95.seed": seed,                   # 随机种子
            # "124.unet_name": model             # 模型名称
        }
        
        # 合并用户提供的额外参数
        for key, value in kwargs.items():
            if "." in key:
                default_params[key] = value
        
        # 更新工作流参数
        for key, value in default_params.items():
            if "." in key:
                node_id, param_name = key.split(".", 1)
                if node_id in workflow and "inputs" in workflow[node_id] and param_name in workflow[node_id]["inputs"]:
                    workflow[node_id]["inputs"][param_name] = value
        
        # 发送请求
        prompt_data = {
            "client_id": self.client_id,
            "prompt": workflow
        }
        
        # 发送请求到ComfyUI服务器
        response = requests.post(f"{self.server_address}/api/prompt", json=prompt_data)
        if response.status_code != 200:
            raise Exception(f"请求失败: {response.status_code} {response.text}")
        
        prompt_id = response.json()["prompt_id"]
        print(f"请求已发送，正在等待生成结果 (Prompt ID: {prompt_id})...")
        return prompt_id
    def status(self, prompt_id=None,task_id=""):
        if prompt_id is None:
            print("请提供有效的prompt_id")
            return
        # 等待生成完成
        start_time = time.time()
        while True:
            # 使用封装方法获取队列状态、历史记录和内部日志
            history = self.get_history()
            current_time = time.time()
            elapsed_time = int(current_time - start_time)
            
            # 检查历史记录中是否已完成
            if history and prompt_id in history:
                status = history[prompt_id]["status"]
                # 检查是否完成
                if status["completed"]:
                    elapsed_time = current_time - start_time
                    print(f"\r✅ 图像生成完成！耗时: {elapsed_time:.2f}秒" + " " * 50)
                    # 打印任务摘要
                    self.print_task_summary()
                    break
            time.sleep(5)
        
        # 获取生成的图像
        outputs = history[prompt_id]["outputs"]
        if "102" not in outputs:
            raise Exception("生成失败，未找到输出图像")
        
        images = outputs["102"]["images"]
        index=0
        for image_data in images:
            filename = image_data["filename"]
            subfolder = image_data["subfolder"]
            filetype = image_data["type"]
            
            # 下载图像
            image_url = f"{self.server_address}/api/view?filename={filename}&subfolder={subfolder}&type={filetype}"
            image_response = requests.get(image_url)
            if image_response.status_code != 200:
                raise Exception(f"下载图像失败: {image_response.status_code}")
            
            # 保存图像
            output_file = self.get_file(task_id,index)
            
            with open(output_file, "wb") as f:
                f.write(image_response.content)
            index+=1
            print(f"图像已保存到: {output_file}")
        return images
    

    # 创建保存目录 ./res/img+月份
    save_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), f"resources/img/{time.strftime("%m")}/")
    def get_file(self,prompt_id,index=0):
        save_dir = os.path.join(self.save_dir, f"{prompt_id}")
        os.makedirs(save_dir, exist_ok=True)
        
        # 使用prompt_id作为文件名
        output_file = os.path.join(save_dir, f"{index}.png")
        return output_file
    def get_files(self,prompt_id):
        save_dir = os.path.join(self.save_dir, f"{prompt_id}")
        file_root=save_dir.replace(os.path.dirname(os.path.dirname(__file__)),"").replace("\\","/")
        if not os.path.exists(save_dir):
            raise Exception(f"文件夹不存在: {file_root}")
        
        # 获取文件夹中的所有PNG文件
        files = [os.path.join(file_root, f) for f in os.listdir(save_dir) if f.endswith(".png")]
        if not files:
            raise Exception(f"未找到任何PNG文件: {file_root}")
        
        return files
    def display_image(self, image_path):
        """
        显示生成的图像
        
        Args:
            image_path (str): 图像文件路径
        """
        try:
            img = Image.open(image_path)
            img.show()
        except Exception as e:
            print(f"无法显示图像: {e}")
    
    def get_queue_status(self):
        """
        获取ComfyUI服务器的队列状态
        
        Returns:
            dict: 队列状态信息，包含运行中和等待中的任务
        """
        response = requests.get(f"{self.server_address}/api/queue")
        if response.status_code != 200:
            print(f"获取队列状态失败: {response.status_code}")
            return None
        return response.json()
    
    def get_history(self):
        """
        获取ComfyUI服务器的历史记录
        
        Returns:
            dict: 历史记录信息，包含已完成的任务
        """
        response = requests.get(f"{self.server_address}/api/history")
        if response.status_code != 200:
            print(f"获取历史记录失败: {response.status_code}")
            return None
        return response.json()
    def get_progress(self):
        logs_data=self.get_logs()
        if logs_data:
            try:
                # 查找与当前prompt_id相关的日志
                if "entries" in logs_data and logs_data["entries"]:
                    log_entry = logs_data["entries"][-1:][0]
                    if "%" in str(log_entry):
                        progress_percent = int(re.search(r'(\d+)%', log_entry['m']).group(1))
                        return progress_percent
            except Exception as e:
                print(f"解析日志数据时出错: {e}")
        return 0
    def get_logs(self):
        """
        获取ComfyUI服务器的内部日志信息
        
        Returns:
            dict: 内部日志信息，包含详细的执行日志
        """
        response = requests.get(f"{self.server_address}/internal/logs/raw")
        if response.status_code != 200:
            print(f"获取内部日志失败: {response.status_code}")
            return None
        return response.json()
            
    def track_task_progress(self, status, workflow, current_time, logs_data=None):
        """
        跟踪任务进度并返回格式化的进度信息
        
        Args:
            status (dict): 任务状态信息
            workflow (dict): 工作流定义
            current_time (float): 当前时间戳
            logs_data (list, optional): 内部日志数据
            
        Returns:
            tuple: (进度百分比, 当前节点信息, 节点执行统计, 详细进度信息)
        """
        # 此方法已被修改，大部分逻辑移至主循环中
        # 保留此方法以保持向后兼容性
        
        # 初始化任务开始时间
        if self.task_start_time is None:
            self.task_start_time = current_time
            
        # 从status中尝试获取进度信息（兼容旧版本）
        progress_percent = 0
        current_node_info = ""
        node_stats = {}
        detailed_progress_info = None
        
        # 首先尝试从内部日志获取详细信息
        if logs_data:
            prompt_id = None
            if "prompt_id" in status:
                prompt_id = status["prompt_id"]
                
            for log_entry in logs_data:
                if isinstance(log_entry, dict) and "prompt_id" in log_entry and log_entry["prompt_id"] == prompt_id:
                    if "progress" in log_entry:
                        progress_percent = int(log_entry["progress"] * 100)
                    if "node" in log_entry:
                        node_id = log_entry["node"]
                        if node_id in self.node_execution_times and "start" in self.node_execution_times[node_id]:
                            execution_time = current_time - self.node_execution_times[node_id]["start"]
                            self.node_execution_times[node_id]["time"] = execution_time
                            self.node_execution_times[node_id]["status"] = "已完成"
                    
                    # 获取更详细的进度信息
                    if "step" in log_entry and "total_steps" in log_entry:
                        step = log_entry["step"]
                        total_steps = log_entry["total_steps"]
                        detailed_progress_info = f"步骤: {step}/{total_steps}"
        
        # 如果内部日志没有提供足够信息，回退到旧的API格式
        if "messages" in status and status["messages"]:
            for msg in status["messages"]:
                if isinstance(msg, list) and len(msg) > 0:
                    # 节点执行完成
                    if msg[0] == "execution_cached" or msg[0] == "executed":
                        if len(msg) > 1 and isinstance(msg[1], dict) and "node" in msg[1]:
                            node_id = msg[1]["node"]
                            if node_id in self.node_execution_times and "start" in self.node_execution_times[node_id]:
                                execution_time = current_time - self.node_execution_times[node_id]["start"]
                                self.node_execution_times[node_id]["time"] = execution_time
                                self.node_execution_times[node_id]["status"] = "已完成"
        
        # 生成节点执行统计
        for node_id, data in self.node_execution_times.items():
            if "time" in data:
                node_title = f"节点 {node_id}"
                if node_id in workflow and "_meta" in workflow[node_id] and "title" in workflow[node_id]["_meta"]:
                    node_title = workflow[node_id]["_meta"]["title"]
                node_stats[node_id] = {
                    "title": node_title,
                    "time": data["time"],
                    "status": data["status"]
                }
        
        return progress_percent, current_node_info, node_stats, detailed_progress_info
        
    def print_task_summary(self):
        """
        打印任务执行摘要
        """
        if not self.node_execution_times or self.task_start_time is None:
            return
            
        total_time = time.time() - self.task_start_time
        print("\n" + "=" * 50)
        print(f"任务执行摘要 (总耗时: {total_time:.2f}秒)")
        print("-" * 50)
        
        # 按执行顺序排序节点
        sorted_nodes = sorted(
            [(k, v) for k, v in self.node_execution_times.items() if "time" in v],
            key=lambda x: x[1]["start"]
        )
        
        for node_id, data in sorted_nodes:
            node_title = f"节点 {node_id}"
            if "title" in data:
                node_title = data["title"]
            print(f"{node_title}: {data['time']:.2f}秒 ({data['status']})")
            
        print("=" * 50)
        
        # 重置跟踪数据
        self.node_execution_times = {}
        self.task_start_time = None

if __name__ == "__main__":
    # 简单的测试
    client = ComfyUIClient()
    
    # 基本用法
    id = client.generate_image(
        prompt="beautiful mountain landscape with lake, sunset, photorealistic",
        negative_prompt="ugly, deformed",
        width=512,
        height=512
    )
    output=client.status(id)
    # # 使用变量替换方式和额外参数
    # id = client.generate_image(
    #     prompt="cyberpunk city with neon lights, futuristic architecture",
    #     negative_prompt="blurry, low quality",
    #     width=640,
    #     height=480,
    #     # 使用节点ID.参数名的方式设置额外参数
    #     **{
    #         "95.sampler_name": "euler_ancestral",  # 设置采样器
    #         "95.scheduler": "karras",              # 设置调度器
    #         "94.vae_name": "qwen_image_vae.safetensors"  # 设置VAE模型
    #     }
    # )
    # output=client.status(id)