"""
Embedding Service データモデル

埋め込みベクトル生成・管理に関するデータモデル
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from uuid import UUID, uuid4
from datetime import datetime
from .base import BaseResponseModel


class EmbeddingVector(BaseModel):
    """埋め込みベクトルモデル"""
    embedding_id: UUID = Field(default_factory=uuid4)
    chunk_id: UUID
    document_id: UUID
    vector: List[float]
    dimension: int
    model_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('vector')
    def validate_vector(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Vector cannot be empty")
        return v
    
    @validator('dimension')
    def validate_dimension(cls, v, values):
        vector = values.get('vector', [])
        if vector and len(vector) != v:
            raise ValueError("Dimension must match vector length")
        return v
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class EmbeddingConfig(BaseModel):
    """埋め込み設定"""
    model_name: str = Field(default="all-MiniLM-L6-v2")
    batch_size: int = Field(default=32, ge=1, le=1000)
    max_sequence_length: int = Field(default=512, ge=1, le=2048)
    normalize_embeddings: bool = Field(default=True)
    device: str = Field(default="cpu")  # cpu, cuda, mps
    cache_embeddings: bool = Field(default=True)


class EmbeddingRequest(BaseModel):
    """埋め込み生成リクエスト"""
    texts: List[str]
    chunk_ids: Optional[List[UUID]] = None
    document_id: Optional[UUID] = None
    config: Optional[EmbeddingConfig] = None
    
    @validator('texts')
    def validate_texts(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Texts list cannot be empty")
        for text in v:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")
        return v
    
    @validator('chunk_ids')
    def validate_chunk_ids(cls, v, values):
        texts = values.get('texts', [])
        if v and len(v) != len(texts):
            raise ValueError("chunk_ids length must match texts length")
        return v


class EmbeddingResponse(BaseResponseModel):
    """埋め込み生成レスポンス"""
    embeddings: List[EmbeddingVector]
    total_count: int
    model_info: Dict[str, Any]
    processing_time: float
    config_used: EmbeddingConfig


class BatchEmbeddingRequest(BaseModel):
    """バッチ埋め込みリクエスト"""
    document_id: UUID
    chunks: List[Dict[str, Any]]  # chunk_id, content含む
    config: Optional[EmbeddingConfig] = None
    
    @validator('chunks')
    def validate_chunks(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Chunks list cannot be empty")
        for chunk in v:
            if 'chunk_id' not in chunk or 'content' not in chunk:
                raise ValueError("Each chunk must have chunk_id and content")
        return v


class EmbeddingListRequest(BaseModel):
    """埋め込み一覧取得リクエスト"""
    document_id: Optional[UUID] = None
    chunk_ids: Optional[List[UUID]] = None
    limit: Optional[int] = Field(default=100, le=1000)
    offset: Optional[int] = Field(default=0, ge=0)


class EmbeddingListResponse(BaseResponseModel):
    """埋め込み一覧レスポンス"""
    embeddings: List[EmbeddingVector]
    total_count: int
    limit: int
    offset: int
    filter_applied: Dict[str, Any]


class EmbeddingDetailResponse(BaseResponseModel):
    """埋め込み詳細レスポンス"""
    embedding: EmbeddingVector


class EmbeddingStatsResponse(BaseResponseModel):
    """埋め込み統計レスポンス"""
    document_id: Optional[UUID] = None
    total_embeddings: int
    dimension: int
    model_name: str
    average_vector_norm: float
    created_date_range: Dict[str, str]
    storage_size_mb: float


class SimilaritySearchRequest(BaseModel):
    """類似度検索リクエスト"""
    query_vector: List[float]
    document_ids: Optional[List[UUID]] = None
    top_k: int = Field(default=10, ge=1, le=100)
    similarity_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    @validator('query_vector')
    def validate_query_vector(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Query vector cannot be empty")
        return v


class SimilarityResult(BaseModel):
    """類似度検索結果"""
    embedding_id: UUID
    chunk_id: UUID
    document_id: UUID
    similarity_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimilaritySearchResponse(BaseResponseModel):
    """類似度検索レスポンス"""
    results: List[SimilarityResult]
    query_dimension: int
    search_time: float
    total_candidates: int


class ModelInfoResponse(BaseResponseModel):
    """モデル情報レスポンス"""
    available_models: List[Dict[str, Any]]
    current_model: Dict[str, Any]
    device_info: Dict[str, str]