"""
Text Processing Service データモデル

テキスト分割・前処理に関するデータモデル
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from .base import BaseResponseModel


class TextChunk(BaseModel):
    """テキストチャンクモデル"""
    chunk_id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    content: str
    chunk_index: int
    start_position: int
    end_position: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }


class TextProcessingConfig(BaseModel):
    """テキスト処理設定"""
    chunk_size: int = Field(default=800, ge=100, le=2000)
    chunk_overlap: int = Field(default=100, ge=0, le=500)
    separators: List[str] = Field(default=["\n\n", "\n", "。", ".", " "])
    min_chunk_size: int = Field(default=100, ge=50)
    remove_whitespace: bool = Field(default=True)
    remove_empty_lines: bool = Field(default=True)
    language: str = Field(default="ja")
    
    @validator('chunk_overlap')
    def validate_overlap(cls, v, values):
        chunk_size = values.get('chunk_size', 800)
        if v >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return v


class TextProcessingRequest(BaseModel):
    """テキスト処理リクエスト"""
    document_id: UUID
    text: str
    config: Optional[TextProcessingConfig] = None
    
    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Text cannot be empty")
        return v


class TextProcessingResponse(BaseResponseModel):
    """テキスト処理レスポンス"""
    document_id: UUID
    chunks: List[TextChunk]
    total_chunks: int
    original_length: int
    processed_length: int
    processing_time: float
    config_used: TextProcessingConfig


class ChunkListRequest(BaseModel):
    """チャンク一覧取得リクエスト"""
    document_id: UUID
    limit: Optional[int] = Field(default=100, le=1000)
    offset: Optional[int] = Field(default=0, ge=0)


class ChunkListResponse(BaseResponseModel):
    """チャンク一覧レスポンス"""
    document_id: UUID
    chunks: List[TextChunk]
    total_chunks: int
    limit: int
    offset: int


class ChunkDetailResponse(BaseResponseModel):
    """チャンク詳細レスポンス"""
    chunk: TextChunk


class TextStatsResponse(BaseResponseModel):
    """テキスト統計レスポンス"""
    document_id: UUID
    total_chunks: int
    total_characters: int
    average_chunk_size: float
    min_chunk_size: int
    max_chunk_size: int
    processing_date: str