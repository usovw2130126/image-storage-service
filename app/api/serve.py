from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from typing import Optional

from app.api.auth import get_api_key
from app.services.storage import StorageService
from app.services.image_processor import ImageProcessor
from app.utils.validators import validate_image_dimensions, validate_quality
from app.utils.security import ImageServiceError

router = APIRouter(prefix="/api/v1/images", tags=["serve"])

# 全域服務實例
storage_service = StorageService()
image_processor = ImageProcessor()

@router.get("/{uuid}")
async def get_image(
    uuid: str,
    width: Optional[int] = Query(None, description="Target width"),
    height: Optional[int] = Query(None, description="Target height"),
    quality: Optional[int] = Query(None, ge=1, le=100, description="Image quality (1-100)"),
    format: Optional[str] = Query(None, description="Output format (jpeg, png, webp)"),
    mode: Optional[str] = Query("fit", description="Resize mode (fit, fill, crop)"),
    api_key: str = Depends(get_api_key)
):
    """獲取圖片（支援動態調整大小）"""
    try:
        # 驗證參數
        validate_image_dimensions(width, height)
        if quality is not None:
            validate_quality(quality)
        
        # 驗證調整模式
        if mode not in ["fit", "fill", "crop"]:
            raise ImageServiceError(
                code="INVALID_MODE",
                message="Invalid resize mode",
                status_code=400,
                details="Mode must be one of: fit, fill, crop"
            )
        
        # 驗證並轉換輸出格式
        if format:
            format = image_processor.validate_and_convert_format(format)
        
        # 獲取圖片元數據
        image_metadata = storage_service.metadata_manager.get_image(uuid)
        if not image_metadata:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "IMAGE_NOT_FOUND",
                        "message": "Image not found",
                        "details": f"Image with UUID {uuid} does not exist"
                    }
                }
            )
        
        # 檢查權限
        if not storage_service.metadata_manager.check_image_permission(uuid, api_key):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Access denied",
                        "details": "You do not have permission to access this image"
                    }
                }
            )
        
        # 讀取原始檔案
        file_content = await storage_service.read_file(image_metadata["file_path"])
        
        # 如果需要調整大小或格式，進行處理
        if width or height or format or quality:
            processed_content, output_format = image_processor.resize_image(
                file_content=file_content,
                width=width,
                height=height,
                quality=quality or 85,
                output_format=format,
                mode=mode
            )
            
            # 設定正確的 MIME 類型
            mime_type_map = {
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'webp': 'image/webp',
                'gif': 'image/gif'
            }
            mime_type = mime_type_map.get(output_format, 'image/jpeg')
            
            return Response(
                content=processed_content,
                media_type=mime_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # 1小時快取
                    "Content-Disposition": f"inline; filename=\"{uuid}.{output_format}\""
                }
            )
        else:
            # 返回原始圖片
            original_format = image_metadata.get("format", "JPEG").lower()
            format_ext_map = {
                'jpeg': 'jpeg',
                'jpg': 'jpeg', 
                'png': 'png',
                'gif': 'gif',
                'webp': 'webp'
            }
            
            format_key = format_ext_map.get(original_format, 'jpeg')
            mime_type_map = {
                'jpeg': 'image/jpeg',
                'png': 'image/png', 
                'webp': 'image/webp',
                'gif': 'image/gif'
            }
            mime_type = mime_type_map.get(format_key, 'image/jpeg')
            
            return Response(
                content=file_content,
                media_type=mime_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # 1小時快取
                    "Content-Disposition": f"inline; filename=\"{image_metadata['original_name']}\""
                }
            )
    
    except ImageServiceError as e:
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