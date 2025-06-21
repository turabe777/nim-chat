from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import httpx
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import time

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM Service",
    description="質問応答・RAG統合サービス（改善版）",
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

# 他のサービスのURL
EMBEDDING_SERVICE_URL = "http://embedding-service:8003"
VECTOR_STORE_SERVICE_URL = "http://vector-store-service:8004"

# リクエストモデル
class QuestionAnsweringRequest(BaseModel):
    question: str
    document_id: str
    context_length: int = 3
    similarity_threshold: float = 0.3  # 改善された閾値
    model: str = "mock-llm-model"
    max_tokens: int = 1000
    temperature: float = 0.7

class ContextItem(BaseModel):
    chunk_id: str
    content: str
    similarity_score: float

class QuestionAnsweringResponse(BaseModel):
    success: bool
    question: str
    answer: str
    confidence: float
    contexts_used: List[ContextItem]
    total_contexts_found: int
    model_used: str
    processing_time: float
    token_usage: Dict[str, int]

# 改善されたモックLLM応答生成
def generate_mock_answer(question: str, contexts: List[str]) -> str:
    """改善されたモックLLM（実際のコンテンツを使用）"""
    if not contexts:
        return f"申し訳ございませんが、'{question}'に関する情報がドキュメント内に見つかりませんでした。"
    
    # より自然な応答生成
    response = f"質問「{question}」について、ドキュメントの内容をもとに回答いたします。\n\n"
    
    for i, context in enumerate(contexts, 1):
        # コンテキストの最初の100文字を使用
        preview = context[:100] + "..." if len(context) > 100 else context
        response += f"{i}. {preview}\n"
    
    response += f"\n以上のように、{len(contexts)}つの関連する情報を見つけました。詳細については、元のドキュメントをご参照ください。"
    
    return response

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "service": "llm-service",
        "version": "1.0.0-improved"
    }

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "LLM Service (Improved)",
        "status": "running"
    }

@app.post("/api/v1/qa", response_model=QuestionAnsweringResponse)
async def question_answering(request: QuestionAnsweringRequest):
    """質問応答（改善されたRAGパイプライン）"""
    start_time = time.time()
    
    try:
        # 1. 質問の埋め込み生成
        async with httpx.AsyncClient() as client:
            logger.info(f"Generating embeddings for question: {request.question[:50]}...")
            
            # 質問の埋め込み生成
            embedding_response = await client.post(
                f"{EMBEDDING_SERVICE_URL}/api/v1/embeddings/generate",
                json={
                    "texts": [request.question],
                    "document_id": "query",
                    "config": {}
                },
                timeout=30.0
            )
            embedding_response.raise_for_status()
            embedding_data = embedding_response.json()
            
            if not embedding_data["success"] or not embedding_data["embeddings"]:
                raise HTTPException(status_code=500, detail="Failed to generate question embedding")
            
            query_vector = embedding_data["embeddings"][0]["vector"]
            logger.info(f"Generated query vector with dimension: {len(query_vector)}")
            
            # 2. ベクトル検索
            logger.info(f"Searching vectors with threshold: {request.similarity_threshold}")
            
            search_response = await client.post(
                f"{VECTOR_STORE_SERVICE_URL}/api/v1/vector/search",
                json={
                    "document_id": request.document_id,
                    "query_vector": query_vector,
                    "top_k": request.context_length,
                    "similarity_threshold": request.similarity_threshold
                },
                timeout=30.0
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            
            logger.info(f"Vector search found {len(search_data.get('results', []))} results")
            
            # 3. コンテキスト準備（改善版：メタデータから実際のコンテンツを取得）
            contexts_used = []
            context_texts = []
            
            for result in search_data.get("results", []):
                # メタデータからコンテンツプレビューを取得
                metadata = result.get("metadata", {})
                content = metadata.get("content_preview", f"チャンク {result['chunk_id']}")
                
                contexts_used.append(ContextItem(
                    chunk_id=result["chunk_id"],
                    content=content,
                    similarity_score=result["similarity_score"]
                ))
                context_texts.append(content)
                
                logger.info(f"Found context: {content[:50]}... (similarity: {result['similarity_score']:.4f})")
            
            # 4. LLM応答生成（改善されたモック）
            answer = generate_mock_answer(request.question, context_texts)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Generated answer with {len(contexts_used)} contexts in {processing_time:.3f}s")
            
            return QuestionAnsweringResponse(
                success=True,
                question=request.question,
                answer=answer,
                confidence=0.85 if contexts_used else 0.1,
                contexts_used=contexts_used,
                total_contexts_found=len(contexts_used),
                model_used=request.model,
                processing_time=processing_time,
                token_usage={
                    "prompt_tokens": len(request.question.split()) + sum(len(ctx.split()) for ctx in context_texts),
                    "completion_tokens": len(answer.split()),
                    "total_tokens": len(request.question.split()) + sum(len(ctx.split()) for ctx in context_texts) + len(answer.split())
                }
            )
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error in RAG pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Service communication error: {str(e)}")
    except Exception as e:
        logger.error(f"RAG pipeline error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG pipeline failed: {str(e)}")

@app.post("/api/v1/generate")
async def generate_response(request: dict):
    """直接応答生成（モック）"""
    try:
        prompt = request.get("prompt", "")
        context = request.get("context", "")
        
        # モック応答
        answer = f"プロンプト「{prompt}」に対する応答です。"
        if context:
            answer += f" コンテキスト: {context[:100]}..."
        
        return {
            "success": True,
            "answer": answer,
            "model_used": "mock-llm-model",
            "token_usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(answer.split()),
                "total_tokens": len(prompt.split()) + len(answer.split())
            },
            "processing_time": 0.1
        }
        
    except Exception as e:
        logger.error(f"Generate response error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")

@app.get("/api/v1/test")
async def test_connection():
    """API接続テスト"""
    return {
        "success": True,
        "status": "connected",
        "available_models": ["mock-llm-model"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)