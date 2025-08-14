import asyncio
import httpx
import json
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.config import WEBHOOK_TIMEOUT, WEBHOOK_RETRY_ATTEMPTS, WEBHOOK_RETRY_DELAY

logger = logging.getLogger(__name__)

class WebhookService:
    """Webhook 服務"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT)
    
    async def send_webhook(
        self, 
        url: str, 
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        retry_attempts: int = WEBHOOK_RETRY_ATTEMPTS
    ) -> bool:
        """發送 webhook 通知"""
        if not url:
            return False
            
        default_headers = {
            "Content-Type": "application/json",
            "User-Agent": "ImageStorageService/1.0"
        }
        
        if headers:
            default_headers.update(headers)
        
        # 添加時間戳
        payload["timestamp"] = datetime.utcnow().isoformat()
        
        for attempt in range(retry_attempts):
            try:
                logger.info(f"Sending webhook to {url} (attempt {attempt + 1})")
                
                response = await self.client.post(
                    url,
                    json=payload,
                    headers=default_headers
                )
                
                if response.status_code in [200, 201, 202, 204]:
                    logger.info(f"Webhook sent successfully to {url}")
                    return True
                else:
                    logger.warning(f"Webhook failed with status {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Webhook error (attempt {attempt + 1}): {str(e)}")
                
                # 如果還有重試次數，等待後重試
                if attempt < retry_attempts - 1:
                    await asyncio.sleep(WEBHOOK_RETRY_DELAY)
        
        logger.error(f"Webhook failed after {retry_attempts} attempts to {url}")
        return False
    
    async def send_batch_progress_webhook(
        self,
        webhook_url: str,
        batch_id: str,
        status: str,
        progress: Dict[str, Any],
        api_key: str,
        webhook_headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """發送批次上傳進度 webhook"""
        payload = {
            "event_type": "batch_progress",
            "batch_id": batch_id,
            "status": status,
            "progress": progress,
            "api_key": api_key
        }
        
        return await self.send_webhook(webhook_url, payload, webhook_headers)
    
    async def send_batch_completed_webhook(
        self,
        webhook_url: str,
        batch_id: str,
        results: Dict[str, Any],
        api_key: str,
        webhook_headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """發送批次完成 webhook"""
        payload = {
            "event_type": "batch_completed",
            "batch_id": batch_id,
            "results": results,
            "api_key": api_key
        }
        
        return await self.send_webhook(webhook_url, payload, webhook_headers)
    
    async def close(self):
        """關閉 HTTP 客戶端"""
        await self.client.aclose()

# 全域實例
webhook_service = WebhookService()