# ComfyAPI 工具集

这是一个基于 ComfyUI 的图像生成工具集，提供了命令行工具和 API 服务，方便用户使用 ComfyUI 生成图像。
# 快速运行
```
docker run -d  --name comfyapi -p 8081:8081 -v ./data:/app/resources  docker.1ms.run/rachelos/comfyapi:latest
```
## 项目结构

```
comfyui/
├── api/                # API 服务相关代码
│   ├── __init__.py
│   └── fastapi_app.py  # FastAPI 应用
├── client/             # ComfyUI 客户端代码
│   ├── __init__.py
│   └── comfyui_client.py  # ComfyUI 客户端
├── core/               # 核心功能模块
│   ├── __init__.py
│   └── image_generator.py  # 图像生成器
├── resources/          # 资源文件
│   └── img08/          # 生成的图像文件
├── templates/          # 模板文件
│   ├── qwen-image-workflowAPI.json    # 通义千问图像工作流模板
│   └── qwen-image-workflowAPI4.json   # 通义千问图像工作流模板（4步版本）
├── tests/              # 测试代码
│   ├── __init__.py
│   ├── test_api.py     # API 测试
│   └── test_progress.py  # 进度显示测试
├── utils/              # 工具函数和辅助代码
│   ├── __init__.py
│   └── generate_image.py  # 图像生成命令行工具
├── main.py             # 主入口文件
└── start_api_server.py  # API 服务启动脚本
```

## 使用方法

### 启动 API 服务

```bash
python main.py api --port 8000
```

或者直接使用：

```bash
python start_api_server.py
```

### 生成图像（命令行）

```bash
python main.py generate --prompt "美丽的山水风景" --negative "模糊，低质量" --width 640 --height 480
```

或者直接使用：

```bash
python utils/generate_image.py --prompt "美丽的山水风景" --negative "模糊，低质量" --width 640 --height 480
```

### 运行测试

```bash
python main.py test
```

## API 接口

### 生成图像

- **URL**: `/api/generate_image`
- **方法**: POST
- **请求体**:
  ```json
  {
    "prompt": "美丽的山水风景",
    "negative_prompt": "模糊，低质量",
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
  ```
- **响应**:
  ```json
  {
    "status": "success",
    "task_id": "任务ID",
    "message": "任务已提交，请使用任务ID查询状态"
  }
  ```

### 获取任务状态

- **URL**: `/api/task_status/{task_id}`
- **方法**: GET
- **响应**:
  ```json
  {
    "status": "completed",
    "task_id": "任务ID",
    "result": "图像文件路径",
    "execution_time": 10.5
  }
  ```

### 获取图像文件路径

- **URL**: `/api/get_file/{prompt_id}`
- **方法**: GET
- **响应**:
  ```json
  {
    "status": "success",
    "file_path": "图像文件路径"
  }
  ```

### 下载图像

- **URL**: `/api/download_image/{prompt_id}`
- **方法**: GET
- **响应**: 图像文件（PNG）

### 代理远程图片

- **URL**: `/api/proxy_image`
- **方法**: GET
- **参数**: 
  - `url` (查询参数): 要代理的远程图片URL
- **响应**: 图片流（支持跨域访问）
- **示例**: 
  ```
  GET /api/proxy_image?url=https://example.com/image.jpg
  ```
- **功能特点**:
  - 解决跨域访问问题
  - 支持多种图片格式（JPEG、PNG、GIF）
  - 自动图片优化和压缩
  - 缓存机制提高性能
  - 支持重定向跟随