from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
import os

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Vector Store Service",
    description="ベクトル検索・類似度検索サービス（mainブランチ方式）",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データディレクトリ設定
DATA_DIR = "/app/data"
VECTOR_STORE_FILE = os.path.join(DATA_DIR, "vectors.json")

# リクエスト・レスポンスモデル
class VectorData(BaseModel):
    chunk_id: str
    vector: List[float]
    metadata: Dict[str, Any] = {}

class StoreRequest(BaseModel):
    document_id: str
    vectors: List[VectorData]

class SearchRequest(BaseModel):
    document_id: str
    query_vector: List[float]
    top_k: int = 5
    similarity_threshold: float = 0.7  # より高い閾値（mainブランチ相当）

class GlobalSearchRequest(BaseModel):
    query_vector: List[float]
    top_k: int = 10
    similarity_threshold: float = 0.3

class SearchResult(BaseModel):
    chunk_id: str
    similarity_score: float
    metadata: Dict[str, Any] = {}

class SearchResponse(BaseModel):
    success: bool
    results: List[SearchResult]
    total_found: int
    query_time: float

# インメモリベクトルストア
vector_store: Dict[str, List[VectorData]] = {}

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """mainブランチと同じコサイン類似度計算"""
    # 正規化されたベクトル同士の内積はコサイン類似度と等価
    # SentenceTransformerではnormalize_embeddings=Trueで正規化済み
    return float(np.dot(a, b))

