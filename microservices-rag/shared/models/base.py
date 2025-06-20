"""
基底データモデル

全レスポンスで使用される共通の基底クラスを定義
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from uuid import UUID


class BaseResponseModel(BaseModel):
    """全レスポンスの基底クラス"""
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: str
    version: str = "1.0.0"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class ErrorModel(BaseModel):
    """エラー情報モデル"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponseModel(BaseResponseModel):
    """エラーレスポンスモデル"""
    success: bool = False
    error: ErrorModel


class HealthCheckResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: Literal["healthy", "unhealthy"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: str
    version: str = "1.0.0"
    uptime: int  # seconds
    dependencies: Dict[str, str] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }