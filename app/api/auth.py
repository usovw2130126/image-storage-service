from fastapi import Depends, Header, HTTPException
from typing import Optional, Annotated
from app.utils.security import validate_api_key, ImageServiceError

async def get_api_key(x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None) -> str:
    """從 Header 中獲取並驗證 API Key"""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "AUTH_REQUIRED",
                    "message": "API key is required",
                    "details": "Please provide X-API-Key header"
                }
            }
        )
    
    try:
        # 驗證 API Key
        validate_api_key(x_api_key)
        return x_api_key
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

async def get_api_key_config(api_key: str = Depends(get_api_key)) -> dict:
    """獲取 API Key 的配置資訊"""
    return validate_api_key(api_key)

def verify_user_path_permission(user_path: str, api_key: str) -> bool:
    """驗證使用者路徑權限"""
    try:
        api_key_config = validate_api_key(api_key)
        allowed_prefix = api_key_config.get("allowed_prefix", "")
        
        if not user_path.startswith(allowed_prefix):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "PATH_FORBIDDEN",
                        "message": "Path access denied",
                        "details": f"Path must start with '{allowed_prefix}'"
                    }
                }
            )
        return True
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