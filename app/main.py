from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

from app.api import upload, serve, manage
from app.utils.security import ImageServiceError
from app.config import STORAGE_PATH

# 創建 FastAPI 應用
app = FastAPI(
    title="Image Storage Microservice",
    description="A high-performance image storage microservice with authentication and dynamic resizing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 中介軟體
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境中應該設定具體的來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域異常處理器
@app.exception_handler(ImageServiceError)
async def image_service_exception_handler(request: Request, exc: ImageServiceError):
    """處理自定義圖片服務異常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            },
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """處理 HTTP 異常"""
    # 如果 detail 已經是字典格式（包含錯誤資訊），直接返回
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = exc.detail.copy()
        content["timestamp"] = datetime.utcnow().isoformat()
        content["path"] = str(request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content=content
        )
    
    # 否則包裝成標準格式
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "details": None
            },
            "timestamp": datetime.utcnow().isoformat(), 
            "path": str(request.url.path)
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc):
    """處理內部服務器錯誤"""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "details": "An unexpected error occurred"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )

# 註冊路由
app.include_router(upload.router)
app.include_router(serve.router)
app.include_router(manage.router)

# 根路由
@app.get("/")
async def root():
    """API 根路徑"""
    return {
        "message": "Image Storage Microservice",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# 健康檢查
@app.get("/health")
async def health_check():
    """健康檢查端點"""
    try:
        # 檢查儲存目錄是否可存取
        storage_accessible = os.path.exists(STORAGE_PATH) and os.access(STORAGE_PATH, os.W_OK)
        
        return {
            "status": "healthy" if storage_accessible else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "storage_accessible": storage_accessible,
            "storage_path": STORAGE_PATH
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )

# 啟動事件
@app.on_event("startup")
async def startup_event():
    """應用啟動時執行"""
    # 確保儲存目錄存在
    os.makedirs(STORAGE_PATH, exist_ok=True)
    print(f"Image Storage Microservice started")
    print(f"Storage path: {STORAGE_PATH}")
    print(f"API documentation: http://localhost:8000/docs")

# 關閉事件
@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時執行"""
    print("Image Storage Microservice shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8000,
        reload=True,
        log_level="info"
    )