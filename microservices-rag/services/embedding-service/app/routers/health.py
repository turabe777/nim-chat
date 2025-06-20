"""
Embedding Service ヘルスチェックAPI
"""

from fastapi import APIRouter
import psutil
import time
import torch
from datetime import datetime

from shared.utils.config import EmbeddingServiceConfig
from shared.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
config = EmbeddingServiceConfig()

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
    
    # PyTorch/デバイス情報
    device_info = {
        "torch_available": torch.cuda.is_available(),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
    }
    
    if torch.cuda.is_available():
        device_info["cuda_version"] = torch.version.cuda
        device_info["current_device"] = torch.cuda.current_device()
    
    # MPS (Apple Silicon) サポート確認
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device_info["mps_available"] = True
    else:
        device_info["mps_available"] = False
    
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
            "embedding_model": "healthy",
            "torch": "healthy" if torch.cuda.is_available() or device_info["mps_available"] else "warning"
        },
        "system": {
            "memory_usage": f"{memory_usage:.1f}%",
            "cpu_usage": f"{cpu_usage:.1f}%", 
            "disk_usage": f"{disk_usage:.1f}%"
        },
        "config": {
            "default_embedding_model": config.default_embedding_model,
            "max_batch_size": config.max_batch_size,
            "embedding_cache_ttl": config.embedding_cache_ttl
        },
        "device_info": device_info
    }
    
    logger.debug(f"Health check: {status}")
    return health_info