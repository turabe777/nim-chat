"""
Embedding API

埋め込みベクトル生成・管理のエンドポイント
"""

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import List, Optional
from uuid import UUID
import time

from shared.models.embedding import (
    EmbeddingRequest, EmbeddingResponse, EmbeddingConfig,
    BatchEmbeddingRequest, EmbeddingListResponse, EmbeddingDetailResponse,
    EmbeddingStatsResponse, SimilaritySearchRequest, SimilaritySearchResponse,
    ModelInfoResponse, SimilarityResult
)
from shared.utils.config import EmbeddingServiceConfig
from shared.utils.logging import get_logger
from shared.utils.exceptions import DocumentNotFoundError, ProcessingError
from ..services.embedding_generator import EmbeddingGeneratorService
from ..services.embedding_manager import EmbeddingManagerService

router = APIRouter(prefix="/embeddings")
logger = get_logger(__name__)
config = EmbeddingServiceConfig()


def get_embedding_generator() -> EmbeddingGeneratorService:
    """埋め込み生成サービスの依存関係注入"""
    return EmbeddingGeneratorService()


def get_embedding_manager() -> EmbeddingManagerService:
    """埋め込み管理サービスの依存関係注入"""
    return EmbeddingManagerService(config.storage_path)


@router.post("/generate", response_model=EmbeddingResponse)
async def generate_embeddings(
    request: EmbeddingRequest,
    generator: EmbeddingGeneratorService = Depends(get_embedding_generator),
    manager: EmbeddingManagerService = Depends(get_embedding_manager)
):
    """テキストから埋め込みベクトルを生成"""
    
    logger.info(f"🔮 Generating embeddings for {len(request.texts)} texts")
    
    start_time = time.time()
    
    try:
        # デフォルト設定またはリクエスト設定を使用
        embedding_config = request.config or EmbeddingConfig(
            model_name=config.default_embedding_model,
            batch_size=min(config.max_batch_size, len(request.texts))
        )
        
        # 埋め込み生成
        embeddings = await generator.generate_embeddings(
            texts=request.texts,
            chunk_ids=request.chunk_ids,
            document_id=request.document_id,
            config=embedding_config
        )
        
        # ドキュメントIDが指定されていれば保存
        if request.document_id:
            await manager.save_embeddings(request.document_id, embeddings)
        
        processing_time = time.time() - start_time
        model_info = generator.get_model_info()
        
        logger.info(f"✅ Generated {len(embeddings)} embeddings in {processing_time:.3f}s")
        
        return EmbeddingResponse(
            service=config.service_name,
            embeddings=embeddings,
            total_count=len(embeddings),
            model_info=model_info,
            processing_time=processing_time,
            config_used=embedding_config
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to generate embeddings: {str(e)}")
        raise ProcessingError("embedding_generation", str(e))


@router.post("/batch", response_model=EmbeddingResponse)
async def generate_batch_embeddings(
    request: BatchEmbeddingRequest,
    generator: EmbeddingGeneratorService = Depends(get_embedding_generator),
    manager: EmbeddingManagerService = Depends(get_embedding_manager)
):
    """チャンクデータから一括で埋め込みベクトルを生成"""
    
    logger.info(f"📦 Batch generating embeddings for {len(request.chunks)} chunks")
    
    start_time = time.time()
    
    try:
        # チャンクデータから texts と chunk_ids を抽出
        texts = [chunk['content'] for chunk in request.chunks]
        chunk_ids = [UUID(chunk['chunk_id']) for chunk in request.chunks]
        
        # デフォルト設定
        embedding_config = request.config or EmbeddingConfig(
            model_name=config.default_embedding_model,
            batch_size=min(config.max_batch_size, len(texts))
        )
        
        # 埋め込み生成
        embeddings = await generator.generate_embeddings(
            texts=texts,
            chunk_ids=chunk_ids,
            document_id=request.document_id,
            config=embedding_config
        )
        
        # 埋め込み保存
        await manager.save_embeddings(request.document_id, embeddings)
        
        processing_time = time.time() - start_time
        model_info = generator.get_model_info()
        
        logger.info(f"✅ Batch generated {len(embeddings)} embeddings in {processing_time:.3f}s")
        
        return EmbeddingResponse(
            service=config.service_name,
            embeddings=embeddings,
            total_count=len(embeddings),
            model_info=model_info,
            processing_time=processing_time,
            config_used=embedding_config
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to generate batch embeddings: {str(e)}")
        raise ProcessingError("batch_embedding_generation", str(e))


@router.get("/documents/{document_id}", response_model=EmbeddingListResponse)
async def get_embeddings(
    document_id: UUID = Path(..., description="ドキュメントID"),
    limit: Optional[int] = Query(100, le=1000, description="取得数上限"),
    offset: int = Query(0, ge=0, description="オフセット"),
    manager: EmbeddingManagerService = Depends(get_embedding_manager)
):
    """ドキュメントの埋め込みベクトル一覧を取得"""
    
    logger.info(f"📖 Getting embeddings for document {document_id}")
    
    try:
        embeddings = await manager.get_embeddings(document_id, limit, offset)
        
        # 総数取得（メタデータから）
        metadata = await manager.get_embedding_metadata(document_id)
        total_count = metadata.get('total_embeddings', len(embeddings)) if metadata else len(embeddings)
        
        return EmbeddingListResponse(
            service=config.service_name,
            embeddings=embeddings,
            total_count=total_count,
            limit=limit or len(embeddings),
            offset=offset,
            filter_applied={"document_id": str(document_id)}
        )
        
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Embeddings not found for document {document_id}"
        )
    except Exception as e:
        logger.error(f"❌ Failed to get embeddings for {document_id}: {str(e)}")
        raise ProcessingError("embedding_retrieval", str(e))


@router.get("/documents/{document_id}/{embedding_id}", response_model=EmbeddingDetailResponse)
async def get_embedding_detail(
    document_id: UUID = Path(..., description="ドキュメントID"),
    embedding_id: UUID = Path(..., description="埋め込みID"),
    manager: EmbeddingManagerService = Depends(get_embedding_manager)
):
    """指定された埋め込みベクトルの詳細を取得"""
    
    logger.info(f"📝 Getting embedding detail {embedding_id} for document {document_id}")
    
    try:
        embedding = await manager.get_embedding_by_id(document_id, embedding_id)
        
        if not embedding:
            raise HTTPException(
                status_code=404,
                detail=f"Embedding {embedding_id} not found in document {document_id}"
            )
        
        return EmbeddingDetailResponse(
            service=config.service_name,
            embedding=embedding
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get embedding {embedding_id}: {str(e)}")
        raise ProcessingError("embedding_detail", str(e))


@router.get("/stats/{document_id}", response_model=EmbeddingStatsResponse)
async def get_embedding_statistics(
    document_id: UUID = Path(..., description="ドキュメントID"),
    manager: EmbeddingManagerService = Depends(get_embedding_manager)
):
    """ドキュメントの埋め込み統計を取得"""
    
    logger.info(f"📊 Getting embedding statistics for document {document_id}")
    
    try:
        stats = await manager.get_statistics(document_id)
        
        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"Statistics not found for document {document_id}"
            )
        
        return EmbeddingStatsResponse(
            service=config.service_name,
            document_id=document_id,
            total_embeddings=stats['total_embeddings'],
            dimension=stats['dimension'],
            model_name=stats['model_name'],
            average_vector_norm=stats['average_vector_norm'],
            created_date_range={
                "start": stats['created_at'],
                "end": stats['created_at']  # 単一ドキュメントなので同じ
            },
            storage_size_mb=stats['storage_size_mb']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get statistics for {document_id}: {str(e)}")
        raise ProcessingError("statistics", str(e))


@router.post("/search", response_model=SimilaritySearchResponse)
async def search_similar_embeddings(
    request: SimilaritySearchRequest,
    generator: EmbeddingGeneratorService = Depends(get_embedding_generator),
    manager: EmbeddingManagerService = Depends(get_embedding_manager)
):
    """類似度検索"""
    
    logger.info(f"🔍 Searching similar embeddings, top_k={request.top_k}")
    
    start_time = time.time()
    
    try:
        results = []
        total_candidates = 0
        
        # ドキュメントが指定されている場合は絞り込み検索
        document_ids = request.document_ids or []
        
        if not document_ids:
            # すべてのドキュメントから検索
            processed_docs = await manager.list_processed_documents()
            document_ids = [UUID(doc['document_id']) for doc in processed_docs]
        
        # 各ドキュメントで類似度検索
        for doc_id in document_ids:
            try:
                # ドキュメントの埋め込みベクトルを取得
                embeddings = await manager.get_embeddings(doc_id)
                if not embeddings:
                    continue
                
                total_candidates += len(embeddings)
                
                # ベクトルリストを準備
                candidate_vectors = [emb.vector for emb in embeddings]
                
                # 類似度計算
                similarities = await generator.compute_similarity(
                    query_vector=request.query_vector,
                    candidate_vectors=candidate_vectors,
                    top_k=len(embeddings)  # 全候補で計算
                )
                
                # 結果に追加
                for idx, score in similarities:
                    if request.similarity_threshold is None or score >= request.similarity_threshold:
                        embedding = embeddings[idx]
                        result = SimilarityResult(
                            embedding_id=embedding.embedding_id,
                            chunk_id=embedding.chunk_id,
                            document_id=doc_id,
                            similarity_score=score,
                            metadata=embedding.metadata
                        )
                        results.append(result)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to search in document {doc_id}: {str(e)}")
                continue
        
        # 結果をスコア順でソート、top_kに絞り込み
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        results = results[:request.top_k]
        
        search_time = time.time() - start_time
        
        logger.info(f"✅ Found {len(results)} similar embeddings in {search_time:.3f}s")
        
        return SimilaritySearchResponse(
            service=config.service_name,
            results=results,
            query_dimension=len(request.query_vector),
            search_time=search_time,
            total_candidates=total_candidates
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to search similar embeddings: {str(e)}")
        raise ProcessingError("similarity_search", str(e))


@router.delete("/documents/{document_id}")
async def delete_embeddings(
    document_id: UUID = Path(..., description="ドキュメントID"),
    manager: EmbeddingManagerService = Depends(get_embedding_manager)
):
    """ドキュメントの埋め込みベクトルを削除"""
    
    logger.info(f"🗑️ Deleting embeddings for document {document_id}")
    
    try:
        success = await manager.delete_embeddings(document_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Embeddings not found for document {document_id}"
            )
        
        logger.info(f"✅ Deleted embeddings for document {document_id}")
        return {"message": "Embeddings deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete embeddings for {document_id}: {str(e)}")
        raise ProcessingError("embedding_deletion", str(e))


@router.get("/models", response_model=ModelInfoResponse)
async def get_model_info(
    generator: EmbeddingGeneratorService = Depends(get_embedding_generator)
):
    """モデル情報を取得"""
    
    logger.info("🤖 Getting model information")
    
    try:
        available_models = generator.get_available_models()
        current_model = generator.get_model_info()
        
        device_info = current_model.get('device_info', {})
        
        return ModelInfoResponse(
            service=config.service_name,
            available_models=available_models,
            current_model=current_model,
            device_info=device_info
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get model info: {str(e)}")
        raise ProcessingError("model_info", str(e))


@router.get("/documents")
async def list_processed_documents(
    manager: EmbeddingManagerService = Depends(get_embedding_manager)
):
    """処理済みドキュメント一覧を取得"""
    
    logger.info("📋 Listing processed documents")
    
    try:
        documents = await manager.list_processed_documents()
        
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