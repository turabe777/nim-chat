from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import numpy as np
from typing import List, Dict, Any
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import time

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Embedding Service",
    description="SentenceTransformer埋め込み生成サービス",
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

# SentenceTransformerモデル（mainブランチと同じ）
model = None

def get_model():
    global model
    if model is None:
        logger.info("Loading SentenceTransformer model: all-MiniLM-L6-v2")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info(f"Model loaded. Dimension: {model.get_sentence_embedding_dimension()}")
    return model

# リクエスト・レスポンスモデル
class EmbeddingRequest(BaseModel):
    texts: List[str]
    document_id: str
    config: Dict[str, Any] = {}

class EmbeddingItem(BaseModel):
    text: str
    vector: List[float]
    index: int

class EmbeddingResponse(BaseModel):
    success: bool
    embeddings: List[EmbeddingItem]
    model_used: str
    processing_time: float
    vector_dimension: int

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "service": "embedding-service",
        "version": "1.0.0-sentencetransformer",
        "model": "all-MiniLM-L6-v2"
    }

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Embedding Service (SentenceTransformer)",
        "status": "running"
    }

@app.post("/api/v1/embeddings/generate", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """SentenceTransformerで埋め込み生成"""
    start_time = time.time()
    
    try:
        if not request.texts:
            raise HTTPException(status_code=400, detail="No texts provided")
        
        # モデル取得
        embedding_model = get_model()
        
        logger.info(f"Generating embeddings for {len(request.texts)} texts")
        
        # 埋め込み生成（mainブランチと同じ方法）
        embeddings = embedding_model.encode(request.texts, normalize_embeddings=True)
        
        # レスポンス作成
        embedding_items = []
        for i, (text, embedding) in enumerate(zip(request.texts, embeddings)):
            embedding_items.append(EmbeddingItem(
                text=text[:100] + "..." if len(text) > 100 else text,
                vector=embedding.tolist(),
                index=i
            ))
        
        processing_time = time.time() - start_time
        
        logger.info(f"Generated {len(embeddings)} embeddings in {processing_time:.3f}s")
        logger.info(f"Vector dimension: {embeddings.shape[1]}")
        
        return EmbeddingResponse(
            success=True,
            embeddings=embedding_items,
            model_used="all-MiniLM-L6-v2",
            processing_time=processing_time,
            vector_dimension=int(embeddings.shape[1])
        )
        
    except Exception as e:
        logger.error(f"Embedding generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)