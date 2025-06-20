"""
埋め込みベクトル管理サービス

生成された埋め込みベクトルの保存・取得・管理
"""

import json
import aiofiles
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from shared.models.embedding import EmbeddingVector
from shared.utils.logging import get_logger
from shared.utils.exceptions import ProcessingError, DocumentNotFoundError

logger = get_logger(__name__)


class EmbeddingManagerService:
    """埋め込みベクトル管理サービス"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.embeddings_dir = self.storage_path / "embeddings"
        self.metadata_dir = self.storage_path / "embedding_metadata"
        self.cache_dir = self.storage_path / "cache"
        
        # ディレクトリ作成
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """必要なディレクトリを作成"""
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Embedding storage directories ensured: {self.storage_path}")
    
    def _get_embeddings_file_path(self, document_id: UUID) -> Path:
        """埋め込みファイルパスを取得"""
        return self.embeddings_dir / f"{document_id}.json"
    
    def _get_vectors_file_path(self, document_id: UUID) -> Path:
        """ベクトルファイルパス（numpy）を取得"""
        return self.embeddings_dir / f"{document_id}_vectors.npy"
    
    def _get_metadata_file_path(self, document_id: UUID) -> Path:
        """メタデータファイルパスを取得"""
        return self.metadata_dir / f"{document_id}_embedding_metadata.json"
    
    async def save_embeddings(
        self, 
        document_id: UUID, 
        embeddings: List[EmbeddingVector]
    ) -> bool:
        """埋め込みベクトルを保存"""
        
        embeddings_file = self._get_embeddings_file_path(document_id)
        vectors_file = self._get_vectors_file_path(document_id)
        metadata_file = self._get_metadata_file_path(document_id)
        
        try:
            # 埋め込みデータ保存（メタデータ含む）
            embeddings_data = []
            vectors = []
            
            for embedding in embeddings:
                # ベクトル部分を分離
                embedding_dict = embedding.model_dump()
                vectors.append(embedding_dict.pop('vector'))
                embeddings_data.append(embedding_dict)
            
            # JSON保存（ベクトル以外のメタデータ）
            async with aiofiles.open(embeddings_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(embeddings_data, ensure_ascii=False, indent=2, default=str))
            
            # ベクトルをnumpy形式で保存（効率的）
            vectors_array = np.array(vectors, dtype=np.float32)
            np.save(vectors_file, vectors_array)
            
            # メタデータ保存
            metadata = {
                "document_id": str(document_id),
                "total_embeddings": len(embeddings),
                "dimension": embeddings[0].dimension if embeddings else 0,
                "model_name": embeddings[0].model_name if embeddings else "",
                "created_at": datetime.utcnow().isoformat(),
                "vector_norms": [float(np.linalg.norm(v)) for v in vectors],
                "storage_format": "numpy_json_hybrid"
            }
            
            async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(metadata, ensure_ascii=False, indent=2, default=str))
            
            logger.info(f"💾 Saved {len(embeddings)} embeddings for document {document_id}")
            return True
            
        except Exception as e:
            # エラー時のクリーンアップ
            for file_path in [embeddings_file, vectors_file, metadata_file]:
                if file_path.exists():
                    file_path.unlink()
            
            raise ProcessingError("embedding_save", f"Failed to save embeddings: {str(e)}")
    
    async def get_embeddings(
        self,
        document_id: UUID,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[EmbeddingVector]:
        """埋め込みベクトルを取得"""
        
        embeddings_file = self._get_embeddings_file_path(document_id)
        vectors_file = self._get_vectors_file_path(document_id)
        
        if not embeddings_file.exists() or not vectors_file.exists():
            raise DocumentNotFoundError(f"Embeddings not found for document {document_id}")
        
        try:
            # メタデータ読み込み
            async with aiofiles.open(embeddings_file, 'r', encoding='utf-8') as f:
                embeddings_data = json.loads(await f.read())
            
            # ベクトル読み込み
            vectors = np.load(vectors_file)
            
            # EmbeddingVectorオブジェクト再構築
            embeddings = []
            for i, (embedding_dict, vector) in enumerate(zip(embeddings_data, vectors)):
                embedding_dict['vector'] = vector.tolist()
                embedding = EmbeddingVector.model_validate(embedding_dict)
                embeddings.append(embedding)
            
            # ページネーション適用
            if limit:
                embeddings = embeddings[offset:offset + limit]
            elif offset > 0:
                embeddings = embeddings[offset:]
            
            logger.debug(f"📖 Retrieved {len(embeddings)} embeddings for document {document_id}")
            return embeddings
            
        except Exception as e:
            raise ProcessingError("embedding_retrieval", f"Failed to retrieve embeddings: {str(e)}")
    
    async def get_embedding_by_id(
        self, 
        document_id: UUID, 
        embedding_id: UUID
    ) -> Optional[EmbeddingVector]:
        """指定された埋め込みベクトルを取得"""
        
        embeddings = await self.get_embeddings(document_id)
        
        for embedding in embeddings:
            if embedding.embedding_id == embedding_id:
                return embedding
        
        return None
    
    async def get_embeddings_by_chunk_ids(
        self,
        document_id: UUID,
        chunk_ids: List[UUID]
    ) -> List[EmbeddingVector]:
        """チャンクIDリストで埋め込みベクトルを取得"""
        
        embeddings = await self.get_embeddings(document_id)
        chunk_id_set = set(chunk_ids)
        
        filtered_embeddings = [
            embedding for embedding in embeddings
            if embedding.chunk_id in chunk_id_set
        ]
        
        return filtered_embeddings
    
    async def get_vectors_only(self, document_id: UUID) -> Optional[np.ndarray]:
        """ベクトルデータのみを高速取得"""
        
        vectors_file = self._get_vectors_file_path(document_id)
        
        if not vectors_file.exists():
            return None
        
        try:
            vectors = np.load(vectors_file)
            return vectors
        except Exception as e:
            logger.error(f"❌ Failed to load vectors for {document_id}: {str(e)}")
            return None
    
    async def get_embedding_metadata(self, document_id: UUID) -> Optional[Dict[str, Any]]:
        """埋め込みメタデータを取得"""
        
        metadata_file = self._get_metadata_file_path(document_id)
        
        if not metadata_file.exists():
            return None
        
        try:
            async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.loads(await f.read())
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to load embedding metadata {document_id}: {str(e)}")
            return None
    
    async def delete_embeddings(self, document_id: UUID) -> bool:
        """埋め込みベクトルを削除"""
        
        embeddings_file = self._get_embeddings_file_path(document_id)
        vectors_file = self._get_vectors_file_path(document_id)
        metadata_file = self._get_metadata_file_path(document_id)
        
        deleted = False
        
        try:
            for file_path in [embeddings_file, vectors_file, metadata_file]:
                if file_path.exists():
                    file_path.unlink()
                    deleted = True
            
            if deleted:
                logger.info(f"🗑️ Deleted embeddings for document: {document_id}")
            
            return deleted
            
        except Exception as e:
            raise ProcessingError("embedding_deletion", f"Failed to delete embeddings: {str(e)}")
    
    async def list_processed_documents(self) -> List[Dict[str, Any]]:
        """処理済みドキュメント一覧を取得"""
        
        documents = []
        
        try:
            for metadata_file in self.metadata_dir.glob("*_embedding_metadata.json"):
                try:
                    async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.loads(await f.read())
                    documents.append(metadata)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load metadata file {metadata_file}: {str(e)}")
                    continue
            
            # 作成日時でソート（新しい順）
            documents.sort(
                key=lambda doc: doc.get('created_at', ''),
                reverse=True
            )
            
            return documents
            
        except Exception as e:
            raise ProcessingError("document_listing", f"Failed to list processed documents: {str(e)}")
    
    async def get_statistics(self, document_id: UUID) -> Optional[Dict[str, Any]]:
        """ドキュメントの統計情報を取得"""
        
        metadata = await self.get_embedding_metadata(document_id)
        if not metadata:
            return None
        
        vector_norms = metadata.get('vector_norms', [])
        
        # ストレージサイズ計算
        storage_size = 0
        for file_path in [
            self._get_embeddings_file_path(document_id),
            self._get_vectors_file_path(document_id),
            self._get_metadata_file_path(document_id)
        ]:
            if file_path.exists():
                storage_size += file_path.stat().st_size
        
        storage_size_mb = storage_size / (1024 * 1024)
        
        stats = {
            **metadata,
            "average_vector_norm": sum(vector_norms) / len(vector_norms) if vector_norms else 0.0,
            "min_vector_norm": min(vector_norms) if vector_norms else 0.0,
            "max_vector_norm": max(vector_norms) if vector_norms else 0.0,
            "storage_size_mb": round(storage_size_mb, 3)
        }
        
        return stats