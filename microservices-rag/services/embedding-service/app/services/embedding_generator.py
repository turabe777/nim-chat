"""
埋め込みベクトル生成サービス

sentence-transformersを使用した埋め込みベクトル生成
"""

import time
import torch
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from shared.models.embedding import EmbeddingVector, EmbeddingConfig
from shared.utils.logging import get_logger
from shared.utils.exceptions import ProcessingError

logger = get_logger(__name__)


class EmbeddingGeneratorService:
    """埋め込みベクトル生成サービス"""
    
    def __init__(self):
        self.models: Dict[str, SentenceTransformer] = {}
        self.current_model: Optional[SentenceTransformer] = None
        self.current_model_name: Optional[str] = None
        self.device = self._get_best_device()
        
        logger.info(f"🤖 EmbeddingGenerator initialized with device: {self.device}")
    
    def _get_best_device(self) -> str:
        """最適なデバイスを選択"""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    async def load_model(self, model_name: str, device: Optional[str] = None) -> bool:
        """モデルをロード"""
        
        if device:
            self.device = device
        
        if model_name in self.models:
            self.current_model = self.models[model_name]
            self.current_model_name = model_name
            logger.info(f"✅ Model {model_name} already loaded")
            return True
        
        try:
            logger.info(f"📥 Loading embedding model: {model_name}")
            start_time = time.time()
            
            model = SentenceTransformer(model_name, device=self.device)
            
            # モデル情報取得
            max_seq_length = getattr(model, 'max_seq_length', 512)
            dimension = model.get_sentence_embedding_dimension()
            
            self.models[model_name] = model
            self.current_model = model
            self.current_model_name = model_name
            
            load_time = time.time() - start_time
            logger.info(f"✅ Model loaded: {model_name} (dim={dimension}, max_seq={max_seq_length}, time={load_time:.2f}s)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load model {model_name}: {str(e)}")
            raise ProcessingError("model_loading", f"Failed to load embedding model: {str(e)}")
    
    async def generate_embeddings(
        self,
        texts: List[str],
        chunk_ids: Optional[List[UUID]] = None,
        document_id: Optional[UUID] = None,
        config: Optional[EmbeddingConfig] = None
    ) -> List[EmbeddingVector]:
        """テキストから埋め込みベクトルを生成"""
        
        if not texts:
            raise ProcessingError("empty_input", "No texts provided for embedding")
        
        # デフォルト設定
        config = config or EmbeddingConfig()
        
        # モデルロード
        if not self.current_model or self.current_model_name != config.model_name:
            await self.load_model(config.model_name, config.device)
        
        logger.info(f"🔮 Generating embeddings for {len(texts)} texts")
        start_time = time.time()
        
        try:
            # バッチ処理
            embeddings = []
            batch_size = config.batch_size
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_chunk_ids = chunk_ids[i:i + batch_size] if chunk_ids else None
                
                # 埋め込み生成
                vectors = self.current_model.encode(
                    batch_texts,
                    batch_size=len(batch_texts),
                    normalize_embeddings=config.normalize_embeddings,
                    convert_to_numpy=True
                )
                
                # EmbeddingVectorオブジェクト作成
                for j, vector in enumerate(vectors):
                    global_idx = i + j
                    chunk_id = batch_chunk_ids[j] if batch_chunk_ids else None
                    
                    embedding = EmbeddingVector(
                        chunk_id=chunk_id or UUID(int=0),  # ダミーUUID
                        document_id=document_id or UUID(int=0),  # ダミーUUID
                        vector=vector.tolist(),
                        dimension=len(vector),
                        model_name=config.model_name,
                        metadata={
                            "text_length": len(batch_texts[j]),
                            "batch_index": i // batch_size,
                            "device": self.device,
                            "normalized": config.normalize_embeddings
                        }
                    )
                    embeddings.append(embedding)
                
                logger.debug(f"📦 Processed batch {i//batch_size + 1}: {len(batch_texts)} texts")
            
            processing_time = time.time() - start_time
            logger.info(f"✅ Generated {len(embeddings)} embeddings in {processing_time:.3f}s")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Failed to generate embeddings: {str(e)}")
            raise ProcessingError("embedding_generation", f"Failed to generate embeddings: {str(e)}")
    
    async def compute_similarity(
        self,
        query_vector: List[float],
        candidate_vectors: List[List[float]],
        top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """ベクトル間の類似度を計算"""
        
        if not candidate_vectors:
            return []
        
        try:
            # numpy配列に変換
            query_array = np.array(query_vector).reshape(1, -1)
            candidates_array = np.array(candidate_vectors)
            
            # コサイン類似度計算
            similarities = cosine_similarity(query_array, candidates_array)[0]
            
            # top_k結果を取得
            top_indices = np.argsort(similarities)[::-1][:top_k]
            results = [(int(idx), float(similarities[idx])) for idx in top_indices]
            
            logger.debug(f"🔍 Computed similarity for {len(candidate_vectors)} candidates, top_k={top_k}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to compute similarity: {str(e)}")
            raise ProcessingError("similarity_computation", f"Failed to compute similarity: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """現在のモデル情報を取得"""
        
        if not self.current_model:
            return {
                "model_loaded": False,
                "device": self.device
            }
        
        dimension = self.current_model.get_sentence_embedding_dimension()
        max_seq_length = getattr(self.current_model, 'max_seq_length', 512)
        
        return {
            "model_loaded": True,
            "model_name": self.current_model_name,
            "dimension": dimension,
            "max_sequence_length": max_seq_length,
            "device": self.device,
            "device_info": {
                "cuda_available": torch.cuda.is_available(),
                "mps_available": hasattr(torch.backends, 'mps') and torch.backends.mps.is_available(),
                "current_device": str(self.current_model.device) if self.current_model else None
            }
        }
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """利用可能なモデル一覧を取得"""
        
        # よく使われる日本語対応モデル
        popular_models = [
            {
                "name": "all-MiniLM-L6-v2",
                "dimension": 384,
                "description": "軽量で高速、多言語対応",
                "language": "multilingual"
            },
            {
                "name": "all-mpnet-base-v2",
                "dimension": 768,
                "description": "高精度、英語最適化",
                "language": "english"
            },
            {
                "name": "paraphrase-multilingual-MiniLM-L12-v2",
                "dimension": 384,
                "description": "多言語パラフレーズ検出",
                "language": "multilingual"
            },
            {
                "name": "sentence-transformers/all-MiniLM-L12-v2",
                "dimension": 384,
                "description": "バランスの取れた汎用モデル",
                "language": "multilingual"
            }
        ]
        
        # ロード済みモデルをマーク
        for model in popular_models:
            model["loaded"] = model["name"] in self.models
            model["current"] = model["name"] == self.current_model_name
        
        return popular_models