#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sys

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.image_generator import image_generator

# 创建FastAPI应用
app = FastAPI(title="ComfyUI API", description="ComfyUI API服务，提供图像生成功能")

class ImageGenerationRequest(BaseModel):
    prompt: str = ""
    negative_prompt: str = ""
    width: int = 512
    height: int = 512

@app.post("/api/generate_image")
async def generate_image(request: ImageGenerationRequest):
    """
    生成图像API
    
    接收图像生成参数，提交图像生成任务，并返回任务ID
    """
    try:
        # 准备参数
        params = request.dict()
        
        # 提交图像生成任务
        task_id = image_generator.generate_image(**params)
        
        return {"status": "success", "task_id": task_id, "message": "任务已提交，请使用任务ID查询状态"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交图像生成任务失败: {str(e)}")

@app.get("/api/task_status/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态API
    
    根据任务ID获取图像生成任务的状态
    """
    try:
        status = image_generator.get_task_status(task_id)
        if status["status"] == "not_found":
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")

@app.get("/api/get_file/{prompt_id}")
async def get_file(prompt_id: str):
    """
    获取图像文件API
    
    根据prompt_id获取生成的图像文件路径
    """
    try:
        file_path = image_generator.get_files(prompt_id)
        return {"status": "success", "file_path": file_path}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"获取文件失败: {str(e)}")

@app.get("/api/download_image/{prompt_id}")
async def download_image(prompt_id: str):
    """
    下载图像API
    
    根据prompt_id下载生成的图像文件
    """
    try:
        file_path = image_generator.get_files(prompt_id)
        return FileResponse(file_path, media_type="image/png", filename=f"{prompt_id}.png")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"下载图像失败: {str(e)}")