from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import PyPDF2
import io

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Text Processing Service",
    description="テキスト分割・チャンク化サービス",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 他のサービスのURL
DOCUMENT_SERVICE_URL = "http://document-service:8001"
EMBEDDING_SERVICE_URL = "http://embedding-service:8003"
VECTOR_STORE_SERVICE_URL = "http://vector-store-service:8004"

# リクエスト・レスポンスモデル
class ProcessRequest(BaseModel):
    document_id: str
    chunk_size: int = 500
    chunk_overlap: int = 50

class TextChunk(BaseModel):
    chunk_id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = {}

class ProcessResponse(BaseModel):
    success: bool
    document_id: str
    chunks_created: int
    embeddings_generated: int
    vectors_stored: int
    processing_time: float
    message: str

def extract_text_from_pdf(file_path: str) -> str:
    """PDFファイルからテキストを抽出"""
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF extraction error: {str(e)}")

def split_text_into_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """テキストをチャンクに分割"""
    if not text.strip():
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # チャンクが文字制限を超える場合、文の区切りで調整
        if end < len(text):
            # 句読点で区切りを探す
            for punct in ['。', '！', '？', '.', '!', '?']:
                punct_pos = text.rfind(punct, start, end)
                if punct_pos != -1:
                    end = punct_pos + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - chunk_overlap
        if start >= len(text):
            break
    
    return chunks

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "service": "text-processing-service",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Text Processing Service",
        "status": "running"
    }

@app.post("/api/v1/text/process", response_model=ProcessResponse)
async def process_document(request: ProcessRequest):
    """文書を処理してベクトル化"""
    import time
    start_time = time.time()
    
    try:
        document_id = request.document_id
        
        # 1. 文書サービスから文書情報を取得
        async with httpx.AsyncClient() as client:
            doc_response = await client.get(
                f"{DOCUMENT_SERVICE_URL}/api/v1/documents/{document_id}",
                timeout=30.0
            )
            doc_response.raise_for_status()
            doc_data = doc_response.json()
            
            if not doc_data["success"]:
                raise HTTPException(status_code=404, detail="Document not found")
            
            document_info = doc_data["document"]
            file_path = f"/app/data/files/{document_info['saved_filename']}"
            
            # 2. PDFからテキスト抽出
            logger.info(f"Extracting text from: {file_path}")
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
            
            text_content = extract_text_from_pdf(file_path)
            
            if not text_content.strip():
                raise HTTPException(status_code=400, detail="No text content extracted from PDF")
            
            logger.info(f"Extracted {len(text_content)} characters from PDF")
            
            # 3. テキストをチャンクに分割
            chunks = split_text_into_chunks(
                text_content, 
                request.chunk_size, 
                request.chunk_overlap
            )
            
            if not chunks:
                raise HTTPException(status_code=400, detail="No text chunks created")
            
            logger.info(f"Created {len(chunks)} text chunks")
            
            # 4. 埋め込み生成
            logger.info("Generating embeddings...")
            embedding_response = await client.post(
                f"{EMBEDDING_SERVICE_URL}/api/v1/embeddings/generate",
                json={
                    "texts": chunks,
                    "document_id": document_id,
                    "config": {}
                },
                timeout=60.0
            )
            embedding_response.raise_for_status()
            embedding_data = embedding_response.json()
            
            if not embedding_data["success"]:
                raise HTTPException(status_code=500, detail="Failed to generate embeddings")
            
            embeddings = embedding_data["embeddings"]
            logger.info(f"Generated {len(embeddings)} embeddings")
            
            # 5. ベクトルストアに保存
            logger.info("Storing vectors...")
            vectors = []
            for i, embedding in enumerate(embeddings):
                vectors.append({
                    "chunk_id": f"{document_id}_chunk_{i:04d}",
                    "vector": embedding["vector"],
                    "metadata": {
                        "document_id": document_id,
                        "chunk_index": i,
                        "content_preview": chunks[i][:100] + "..." if len(chunks[i]) > 100 else chunks[i],
                        "filename": document_info["filename"]
                    }
                })
            
            vector_response = await client.post(
                f"{VECTOR_STORE_SERVICE_URL}/api/v1/vector/store",
                json={
                    "document_id": document_id,
                    "vectors": vectors
                },
                timeout=60.0
            )
            vector_response.raise_for_status()
            vector_data = vector_response.json()
            
            if not vector_data["success"]:
                raise HTTPException(status_code=500, detail="Failed to store vectors")
            
            processing_time = time.time() - start_time
            
            logger.info(f"Document processing completed: {document_id} in {processing_time:.2f}s")
            
            return ProcessResponse(
                success=True,
                document_id=document_id,
                chunks_created=len(chunks),
                embeddings_generated=len(embeddings),
                vectors_stored=len(vectors),
                processing_time=processing_time,
                message=f"Successfully processed document with {len(chunks)} chunks"
            )
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error during processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Service communication error: {str(e)}")
    except Exception as e:
        logger.error(f"Document processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/api/v1/text/chunks/{document_id}")
async def get_document_chunks(document_id: str):
    """文書のチャンク情報を取得"""
    try:
        async with httpx.AsyncClient() as client:
            # ベクトルストアから文書情報を取得
            stats_response = await client.get(
                f"{VECTOR_STORE_SERVICE_URL}/api/v1/vector/stats",
                timeout=30.0
            )
            stats_response.raise_for_status()
            stats_data = stats_response.json()
            
            if document_id in stats_data["documents"]:
                return {
                    "success": True,
                    "document_id": document_id,
                    "total_chunks": stats_data["documents"][document_id],
                    "message": f"Document has {stats_data['documents'][document_id]} chunks"
                }
            else:
                return {
                    "success": False,
                    "document_id": document_id,
                    "total_chunks": 0,
                    "message": "Document not processed or not found"
                }
                
    except Exception as e:
        logger.error(f"Error getting chunks info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get chunks info: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)