def load_vectors():
    """ベクトルデータを読み込み"""
    global vector_store
    try:
        if os.path.exists(VECTOR_STORE_FILE):
            with open(VECTOR_STORE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                vector_store = {}
                for doc_id, vectors in data.items():
                    vector_store[doc_id] = [VectorData(**v) for v in vectors]
            logger.info(f"Loaded {len(vector_store)} documents from storage")
    except Exception as e:
        logger.error(f"Failed to load vectors: {e}")
        vector_store = {}

def save_vectors():
    """ベクトルデータを保存"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        data = {}
        for doc_id, vectors in vector_store.items():
            data[doc_id] = [v.dict() for v in vectors]
        
        with open(VECTOR_STORE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(vector_store)} documents to storage")
    except Exception as e:
        logger.error(f"Failed to save vectors: {e}")

@app.on_event("startup")
async def startup_event():
    """サービス起動時の処理"""
    load_vectors()

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "service": "vector-store-service",
        "version": "1.0.0-improved-similarity",
        "documents_count": len(vector_store)
    }

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Vector Store Service (Improved Similarity)",
        "status": "running"
    }

@app.post("/api/v1/vector/store")
async def store_vectors(request: StoreRequest):
    """ベクトルを保存"""
    try:
        document_id = request.document_id
        
        # ベクトル次元チェック
        if request.vectors:
            expected_dim = len(request.vectors[0].vector)
            for i, vector_data in enumerate(request.vectors):
                if len(vector_data.vector) != expected_dim:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Vector dimension mismatch at index {i}: expected {expected_dim}, got {len(vector_data.vector)}"
                    )
            
            logger.info(f"Storing vectors with dimension: {expected_dim}")
        
        # ベクトルを保存
        vector_store[document_id] = request.vectors
        save_vectors()
        
        logger.info(f"Stored {len(request.vectors)} vectors for document {document_id}")
        
        return {
            "success": True,
            "document_id": document_id,
            "vectors_stored": len(request.vectors),
            "message": "Vectors stored successfully"
        }
        
    except Exception as e:
        logger.error(f"Error storing vectors: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to store vectors: {str(e)}")

@app.post("/api/v1/vector/search", response_model=SearchResponse)
async def search_vectors(request: SearchRequest):
    """ベクトル検索（mainブランチ方式の類似度計算）"""
    import time
    start_time = time.time()
    
    try:
        document_id = request.document_id
        query_vector = np.array(request.query_vector, dtype=np.float32)
        
        logger.info(f"Searching vectors for document: {document_id}")
        logger.info(f"Query vector dimension: {len(query_vector)}")
        logger.info(f"Similarity threshold: {request.similarity_threshold}")
        
        if document_id not in vector_store:
            logger.warning(f"Document {document_id} not found in vector store")
            return SearchResponse(
                success=True,
                results=[],
                total_found=0,
                query_time=time.time() - start_time
            )
        
        # 類似度計算（mainブランチ方式）
        similarities = []
        for vector_data in vector_store[document_id]:
            stored_vector = np.array(vector_data.vector, dtype=np.float32)
            
            # mainブランチと同じコサイン類似度計算
            similarity = cosine_similarity(query_vector, stored_vector)
            
            logger.debug(f"Chunk {vector_data.chunk_id}: similarity = {similarity:.4f}")
            
            if similarity >= request.similarity_threshold:
                similarities.append((similarity, vector_data))
        
        # 類似度でソート（降順）
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        logger.info(f"Found {len(similarities)} vectors above threshold {request.similarity_threshold}")
        
        # Top-K取得
        results = []
        for similarity, vector_data in similarities[:request.top_k]:
            results.append(SearchResult(
                chunk_id=vector_data.chunk_id,
                similarity_score=float(similarity),
                metadata=vector_data.metadata
            ))
        
        query_time = time.time() - start_time
        
        logger.info(f"Vector search completed: {len(results)} results in {query_time:.3f}s")
        if results:
            logger.info(f"Top similarity score: {results[0].similarity_score:.4f}")
        
        return SearchResponse(
            success=True,
            results=results,
            total_found=len(similarities),
            query_time=query_time
        )
        
    except Exception as e:
        logger.error(f"Vector search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/api/v1/vector/search/global", response_model=SearchResponse)
async def global_search_vectors(request: GlobalSearchRequest):
    """全ドキュメント横断ベクトル検索"""
    import time
    start_time = time.time()
    
    try:
        query_vector = np.array(request.query_vector, dtype=np.float32)
        
        logger.info(f"Global vector search across all documents")
        logger.info(f"Query vector dimension: {len(query_vector)}")
        logger.info(f"Similarity threshold: {request.similarity_threshold}")
        
        # 全ドキュメントからベクトル検索
        all_similarities = []
        
        for document_id, vectors in vector_store.items():
            for vector_data in vectors:
                stored_vector = np.array(vector_data.vector, dtype=np.float32)
                
                # コサイン類似度計算
                similarity = cosine_similarity(query_vector, stored_vector)
                
                if similarity >= request.similarity_threshold:
                    all_similarities.append({
                        "chunk_id": vector_data.chunk_id,
                        "similarity_score": similarity,
                        "metadata": vector_data.metadata,
                        "document_id": document_id
                    })
        
        # 類似度でソートして上位K件を選択
        all_similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_results = all_similarities[:request.top_k]
        
        results = []
        for item in top_results:
            results.append(SearchResult(
                chunk_id=item["chunk_id"],
                similarity_score=item["similarity_score"],
                metadata=item["metadata"]
            ))
        
        query_time = time.time() - start_time
        
        logger.info(f"Global search completed: {len(results)} results from {len(vector_store)} documents in {query_time:.3f}s")
        
        return SearchResponse(
            success=True,
            results=results,
            total_found=len(results),
            query_time=query_time
        )
        
    except Exception as e:
        logger.error(f"Error in global vector search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Global search failed: {str(e)}")

@app.get("/api/v1/vector/stats")
async def get_stats():
    """ベクトルストアの統計情報"""
    total_vectors = sum(len(vectors) for vectors in vector_store.values())
    
    return {
        "total_documents": len(vector_store),
        "total_vectors": total_vectors,
        "documents": {
            doc_id: len(vectors) for doc_id, vectors in vector_store.items()
        }
    }

@app.delete("/api/v1/vector/document/{document_id}")
async def delete_document_vectors(document_id: str):
    """文書のベクトルを削除"""
    try:
        if document_id in vector_store:
            del vector_store[document_id]
            save_vectors()
            return {"success": True, "message": f"Deleted vectors for document: {document_id}"}
        else:
            return {"success": False, "message": f"Document not found: {document_id}"}
    except Exception as e:
        logger.error(f"Error deleting document vectors: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete vectors: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)