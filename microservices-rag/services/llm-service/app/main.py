from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import httpx
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import time
import json

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

# 環境変数（初期値）
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")  # デフォルトはCloud API
NIM_LOCAL_ENDPOINT = os.getenv("NIM_LOCAL_ENDPOINT")  # ローカルNIMエンドポイント

# 動的モード管理（現在のモードを保持）
CURRENT_MODE_OVERRIDE = None  # None=自動, "nim_local", "nvidia_cloud", "mock"

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

class MultiDocumentRequest(BaseModel):
    question: str
    document_ids: List[str] = []  # 空の場合は全ドキュメント検索
    context_length: int = 5
    similarity_threshold: float = 0.3
    model: str = "mock-llm-model"
    max_tokens: int = 1000
    temperature: float = 0.7

class ContextItem(BaseModel):
    chunk_id: str
    content: str
    similarity_score: float

class QuestionAnsweringResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    success: bool
    question: str
    answer: str
    confidence: float
    contexts_used: List[ContextItem]
    total_contexts_found: int
    model_used: str
    processing_time: float
    token_usage: Dict[str, int]

def get_current_mode() -> str:
    """現在のLLMモードを決定（手動切り替え対応）"""
    global CURRENT_MODE_OVERRIDE
    
    # 手動切り替えが設定されている場合
    if CURRENT_MODE_OVERRIDE:
        return CURRENT_MODE_OVERRIDE
    
    # 自動判定（従来のロジック）
    if NIM_LOCAL_ENDPOINT:
        return "nim_local"
    elif NVIDIA_API_KEY:
        return "nvidia_cloud"
    else:
        return "mock"

# NVIDIA LLM統合（Cloud API + ローカルNIM対応）
async def generate_nvidia_response(question: str, contexts: List[str], model: str = "nvidia/llama-3.1-nemotron-70b-instruct") -> str:
    """NVIDIA LLMを使用して回答を生成（Cloud API or ローカルNIM）"""
    
    current_mode = get_current_mode()
    
    if current_mode == "nim_local":
        logger.info("Using local NIM endpoint")
        return await generate_nim_local_response(question, contexts, model)
    elif current_mode == "nvidia_cloud":
        logger.info("Using NVIDIA Cloud API")
        return await generate_nvidia_cloud_response(question, contexts, model)
    else:
        logger.warning("Using mock response")
        return generate_mock_answer(question, contexts)

async def generate_nim_local_response(question: str, contexts: List[str], model: str) -> str:
    """ローカルNIMエンドポイント用の応答生成"""
    try:
        # コンテキストを結合
        context_text = "\n\n".join([f"関連情報{i+1}: {ctx}" for i, ctx in enumerate(contexts)])
        
        # ローカルNIM用のプロンプト構築
        system_prompt = """あなたは文書を基にした質問応答システムです。提供された関連情報を基に、正確で有用な回答を日本語で提供してください。関連情報が質問に直接答えられない場合は、その旨を明確に伝えてください。"""
        
        user_prompt = f"""質問: {question}

関連情報:
{context_text}

上記の関連情報を基に、質問に対する詳細で有用な回答を日本語で提供してください。"""
        
        # ローカルNIM API呼び出し（認証なし）
        headers = {
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": False
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NIM_LOCAL_ENDPOINT}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                logger.info(f"Local NIM response generated successfully")
                return answer
            else:
                logger.error(f"Local NIM API error: {response.status_code} - {response.text}")
                return generate_mock_answer(question, contexts)
                
    except Exception as e:
        logger.error(f"Error calling local NIM API: {str(e)}")
        return generate_mock_answer(question, contexts)

