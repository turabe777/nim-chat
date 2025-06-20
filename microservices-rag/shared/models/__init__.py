"""
共通データモデル

全マイクロサービスで使用される共通のPydanticモデルを定義
"""

from .base import BaseResponseModel, ErrorModel, ErrorResponseModel, HealthCheckResponse
from .document import (
    Document, DocumentMetadata, DocumentUploadRequest, DocumentUploadResponse,
    DocumentListResponse, TextExtractionRequest, TextExtractionResponse
)
from .text_processing import (
    TextChunk, TextProcessingConfig, TextProcessingRequest, TextProcessingResponse,
    ChunkListRequest, ChunkListResponse, ChunkDetailResponse, TextStatsResponse
)
from .embedding import (
    EmbeddingVector, EmbeddingConfig, EmbeddingRequest, EmbeddingResponse,
    BatchEmbeddingRequest, EmbeddingListResponse, EmbeddingDetailResponse,
    EmbeddingStatsResponse, SimilaritySearchRequest, SimilaritySearchResponse,
    ModelInfoResponse
)

__all__ = [
    # Base models
    "BaseResponseModel",
    "ErrorModel", 
    "ErrorResponseModel",
    "HealthCheckResponse",
    
    # Document models
    "Document",
    "DocumentMetadata",
    "DocumentUploadRequest",
    "DocumentUploadResponse", 
    "DocumentListResponse",
    "TextExtractionRequest",
    "TextExtractionResponse",
    
    # Text Processing models
    "TextChunk",
    "TextProcessingConfig",
    "TextProcessingRequest",
    "TextProcessingResponse",
    "ChunkListRequest",
    "ChunkListResponse", 
    "ChunkDetailResponse",
    "TextStatsResponse",
    
    # Embedding models
    "EmbeddingVector",
    "EmbeddingConfig",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "BatchEmbeddingRequest",
    "EmbeddingListResponse",
    "EmbeddingDetailResponse",
    "EmbeddingStatsResponse",
    "SimilaritySearchRequest",
    "SimilaritySearchResponse",
    "ModelInfoResponse",
]