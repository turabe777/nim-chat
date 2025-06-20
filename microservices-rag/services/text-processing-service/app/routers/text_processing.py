"""
Text Processing API

テキスト分割・チャンク管理のエンドポイント
"""

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import List, Optional
from uuid import UUID
import time

from shared.models.text_processing import (
    TextProcessingRequest, TextProcessingResponse, TextProcessingConfig,
    ChunkListResponse, ChunkDetailResponse, TextStatsResponse
)
from shared.utils.config import TextProcessingServiceConfig
from shared.utils.logging import get_logger
from shared.utils.exceptions import DocumentNotFoundError, ProcessingError
from ..services.text_splitter import TextSplitterService
from ..services.chunk_manager import ChunkManagerService

router = APIRouter(prefix="/text")
logger = get_logger(__name__)
config = TextProcessingServiceConfig()


def get_text_splitter() -> TextSplitterService:
    """テキスト分割サービスの依存関係注入"""
    return TextSplitterService()


def get_chunk_manager() -> ChunkManagerService:
    """チャンク管理サービスの依存関係注入"""
    return ChunkManagerService(config.storage_path)


@router.post("/process", response_model=TextProcessingResponse)
async def process_text(
    request: TextProcessingRequest,
    text_splitter: TextSplitterService = Depends(get_text_splitter),
    chunk_manager: ChunkManagerService = Depends(get_chunk_manager)
):
    """テキストを分割してチャンクを作成"""
    
    logger.info(f"📄 Processing text for document {request.document_id}")
    
    start_time = time.time()
    
    try:
        # デフォルト設定またはリクエスト設定を使用
        processing_config = request.config or TextProcessingConfig(
            chunk_size=config.default_chunk_size,
            chunk_overlap=config.default_chunk_overlap
        )
        
        # テキスト分割
        chunks = await text_splitter.split_text(
            document_id=request.document_id,
            text=request.text,
            config=processing_config
        )
        
        # チャンク保存
        await chunk_manager.save_chunks(request.document_id, chunks)
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ Processed {len(chunks)} chunks for document {request.document_id}")
        
        return TextProcessingResponse(
            service=config.service_name,
            document_id=request.document_id,
            chunks=chunks,
            total_chunks=len(chunks),
            original_length=len(request.text),
            processed_length=sum(len(chunk.content) for chunk in chunks),
            processing_time=processing_time,
            config_used=processing_config
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to process text for {request.document_id}: {str(e)}")
        raise ProcessingError("text_processing", str(e))


@router.get("/chunks/{document_id}", response_model=ChunkListResponse)
async def get_chunks(
    document_id: UUID = Path(..., description="ドキュメントID"),
    limit: Optional[int] = Query(100, le=1000, description="取得数上限"),
    offset: int = Query(0, ge=0, description="オフセット"),
    chunk_manager: ChunkManagerService = Depends(get_chunk_manager)
):
    """ドキュメントのチャンク一覧を取得"""
    
    logger.info(f"📖 Getting chunks for document {document_id}")
    
    try:
        chunks = await chunk_manager.get_chunks(document_id, limit, offset)
        
        # 総数取得（メタデータから）
        metadata = await chunk_manager.get_chunk_metadata(document_id)
        total_chunks = metadata.get('total_chunks', len(chunks)) if metadata else len(chunks)
        
        return ChunkListResponse(
            service=config.service_name,
            document_id=document_id,
            chunks=chunks,
            total_chunks=total_chunks,
            limit=limit or len(chunks),
            offset=offset
        )
        
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Chunks not found for document {document_id}"
        )
    except Exception as e:
        logger.error(f"❌ Failed to get chunks for {document_id}: {str(e)}")
        raise ProcessingError("chunk_retrieval", str(e))


@router.get("/chunks/{document_id}/{chunk_id}", response_model=ChunkDetailResponse)
async def get_chunk_detail(
    document_id: UUID = Path(..., description="ドキュメントID"),
    chunk_id: UUID = Path(..., description="チャンクID"),
    chunk_manager: ChunkManagerService = Depends(get_chunk_manager)
):
    """指定されたチャンクの詳細を取得"""
    
    logger.info(f"📝 Getting chunk detail {chunk_id} for document {document_id}")
    
    try:
        chunk = await chunk_manager.get_chunk_by_id(document_id, chunk_id)
        
        if not chunk:
            raise HTTPException(
                status_code=404,
                detail=f"Chunk {chunk_id} not found in document {document_id}"
            )
        
        return ChunkDetailResponse(
            service=config.service_name,
            chunk=chunk
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get chunk {chunk_id}: {str(e)}")
        raise ProcessingError("chunk_detail", str(e))


@router.get("/stats/{document_id}", response_model=TextStatsResponse)
async def get_text_statistics(
    document_id: UUID = Path(..., description="ドキュメントID"),
    chunk_manager: ChunkManagerService = Depends(get_chunk_manager)
):
    """ドキュメントのテキスト統計を取得"""
    
    logger.info(f"📊 Getting text statistics for document {document_id}")
    
    try:
        stats = await chunk_manager.get_statistics(document_id)
        
        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"Statistics not found for document {document_id}"
            )
        
        return TextStatsResponse(
            service=config.service_name,
            document_id=document_id,
            total_chunks=stats['total_chunks'],
            total_characters=stats['total_characters'],
            average_chunk_size=stats['average_chunk_size'],
            min_chunk_size=stats['min_chunk_size'],
            max_chunk_size=stats['max_chunk_size'],
            processing_date=stats['created_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get statistics for {document_id}: {str(e)}")
        raise ProcessingError("statistics", str(e))


@router.delete("/chunks/{document_id}")
async def delete_chunks(
    document_id: UUID = Path(..., description="ドキュメントID"),
    chunk_manager: ChunkManagerService = Depends(get_chunk_manager)
):
    """ドキュメントのチャンクを削除"""
    
    logger.info(f"🗑️ Deleting chunks for document {document_id}")
    
    try:
        success = await chunk_manager.delete_chunks(document_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Chunks not found for document {document_id}"
            )
        
        logger.info(f"✅ Deleted chunks for document {document_id}")
        return {"message": "Chunks deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete chunks for {document_id}: {str(e)}")
        raise ProcessingError("chunk_deletion", str(e))


@router.get("/documents")
async def list_processed_documents(
    chunk_manager: ChunkManagerService = Depends(get_chunk_manager)
):
    """処理済みドキュメント一覧を取得"""
    
    logger.info("📋 Listing processed documents")
    
    try:
        documents = await chunk_manager.list_processed_documents()
        
        logger.info(f"📊 Found {len(documents)} processed documents")
        
        return {
            "service": config.service_name,
            "success": True,
            "documents": documents,
            "total_count": len(documents)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list processed documents: {str(e)}")
        raise ProcessingError("document_listing", str(e))