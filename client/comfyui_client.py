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
    save_images=os.getenv("SAVE_IMAGES",False)
    template_data=None
    def set_workflow(self,flow_id="1.yml"):
        self.template_name=flow_id
    def __init__(self, server_address="http://10.10.10.59:6700",template_name="1.yaml"):
        """
        初始化ComfyUI客户端
        
        Args:
            server_address (str): ComfyUI服务器地址，默认为http://10.10.10.59:6700
        """
        self.template_name=template_name
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.node_execution_times = {}  # 记录节点执行时间
        self.task_start_time = None     # 任务开始时间
    def get_template(self):
        template_path = os.path.join( "./resources/templates", self.template_name)
        import yaml
        try:
            self.template_data = yaml.load(open(template_path, "r", encoding="utf-8"),Loader=yaml.FullLoader)
        except:
            print(os.path.abspath(template_path))
            raise Exception(f"模板文件不存在{template_path}")
        return self.template_data


    def get_args(self,key="args"):
        data=self.get_template()
        args=data.get(key,{})
        return args
    def get_template_file(self):
        data=self.get_template()
        file=data.get("file","")
        file=os.path.join( "./resources/templates", file)
        if not os.path.exists(file):
            raise Exception("模板文件不存在")
        with open(file, "r", encoding="utf-8") as f:
            workflow_template = json.load(f)
        return workflow_template
    def get_workflow_template(self,params={},**kwargs):
        """
        获取基本的工作流模板
        
        Returns:
            dict: 工作流模板
        """
        import json
        import os
        
        # 从配置文件中读取模板
        workflow = self.get_template_file()
        args=self.get_args()
         # 默认参数映射
        default_params = {
            args.get("prompt","prompt"): params.get("prompt",""),                # 正向提示词100.text": params.get("prompt",""),                # 正向提示词
            args.get("negative_prompt","negative_prompt"): params.get("negative_prompt",""),        # 负向提示词
            args.get("width","width"): params.get("width",512),                 # 图像宽度
            args.get("height","height"): params.get("height",512),               # 图像高度
            args.get("batch_size","batch_size"): params.get("batch_size",2),         # 生成数量
        }
        #采样步数
        if params.get("steps",None) is not None:
            default_params[args.get("steps","steps")]=params.get("steps",4)
        #CFG比例
        if params.get("cfg",None) is not None:
            default_params[args.get("cfg","cfg")]=params.get("cfg","")
        #随机种子
        if params.get("seed",None) is not None:
            default_params[args.get("seed","seed")]=params.get("seed",-1)

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
        return workflow
    
    def generate_image(self, prompt="", negative_prompt="", width=512, height=512, 
                    batch_size=2,
                    steps=None,cfg=None,seed=None,
                     **kwargs):
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
        workflow = self.get_workflow_template({
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "batch_size": batch_size,
            "steps": steps,
            "cfg": cfg,
            "seed": seed,
        },**kwargs)
        
        
       
        
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
        print(f"请求已发送，{self.template_name}正在等待生成结果 (Prompt ID: {prompt_id})...")
        print(workflow)
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
        key=self.get_args(key="output").get("file","102")
        if key not in outputs:
            raise Exception("生成失败，未找到输出图像")
        
        images = outputs[key]["images"]
        index=0
        for image_data in images:
            filename = image_data["filename"]
            subfolder = image_data["subfolder"]
            filetype = image_data["type"]
            
            # 下载图像
            image_url = f"{self.server_address}/api/view?filename={filename}&subfolder={subfolder}&type={filetype}"
            images[index]["url"]=image_url
            index+=1
            if self.save_images==False:
                print(f"图像URL: {image_url}")
                continue
            image_response = requests.get(image_url)
            if image_response.status_code != 200:
                raise Exception(f"下载图像失败: {image_response.status_code}")
            
            # 保存图像
            output_file = self.get_file(task_id,index,ext=filename[filename.rfind("."):])
            
            with open(output_file, "wb") as f:
                f.write(image_response.content)
            
            print(f"图像已保存到: {output_file}")
        #保存JSON
        self.save_images_json(prompt_id=task_id,images=images)
        return images
    
    # 保存图像json
    def save_images_json(self,prompt_id,images):
        value=json.dumps(images, ensure_ascii=False, indent=4).encode("utf-8")
        output_file = self.get_file(prompt_id, "images",ext=".json")
        with open(output_file, "wb") as f:
              f.write(value)
        pass
    
    # 获取图像json
    def get_images_json(self,prompt_id):
        output_file = self.get_file(prompt_id, "images",ext=".json")
        if not os.path.exists(output_file):
            raise Exception("图像JSON文件不存在")
        images=json.loads(open(output_file, "r", encoding="utf-8").read())
        return images
    
    # 打印任务摘要
    
    # 创建保存目录 ./res/img+月份
    save_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), f"resources/img/{time.strftime("%m")}/")
    def get_file(self,prompt_id,index=0,ext=".png"):
        save_dir = os.path.join(self.save_dir, f"{prompt_id}")
        os.makedirs(save_dir, exist_ok=True)
        
        # 使用prompt_id作为文件名
        output_file = os.path.join(save_dir, f"{index}{ext}")
        return output_file
    
    # 清除保存的文件
    def clean_files(self):
        # 删除保存目录及其内容（包括非空目录）
        import shutil
        if os.path.exists(self.save_dir):
            shutil.rmtree(self.save_dir)
            # 重新创建目录
            os.makedirs(self.save_dir, exist_ok=True)
        pass
    def get_workflows(self):
        """
        获取template目录下所有的.yml和.yaml文件名
        
        Returns:
            list: 工作流模板文件名列表
        """
        import os
        import glob
        import yaml
        # 获取template目录路径
        templates_dir = os.path.join("./resources/templates")
        
        # 使用glob模块获取所有.yml和.yaml文件
        yml_files = glob.glob(os.path.join(templates_dir, "*.yml"))
        yaml_files = glob.glob(os.path.join(templates_dir, "*.yaml"))
        
        # 合并文件列表并只保留文件名（不含路径）
        workflow_files = []
        for file_path in yml_files + yaml_files:
            data=yaml.load(open(file_path, "r", encoding="utf-8"), Loader=yaml.FullLoader) if yaml.load(open(file_path, "r", encoding="utf-8"), Loader=yaml.FullLoader)["name"] else os.path.basename(file_path)
            workflow_files.append({
                "name": data["name"],
                "path": os.path.basename(file_path).replace("\\","/")
            })
            
        return workflow_files
    def get_files(self,prompt_id):
        save_dir = os.path.join(self.save_dir, f"{prompt_id}")
        if self.save_images==False:
            data=self.get_images_json(prompt_id)
            files=[url['url'] for url in data if 'url' in url]
            return files
        
        # 检查保存目录是否存在
        file_root=save_dir.replace(os.path.dirname(os.path.dirname(__file__)),"").replace("\\","/")
        if not os.path.exists(save_dir):
            raise Exception(f"文件夹不存在: {file_root}")
        
        # 获取文件夹中的所有PNG文件
        files = [os.path.join(file_root, f) for f in os.listdir(save_dir) if f.endswith(".png") or f.endswith(".webp") or f.endswith(".jpg")]
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
    os.environ["SAVE_IMAGES"] = "True"
    client = ComfyUIClient(server_address="http://10.10.10.54:8188", template_name="2.yaml",)
    client.clean_files()
    print(client.get_workflows())
    # 基本用法
    id = client.generate_image(
        prompt="beautiful cat landscape with lake, sunset, photorealistic",
        negative_prompt="ugly, deformed",
        width=512,
        height=512,
        steps=10,
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