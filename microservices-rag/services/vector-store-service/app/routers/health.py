"""
Vector Store Service Health Check

ヘルスチェックエンドポイント
"""

from fastapi import APIRouter
from shared.utils.config import VectorStoreServiceConfig
from shared.utils.logging import get_logger

router = APIRouter()
config = VectorStoreServiceConfig()
logger = get_logger(__name__)


@router.get("/health")
async def health_check():
    """ヘルスチェック"""
    
    logger.debug("🏥 Health check requested")
    
    return {
        "status": "healthy",
        "service": config.service_name,
        "version": config.version,
        "config": {
            "default_index_type": config.default_index_type,
            "default_metric_type": config.default_metric_type,
            "storage_path": config.storage_path
        },
        "message": "Vector Store Service is running"
    }