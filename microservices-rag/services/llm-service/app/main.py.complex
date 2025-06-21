"""
LLM Service FastAPI アプリケーション

NVIDIA Cloud LLMを使用した質問応答マイクロサービス
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import time
import sys
import os
import json
from datetime import datetime
from uuid import UUID

# 共通ライブラリのパスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

from shared.utils.config import LLMServiceConfig
from shared.utils.logging import setup_logging, get_logger
from shared.utils.exceptions import RAGServiceException
from shared.models.base import ErrorResponseModel, ErrorModel
from .routers import llm, health

# カスタムJSONエンコーダー
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)

# 設定読み込み
config = LLMServiceConfig()

# ログ設定
setup_logging(config.service_name, config.log_level)
logger = get_logger(__name__)

# FastAPIアプリケーション作成
app = FastAPI(
    title="LLM Service",
    description="NVIDIA Cloud LLMを使用した質問応答マイクロサービス",
    version=config.version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエスト処理時間ログ用ミドルウェア
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    return response

# 例外ハンドラー
@app.exception_handler(RAGServiceException)
async def rag_exception_handler(request: Request, exc: RAGServiceException):
    logger.error(f"RAG Service Exception: {exc.message}", exc_info=True)
    
    error_response = ErrorResponseModel(
        service=config.service_name,
        error=ErrorModel(
            code=exc.error_code,
            message=exc.message,
            details=exc.details
        )
    )
    
    content_json = json.dumps(error_response.dict(), cls=CustomJSONEncoder)
    return JSONResponse(
        status_code=400,
        content=json.loads(content_json)
    )

# 一般例外ハンドラー
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    error_response = ErrorResponseModel(
        service=config.service_name,
        error=ErrorModel(
            code="INTERNAL_ERROR",
            message="Internal server error occurred",
            details={"error_type": type(exc).__name__}
        )
    )
    
    content_json = json.dumps(error_response.dict(), cls=CustomJSONEncoder)
    return JSONResponse(
        status_code=500,
        content=json.loads(content_json)
    )

# ルーター登録
app.include_router(
    health.router,
    tags=["Health"]
)

app.include_router(
    llm.router,
    prefix="/api/v1",
    tags=["LLM"]
)

# サーバー起動時のログ
@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 {config.service_name} starting up...")
    logger.info(f"🔧 Config: Debug={config.debug}, Port={config.port}")
    logger.info(f"🤖 NVIDIA API Key: {'Set' if config.nvidia_api_key else 'Not Set'}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"🔄 {config.service_name} shutting down...")

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )