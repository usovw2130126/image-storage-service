from fastapi import HTTPException, Header
from typing import Optional
import uuid
import os
from app.config import API_KEYS

class ImageServiceError(Exception):
    """自定義異常類別"""
    def __init__(self, code: str, message: str, status_code: int, details: Optional[str] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

def validate_api_key(api_key: str) -> dict:
    """驗證 API Key 並返回配置"""
    if not api_key:
        raise ImageServiceError(
            code="AUTH_REQUIRED",
            message="API key is required",
            status_code=401
        )
    
    if api_key not in API_KEYS:
        raise ImageServiceError(
            code="AUTH_FAILED",
            message="Invalid API key",
            status_code=401,
            details="The provided API key is not valid"
        )
    
    return API_KEYS[api_key]

def validate_user_path(user_path: str, api_key_config: dict) -> bool:
    """驗證使用者路徑是否在允許的前綴範圍內"""
    allowed_prefix = api_key_config.get("allowed_prefix", "")
    if not user_path.startswith(allowed_prefix):
        raise ImageServiceError(
            code="PATH_FORBIDDEN",
            message="Path access denied",
            status_code=403,
            details=f"Path must start with '{allowed_prefix}'"
        )
    return True

def generate_uuid() -> str:
    """生成唯一的 UUID"""
    return str(uuid.uuid4())

def sanitize_filename(filename: str) -> str:
    """清理檔案名稱，避免路徑遍歷攻擊"""
    # 移除路徑分隔符和特殊字符
    filename = os.path.basename(filename)
    # 移除或替換危險字符
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    return filename