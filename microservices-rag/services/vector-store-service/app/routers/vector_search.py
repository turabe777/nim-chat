"""
Vector Store Service API Routes

ベクトル検索・類似度検索エンドポイント
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import time

from shared.models.vector_store import (
    VectorIndexRequest, VectorIndexResponse,
    VectorSearchQuery, VectorSearchResponse, VectorSearchResult,
    SimilaritySearchRequest, SimilaritySearchResponse,
    VectorStoreConfig, VectorIndexStats
)
from shared.utils.config import VectorStoreServiceConfig
from shared.utils.logging import get_logger
from shared.utils.exceptions import ProcessingError, DocumentNotFoundError
from ..services.faiss_manager import FAISSManagerService

router = APIRouter()
config = VectorStoreServiceConfig()
logger = get_logger(__name__)

# サービス依存関数
def get_faiss_manager():
    """FAISS管理サービスを取得"""
    return FAISSManagerService(config.storage_path)


@router.post("/vector/index", response_model=VectorIndexResponse)
async def create_vector_index(
    request: VectorIndexRequest,
    faiss_manager: FAISSManagerService = Depends(get_faiss_manager)
):
    """ベクトルインデックスを作成"""
    
    logger.info(f"🔍 Creating vector index for document {request.document_id}")
    
    try:
        # 設定準備
        vector_config = VectorStoreConfig()
        if request.index_config:
            # リクエストの設定で上書き
            for key, value in request.index_config.items():
                if hasattr(vector_config, key):
                    setattr(vector_config, key, value)
        
        # インデックス作成
        result = await faiss_manager.create_index(
            document_id=request.document_id,
            vectors=request.embedding_vectors,
            embedding_ids=request.embedding_ids,
            chunk_ids=request.chunk_ids,
            config=vector_config
        )
        
        logger.info(f"✅ Created vector index for document {request.document_id}")
        
        return VectorIndexResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Failed to create vector index: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vector/search", response_model=VectorSearchResponse)
async def search_vectors(
    query: VectorSearchQuery,
    faiss_manager: FAISSManagerService = Depends(get_faiss_manager)
):
    """ベクトル検索を実行"""
    
    start_time = time.time()
    
    logger.info(f"🔍 Vector search for document {query.document_id}")
    
    try:
        if not query.document_id:
            raise ProcessingError("search_error", "document_id is required for vector search")
        
        # ベクトル検索実行
        search_results = await faiss_manager.search_vectors(
            document_id=query.document_id,
            query_vector=query.query_vector,
            top_k=query.top_k,
            similarity_threshold=query.similarity_threshold
        )
        
        # 結果変換
        results = []
        for result in search_results:
            vector_result = VectorSearchResult(
                embedding_id=result["embedding_id"],
                chunk_id=result["chunk_id"],
                document_id=result["document_id"],
                similarity_score=result["similarity_score"],
                metadata={"rank": result["rank"]} if query.include_metadata else None
            )
            results.append(vector_result)
        
        search_time = time.time() - start_time
        
        # インデックス情報取得
        index_stats = await faiss_manager.get_index_stats(query.document_id)
        index_info = {
            "total_vectors": index_stats.total_vectors if index_stats else 0,
            "dimension": index_stats.dimension if index_stats else 0,
            "index_type": index_stats.index_type if index_stats else "unknown"
        }
        
        logger.info(f"✅ Vector search completed: {len(results)} results in {search_time:.3f}s")
        
        return VectorSearchResponse(
            results=results,
            total_found=len(results),
            search_time=search_time,
            index_info=index_info
        )
        
    except DocumentNotFoundError as e:
        logger.error(f"❌ Document not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Vector search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vector/similarity", response_model=SimilaritySearchResponse)
async def similarity_search(
    request: SimilaritySearchRequest,
    faiss_manager: FAISSManagerService = Depends(get_faiss_manager)
):
    """類似度検索を実行"""
    
    start_time = time.time()
    
    logger.info(f"🔍 Similarity search request")
    
    try:
        if not request.query_vector:
            raise ProcessingError("search_error", "query_vector is required for similarity search")
        
        # 対象ドキュメントが指定されていない場合は全ドキュメント検索
        if not request.document_ids:
            # 全インデックス一覧取得
            all_indexes = await faiss_manager.list_indexes()
            document_ids = [UUID(idx["document_id"]) for idx in all_indexes]
        else:
            document_ids = request.document_ids
        
        # 全ドキュメントで検索実行
        all_results = []
        for doc_id in document_ids:
            try:
                doc_results = await faiss_manager.search_vectors(
                    document_id=doc_id,
                    query_vector=request.query_vector,
                    top_k=request.top_k * 2,  # 多めに取得してからフィルタリング
                    similarity_threshold=request.similarity_threshold
                )
                all_results.extend(doc_results)
            except DocumentNotFoundError:
                logger.warning(f"⚠️ Index not found for document {doc_id}")
                continue
        
        # スコアでソートして上位K件取得
        all_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_results = all_results[:request.top_k]
        
        # 結果変換
        results = []
        for result in top_results:
            vector_result = VectorSearchResult(
                embedding_id=result["embedding_id"],
                chunk_id=result["chunk_id"],
                document_id=result["document_id"],
                similarity_score=result["similarity_score"],
                vector=request.query_vector if request.include_vectors else None,
                metadata={"rank": result["rank"]} if request.include_content else None
            )
            results.append(vector_result)
        
        search_time = time.time() - start_time
        
        logger.info(f"✅ Similarity search completed: {len(results)} results in {search_time:.3f}s")
        
        return SimilaritySearchResponse(
            query_info={
                "query_type": "vector",
                "target_documents": len(document_ids),
                "similarity_threshold": request.similarity_threshold
            },
            results=results,
            total_found=len(results),
            search_stats={
                "search_time": search_time,
                "total_candidates": len(all_results),
                "documents_searched": len(document_ids)
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Similarity search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector/stats/{document_id}", response_model=VectorIndexStats)
async def get_index_stats(
    document_id: UUID,
    faiss_manager: FAISSManagerService = Depends(get_faiss_manager)
):
    """インデックス統計情報を取得"""
    
    logger.info(f"📊 Getting index stats for document {document_id}")
    
    try:
        stats = await faiss_manager.get_index_stats(document_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail=f"Index not found for document {document_id}")
        
        logger.info(f"✅ Retrieved index stats for document {document_id}")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Failed to get index stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vector/indexes")
async def list_indexes(
    faiss_manager: FAISSManagerService = Depends(get_faiss_manager)
):
    """インデックス一覧を取得"""
    
    logger.info("📋 Listing vector indexes")
    
    try:
        indexes = await faiss_manager.list_indexes()
        
        logger.info(f"📊 Found {len(indexes)} vector indexes")
        
        return {
            "indexes": indexes,
            "total_count": len(indexes)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list indexes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vector/index/{document_id}")
async def delete_index(
    document_id: UUID,
    faiss_manager: FAISSManagerService = Depends(get_faiss_manager)
):
    """インデックスを削除"""
    
    logger.info(f"🗑️ Deleting vector index for document {document_id}")
    
    try:
        deleted = await faiss_manager.delete_index(document_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Index not found for document {document_id}")
        
        logger.info(f"✅ Deleted vector index for document {document_id}")
        
        return {
            "message": "Index deleted successfully",
            "document_id": document_id
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to delete index: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))