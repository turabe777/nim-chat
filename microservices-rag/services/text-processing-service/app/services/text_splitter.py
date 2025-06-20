"""
テキスト分割サービス

テキストを設定可能なサイズ・オーバーラップでチャンクに分割
"""

import re
from typing import List, Dict, Any, Optional
from uuid import UUID
import time

from shared.models.text_processing import TextChunk, TextProcessingConfig
from shared.utils.logging import get_logger
from shared.utils.exceptions import ProcessingError

logger = get_logger(__name__)


class TextSplitterService:
    """テキスト分割サービス"""
    
    def __init__(self):
        self.default_separators = ["\n\n", "\n", "。", ".", " ", ""]
    
    async def split_text(
        self, 
        document_id: UUID, 
        text: str, 
        config: TextProcessingConfig
    ) -> List[TextChunk]:
        """テキストをチャンクに分割"""
        
        start_time = time.time()
        logger.info(f"📄 Splitting text for document {document_id} (length: {len(text)})")
        
        try:
            # テキスト前処理
            processed_text = self._preprocess_text(text, config)
            
            # チャンク分割
            chunks = self._split_into_chunks(
                document_id=document_id,
                text=processed_text,
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                separators=config.separators or self.default_separators
            )
            
            # 最小サイズフィルタリング
            filtered_chunks = [
                chunk for chunk in chunks 
                if len(chunk.content) >= config.min_chunk_size
            ]
            
            processing_time = time.time() - start_time
            logger.info(f"✅ Split into {len(filtered_chunks)} chunks in {processing_time:.2f}s")
            
            return filtered_chunks
            
        except Exception as e:
            raise ProcessingError("text_splitting", f"Failed to split text: {str(e)}")
    
    def _preprocess_text(self, text: str, config: TextProcessingConfig) -> str:
        """テキストの前処理"""
        
        if config.remove_whitespace:
            # 余分な空白を削除
            text = re.sub(r'\s+', ' ', text)
        
        if config.remove_empty_lines:
            # 空行を削除
            lines = text.split('\n')
            text = '\n'.join(line for line in lines if line.strip())
        
        return text.strip()
    
    def _split_into_chunks(
        self,
        document_id: UUID,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
        separators: List[str]
    ) -> List[TextChunk]:
        """テキストを再帰的にチャンクに分割"""
        
        chunks = []
        current_pos = 0
        chunk_index = 0
        
        while current_pos < len(text):
            # チャンクの終了位置を計算
            end_pos = min(current_pos + chunk_size, len(text))
            
            # 適切な分割点を探す
            best_split_pos = self._find_best_split_position(
                text, current_pos, end_pos, separators
            )
            
            # チャンク作成
            chunk_content = text[current_pos:best_split_pos].strip()
            
            if chunk_content:  # 空でないチャンクのみ追加
                chunk = TextChunk(
                    document_id=document_id,
                    content=chunk_content,
                    chunk_index=chunk_index,
                    start_position=current_pos,
                    end_position=best_split_pos,
                    metadata={
                        "length": len(chunk_content),
                        "separator_used": self._get_separator_used(text, best_split_pos, separators)
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # 次のチャンクの開始位置（オーバーラップを考慮）
            next_start = max(current_pos + 1, best_split_pos - chunk_overlap)
            
            # 無限ループ防止
            if next_start <= current_pos:
                next_start = current_pos + 1
            
            current_pos = next_start
        
        return chunks
    
    def _find_best_split_position(
        self, 
        text: str, 
        start_pos: int, 
        max_end_pos: int, 
        separators: List[str]
    ) -> int:
        """最適な分割位置を探す"""
        
        if max_end_pos >= len(text):
            return len(text)
        
        # 各セパレーターで最適な分割点を探す
        for separator in separators:
            if not separator:  # 空文字セパレーター（文字単位分割）
                return max_end_pos
            
            # セパレーター位置を後ろから探す
            search_start = max(start_pos, max_end_pos - len(separator))
            pos = text.rfind(separator, search_start, max_end_pos)
            
            if pos != -1 and pos > start_pos:
                return pos + len(separator)
        
        # セパレーターが見つからない場合は最大位置で分割
        return max_end_pos
    
    def _get_separator_used(self, text: str, pos: int, separators: List[str]) -> str:
        """使用されたセパレーターを特定"""
        
        for separator in separators:
            if not separator:
                continue
            if pos >= len(separator) and text[pos-len(separator):pos] == separator:
                return separator
        
        return "none"
    
    async def get_text_statistics(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """テキスト統計を計算"""
        
        if not chunks:
            return {
                "total_chunks": 0,
                "total_characters": 0,
                "average_chunk_size": 0.0,
                "min_chunk_size": 0,
                "max_chunk_size": 0
            }
        
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "total_characters": sum(chunk_sizes),
            "average_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes)
        }