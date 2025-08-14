from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks
from typing import List, Optional
import uuid
import os
from datetime import datetime

from app.api.auth import get_api_key, get_api_key_config
from app.services.storage import StorageService, MetadataManager
from app.services.image_processor import ImageProcessor
from app.utils.validators import validate_file_content
from app.utils.security import generate_uuid, sanitize_filename, ImageServiceError
from app.schemas.image import ImageUploadResponse, BatchUploadResponse, BatchProgressResponse, ImageInfo
from app.config import MAX_BATCH_SIZE

router = APIRouter(prefix="/api/v1/images", tags=["upload"])

# 全域服務實例
storage_service = StorageService()
image_processor = ImageProcessor()

# 批次進度追蹤（內存存儲）
batch_progress = {}

@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    user_path: str = Form(...),
    api_key: str = Depends(get_api_key),
    api_key_config: dict = Depends(get_api_key_config)
):
    """單張圖片上傳"""
    try:
        # 驗證路徑權限
        allowed_prefix = api_key_config.get("allowed_prefix", "")
        if not user_path.startswith(allowed_prefix):
            raise ImageServiceError(
                code="PATH_FORBIDDEN",
                message="Path access denied",
                status_code=403,
                details=f"Path must start with '{allowed_prefix}'"
            )
        
        # 讀取檔案內容
        file_content = await file.read()
        
        # 驗證檔案
        validate_file_content(file_content, file.filename)
        
        # 獲取圖片資訊
        image_info = image_processor.get_image_info(file_content)
        
        # 生成 UUID 和檔案名
        image_uuid = generate_uuid()
        safe_filename = sanitize_filename(file.filename)
        file_extension = safe_filename.split('.')[-1] if '.' in safe_filename else 'jpg'
        storage_filename = f"{image_uuid}.{file_extension}"
        
        # 保存檔案
        relative_file_path = os.path.join(user_path, storage_filename).replace('\\', '/')
        await storage_service.save_file(file_content, user_path, storage_filename)
        
        # 保存元數據
        metadata = storage_service.metadata_manager.add_image(
            uuid=image_uuid,
            file_path=relative_file_path,
            original_name=safe_filename,
            api_key=api_key,
            user_path=user_path,
            file_size=len(file_content),
            format_type=image_info['format'],
            dimensions=image_info['dimensions']
        )
        
        # 構建回應
        image_response = ImageInfo(
            uuid=image_uuid,
            original_name=safe_filename,
            user_path=user_path,
            file_size=len(file_content),
            format=image_info['format'],
            dimensions=image_info['dimensions'],
            upload_time=datetime.fromisoformat(metadata['upload_time']),
            access_url=f"/api/v1/images/{image_uuid}"
        )
        
        return ImageUploadResponse(success=True, images=[image_response])
        
    except ImageServiceError as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
            }
        )
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "details": str(e)
                }
            }
        )

@router.post("/batch-upload", response_model=BatchUploadResponse)
async def batch_upload_images(
    files: List[UploadFile] = File(...),
    user_path: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    api_key: str = Depends(get_api_key),
    api_key_config: dict = Depends(get_api_key_config)
):
    """批次圖片上傳"""
    try:
        # 驗證路徑權限
        allowed_prefix = api_key_config.get("allowed_prefix", "")
        if not user_path.startswith(allowed_prefix):
            raise ImageServiceError(
                code="PATH_FORBIDDEN", 
                message="Path access denied",
                status_code=403,
                details=f"Path must start with '{allowed_prefix}'"
            )
        
        # 驗證檔案數量
        if len(files) > MAX_BATCH_SIZE:
            raise ImageServiceError(
                code="TOO_MANY_FILES",
                message="Too many files",
                status_code=400,
                details=f"Maximum {MAX_BATCH_SIZE} files allowed"
            )
        
        # 生成批次 ID
        batch_id = f"batch-{generate_uuid()}"
        
        # 初始化批次進度
        batch_progress[batch_id] = {
            "total": len(files),
            "completed": 0,
            "failed": 0,
            "status": "processing",
            "results": [],
            "start_time": datetime.utcnow().isoformat()
        }
        
        # 添加背景任務
        background_tasks.add_task(
            process_batch_upload,
            batch_id, files, user_path, api_key
        )
        
        return BatchUploadResponse(
            success=True,
            batch_id=batch_id,
            status="processing",
            total_files=len(files),
            progress_url=f"/api/v1/batch/{batch_id}/progress"
        )
        
    except ImageServiceError as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
            }
        )

@router.get("/batch/{batch_id}/progress", response_model=BatchProgressResponse)
async def get_batch_progress(
    batch_id: str,
    api_key: str = Depends(get_api_key)
):
    """獲取批次上傳進度"""
    if batch_id not in batch_progress:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "BATCH_NOT_FOUND",
                    "message": "Batch not found",
                    "details": f"Batch ID {batch_id} does not exist"
                }
            }
        )
    
    progress = batch_progress[batch_id]
    
    # 計算進度百分比
    if progress["total"] > 0:
        progress_percentage = (progress["completed"] + progress["failed"]) / progress["total"] * 100
    else:
        progress_percentage = 100.0
    
    # 估算剩餘時間（簡單實作）
    estimated_time = None
    if progress["status"] == "processing" and progress["completed"] > 0:
        start_time = datetime.fromisoformat(progress["start_time"])
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        if elapsed > 0:
            rate = progress["completed"] / elapsed
            remaining = progress["total"] - progress["completed"] - progress["failed"]
            if rate > 0:
                estimated_seconds = remaining / rate
                estimated_time = f"{int(estimated_seconds)} seconds"
    
    return BatchProgressResponse(
        batch_id=batch_id,
        total=progress["total"],
        completed=progress["completed"],
        failed=progress["failed"],
        status=progress["status"],
        progress_percentage=progress_percentage,
        estimated_time_remaining=estimated_time,
        results=progress["results"]
    )

async def process_batch_upload(batch_id: str, files: List[UploadFile], 
                             user_path: str, api_key: str):
    """背景處理批次上傳"""
    progress = batch_progress[batch_id]
    
    for i, file in enumerate(files):
        try:
            # 讀取檔案內容
            file_content = await file.read()
            
            # 驗證檔案
            validate_file_content(file_content, file.filename)
            
            # 獲取圖片資訊
            image_info = image_processor.get_image_info(file_content)
            
            # 生成 UUID 和檔案名
            image_uuid = generate_uuid()
            safe_filename = sanitize_filename(file.filename)
            file_extension = safe_filename.split('.')[-1] if '.' in safe_filename else 'jpg'
            storage_filename = f"{image_uuid}.{file_extension}"
            
            # 保存檔案
            relative_file_path = os.path.join(user_path, storage_filename).replace('\\', '/')
            await storage_service.save_file(file_content, user_path, storage_filename)
            
            # 保存元數據
            storage_service.metadata_manager.add_image(
                uuid=image_uuid,
                file_path=relative_file_path,
                original_name=safe_filename,
                api_key=api_key,
                user_path=user_path,
                file_size=len(file_content),
                format_type=image_info['format'],
                dimensions=image_info['dimensions']
            )
            
            # 記錄成功結果
            progress["results"].append({
                "uuid": image_uuid,
                "filename": safe_filename,
                "status": "success"
            })
            progress["completed"] += 1
            
        except Exception as e:
            # 記錄失敗結果
            progress["results"].append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e)
            })
            progress["failed"] += 1
    
    # 更新最終狀態
    progress["status"] = "completed"
    progress["end_time"] = datetime.utcnow().isoformat()