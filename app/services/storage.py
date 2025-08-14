import os
import json
import aiofiles
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.config import STORAGE_PATH, METADATA_FILE
from app.utils.security import ImageServiceError

class MetadataManager:
    """管理圖片元數據"""
    
    def __init__(self):
        self.metadata_file = METADATA_FILE
        self._ensure_storage_structure()
    
    def _ensure_storage_structure(self):
        """確保儲存目錄和元數據檔案存在"""
        os.makedirs(STORAGE_PATH, exist_ok=True)
        if not os.path.exists(self.metadata_file):
            self._save_metadata({})
    
    def _load_metadata(self) -> Dict[str, Any]:
        """載入元數據"""
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """保存元數據"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
    
    def add_image(self, uuid: str, file_path: str, original_name: str, 
                  api_key: str, user_path: str, file_size: int, 
                  format_type: str, dimensions: Dict[str, int]) -> Dict[str, Any]:
        """添加圖片元數據"""
        metadata = self._load_metadata()
        
        image_data = {
            "file_path": file_path,
            "original_name": original_name,
            "api_key": api_key,
            "user_path": user_path,
            "file_size": file_size,
            "format": format_type,
            "dimensions": dimensions,
            "upload_time": datetime.utcnow().isoformat()
        }
        
        metadata[uuid] = image_data
        self._save_metadata(metadata)
        return image_data
    
    def get_image(self, uuid: str) -> Optional[Dict[str, Any]]:
        """獲取圖片元數據"""
        metadata = self._load_metadata()
        return metadata.get(uuid)
    
    def delete_image(self, uuid: str) -> bool:
        """刪除圖片元數據"""
        metadata = self._load_metadata()
        if uuid in metadata:
            del metadata[uuid]
            self._save_metadata(metadata)
            return True
        return False
    
    def list_images(self, api_key: str, user_path: Optional[str] = None, 
                   skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """列出圖片（支援分頁和路徑篩選）"""
        metadata = self._load_metadata()
        
        # 篩選屬於該 API Key 的圖片
        filtered_images = []
        for uuid, data in metadata.items():
            if data.get("api_key") == api_key:
                if user_path is None or data.get("user_path", "").startswith(user_path):
                    image_info = data.copy()
                    image_info["uuid"] = uuid
                    filtered_images.append(image_info)
        
        # 按上傳時間排序（最新的在前）
        filtered_images.sort(key=lambda x: x.get("upload_time", ""), reverse=True)
        
        # 分頁
        return filtered_images[skip:skip + limit]
    
    def check_image_permission(self, uuid: str, api_key: str) -> bool:
        """檢查圖片權限"""
        image_data = self.get_image(uuid)
        if not image_data:
            return False
        return image_data.get("api_key") == api_key

class StorageService:
    """檔案儲存服務"""
    
    def __init__(self):
        self.storage_path = STORAGE_PATH
        self.metadata_manager = MetadataManager()
    
    def _get_file_path(self, user_path: str, filename: str) -> str:
        """生成完整的檔案路徑"""
        full_path = os.path.join(self.storage_path, user_path)
        os.makedirs(full_path, exist_ok=True)
        return os.path.join(full_path, filename)
    
    async def save_file(self, file_content: bytes, user_path: str, 
                       filename: str) -> str:
        """保存檔案到儲存系統"""
        file_path = self._get_file_path(user_path, filename)
        
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            return file_path
        except Exception as e:
            raise ImageServiceError(
                code="STORAGE_ERROR",
                message="Failed to save file",
                status_code=500,
                details=str(e)
            )
    
    async def read_file(self, file_path: str) -> bytes:
        """從儲存系統讀取檔案"""
        full_path = os.path.join(self.storage_path, file_path)
        
        if not os.path.exists(full_path):
            raise ImageServiceError(
                code="FILE_NOT_FOUND",
                message="File not found",
                status_code=404
            )
        
        try:
            async with aiofiles.open(full_path, 'rb') as f:
                return await f.read()
        except Exception as e:
            raise ImageServiceError(
                code="STORAGE_ERROR",
                message="Failed to read file",
                status_code=500,
                details=str(e)
            )
    
    def delete_file(self, file_path: str) -> bool:
        """從儲存系統刪除檔案"""
        full_path = os.path.join(self.storage_path, file_path)
        
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
            return False
        except Exception as e:
            raise ImageServiceError(
                code="STORAGE_ERROR", 
                message="Failed to delete file",
                status_code=500,
                details=str(e)
            )
    
    def file_exists(self, file_path: str) -> bool:
        """檢查檔案是否存在"""
        full_path = os.path.join(self.storage_path, file_path)
        return os.path.exists(full_path)