from fastapi import APIRouter
from pydantic import BaseModel
from core.image_generator import  get_image_generator
from fastapi.responses import FileResponse
from fastapi import HTTPException

router = APIRouter(prefix="/api", tags=["Image Generation"])
image_generator = get_image_generator()
class ImageGenerationRequest(BaseModel):
    prompt: str = ""
    negative_prompt: str = ""
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
