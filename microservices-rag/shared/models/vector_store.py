"""
Vector Store Data Models

ベクトルストア関連のデータモデル定義
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime


class VectorSearchQuery(BaseModel):
    """ベクトル検索クエリ"""
    
    query_vector: List[float] = Field(..., description="検索クエリベクトル")
    document_id: Optional[UUID] = Field(None, description="特定ドキュメント内検索")
    top_k: int = Field(default=5, ge=1, le=100, description="上位K件取得")
    similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="類似度閾値")
    include_metadata: bool = Field(default=True, description="メタデータ含む")


class VectorSearchResult(BaseModel):
    """ベクトル検索結果"""
    
    embedding_id: UUID = Field(..., description="埋め込みID")
    chunk_id: UUID = Field(..., description="チャンクID") 
    document_id: UUID = Field(..., description="ドキュメントID")
    similarity_score: float = Field(..., description="類似度スコア")
    vector: Optional[List[float]] = Field(None, description="ベクトル（オプション）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="メタデータ")


class VectorSearchResponse(BaseModel):
    """ベクトル検索レスポンス"""
    
    query_id: UUID = Field(default_factory=uuid4, description="クエリID")
    results: List[VectorSearchResult] = Field(..., description="検索結果")
    total_found: int = Field(..., description="総検索結果数")
    search_time: float = Field(..., description="検索時間（秒）")
    index_info: Dict[str, Any] = Field(..., description="インデックス情報")


class VectorIndexStats(BaseModel):
    """ベクトルインデックス統計"""
    
    total_vectors: int = Field(..., description="総ベクトル数")
    dimension: int = Field(..., description="次元数")
    index_type: str = Field(..., description="インデックスタイプ")
    memory_usage_mb: float = Field(..., description="メモリ使用量（MB）")
    last_updated: datetime = Field(..., description="最終更新日時")
    documents_count: int = Field(..., description="ドキュメント数")


class VectorIndexRequest(BaseModel):
    """ベクトルインデックス作成リクエスト"""
    
    document_id: UUID = Field(..., description="ドキュメントID")
    embedding_vectors: List[List[float]] = Field(..., description="埋め込みベクトル")
    embedding_ids: List[UUID] = Field(..., description="埋め込みID")
    chunk_ids: List[UUID] = Field(..., description="チャンクID")
    index_config: Optional[Dict[str, Any]] = Field(None, description="インデックス設定")


class VectorIndexResponse(BaseModel):
    """ベクトルインデックス作成レスポンス"""
    
    document_id: UUID = Field(..., description="ドキュメントID")
    indexed_count: int = Field(..., description="インデックス化された数")
    index_size_mb: float = Field(..., description="インデックスサイズ（MB）")
    creation_time: float = Field(..., description="作成時間（秒）")
    index_info: Dict[str, Any] = Field(..., description="インデックス情報")


class VectorStoreConfig(BaseModel):
    """ベクトルストア設定"""
    
    index_type: str = Field(default="IVFFlat", description="FAISSインデックスタイプ")
    nlist: int = Field(default=100, description="クラスタ数")
    nprobe: int = Field(default=10, description="検索時プローブ数")
    metric_type: str = Field(default="IP", description="距離メトリック（IP/L2）")
    use_gpu: bool = Field(default=False, description="GPU使用")
    normalize_vectors: bool = Field(default=True, description="ベクトル正規化")


class SimilaritySearchRequest(BaseModel):
    """類似度検索リクエスト"""
    
    query_text: Optional[str] = Field(None, description="検索テキスト")
    query_vector: Optional[List[float]] = Field(None, description="検索ベクトル")
    document_ids: Optional[List[UUID]] = Field(None, description="対象ドキュメントID")
    top_k: int = Field(default=5, ge=1, le=100, description="上位K件")
    similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="類似度閾値")
    include_vectors: bool = Field(default=False, description="ベクトル含む")
    include_content: bool = Field(default=True, description="コンテンツ含む")


class SimilaritySearchResponse(BaseModel):
    """類似度検索レスポンス"""
    
    search_id: UUID = Field(default_factory=uuid4, description="検索ID")
    query_info: Dict[str, Any] = Field(..., description="クエリ情報")
    results: List[VectorSearchResult] = Field(..., description="検索結果")
    total_found: int = Field(..., description="総検索結果数")
    search_stats: Dict[str, Any] = Field(..., description="検索統計")