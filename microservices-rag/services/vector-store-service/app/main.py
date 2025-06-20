"""
Vector Store Service

ベクトル検索・類似度検索マイクロサービス
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import time
from datetime import datetime

from shared.utils.config import VectorStoreServiceConfig
from shared.utils.logging import setup_logging, get_logger
from shared.utils.exceptions import RAGServiceException
from shared.models.base import ErrorResponseModel, ErrorModel
from .routers import vector_search, health

# 設定とロガー初期化
config = VectorStoreServiceConfig()
setup_logging(config.service_name, config.log_level)
logger = get_logger(__name__)

# FastAPIアプリ作成
app = FastAPI(
    title="Vector Store Service",
    description="ベクトル検索・類似度検索マイクロサービス",
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

# リクエスト/レスポンス時間計測とログミドルウェア
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """リクエスト処理時間を計測・ログ記録"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 例外ハンドラー
@app.exception_handler(RAGServiceException)
async def rag_exception_handler(request: Request, exc: RAGServiceException):
    """RAGサービス例外ハンドラー"""
    logger.error(f"RAG Service Exception: {exc.message}", exc_info=True)
    
    error_response = ErrorResponseModel(
        service=config.service_name,
        error=ErrorModel(
            code=exc.error_code,
            message=exc.message,
            details=exc.details
        )
    )
    
    return JSONResponse(
        status_code=400,
        content=error_response.model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """一般例外ハンドラー"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    error_response = ErrorResponseModel(
        service=config.service_name,
        error=ErrorModel(
            code="internal_server_error",
            message="An unexpected error occurred"
        )
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )

# ルーター登録
app.include_router(health.router, tags=["Health"])
app.include_router(vector_search.router, prefix="/api/v1", tags=["Vector Search"])

# スタートアップ・シャットダウンイベント
@app.on_event("startup")
async def startup_event():
    """サービス起動時の処理"""
    logger.info(f"🚀 {config.service_name} starting up...")
    logger.info(f"🔧 Config: Debug={config.debug}, Port={config.port}")
    logger.info(f"🔍 Vector search settings: index_type={config.default_index_type}, metric={config.default_metric_type}")

@app.on_event("shutdown")
async def shutdown_event():
    """サービス終了時の処理"""
    logger.info(f"🔄 {config.service_name} shutting down...")

# 開発用サーバー起動
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )