from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ImageInfo(BaseModel):
    uuid: str
    original_name: str
    user_path: str
    file_size: int
    format: str
    dimensions: Dict[str, int]
    upload_time: datetime
    access_url: str

class ImageUploadResponse(BaseModel):
    success: bool
    images: List[ImageInfo]

class BatchUploadResponse(BaseModel):
    success: bool
    batch_id: str
    status: str
    total_files: int
    progress_url: str

class BatchProgressResponse(BaseModel):
    batch_id: str
    total: int
    completed: int
    failed: int
    status: str
    progress_percentage: float
    estimated_time_remaining: Optional[str]
    results: List[Dict[str, Any]]

class BatchDeleteRequest(BaseModel):
    uuids: List[str]

class ErrorResponse(BaseModel):
    error: Dict[str, str]
    timestamp: str
    path: str