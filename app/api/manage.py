from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List

from app.api.auth import get_api_key
from app.services.storage import StorageService
from app.schemas.image import BatchDeleteRequest
from app.utils.security import ImageServiceError

router = APIRouter(prefix="/api/v1/images", tags=["manage"])

# 全域服務實例
storage_service = StorageService()

@router.get("")
async def list_images(
    user_path: Optional[str] = Query(None, description="Filter by user path"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    api_key: str = Depends(get_api_key)
):
    """列出圖片（支援分頁和路徑篩選）"""
    try:
        skip = (page - 1) * limit
        
        images = storage_service.metadata_manager.list_images(
            api_key=api_key,
            user_path=user_path,
            skip=skip,
            limit=limit
        )
        
        # 為每個圖片添加存取 URL
        for image in images:
            image["access_url"] = f"/api/v1/images/{image['uuid']}"
        
        return {
            "success": True,
            "images": images,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(images)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to list images",
                    "details": str(e)
                }
            }
        )

@router.get("/{uuid}/info")
async def get_image_info(
    uuid: str,
    api_key: str = Depends(get_api_key)
):
    """獲取圖片詳細資訊"""
    try:
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
        
        # 返回圖片資訊
        return {
            "uuid": uuid,
            "original_name": image_metadata["original_name"],
            "user_path": image_metadata["user_path"],
            "file_size": image_metadata["file_size"],
            "format": image_metadata["format"],
            "dimensions": image_metadata["dimensions"],
            "upload_time": image_metadata["upload_time"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to get image info",
                    "details": str(e)
                }
            }
        )

@router.delete("/{uuid}")
async def delete_image(
    uuid: str,
    api_key: str = Depends(get_api_key)
):
    """刪除單張圖片"""
    try:
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
                        "details": "You do not have permission to delete this image"
                    }
                }
            )
        
        # 刪除實際檔案
        file_deleted = storage_service.delete_file(image_metadata["file_path"])
        
        # 刪除元數據
        metadata_deleted = storage_service.metadata_manager.delete_image(uuid)
        
        if file_deleted and metadata_deleted:
            return {
                "success": True,
                "message": "Image deleted successfully",
                "uuid": uuid
            }
        else:
            return {
                "success": False,
                "message": "Image deletion partially failed",
                "uuid": uuid,
                "details": {
                    "file_deleted": file_deleted,
                    "metadata_deleted": metadata_deleted
                }
            }
        
    except HTTPException:
        raise
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
                    "message": "Failed to delete image",
                    "details": str(e)
                }
            }
        )

@router.delete("/batch")
async def batch_delete_images(
    request: BatchDeleteRequest,
    api_key: str = Depends(get_api_key)
):
    """批次刪除圖片"""
    try:
        results = []
        
        for uuid in request.uuids:
            try:
                # 獲取圖片元數據
                image_metadata = storage_service.metadata_manager.get_image(uuid)
                if not image_metadata:
                    results.append({
                        "uuid": uuid,
                        "success": False,
                        "error": "Image not found"
                    })
                    continue
                
                # 檢查權限
                if not storage_service.metadata_manager.check_image_permission(uuid, api_key):
                    results.append({
                        "uuid": uuid,
                        "success": False,
                        "error": "Access denied"
                    })
                    continue
                
                # 刪除實際檔案
                file_deleted = storage_service.delete_file(image_metadata["file_path"])
                
                # 刪除元數據
                metadata_deleted = storage_service.metadata_manager.delete_image(uuid)
                
                if file_deleted and metadata_deleted:
                    results.append({
                        "uuid": uuid,
                        "success": True,
                        "message": "Deleted successfully"
                    })
                else:
                    results.append({
                        "uuid": uuid,
                        "success": False,
                        "error": "Deletion partially failed",
                        "details": {
                            "file_deleted": file_deleted,
                            "metadata_deleted": metadata_deleted
                        }
                    })
                    
            except Exception as e:
                results.append({
                    "uuid": uuid,
                    "success": False,
                    "error": str(e)
                })
        
        # 計算統計資訊
        successful_deletions = sum(1 for r in results if r["success"])
        total_requests = len(request.uuids)
        
        return {
            "success": True,
            "message": f"Batch deletion completed: {successful_deletions}/{total_requests} successful",
            "results": results,
            "summary": {
                "total": total_requests,
                "successful": successful_deletions,
                "failed": total_requests - successful_deletions
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to process batch deletion",
                    "details": str(e)
                }
            }
        )