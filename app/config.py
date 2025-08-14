import os
from typing import Dict, Any

# 基本配置
STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", 100))
METADATA_FILE = os.path.join(STORAGE_PATH, "metadata.json")

# API Key 配置
API_KEYS: Dict[str, Dict[str, Any]] = {
    "dev-key-123": {
        "name": "Development User",
        "allowed_prefix": "user1/"
    },
    "dev-key-456": {
        "name": "Company Team", 
        "allowed_prefix": "company/team1/"
    },
    "test-key-789": {
        "name": "Test User",
        "allowed_prefix": "test/"
    }
}

# 支援的圖片格式
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_MIME_TYPES = {
    "image/jpeg", 
    "image/png", 
    "image/gif", 
    "image/webp"
}

# 圖片處理預設值
DEFAULT_QUALITY = 85
DEFAULT_RESIZE_MODE = "fit"  # fit, fill, crop