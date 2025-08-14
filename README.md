# 圖片儲存微服務

基於 FastAPI 開發的高效能圖片儲存微服務，提供安全的圖片上傳、儲存、訪問和刪除功能。

## ✨ 功能特色

- 🔐 **API Key 認證**：安全的 API 金鑰驗證機制
- 🗂️ **路徑權限控制**：每個 API Key 限制在指定路徑前綴內
- 📤 **單張/批次上傳**：支援單張和批次上傳（100+ 張圖片）
- 🖼️ **動態圖片處理**：即時調整大小、格式轉換、品質調整
- 🗃️ **UUID 檔案管理**：使用 UUID 作為圖片唯一識別符
- 📊 **批次進度追蹤**：即時監控批次上傳進度
- 🐳 **Docker 支援**：一鍵部署，支援 Docker Compose
- 📝 **自動 API 文檔**：Swagger UI 自動生成文檔

## 🚀 快速開始

### 使用 Docker Compose（推薦）

1. **啟動服務**
```bash
git clone <repository-url>
cd image-storage-service
docker-compose up -d
```

2. **檢查服務狀態**
```bash
curl http://localhost:8000/health
```

### 本地開發

1. **安裝依賴**
```bash
pip install -r requirements.txt
```

2. **啟動服務**
```bash
cd app
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📖 API 使用說明

### 認證

所有 API 都需要在請求頭中包含 `X-API-Key`：

```http
X-API-Key: your-api-key
```

**預設 API Keys:**
- `dev-key-123`: 允許路徑 `user1/*`
- `dev-key-456`: 允許路徑 `company/team1/*`
- `test-key-789`: 允許路徑 `test/*`

### 1. 圖片上傳

#### 單張上傳
```bash
curl -X POST "http://localhost:8000/api/v1/images/upload" \
  -H "X-API-Key: dev-key-123" \
  -F "file=@image.jpg" \
  -F "user_path=user1/vacation/2024"
```

**回應範例:**
```json
{
  "success": true,
  "images": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "original_name": "image.jpg",
      "user_path": "user1/vacation/2024",
      "file_size": 1024000,
      "format": "JPEG",
      "dimensions": {"width": 1920, "height": 1080},
      "upload_time": "2024-01-01T12:00:00Z",
      "access_url": "/api/v1/images/550e8400-e29b-41d4-a716-446655440000"
    }
  ]
}
```

#### 批次上傳
```bash
curl -X POST "http://localhost:8000/api/v1/images/batch-upload" \
  -H "X-API-Key: dev-key-123" \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "user_path=user1/batch"
```

**查詢批次進度:**
```bash
curl -H "X-API-Key: dev-key-123" \
  "http://localhost:8000/api/v1/batch/{batch_id}/progress"
```

### 2. 圖片訪問

#### 原始圖片
```bash
curl -H "X-API-Key: dev-key-123" \
  "http://localhost:8000/api/v1/images/{uuid}"
```

#### 動態調整大小
```bash
# 調整為 800x600
curl -H "X-API-Key: dev-key-123" \
  "http://localhost:8000/api/v1/images/{uuid}?width=800&height=600"

# 轉換格式並調整品質
curl -H "X-API-Key: dev-key-123" \
  "http://localhost:8000/api/v1/images/{uuid}?width=800&format=webp&quality=85"
```

**支援參數:**
- `width`: 目標寬度
- `height`: 目標高度  
- `quality`: 品質 (1-100)
- `format`: 輸出格式 (jpeg, png, webp)
- `mode`: 縮放模式 (fit, fill, crop)

### 3. 圖片管理

#### 列出圖片
```bash
curl -H "X-API-Key: dev-key-123" \
  "http://localhost:8000/api/v1/images?user_path=user1/vacation&page=1&limit=20"
```

#### 圖片資訊
```bash
curl -H "X-API-Key: dev-key-123" \
  "http://localhost:8000/api/v1/images/{uuid}/info"
```

#### 刪除圖片
```bash
# 單張刪除
curl -X DELETE -H "X-API-Key: dev-key-123" \
  "http://localhost:8000/api/v1/images/{uuid}"

# 批次刪除
curl -X DELETE -H "X-API-Key: dev-key-123" \
  -H "Content-Type: application/json" \
  -d '{"uuids": ["uuid1", "uuid2", "uuid3"]}' \
  "http://localhost:8000/api/v1/images/batch"
```

## ⚙️ 配置說明

### 環境變數

```bash
STORAGE_PATH=/app/storage        # 圖片儲存路徑
MAX_FILE_SIZE=10485760          # 最大檔案大小 (10MB)
MAX_BATCH_SIZE=100              # 批次上傳最大檔案數
```

### API Keys 配置

在 `app/config.py` 中修改：

```python
API_KEYS = {
    "your-api-key": {
        "name": "Your Service Name",
        "allowed_prefix": "your-path/"
    }
}
```

### 支援格式

**圖片格式:** JPEG, PNG, GIF, WebP
**最大檔案大小:** 10MB (可配置)
**批次上傳限制:** 100 檔案 (可配置)

## 🏗️ 系統架構

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│  Auth Middleware│────│  File Storage   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │              ┌─────────────────┐
         │                       └──────────────│   Config File   │
         │                                      │   (API Keys)    │
┌─────────────────┐                             └─────────────────┘
│ Image Processor │                             ┌─────────────────┐
└─────────────────┘                             │ Metadata Store  │
                                                 │ (metadata.json) │
                                                 └─────────────────┘
```

## 📁 檔案結構

```
storage/
├── user1/                      # 使用者路徑
│   ├── vacation/
│   │   └── 2024/
│   │       └── uuid1.jpg
│   └── work/
│       └── projects/
├── company/
│   └── team1/
└── metadata.json              # 圖片元數據
```

## 🔒 安全特性

- **API Key 驗證**: 每個請求都需要有效的 API Key
- **路徑隔離**: 每個 API Key 只能存取指定路徑前綴
- **檔案類型檢查**: 白名單機制，檢查檔案頭
- **檔案大小限制**: 防止濫用系統資源
- **路徑遍歷防護**: 清理檔案名稱，防止路徑攻擊

## 📊 監控

### 健康檢查
```bash
curl http://localhost:8000/health
```

### API 文檔
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 測試

### 基本測試
```bash
# 健康檢查
curl http://localhost:8000/health

# 上傳測試圖片
curl -X POST "http://localhost:8000/api/v1/images/upload" \
  -H "X-API-Key: test-key-789" \
  -F "file=@test.jpg" \
  -F "user_path=test/demo"

# 訪問圖片（使用上一步返回的 UUID）
curl -H "X-API-Key: test-key-789" \
  "http://localhost:8000/api/v1/images/{uuid}"
```

## 🚢 部署

### Docker Compose
```yaml
version: '3.8'
services:
  image-service:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./storage:/app/storage
    environment:
      - STORAGE_PATH=/app/storage
      - MAX_FILE_SIZE=10485760
```

### 生產環境考慮

1. **反向代理**: 使用 Nginx 或 Traefik
2. **HTTPS**: 配置 SSL/TLS 證書
3. **負載均衡**: 多實例部署
4. **持久化儲存**: 使用外部儲存系統（S3, MinIO 等）
5. **監控**: 配置日誌和指標收集

## 🛠️ 開發

### 本地開發
```bash
# 安裝依賴
pip install -r requirements.txt

# 啟動開發伺服器
cd app
uvicorn main:app --reload

# 運行測試
python -m pytest tests/
```

### 建構 Docker 映像
```bash
docker build -t image-storage-service .
```

## 📄 API 錯誤碼

| 錯誤碼 | HTTP 狀態 | 說明 |
|--------|-----------|------|
| AUTH_REQUIRED | 401 | 缺少 API Key |
| AUTH_FAILED | 401 | API Key 無效 |
| PATH_FORBIDDEN | 403 | 路徑權限不足 |
| ACCESS_DENIED | 403 | 圖片存取權限不足 |
| IMAGE_NOT_FOUND | 404 | 圖片不存在 |
| FILE_TOO_LARGE | 413 | 檔案過大 |
| INVALID_FILE_TYPE | 400 | 檔案類型不支援 |
| INVALID_FILE_CONTENT | 400 | 檔案內容無效 |

## 📝 版本記錄

### v1.0.0
- ✅ 基本圖片上傳/下載功能
- ✅ API Key 認證機制
- ✅ 路徑權限控制
- ✅ 動態圖片處理
- ✅ 批次上傳支援
- ✅ Docker 容器化部署

## 🤝 貢獻

歡迎提交 Issues 和 Pull Requests！

## 📄 授權

MIT License
