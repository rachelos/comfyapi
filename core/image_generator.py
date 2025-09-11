#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import queue
import time
import uuid
from typing import Dict, Any, Optional, Callable
import os
import sys

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.comfyui_client import ComfyUIClient

class ImageGenerationTask:
    """
    图像生成任务类，用于存储任务信息和结果
    """
    def __init__(self, task_id: str, params: Dict[str, Any]):
        self.task_id = task_id
        self.params = params
        self.status = "pending"  # pending, running, completed, failed
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.progress = 0

class ImageGenerator:
    """
    图像生成器类，使用线程池处理图像生成请求
    """
    def __init__(self, server_address="http://10.10.10.59:6700", max_workers=3):
        self.client = ComfyUIClient(server_address)
        self.task_queue = queue.Queue()
        self.tasks = {}  # 存储所有任务
        self.max_workers = max_workers
        self.workers = []
        self.running = True
        
        # 启动工作线程
        for _ in range(max_workers):
            worker = threading.Thread(target=self._worker_thread, daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def _worker_thread(self):
        """
        工作线程，从队列中获取任务并执行
        """
        while self.running:
            try:
                # 减少超时时间，使线程能更快响应退出信号
                task_id = self.task_queue.get(timeout=0.5)
                if task_id is None:
                    # 收到退出信号
                    self.task_queue.task_done()  # 确保标记任务完成
                    break
                
                task = self.tasks.get(task_id)
                if task is None:
                    self.task_queue.task_done()  # 确保标记任务完成
                    continue
                
                # 更新任务状态
                task.status = "running"
                task.start_time = time.time()
                
                try:
                    # 调用ComfyUI客户端生成图像
                    kwargs = {}
                    if task.params.get("extra_params"):
                        kwargs.update(task.params["extra_params"])
                    self.client.set_workflow(task.params.get("workflow", "1.yml"))
                    id = self.client.generate_image(
                        prompt=task.params.get("prompt", ""),
                        negative_prompt=task.params.get("negative_prompt", ""),
                        template_name=task.params.get("template_name", ""),
                        width=task.params.get("width", 512),
                        height=task.params.get("height", 512),
                        batch_size=task.params.get("batch_size", 2),
                        # steps=task.params.get("steps", 4),
                        # cfg=task.params.get("cfg", 7.0),
                        # seed=task.params.get("seed", -1),
                        # model=task.params.get("model", "qwen-image-Q4_K_M.gguf"),
                        # output_file=task.params.get("output_file"),
                        **kwargs
                    )
                    task.prompt_id=id
                    output_file=self.client.status(id,task_id)
                    # 更新任务结果
                    task.result = output_file
                    
                    task.status = "completed"
                except Exception as e:
                    # 更新任务错误信息
                    task.error = str(e)
                    task.status = "failed"
                finally:
                    task.end_time = time.time()
                    self.task_queue.task_done()
            except queue.Empty:
                # 队列为空，继续检查running状态
                continue
            except Exception as e:
                print(f"工作线程发生错误: {e}")
                # 确保即使发生错误也标记任务完成
                try:
                    self.task_queue.task_done()
                except:
                    pass
    
    def generate_image(self,  **params) -> str:
        """
        提交图像生成任务
        
        Args:
            **params: 图像生成参数
            
        Returns:
            str: 任务ID
        """
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务
        task = ImageGenerationTask(task_id, params)
        self.tasks[task_id] = task
        
        # 将任务添加到队列
        self.task_queue.put(task_id)
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 任务状态信息
        """
        task = self.tasks.get(task_id)
        if task is None:
            return {"status": "not_found", "message": f"任务不存在: {task_id}"}
        
        result = {
            "status": task.status,
            "task_id": task.task_id
        }
        
        if task.status == "completed":
            result["result"] = task.result
            result["execution_time"] = task.end_time - task.start_time
        elif task.status == "failed":
            result["error"] = task.error
        elif task.status == "running":
            task.progress = self.client.get_progress()
            result["progress"] = task.progress
            result["running_time"] = time.time() - task.start_time
        
        return result
    
    def get_files(self, prompt_id: str) -> list:
        """
        获取生成的图像文件路径
        
        Args:
            prompt_id: 提示ID
            
        Returns:
            str: 图像文件路径
        """
        return self.client.get_files(prompt_id)
    
    def get_workflows(self) -> list:
        """
        获取流程
        Returns:
            json: 流程信息
        """
        return self.client.get_workflows()
    
    def shutdown(self):
        """
        关闭图像生成器
        """
        if not self.running:
            return  # 避免重复关闭
            
        self.running = False
        
        # 向队列中添加None，通知工作线程退出
        for _ in self.workers:
            try:
                self.task_queue.put(None, block=False)
            except queue.Full:
                pass  # 队列已满，忽略
        
        # 等待所有工作线程退出，设置超时避免阻塞
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=2.0)
                
        # 清空工作线程列表
        self.workers.clear()
        
    def __del__(self):
        """
        确保在对象被垃圾回收时正确清理资源
        """
        try:
            if hasattr(self, 'running') and self.running:
                self.shutdown()
        except:
            pass  # 忽略清理过程中的错误

# 创建全局图像生成器实例
image_generator = None

def get_image_generator():
    """
    获取全局图像生成器实例，懒加载模式
    """
    global image_generator
    if image_generator is None:
        image_generator = ImageGenerator(server_address=os.getenv("COMFYUI_SERVER", "http://127.0.0.1:6700"))
    return image_generator

# 注册退出处理函数，确保程序退出时正确清理资源
import atexit
def cleanup_resources():
    global image_generator
    if image_generator is not None:
        image_generator.shutdown()
        image_generator = None
atexit.register(cleanup_resources)