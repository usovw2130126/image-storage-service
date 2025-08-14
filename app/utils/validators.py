# import magic  # 簡化實作，不使用 python-magic
from fastapi import UploadFile, HTTPException
from app.config import ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES, MAX_FILE_SIZE
from app.utils.security import ImageServiceError

def validate_file_extension(filename: str) -> bool:
    """驗證檔案副檔名"""
    if not filename:
        return False
    
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    return extension in ALLOWED_EXTENSIONS

def validate_file_size(file: UploadFile) -> bool:
    """驗證檔案大小"""
    # 注意：這裡我們不能直接檢查檔案大小，因為 UploadFile 可能是串流
    # 實際檢查會在讀取檔案內容時進行
    return True

def validate_file_content(file_content: bytes, filename: str) -> bool:
    """驗證檔案內容和 MIME 類型"""
    # 檢查檔案大小
    if len(file_content) > MAX_FILE_SIZE:
        raise ImageServiceError(
            code="FILE_TOO_LARGE",
            message="File too large",
            status_code=413,
            details=f"File size exceeds {MAX_FILE_SIZE} bytes"
        )
    
    # 檢查副檔名
    if not validate_file_extension(filename):
        raise ImageServiceError(
            code="INVALID_FILE_TYPE",
            message="Invalid file type",
            status_code=400,
            details=f"File type not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 檢查檔案頭（Magic Number）- 基本實作
    # 這是一個簡化的實作，在生產環境中建議使用 python-magic
    if len(file_content) < 8:
        raise ImageServiceError(
            code="INVALID_FILE_CONTENT",
            message="Invalid file content",
            status_code=400,
            details="File appears to be corrupted or empty"
        )
    
    # 簡單的 Magic Number 檢查
    file_signatures = {
        b'\xff\xd8\xff': 'image/jpeg',  # JPEG
        b'\x89PNG\r\n\x1a\n': 'image/png',  # PNG
        b'GIF87a': 'image/gif',  # GIF87a
        b'GIF89a': 'image/gif',  # GIF89a
        b'RIFF': 'image/webp',  # WebP (需要進一步檢查)
    }
    
    detected_type = None
    for signature, mime_type in file_signatures.items():
        if file_content.startswith(signature):
            detected_type = mime_type
            break
    
    # WebP 需要額外檢查
    if file_content.startswith(b'RIFF') and b'WEBP' in file_content[:12]:
        detected_type = 'image/webp'
    
    if not detected_type or detected_type not in ALLOWED_MIME_TYPES:
        raise ImageServiceError(
            code="INVALID_FILE_CONTENT",
            message="Invalid file content",
            status_code=400,
            details="File content does not match expected image format"
        )
    
    return True

def validate_image_dimensions(width: int = None, height: int = None) -> bool:
    """驗證圖片尺寸參數"""
    if width is not None and (width <= 0 or width > 8192):
        raise ImageServiceError(
            code="INVALID_DIMENSIONS",
            message="Invalid width parameter",
            status_code=400,
            details="Width must be between 1 and 8192 pixels"
        )
    
    if height is not None and (height <= 0 or height > 8192):
        raise ImageServiceError(
            code="INVALID_DIMENSIONS",
            message="Invalid height parameter", 
            status_code=400,
            details="Height must be between 1 and 8192 pixels"
        )
    
    return True

def validate_quality(quality: int = None) -> bool:
    """驗證圖片品質參數"""
    if quality is not None and (quality < 1 or quality > 100):
        raise ImageServiceError(
            code="INVALID_QUALITY",
            message="Invalid quality parameter",
            status_code=400,
            details="Quality must be between 1 and 100"
        )
    
    return True