async def generate_nvidia_cloud_response(question: str, contexts: List[str], model: str) -> str:
    """NVIDIA Cloud API用の応答生成"""
    
    try:
        # コンテキストを結合
        context_text = "\n\n".join([f"関連情報{i+1}: {ctx}" for i, ctx in enumerate(contexts)])
        
        # NVIDIA Cloud LLM用のプロンプト構築
        system_prompt = """あなたは文書を基にした質問応答システムです。提供された関連情報を基に、正確で有用な回答を日本語で提供してください。関連情報が質問に直接答えられない場合は、その旨を明確に伝えてください。"""
        
        user_prompt = f"""質問: {question}

関連情報:
{context_text}

上記の関連情報を基に、質問に対する詳細で有用な回答を日本語で提供してください。"""
        
        # NVIDIA Cloud API呼び出し
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": False
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NVIDIA_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                logger.info(f"NVIDIA Cloud LLM response generated successfully")
                return answer
            else:
                logger.error(f"NVIDIA Cloud API error: {response.status_code} - {response.text}")
                return generate_mock_answer(question, contexts)
                
    except Exception as e:
        logger.error(f"Error calling NVIDIA Cloud API: {str(e)}")
        return generate_mock_answer(question, contexts)

# フォールバック用のモックLLM応答生成
def generate_mock_answer(question: str, contexts: List[str]) -> str:
    """モックLLM（フォールバック用）"""
    if not contexts:
        return f"申し訳ございませんが、'{question}'に関する情報がドキュメント内に見つかりませんでした。"
    
    # より自然な応答生成
    response = f"質問「{question}」について、ドキュメントの内容をもとに回答いたします。\n\n"
    
    for i, context in enumerate(contexts, 1):
        # コンテキストの最初の100文字を使用
        preview = context[:100] + "..." if len(context) > 100 else context
        response += f"{i}. {preview}\n"
    
    response += f"\n以上のように、{len(contexts)}つの関連する情報を見つけました。詳細については、元のドキュメントをご参照ください。"
    response += "\n\n注意: この回答はモックLLMによるものです。NVIDIA_API_KEYを設定すると高品質なLLM回答が利用できます。"
    
    return response

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    
    current_mode = get_current_mode()
    
    # エンドポイント情報
    if current_mode == "nim_local":
        endpoint_status = f"Local NIM: {NIM_LOCAL_ENDPOINT}"
    elif current_mode == "nvidia_cloud":
        endpoint_status = f"Cloud API: {NVIDIA_BASE_URL}"
    else:
        endpoint_status = "Mock responses only"
    
    return {
        "status": "healthy",
        "service": "llm-service",
        "version": "1.2.0-mode-switching",
        "llm_mode": current_mode,
        "endpoint": endpoint_status,
        "nvidia_api_key": "configured" if NVIDIA_API_KEY else "not_configured",
        "nim_local_endpoint": "configured" if NIM_LOCAL_ENDPOINT else "not_configured",
        "mode_override": CURRENT_MODE_OVERRIDE,
        "is_auto_mode": CURRENT_MODE_OVERRIDE is None
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
            
            # 4. LLM応答生成（NVIDIA Cloud LLM統合）
            answer = await generate_nvidia_response(request.question, context_texts, request.model)
            
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

@app.post("/api/v1/qa/multi", response_model=QuestionAnsweringResponse)
async def multi_document_question_answering(request: MultiDocumentRequest):
    """複数ドキュメント横断質問応答"""
    start_time = time.time()
    
    try:
        logger.info(f"Starting multi-document QA for question: {request.question[:50]}...")
        
        async with httpx.AsyncClient() as client:
            # 1. 質問の埋め込み生成
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
            
            # 2. 複数ドキュメントからベクトル検索
            all_contexts = []
            
            if request.document_ids:
                # 指定されたドキュメントから検索
                for doc_id in request.document_ids:
                    search_response = await client.post(
                        f"{VECTOR_STORE_SERVICE_URL}/api/v1/vector/search",
                        json={
                            "document_id": doc_id,
                            "query_vector": query_vector,
                            "top_k": request.context_length,
                            "similarity_threshold": request.similarity_threshold
                        },
                        timeout=30.0
                    )
                    if search_response.status_code == 200:
                        search_data = search_response.json()
                        all_contexts.extend(search_data.get("results", []))
            else:
                # 全ドキュメントから検索（vector-store-serviceで実装予定）
                search_response = await client.post(
                    f"{VECTOR_STORE_SERVICE_URL}/api/v1/vector/search/global",
                    json={
                        "query_vector": query_vector,
                        "top_k": request.context_length * 2,  # 複数ドキュメントなので多めに取得
                        "similarity_threshold": request.similarity_threshold
                    },
                    timeout=30.0
                )
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    all_contexts = search_data.get("results", [])
                else:
                    logger.warning("Global search not available, using fallback")
                    all_contexts = []
            
            # 3. 類似度でソートして上位を選択
            all_contexts.sort(key=lambda x: x["similarity_score"], reverse=True)
            top_contexts = all_contexts[:request.context_length]
            
            logger.info(f"Found {len(top_contexts)} contexts from {len(request.document_ids) if request.document_ids else 'all'} documents")
            
            # 4. コンテキスト準備
            contexts_used = []
            context_texts = []
            
            for result in top_contexts:
                metadata = result.get("metadata", {})
                content = metadata.get("content_preview", f"チャンク {result['chunk_id']}")
                
                contexts_used.append(ContextItem(
                    chunk_id=result["chunk_id"],
                    content=content,
                    similarity_score=result["similarity_score"]
                ))
                context_texts.append(content)
                
                logger.info(f"Context from {metadata.get('filename', 'unknown')}: {content[:50]}... (similarity: {result['similarity_score']:.4f})")
            
            # 5. NVIDIA Cloud LLM応答生成
            answer = await generate_nvidia_response(request.question, context_texts, request.model)
            
            processing_time = time.time() - start_time
            
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
        logger.error(f"HTTP error in multi-document QA: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Service communication error: {str(e)}")
    except Exception as e:
        logger.error(f"Multi-document QA error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Multi-document QA failed: {str(e)}")

@app.get("/api/v1/models/recommended")
async def get_recommended_model():
    """現在のモードに応じた推奨モデル名を取得"""
    
    current_mode = get_current_mode()
    
    if current_mode == "nim_local" and NIM_LOCAL_ENDPOINT:
        # ローカルNIMから利用可能モデルを取得
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{NIM_LOCAL_ENDPOINT}/v1/models",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    models_data = response.json()
                    available_models = [model["id"] for model in models_data.get("data", [])]
                    recommended_model = available_models[0] if available_models else "mock-llm-model"
                    
                    return {
                        "success": True,
                        "mode": "nim_local",
                        "recommended_model": recommended_model,
                        "available_models": available_models,
                        "endpoint": NIM_LOCAL_ENDPOINT
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get models from local NIM: {str(e)}")
    
    # NVIDIA Cloud APIの場合
    if current_mode == "nvidia_cloud" and NVIDIA_API_KEY:
        return {
            "success": True,
            "mode": "nvidia_cloud",
            "recommended_model": "nvidia/llama-3.1-nemotron-70b-instruct",
            "available_models": ["nvidia/llama-3.1-nemotron-70b-instruct", "nvidia/llama-3.1-70b-instruct"],
            "endpoint": NVIDIA_BASE_URL
        }
    
    # Mockの場合
    return {
        "success": True,
        "mode": "mock",
        "recommended_model": "mock-llm-model",
        "available_models": ["mock-llm-model"],
        "endpoint": "mock"
    }

class ModeSwitch(BaseModel):
    mode: str  # "auto", "nim_local", "nvidia_cloud", "mock"

@app.post("/api/v1/mode/switch")
async def switch_mode(request: ModeSwitch):
    """LLMモードを手動切り替え"""
    global CURRENT_MODE_OVERRIDE
    
    valid_modes = ["auto", "nim_local", "nvidia_cloud", "mock"]
    
    if request.mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Must be one of: {valid_modes}")
    
    # "auto"の場合はオーバーライドを解除
    if request.mode == "auto":
        CURRENT_MODE_OVERRIDE = None
        actual_mode = get_current_mode()
    else:
        # 指定されたモードが利用可能かチェック
        if request.mode == "nim_local" and not NIM_LOCAL_ENDPOINT:
            raise HTTPException(status_code=400, detail="NIM Local endpoint not configured")
        elif request.mode == "nvidia_cloud" and not NVIDIA_API_KEY:
            raise HTTPException(status_code=400, detail="NVIDIA API key not configured")
        
        CURRENT_MODE_OVERRIDE = request.mode
        actual_mode = request.mode
    
    logger.info(f"LLM mode switched to: {request.mode} (actual: {actual_mode})")
    
    # 推奨モデル情報も返す
    model_info = await get_recommended_model()
    
    return {
        "success": True,
        "requested_mode": request.mode,
        "actual_mode": actual_mode,
        "recommended_model": model_info.get("recommended_model", "unknown"),
        "available_modes": {
            "nim_local": bool(NIM_LOCAL_ENDPOINT),
            "nvidia_cloud": bool(NVIDIA_API_KEY),
            "mock": True
        }
    }

@app.get("/api/v1/mode/current")
async def get_current_mode_info():
    """現在のモード情報を取得"""
    current_mode = get_current_mode()
    model_info = await get_recommended_model()
    
    return {
        "success": True,
        "current_mode": current_mode,
        "override_mode": CURRENT_MODE_OVERRIDE,
        "is_auto": CURRENT_MODE_OVERRIDE is None,
        "recommended_model": model_info.get("recommended_model", "unknown"),
        "available_modes": {
            "nim_local": bool(NIM_LOCAL_ENDPOINT),
            "nvidia_cloud": bool(NVIDIA_API_KEY),
            "mock": True
        }
    }

@app.get("/api/v1/test")
async def test_connection():
    """LLM接続テスト（NIM Local/Cloud API）"""
    
    # ローカルNIMテスト
    if NIM_LOCAL_ENDPOINT:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{NIM_LOCAL_ENDPOINT}/v1/models",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    models_data = response.json()
                    available_models = [model["id"] for model in models_data.get("data", [])]
                    
                    return {
                        "success": True,
                        "status": "connected",
                        "message": "Local NIM connection successful",
                        "endpoint": NIM_LOCAL_ENDPOINT,
                        "available_models": available_models,
                        "mode": "nim_local"
                    }
                else:
                    return {
                        "success": False,
                        "status": "connection_error",
                        "message": f"Local NIM returned status {response.status_code}",
                        "endpoint": NIM_LOCAL_ENDPOINT,
                        "mode": "nim_local"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "status": "connection_error", 
                "message": f"Failed to connect to local NIM: {str(e)}",
                "endpoint": NIM_LOCAL_ENDPOINT,
                "mode": "nim_local"
            }
    
    # NVIDIA Cloud APIテスト
    elif NVIDIA_API_KEY:
        try:
            # NVIDIA Cloud API接続テスト
            headers = {
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json",
            }
            
            # モデル一覧取得でAPI接続をテスト
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{NVIDIA_BASE_URL}/models",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    models_data = response.json()
                    available_models = [model["id"] for model in models_data.get("data", [])]
                    
                    return {
                        "success": True,
                        "status": "connected",
                        "message": "NVIDIA Cloud API connection successful",
                        "endpoint": NVIDIA_BASE_URL,
                        "available_models": available_models,
                        "mode": "nvidia_cloud"
                    }
                else:
                    return {
                        "success": False,
                        "status": "api_error",
                        "message": f"NVIDIA Cloud API returned status {response.status_code}",
                        "endpoint": NVIDIA_BASE_URL,
                        "available_models": ["mock-llm-model"],
                        "mode": "nvidia_cloud"
                    }
                    
        except Exception as e:
            logger.error(f"NVIDIA Cloud API connection test failed: {str(e)}")
            return {
                "success": False,
                "status": "connection_error",
                "message": f"Failed to connect to NVIDIA Cloud API: {str(e)}",
                "endpoint": NVIDIA_BASE_URL,
                "available_models": ["mock-llm-model"],
                "mode": "nvidia_cloud"
            }
    
    # フォールバック（Mock）
    else:
        return {
            "success": False,
            "status": "no_endpoint",
            "message": "No NVIDIA endpoint configured (set NIM_LOCAL_ENDPOINT or NVIDIA_API_KEY)",
            "available_models": ["mock-llm-model"],
            "mode": "mock"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)