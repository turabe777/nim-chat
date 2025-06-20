"""
Document Service データモデル

PDFファイル管理・テキスト抽出に関するデータモデル
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from .base import BaseResponseModel


class DocumentMetadata(BaseModel):
    """ドキュメントメタデータ"""
    file_name: str
    size_bytes: int
    pages: Optional[int] = None
    mime_type: str = "application/pdf"
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="uploaded")  # uploaded, processing, processed, error
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ["uploaded", "processing", "processed", "error"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Document(BaseModel):
    """ドキュメントモデル"""
    document_id: UUID = Field(default_factory=uuid4)
    content: Optional[str] = None
    metadata: DocumentMetadata
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }
        
    def dict(self, **kwargs):
        """カスタムdict()でdatetimeを文字列に変換"""
        d = super().dict(**kwargs)
        if 'metadata' in d and 'upload_time' in d['metadata']:
            if isinstance(d['metadata']['upload_time'], datetime):
                d['metadata']['upload_time'] = d['metadata']['upload_time'].isoformat()
        return d


class DocumentUploadRequest(BaseModel):
    """ドキュメントアップロードリクエスト"""
    # FastAPIのUploadFileで処理されるため、実際のファイルデータは含まない
    pass


class DocumentUploadResponse(BaseResponseModel):
    """ドキュメントアップロードレスポンス"""
    uploaded_files: List[Document]


class DocumentListResponse(BaseResponseModel):
    """ドキュメント一覧レスポンス"""
    documents: List[Document]
    total_count: int


class TextExtractionRequest(BaseModel):
    """テキスト抽出リクエスト"""
    document_id: UUID


class TextExtractionResponse(BaseResponseModel):
    """テキスト抽出レスポンス"""
    document_id: UUID
    extracted_text: str
    character_count: int
    extraction_method: str
    processing_time: float
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }