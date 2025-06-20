"""
ヘルスチェックAPI

LLM Service の状態確認エンドポイント
"""

from fastapi import APIRouter, Depends
import psutil
import os
import time
from datetime import datetime

from shared.models.base import HealthCheckResponse
from shared.utils.config import LLMServiceConfig
from shared.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
config = LLMServiceConfig()

# サービス開始時刻
_start_time = time.time()

def get_system_info() -> dict:
    """システム情報を取得"""
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "nvidia_api": "configured" if config.nvidia_api_key else "not_configured",
            "memory_usage": f"{memory.percent}%",
            "disk_usage": f"{(disk.used / disk.total * 100):.1f}%"
        }
    except Exception as e:
        logger.warning(f"Failed to get system info: {e}")
        return {"error": "system_info_unavailable"}

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """ヘルスチェック"""
    try:
        uptime = int(time.time() - _start_time)
        dependencies = get_system_info()
        
        # NVIDIA API キーの確認
        nvidia_status = "healthy" if config.nvidia_api_key else "warning"
        if nvidia_status == "warning":
            dependencies["nvidia_api_warning"] = "API key not configured"
        
        return HealthCheckResponse(
            status="healthy",
            service=config.service_name,
            version=config.version,
            uptime=uptime,
            dependencies=dependencies
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            service=config.service_name,
            version=config.version,
            uptime=0,
            dependencies={"error": str(e)}
        )