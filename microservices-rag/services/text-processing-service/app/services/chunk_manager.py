"""
チャンク管理サービス

分割されたテキストチャンクの保存・取得・管理
"""

import json
import aiofiles
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from shared.models.text_processing import TextChunk
from shared.utils.logging import get_logger
from shared.utils.exceptions import ProcessingError, DocumentNotFoundError

logger = get_logger(__name__)


class ChunkManagerService:
    """チャンク管理サービス"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.chunks_dir = self.storage_path / "chunks"
        self.metadata_dir = self.storage_path / "chunk_metadata"
        
        # ディレクトリ作成
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """必要なディレクトリを作成"""
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Chunk storage directories ensured: {self.storage_path}")
    
    def _get_chunks_file_path(self, document_id: UUID) -> Path:
        """チャンクファイルパスを取得"""
        return self.chunks_dir / f"{document_id}.json"
    
    def _get_metadata_file_path(self, document_id: UUID) -> Path:
        """メタデータファイルパスを取得"""
        return self.metadata_dir / f"{document_id}_metadata.json"
    
    async def save_chunks(self, document_id: UUID, chunks: List[TextChunk]) -> bool:
        """チャンクを保存"""
        
        chunks_file = self._get_chunks_file_path(document_id)
        metadata_file = self._get_metadata_file_path(document_id)
        
        try:
            # チャンクデータ保存
            chunks_data = [chunk.model_dump() for chunk in chunks]
            async with aiofiles.open(chunks_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(chunks_data, ensure_ascii=False, indent=2, default=str))
            
            # メタデータ保存
            metadata = {
                "document_id": str(document_id),
                "total_chunks": len(chunks),
                "created_at": datetime.utcnow().isoformat(),
                "total_characters": sum(len(chunk.content) for chunk in chunks),
                "chunk_sizes": [len(chunk.content) for chunk in chunks]
            }
            
            async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(metadata, ensure_ascii=False, indent=2, default=str))
            
            logger.info(f"💾 Saved {len(chunks)} chunks for document {document_id}")
            return True
            
        except Exception as e:
            # エラー時のクリーンアップ
            if chunks_file.exists():
                chunks_file.unlink()
            if metadata_file.exists():
                metadata_file.unlink()
            
            raise ProcessingError("chunk_save", f"Failed to save chunks: {str(e)}")
    
    async def get_chunks(
        self, 
        document_id: UUID, 
        limit: Optional[int] = None, 
        offset: int = 0
    ) -> List[TextChunk]:
        """チャンクを取得"""
        
        chunks_file = self._get_chunks_file_path(document_id)
        
        if not chunks_file.exists():
            raise DocumentNotFoundError(f"Chunks not found for document {document_id}")
        
        try:
            async with aiofiles.open(chunks_file, 'r', encoding='utf-8') as f:
                chunks_data = json.loads(await f.read())
            
            # Pydanticモデルに変換
            chunks = [TextChunk.model_validate(chunk_data) for chunk_data in chunks_data]
            
            # ページネーション適用
            if limit:
                chunks = chunks[offset:offset + limit]
            elif offset > 0:
                chunks = chunks[offset:]
            
            logger.debug(f"📖 Retrieved {len(chunks)} chunks for document {document_id}")
            return chunks
            
        except Exception as e:
            raise ProcessingError("chunk_retrieval", f"Failed to retrieve chunks: {str(e)}")
    
    async def get_chunk_by_id(self, document_id: UUID, chunk_id: UUID) -> Optional[TextChunk]:
        """指定されたチャンクを取得"""
        
        chunks = await self.get_chunks(document_id)
        
        for chunk in chunks:
            if chunk.chunk_id == chunk_id:
                return chunk
        
        return None
    
    async def get_chunk_metadata(self, document_id: UUID) -> Optional[Dict[str, Any]]:
        """チャンクメタデータを取得"""
        
        metadata_file = self._get_metadata_file_path(document_id)
        
        if not metadata_file.exists():
            return None
        
        try:
            async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.loads(await f.read())
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to load chunk metadata {document_id}: {str(e)}")
            return None
    
    async def delete_chunks(self, document_id: UUID) -> bool:
        """チャンクを削除"""
        
        chunks_file = self._get_chunks_file_path(document_id)
        metadata_file = self._get_metadata_file_path(document_id)
        
        deleted = False
        
        try:
            if chunks_file.exists():
                chunks_file.unlink()
                deleted = True
            
            if metadata_file.exists():
                metadata_file.unlink()
                deleted = True
            
            if deleted:
                logger.info(f"🗑️ Deleted chunks for document: {document_id}")
            
            return deleted
            
        except Exception as e:
            raise ProcessingError("chunk_deletion", f"Failed to delete chunks: {str(e)}")
    
    async def list_processed_documents(self) -> List[Dict[str, Any]]:
        """処理済みドキュメント一覧を取得"""
        
        documents = []
        
        try:
            for metadata_file in self.metadata_dir.glob("*_metadata.json"):
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
        
        metadata = await self.get_chunk_metadata(document_id)
        if not metadata:
            return None
        
        chunk_sizes = metadata.get('chunk_sizes', [])
        if not chunk_sizes:
            return metadata
        
        # 統計計算
        stats = {
            **metadata,
            "average_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes)
        }
        
        return stats