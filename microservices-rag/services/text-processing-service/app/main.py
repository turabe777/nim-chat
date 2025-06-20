"""
Text Processing Service

テキスト分割・前処理マイクロサービス
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import time
from datetime import datetime

from shared.utils.config import TextProcessingServiceConfig
from shared.utils.logging import setup_logging, get_logger
from shared.utils.exceptions import RAGServiceException
from .routers import text_processing, health

# 設定とロガー初期化
config = TextProcessingServiceConfig()
setup_logging(config.log_level)
logger = get_logger(__name__)

# FastAPIアプリ作成
app = FastAPI(
    title="Text Processing Service",
    description="テキスト分割・前処理マイクロサービス",
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

# リクエスト/レスポンス時間計測ミドルウェア
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """リクエスト処理時間を計測"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 例外ハンドラー
@app.exception_handler(RAGServiceException)
async def rag_exception_handler(request: Request, exc: RAGServiceException):
    """RAGサービス例外ハンドラー"""
    logger.error(f"RAG Service Exception: {exc.error_code} - {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "service": config.service_name
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """一般例外ハンドラー"""
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "service": config.service_name
        }
    )

# ルーター登録
app.include_router(health.router, tags=["Health"])
app.include_router(text_processing.router, prefix="/api/v1", tags=["Text Processing"])

# スタートアップ・シャットダウンイベント
@app.on_event("startup")
async def startup_event():
    """サービス起動時の処理"""
    logger.info(f"🚀 {config.service_name} starting up...")
    logger.info(f"🔧 Config: Debug={config.debug}, Port={config.port}")
    logger.info(f"📊 Text processing settings: chunk_size={config.default_chunk_size}, overlap={config.default_chunk_overlap}")

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