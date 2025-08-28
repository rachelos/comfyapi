#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fastapi import FastAPI
import uvicorn
from fastapi.staticfiles import StaticFiles
from routes.image_routes import router as image_router

# 创建FastAPI应用
app = FastAPI(title="ComfyUI API", description="ComfyUI API服务，提供图像生成功能")

# 注册路由
app.include_router(image_router)

# 添加静态文件路由
app.mount("/resources", StaticFiles(directory="resources"), name="resources")
# 添加web_ui前端页面静态路由
app.mount("/", StaticFiles(directory="web_ui", html=True), name="web_ui")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8081, reload=True)