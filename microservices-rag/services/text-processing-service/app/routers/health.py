"""
Text Processing Service ヘルスチェックAPI
"""

from fastapi import APIRouter
import psutil
import time
from datetime import datetime

from shared.utils.config import TextProcessingServiceConfig
from shared.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
config = TextProcessingServiceConfig()

# サービス開始時間
start_time = time.time()

@router.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    
    current_time = time.time()
    uptime = current_time - start_time
    
    # システムリソース取得
    memory_usage = psutil.virtual_memory().percent
    cpu_usage = psutil.cpu_percent(interval=0.1)
    disk_usage = psutil.disk_usage('/').percent
    
    # ヘルス状態判定
    status = "healthy"
    if memory_usage > 90 or cpu_usage > 95 or disk_usage > 95:
        status = "unhealthy"
    elif memory_usage > 80 or cpu_usage > 90 or disk_usage > 90:
        status = "degraded"
    
    health_info = {
        "status": status,
        "service": config.service_name,
        "version": config.version,
        "uptime": round(uptime, 2),
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {
            "text_processing": "healthy",
        },
        "system": {
            "memory_usage": f"{memory_usage:.1f}%",
            "cpu_usage": f"{cpu_usage:.1f}%", 
            "disk_usage": f"{disk_usage:.1f}%"
        },
        "config": {
            "default_chunk_size": config.default_chunk_size,
            "default_chunk_overlap": config.default_chunk_overlap,
            "max_chunk_size": config.max_chunk_size,
            "min_chunk_size": config.min_chunk_size
        }
    }
    
    logger.debug(f"Health check: {status}")
    return health_info