"""
FAISS ベクトルインデックス管理サービス

FAISSを使用した高速ベクトル検索機能
"""

import faiss
import numpy as np
import json
import aiofiles
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
import pickle

from shared.models.vector_store import VectorStoreConfig, VectorIndexStats
from shared.utils.logging import get_logger
from shared.utils.exceptions import ProcessingError, DocumentNotFoundError

logger = get_logger(__name__)


class FAISSManagerService:
    """FAISS ベクトルインデックス管理サービス"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.indexes_dir = self.storage_path / "faiss_indexes"
        self.metadata_dir = self.storage_path / "index_metadata"
        
        # ディレクトリ作成
        self._ensure_directories()
        
        # インデックスキャッシュ
        self._index_cache: Dict[str, faiss.Index] = {}
        self._metadata_cache: Dict[str, Dict] = {}
    
    def _ensure_directories(self) -> None:
        """必要なディレクトリを作成"""
        self.indexes_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 FAISS storage directories ensured: {self.storage_path}")
    
    def _get_index_file_path(self, document_id: UUID) -> Path:
        """インデックスファイルパスを取得"""
        return self.indexes_dir / f"{document_id}.faiss"
    
    def _get_metadata_file_path(self, document_id: UUID) -> Path:
        """メタデータファイルパスを取得"""
        return self.metadata_dir / f"{document_id}_index.json"
    
    def _get_mapping_file_path(self, document_id: UUID) -> Path:
        """ID マッピングファイルパスを取得"""
        return self.metadata_dir / f"{document_id}_mapping.pkl"
    
    def _create_faiss_index(
        self, 
        vectors: np.ndarray, 
        config: VectorStoreConfig
    ) -> faiss.Index:
        """FAISSインデックスを作成"""
        
        dimension = vectors.shape[1]
        n_vectors = vectors.shape[0]
        
        # インデックスタイプに応じてインデックス作成
        if config.index_type == "Flat":
            if config.metric_type == "IP":
                index = faiss.IndexFlatIP(dimension)
            else:  # L2
                index = faiss.IndexFlatL2(dimension)
                
        elif config.index_type == "IVFFlat":
            # クラスタ数調整（ベクトル数が少ない場合）
            nlist = min(config.nlist, max(1, n_vectors // 4))
            
            if config.metric_type == "IP":
                quantizer = faiss.IndexFlatIP(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            else:  # L2
                quantizer = faiss.IndexFlatL2(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            
            # 学習が必要
            if n_vectors >= nlist:
                index.train(vectors)
            else:
                # ベクトル数が少ない場合はFlatにフォールバック
                logger.warning(f"⚠️ Too few vectors ({n_vectors}) for IVFFlat, using Flat index")
                if config.metric_type == "IP":
                    index = faiss.IndexFlatIP(dimension)
                else:
                    index = faiss.IndexFlatL2(dimension)
        else:
            # デフォルトはFlat
            if config.metric_type == "IP":
                index = faiss.IndexFlatIP(dimension)
            else:
                index = faiss.IndexFlatL2(dimension)
        
        return index
    
    async def create_index(
        self,
        document_id: UUID,
        vectors: List[List[float]],
        embedding_ids: List[UUID],
        chunk_ids: List[UUID],
        config: Optional[VectorStoreConfig] = None
    ) -> Dict[str, Any]:
        """ベクトルインデックスを作成"""
        
        if not vectors or len(vectors) != len(embedding_ids) != len(chunk_ids):
            raise ProcessingError("index_creation", "Vector, embedding_id, and chunk_id lists must have same length")
        
        if not config:
            config = VectorStoreConfig()
        
        start_time = datetime.now()
        
        try:
            # ベクトル入力検証
            if not vectors or not isinstance(vectors, list):
                raise ProcessingError("index_creation", "Invalid vector input: must be a non-empty list")
            
            # ベクトルをnumpy配列に変換
            vectors_array = np.array(vectors, dtype=np.float32)
            
            # デバッグ: ベクトル配列の形状を確認
            logger.info(f"🔍 Vector array shape: {vectors_array.shape}")
            logger.info(f"🔍 Expected dimension: 384 (all-MiniLM-L6-v2)")
            
            # 次元数検証
            if len(vectors_array.shape) != 2:
                raise ProcessingError("index_creation", f"Invalid vector shape: expected 2D array, got {vectors_array.shape}")
            
            expected_dim = 384  # all-MiniLM-L6-v2の標準次元数
            actual_dim = vectors_array.shape[1]
            
            if actual_dim != expected_dim:
                logger.error(f"❌ Dimension mismatch: expected {expected_dim}, got {actual_dim}")
                logger.error(f"❌ Vector input sample: {vectors[0][:5] if len(vectors) > 0 and hasattr(vectors[0], '__len__') else 'No sample'}")
                # 強制的に384次元として処理（パディングまたは切り詰め）
                if actual_dim < expected_dim:
                    # パディング（ゼロ埋め）
                    padding = np.zeros((vectors_array.shape[0], expected_dim - actual_dim), dtype=np.float32)
                    vectors_array = np.hstack([vectors_array, padding])
                    logger.warning(f"⚠️ Padded vectors from {actual_dim} to {expected_dim} dimensions")
                else:
                    # 切り詰め
                    vectors_array = vectors_array[:, :expected_dim]
                    logger.warning(f"⚠️ Truncated vectors from {actual_dim} to {expected_dim} dimensions")
            
            # ベクトル正規化
            if config.normalize_vectors:
                faiss.normalize_L2(vectors_array)
                logger.debug(f"📐 Normalized {len(vectors)} vectors")
            
            # FAISSインデックス作成
            index = self._create_faiss_index(vectors_array, config)
            
            # ベクトル追加
            index.add(vectors_array)
            
            # インデックス保存
            index_file = self._get_index_file_path(document_id)
            faiss.write_index(index, str(index_file))
            
            # ID マッピング保存
            mapping_data = {
                "embedding_ids": [str(eid) for eid in embedding_ids],
                "chunk_ids": [str(cid) for cid in chunk_ids]
            }
            mapping_file = self._get_mapping_file_path(document_id)
            async with aiofiles.open(mapping_file, 'wb') as f:
                await f.write(pickle.dumps(mapping_data))
            
            # メタデータ保存
            processing_time = (datetime.now() - start_time).total_seconds()
            index_size_mb = index_file.stat().st_size / (1024 * 1024)
            
            metadata = {
                "document_id": str(document_id),
                "total_vectors": len(vectors),
                "dimension": vectors_array.shape[1],
                "index_type": config.index_type,
                "metric_type": config.metric_type,
                "index_size_mb": round(index_size_mb, 3),
                "creation_time": processing_time,
                "created_at": datetime.utcnow().isoformat(),
                "config": config.model_dump()
            }
            
            metadata_file = self._get_metadata_file_path(document_id)
            async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(metadata, ensure_ascii=False, indent=2, default=str))
            
            # キャッシュ更新
            cache_key = str(document_id)
            self._index_cache[cache_key] = index
            self._metadata_cache[cache_key] = metadata
            
            logger.info(f"🔍 Created FAISS index for document {document_id} ({len(vectors)} vectors, {processing_time:.3f}s)")
            
            return {
                "document_id": document_id,
                "indexed_count": len(vectors),
                "index_size_mb": index_size_mb,
                "creation_time": processing_time,
                "index_info": {
                    "type": config.index_type,
                    "metric": config.metric_type,
                    "dimension": vectors_array.shape[1]
                }
            }
            
        except Exception as e:
            # エラー時のクリーンアップ
            for file_path in [
                self._get_index_file_path(document_id),
                self._get_metadata_file_path(document_id),
                self._get_mapping_file_path(document_id)
            ]:
                if file_path.exists():
                    file_path.unlink()
            
            raise ProcessingError("index_creation", f"Failed to create FAISS index: {str(e)}")
    
    async def _load_index(self, document_id: UUID) -> Tuple[faiss.Index, Dict]:
        """インデックスとマッピングを読み込み"""
        
        cache_key = str(document_id)
        
        # キャッシュチェック
        if cache_key in self._index_cache:
            mapping_file = self._get_mapping_file_path(document_id)
            async with aiofiles.open(mapping_file, 'rb') as f:
                mapping_data = pickle.loads(await f.read())
            return self._index_cache[cache_key], mapping_data
        
        # ファイルから読み込み
        index_file = self._get_index_file_path(document_id)
        mapping_file = self._get_mapping_file_path(document_id)
        
        if not index_file.exists() or not mapping_file.exists():
            raise DocumentNotFoundError(f"Index not found for document {document_id}")
        
        try:
            # インデックス読み込み
            index = faiss.read_index(str(index_file))
            
            # マッピング読み込み
            async with aiofiles.open(mapping_file, 'rb') as f:
                mapping_data = pickle.loads(await f.read())
                
            # キャッシュ保存
            self._index_cache[cache_key] = index
            
            return index, mapping_data
            
        except Exception as e:
            raise ProcessingError("index_loading", f"Failed to load index: {str(e)}")
    
    async def search_vectors(
        self,
        document_id: UUID,
        query_vector: List[float],
        top_k: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """ベクトル検索を実行"""
        
        try:
            # インデックスとマッピング読み込み
            index, mapping_data = await self._load_index(document_id)
            
            # クエリベクトル準備
            query_array = np.array([query_vector], dtype=np.float32)
            
            # 正規化（インデックス作成時と同じ処理）
            faiss.normalize_L2(query_array)
            
            # 検索実行
            scores, indices = index.search(query_array, min(top_k, index.ntotal))
            
            # 結果処理
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # 無効なインデックス
                    continue
                    
                if score < similarity_threshold:
                    continue
                
                embedding_id = UUID(mapping_data["embedding_ids"][idx])
                chunk_id = UUID(mapping_data["chunk_ids"][idx])
                
                results.append({
                    "embedding_id": embedding_id,
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "similarity_score": float(score),
                    "rank": i + 1
                })
            
            logger.debug(f"🔍 Vector search found {len(results)} results for document {document_id}")
            return results
            
        except Exception as e:
            raise ProcessingError("vector_search", f"Failed to search vectors: {str(e)}")
    
    async def get_index_stats(self, document_id: UUID) -> Optional[VectorIndexStats]:
        """インデックス統計情報を取得"""
        
        metadata_file = self._get_metadata_file_path(document_id)
        
        if not metadata_file.exists():
            return None
        
        try:
            async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.loads(await f.read())
            
            # メモリ使用量計算（概算）
            memory_usage_mb = metadata.get("index_size_mb", 0) * 1.2  # ファイルサイズの1.2倍程度
            
            return VectorIndexStats(
                total_vectors=metadata["total_vectors"],
                dimension=metadata["dimension"],
                index_type=metadata["index_type"],
                memory_usage_mb=round(memory_usage_mb, 3),
                last_updated=datetime.fromisoformat(metadata["created_at"]),
                documents_count=1
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to get index stats for {document_id}: {str(e)}")
            return None
    
    async def delete_index(self, document_id: UUID) -> bool:
        """インデックスを削除"""
        
        deleted = False
        cache_key = str(document_id)
        
        try:
            # ファイル削除
            for file_path in [
                self._get_index_file_path(document_id),
                self._get_metadata_file_path(document_id),
                self._get_mapping_file_path(document_id)
            ]:
                if file_path.exists():
                    file_path.unlink()
                    deleted = True
            
            # キャッシュクリア
            if cache_key in self._index_cache:
                del self._index_cache[cache_key]
            if cache_key in self._metadata_cache:
                del self._metadata_cache[cache_key]
            
            if deleted:
                logger.info(f"🗑️ Deleted FAISS index for document: {document_id}")
            
            return deleted
            
        except Exception as e:
            raise ProcessingError("index_deletion", f"Failed to delete index: {str(e)}")
    
    async def list_indexes(self) -> List[Dict[str, Any]]:
        """インデックス一覧を取得"""
        
        indexes = []
        
        try:
            for metadata_file in self.metadata_dir.glob("*_index.json"):
                try:
                    async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.loads(await f.read())
                    indexes.append(metadata)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load index metadata {metadata_file}: {str(e)}")
                    continue
            
            # 作成日時でソート（新しい順）
            indexes.sort(
                key=lambda idx: idx.get('created_at', ''),
                reverse=True
            )
            
            return indexes
            
        except Exception as e:
            raise ProcessingError("index_listing", f"Failed to list indexes: {str(e)}")