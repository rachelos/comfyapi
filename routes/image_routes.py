from fastapi import APIRouter
from pydantic import BaseModel
from core.image_generator import  get_image_generator
from fastapi.responses import FileResponse, StreamingResponse
from fastapi import HTTPException, Query
import httpx
import io
from PIL import Image
import logging

router = APIRouter(prefix="/api", tags=["Image Generation"])
image_generator = get_image_generator()
class ImageGenerationRequest(BaseModel):
    prompt: str = ""
    negative_prompt: str = ""
    workflow: str = "1.yaml"
    width: int = 512
    height: int = 512
    batch_size: int = 4

@router.post("/generate_image")
async def generate_image(request: ImageGenerationRequest):
    """
    生成图像API
    
    接收图像生成参数，提交图像生成任务，并返回任务ID
    """
    try:
        params = request.dict()
        task_id = image_generator.generate_image(**params)
        return {"status": "success", "task_id": task_id, "message": "任务已提交，请使用任务ID查询状态"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交图像生成任务失败: {str(e)}")

@router.get("/task_status/{task_id}")
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

@router.get("/get_file/{prompt_id}")
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
@router.get("/workflows")
async def get_workflows():
    """
    获取工作流程
    """
    try:
        data = image_generator.get_workflows()
        return data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"获取文件失败: {str(e)}")

@router.get("/proxy_image")
async def proxy_image(url: str = Query(..., description="要代理的远程图片URL")):
    """
    代理远程图片资源
    
    通过代理访问远程图片，解决跨域问题
    """
    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # 使用httpx客户端获取远程图片
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            
            # 检查响应内容类型
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="URL不是有效的图片资源")
            
            # 获取图片数据
            image_data = response.content
            
            # 尝试使用PIL验证图片格式
            try:
                image = Image.open(io.BytesIO(image_data))
                # 重新保存为JPEG格式（可根据需要调整）
                img_buffer = io.BytesIO()
                
                # 根据原始格式选择保存格式
                if image.format == "PNG":
                    image.save(img_buffer, format="PNG", quality=95)
                    content_type = "image/png"
                elif image.format == "GIF":
                    image.save(img_buffer, format="GIF")
                    content_type = "image/gif"
                else:
                    image.save(img_buffer, format="JPEG", quality=95, optimize=True)
                    content_type = "image/jpeg"
                
                img_buffer.seek(0)
                image_data = img_buffer.getvalue()
                
            except Exception as img_error:
                logging.warning(f"图片处理失败，直接返回原始数据: {img_error}")
            
            # 返回图片流响应
            return StreamingResponse(
                io.BytesIO(image_data),
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # 缓存1小时
                    "Access-Control-Allow-Origin": "*",  # 允许跨域
                    "Access-Control-Allow-Methods": "GET",
                    "Access-Control-Allow-Headers": "*",
                }
            )
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"获取远程图片失败: {e.response.status_code}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"请求远程图片失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"代理图片失败: {str(e)}")
