"""
LLM API

質問応答・LLM推論エンドポイント
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import time

from shared.models.llm import (
    QuestionAnsweringRequest, QuestionAnsweringResponse,
    LLMGenerationRequest, LLMGenerationResponse,
    ModelListResponse, ConnectionTestResponse
)
from shared.utils.config import LLMServiceConfig
from shared.utils.logging import get_logger
from shared.utils.exceptions import ProcessingError
from ..services.nvidia_client import NVIDIACloudClient
from ..services.rag_pipeline import RAGPipeline

router = APIRouter()
logger = get_logger(__name__)

# 依存関係注入
def get_config() -> LLMServiceConfig:
    return LLMServiceConfig()

def get_nvidia_client(config: LLMServiceConfig = Depends(get_config)) -> NVIDIACloudClient:
    return NVIDIACloudClient(config)

def get_rag_pipeline(config: LLMServiceConfig = Depends(get_config)) -> RAGPipeline:
    return RAGPipeline(config)


@router.post("/qa", response_model=QuestionAnsweringResponse)
async def question_answering(
    request: QuestionAnsweringRequest,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """質問応答API - RAGパイプライン実行"""
    
    logger.info(f"🎯 Question answering request: {request.question[:50]}...")
    
    try:
        result = await rag_pipeline.answer_question(
            question=request.question,
            document_id=request.document_id,
            context_length=request.context_length,
            similarity_threshold=request.similarity_threshold,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        response = QuestionAnsweringResponse(
            service="llm-service",
            question=request.question,
            answer=result["answer"],
            confidence=result["confidence"],
            contexts_used=result["contexts_used"],
            total_contexts_found=result["total_contexts_found"],
            model_used=result["model_used"],
            processing_time=result["processing_time"],
            token_usage=result["token_usage"],
            request_id=result["request_id"]
        )
        
        logger.info(f"✅ Question answered successfully in {result['processing_time']:.3f}s")
        return response
        
    except ProcessingError as e:
        logger.error(f"RAG processing error: {e.message}")
        raise HTTPException(status_code=400, detail=f"Processing error: {e.message}")
    except Exception as e:
        logger.error(f"Unexpected error in question answering: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/generate", response_model=LLMGenerationResponse)
async def generate_text(
    request: LLMGenerationRequest,
    nvidia_client: NVIDIACloudClient = Depends(get_nvidia_client)
):
    """テキスト生成API - 直接LLM呼び出し"""
    
    logger.info(f"✍️ Text generation request: {request.prompt[:50]}...")
    
    try:
        result = await nvidia_client.generate_response(
            question=request.prompt,
            context="",  # コンテキストなしの直接生成
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        response = LLMGenerationResponse(
            service="llm-service",
            prompt=request.prompt,
            generated_text=result["answer"],
            model_used=result["model_used"],
            processing_time=result["processing_time"],
            token_usage=result["token_usage"],
            request_id=result["request_id"]
        )
        
        logger.info(f"✅ Text generated successfully in {result['processing_time']:.3f}s")
        return response
        
    except ProcessingError as e:
        logger.error(f"LLM generation error: {e.message}")
        raise HTTPException(status_code=400, detail=f"Generation error: {e.message}")
    except Exception as e:
        logger.error(f"Unexpected error in text generation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/models", response_model=ModelListResponse)
async def list_models(config: LLMServiceConfig = Depends(get_config)):
    """利用可能モデル一覧"""
    
    logger.info("📋 Model list request")
    
    # NVIDIA NIM で利用可能なモデル一覧
    available_models = [
        {
            "name": "nvidia/llama-3.1-nemotron-70b-instruct",
            "description": "高性能な70Bパラメータモデル",
            "max_tokens": 2048,
            "context_length": 128000,
            "recommended_use": "汎用質問応答"
        },
        {
            "name": "nvidia/llama-3.1-nemotron-51b-instruct",
            "description": "バランスの取れた51Bパラメータモデル",
            "max_tokens": 2048,
            "context_length": 128000,
            "recommended_use": "効率的な質問応答"
        },
        {
            "name": "meta/llama-3.1-8b-instruct",
            "description": "軽量な8Bパラメータモデル",
            "max_tokens": 2048,
            "context_length": 128000,
            "recommended_use": "高速応答"
        }
    ]
    
    return ModelListResponse(
        service="llm-service",
        available_models=available_models,
        default_model="nvidia/llama-3.1-nemotron-70b-instruct"
    )


@router.get("/test", response_model=ConnectionTestResponse)
async def test_connection(nvidia_client: NVIDIACloudClient = Depends(get_nvidia_client)):
    """NVIDIA API接続テスト"""
    
    logger.info("🔌 Testing NVIDIA API connection")
    
    start_time = time.time()
    
    try:
        result = await nvidia_client.test_connection()
        response_time = time.time() - start_time
        
        return ConnectionTestResponse(
            service="llm-service",
            connection_status=result["status"],
            message=result["message"],
            model_tested=result.get("model"),
            response_time=response_time
        )
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return ConnectionTestResponse(
            service="llm-service",
            connection_status="error",
            message=f"Connection test failed: {str(e)}",
            response_time=time.time() - start_time
        )