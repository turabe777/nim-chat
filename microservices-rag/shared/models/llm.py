"""
LLM Service データモデル

質問応答・LLM推論に関するデータモデル
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from .base import BaseResponseModel


class QuestionAnsweringRequest(BaseModel):
    """質問応答リクエスト"""
    question: str = Field(..., min_length=1, description="ユーザーの質問")
    document_id: Optional[UUID] = Field(None, description="検索対象のドキュメントID")
    context_length: int = Field(3, ge=1, le=10, description="検索する関連コンテキスト数")
    similarity_threshold: float = Field(0.3, ge=0.0, le=1.0, description="類似度の閾値")
    
    # LLM設定
    model: Optional[str] = Field(None, description="使用するLLMモデル")
    max_tokens: Optional[int] = Field(None, ge=1, le=2000, description="最大生成トークン数")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="生成温度")
    
    @validator('question')
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()


class ContextItem(BaseModel):
    """検索されたコンテキストアイテム"""
    chunk_id: UUID
    document_id: UUID
    content: str
    similarity_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QuestionAnsweringResponse(BaseResponseModel):
    """質問応答レスポンス"""
    question: str
    answer: str
    confidence: float = Field(ge=0.0, le=1.0, description="回答の信頼度")
    
    # コンテキスト情報
    contexts_used: List[ContextItem]
    total_contexts_found: int
    
    # LLM情報
    model_used: str
    processing_time: float
    token_usage: Dict[str, Any] = Field(default_factory=dict)
    
    # リクエスト情報
    request_id: UUID = Field(default_factory=uuid4)
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class LLMGenerationRequest(BaseModel):
    """LLM生成リクエスト"""
    prompt: str = Field(..., min_length=1, description="生成プロンプト")
    model: Optional[str] = Field(None, description="使用するLLMモデル")
    max_tokens: Optional[int] = Field(None, ge=1, le=2000, description="最大生成トークン数")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="生成温度")
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if not v or not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v.strip()


class LLMGenerationResponse(BaseResponseModel):
    """LLM生成レスポンス"""
    prompt: str
    generated_text: str
    model_used: str
    processing_time: float
    token_usage: Dict[str, Any] = Field(default_factory=dict)
    request_id: UUID = Field(default_factory=uuid4)
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class ModelListResponse(BaseResponseModel):
    """利用可能モデル一覧レスポンス"""
    available_models: List[Dict[str, Any]]
    default_model: str
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class ConnectionTestResponse(BaseResponseModel):
    """接続テストレスポンス"""
    connection_status: str
    message: str
    model_tested: Optional[str] = None
    response_time: Optional[float] = None
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }