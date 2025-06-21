from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import logging
import uuid
import os
import json
import time
from datetime import datetime
from typing import List, Optional

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Document Service",
    description="PDF文書のアップロード・管理サービス",
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

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "service": "document-service",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Document Service",
        "status": "running"
    }

# データディレクトリを確保
DATA_DIR = "/app/data"
FILES_DIR = os.path.join(DATA_DIR, "files")
METADATA_DIR = os.path.join(DATA_DIR, "metadata")

# ディレクトリ作成
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

@app.post("/api/v1/documents/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    document_name: Optional[str] = Form(None)
):
    """PDF文書をアップロード"""
    start_time = time.time()
    
    try:
        uploaded_files = []
        
        for file in files:
            # ファイル検証
            if not file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail="PDF files only")
            
            # ユニークなIDを生成
            document_id = str(uuid.uuid4())
            file_extension = os.path.splitext(file.filename)[1]
            saved_filename = f"{document_id}{file_extension}"
            
            # ファイル保存
            file_path = os.path.join(FILES_DIR, saved_filename)
            content = await file.read()
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            # メタデータ保存
            metadata = {
                "document_id": document_id,
                "filename": file.filename,
                "saved_filename": saved_filename,
                "file_size": len(content),
                "upload_date": datetime.now().isoformat(),
                "document_name": document_name or file.filename,
                "mime_type": "application/pdf"
            }
            
            metadata_path = os.path.join(METADATA_DIR, f"{document_id}.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            uploaded_files.append({
                "document_id": document_id,
                "filename": file.filename,
                "file_size": len(content)
            })
            
            logger.info(f"Uploaded file: {file.filename} -> {document_id}")
        
        upload_time = time.time() - start_time
        
        # 最初のファイルの情報を返す（フロントエンドとの互換性）
        if uploaded_files:
            first_file = uploaded_files[0]
            return {
                "success": True,
                "document_id": first_file["document_id"],
                "filename": first_file["filename"],
                "file_size": first_file["file_size"],
                "upload_time": upload_time,
                "total_files": len(uploaded_files)
            }
        else:
            raise HTTPException(status_code=400, detail="No files uploaded")
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/v1/documents")
async def get_documents():
    """文書一覧取得"""
    try:
        documents = []
        
        # メタデータディレクトリからファイル一覧を取得
        if os.path.exists(METADATA_DIR):
            for metadata_file in os.listdir(METADATA_DIR):
                if metadata_file.endswith('.json'):
                    metadata_path = os.path.join(METADATA_DIR, metadata_file)
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        documents.append(metadata)
        
        return {
            "success": True,
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Get documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get documents: {str(e)}")

@app.get("/api/v1/documents/{document_id}")
async def get_document(document_id: str):
    """特定文書の詳細取得"""
    try:
        metadata_path = os.path.join(METADATA_DIR, f"{document_id}.json")
        
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=404, detail="Document not found")
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        return {
            "success": True,
            "document": metadata
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Get document error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)