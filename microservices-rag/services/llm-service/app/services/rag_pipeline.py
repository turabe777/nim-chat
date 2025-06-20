"""
RAGパイプライン

他のマイクロサービスと連携して完全な質問応答を実行
"""

import httpx
import time
from typing import Dict, Any, List, Optional
from uuid import UUID

from shared.utils.config import LLMServiceConfig
from shared.utils.logging import get_logger
from shared.utils.exceptions import ProcessingError
from shared.models.llm import ContextItem
from .nvidia_client import NVIDIACloudClient

logger = get_logger(__name__)

class RAGPipeline:
    """RAG パイプライン"""
    
    def __init__(self, config: LLMServiceConfig):
        self.config = config
        self.nvidia_client = NVIDIACloudClient(config)
        
        # マイクロサービス エンドポイント
        self.embedding_service = "http://embedding-service:8003"
        self.vector_store_service = "http://vector-store-service:8004"
        self.text_processing_service = "http://text-processing-service:8002"
        
        logger.info("🔗 RAG Pipeline initialized")
    
    async def answer_question(
        self,
        question: str,
        document_id: Optional[UUID] = None,
        context_length: int = 3,
        similarity_threshold: float = 0.3,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """質問応答の実行"""
        
        start_time = time.time()
        
        try:
            # 1. 質問の埋め込みベクトル生成
            logger.info(f"🔍 Generating embedding for question: {question[:50]}...")
            question_embedding = await self._generate_question_embedding(question)
            
            # 2. ベクトル検索でコンテキスト取得
            logger.info(f"🗂️ Searching for relevant contexts...")
            logger.info(f"   Question embedding dimensions: {len(question_embedding)}")
            logger.info(f"   Document ID: {document_id}")
            logger.info(f"   Context length: {context_length}, Threshold: {similarity_threshold}")
            
            contexts = await self._search_contexts(
                question_embedding,
                document_id,
                context_length,
                similarity_threshold
            )
            
            logger.info(f"   Found {len(contexts)} contexts from vector search")
            
            # 3. チャンクIDからコンテンツを取得
            contexts_with_content = []
            if not contexts:
                logger.warning("No relevant contexts found")
                context_text = "関連する情報が見つかりませんでした。"
            else:
                logger.info(f"   Fetching content for {len(contexts)} contexts...")
                contexts_with_content = await self._fetch_chunk_contents(contexts, document_id)
                
                if not contexts_with_content:
                    logger.warning("No content found for contexts")
                    context_text = "関連する情報が見つかりませんでした。"
                else:
                    # 4. コンテキストを結合
                    try:
                        # デバッグ: コンテキストの構造を確認
                        logger.info(f"🔍 Contexts structure before joining: {[list(ctx.keys()) for ctx in contexts_with_content[:2]]}")
                        
                        # 安全にコンテンツを取得
                        valid_contexts = []
                        for ctx in contexts_with_content:
                            if isinstance(ctx, dict) and "content" in ctx:
                                valid_contexts.append(ctx["content"])
                            else:
                                logger.warning(f"⚠️ Invalid context structure: {ctx}")
                        
                        if valid_contexts:
                            context_text = "\n\n".join(valid_contexts)
                            logger.info(f"📄 Found {len(valid_contexts)} valid contexts with content")
                            logger.info(f"   First context preview: {valid_contexts[0][:100]}...")
                        else:
                            logger.warning("No valid contexts with content found")
                            context_text = "関連する情報が見つかりませんでした。"
                            
                    except Exception as e:
                        logger.error(f"Error processing contexts: {e}")
                        logger.error(f"Context details: {contexts_with_content[:1] if contexts_with_content else 'No contexts'}")
                        context_text = "関連する情報が見つかりませんでした。"
            
            # 4. LLMで回答生成
            logger.info(f"🤖 Generating answer with LLM...")
            llm_response = await self.nvidia_client.generate_response(
                question=question,
                context=context_text,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            total_time = time.time() - start_time
            
            # 5. 信頼度計算（簡易版）
            confidence = self._calculate_confidence(contexts_with_content, llm_response)
            
            logger.info(f"✅ RAG pipeline completed in {total_time:.3f}s")
            
            return {
                "answer": llm_response["answer"],
                "confidence": confidence,
                "contexts_used": [self._format_context(ctx) for ctx in contexts_with_content if isinstance(ctx, dict) and "content" in ctx],
                "total_contexts_found": len(contexts_with_content),
                "model_used": llm_response["model_used"],
                "processing_time": total_time,
                "token_usage": llm_response.get("token_usage", {}),
                "request_id": llm_response["request_id"]
            }
            
        except Exception as e:
            import traceback
            logger.error(f"RAG pipeline failed: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise ProcessingError("rag_pipeline", str(e))
    
    async def _generate_question_embedding(self, question: str) -> List[float]:
        """質問の埋め込みベクトル生成"""
        
        from uuid import uuid4
        
        payload = {
            "texts": [question],
            "document_id": str(uuid4()),  # 質問用の一時的なUUID
            "config": {
                "model_name": "all-MiniLM-L6-v2",
                "normalize_embeddings": True
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.embedding_service}/api/v1/embeddings/generate",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("embeddings") and len(data["embeddings"]) > 0:
                    return data["embeddings"][0]["vector"]
                else:
                    raise ProcessingError("embedding_generation", "Failed to generate question embedding")
                    
        except httpx.RequestError as e:
            logger.error(f"Embedding service connection error: {e}")
            raise ProcessingError("embedding_service", "Failed to connect to embedding service")
    
    async def _search_contexts(
        self,
        query_vector: List[float],
        document_id: Optional[UUID],
        top_k: int,
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """ベクトル検索でコンテキスト取得"""
        
        if document_id:
            # 特定ドキュメント内検索
            payload = {
                "document_id": str(document_id),
                "query_vector": query_vector,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold
            }
        else:
            # 全ドキュメント検索（今回は未実装）
            raise ProcessingError("search_scope", "Document ID is required for vector search")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.vector_store_service}/api/v1/vector/search",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                # 閾値フィルタリング
                filtered_results = [
                    result for result in results 
                    if result.get("similarity_score", 0) >= similarity_threshold
                ]
                
                return filtered_results
                
        except httpx.RequestError as e:
            logger.error(f"Vector store service connection error: {e}")
            raise ProcessingError("vector_store_service", "Failed to connect to vector store service")
    
    async def _fetch_chunk_contents(self, search_results: List[Dict[str, Any]], document_id: UUID) -> List[Dict[str, Any]]:
        """ベクトル検索結果からチャンクコンテンツを取得"""
        
        if not search_results:
            return []
        
        contexts_with_content = []
        
        try:
            # テキスト処理サービスからドキュメントのチャンクを取得
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.text_processing_service}/api/v1/text/chunks/{document_id}"
                )
                response.raise_for_status()
                chunk_data = response.json()
                
                # チャンクをchunk_idでインデックス化
                chunks_by_id = {chunk.get("chunk_id"): chunk for chunk in chunk_data.get("chunks", [])}
                
                # デバッグ: 検索結果の構造を確認
                logger.info(f"🔍 Search results structure: {search_results[:1] if search_results else 'Empty'}")
                logger.info(f"🔍 Available chunks: {list(chunks_by_id.keys())[:5] if chunks_by_id else 'No chunks'}")
                
                # 検索結果とチャンクコンテンツをマッチング
                for i, result in enumerate(search_results):
                    chunk_id = result.get("chunk_id")
                    logger.info(f"🔍 Processing result {i}: chunk_id={chunk_id}, available_keys={list(result.keys())}")
                    
                    if chunk_id and chunk_id in chunks_by_id:
                        chunk = chunks_by_id[chunk_id]
                        logger.info(f"🔍 Found chunk: keys={list(chunk.keys())}, content_preview={chunk.get('content', '')[:50]}...")
                        
                        context_with_content = {
                            "chunk_id": chunk_id,
                            "document_id": result.get("document_id"),
                            "content": chunk.get("content", ""),
                            "similarity_score": result.get("similarity_score", 0.0),
                            "metadata": {
                                **result.get("metadata", {}),
                                **chunk.get("metadata", {})
                            }
                        }
                        contexts_with_content.append(context_with_content)
                    else:
                        logger.warning(f"⚠️ Chunk not found: chunk_id={chunk_id}, in_chunks={chunk_id in chunks_by_id if chunk_id else False}")
                
                logger.info(f"📖 Retrieved content for {len(contexts_with_content)}/{len(search_results)} chunks")
                
                # デバッグ: 最終結果の構造を確認
                if contexts_with_content:
                    logger.info(f"🔍 First context with content keys: {list(contexts_with_content[0].keys())}")
                
                return contexts_with_content
                
        except httpx.RequestError as e:
            logger.error(f"Text processing service connection error: {e}")
            raise ProcessingError("text_processing_service", "Failed to connect to text processing service")
        except Exception as e:
            logger.error(f"Error fetching chunk contents: {e}")
            return []
    
    def _format_context(self, context_data: Dict[str, Any]) -> ContextItem:
        """コンテキストデータをフォーマット"""
        from uuid import uuid4
        
        try:
            return ContextItem(
                chunk_id=context_data.get("chunk_id", str(uuid4())),
                document_id=context_data.get("document_id", str(uuid4())),
                content=context_data.get("content", ""),
                similarity_score=context_data.get("similarity_score", 0.0),
                metadata=context_data.get("metadata", {})
            )
        except Exception as e:
            logger.error(f"Error formatting context: {e}, data: {context_data}")
            # フォールバック値を返す
            return ContextItem(
                chunk_id=str(uuid4()),
                document_id=str(uuid4()),
                content="",
                similarity_score=0.0,
                metadata={}
            )
    
    def _calculate_confidence(self, contexts: List[Dict[str, Any]], llm_response: Dict[str, Any]) -> float:
        """回答の信頼度計算（簡易版）"""
        
        if not contexts:
            return 0.1  # コンテキストなしの場合は低信頼度
        
        # 最高類似度スコアベースの信頼度
        max_similarity = max([ctx.get("similarity_score", 0) for ctx in contexts])
        
        # コンテキスト数による調整
        context_bonus = min(len(contexts) * 0.1, 0.3)
        
        # 基本信頼度計算
        base_confidence = max_similarity * 0.7 + context_bonus
        
        return min(base_confidence, 0.95)  # 最大95%