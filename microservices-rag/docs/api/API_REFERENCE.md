# 📚 API Reference

RAGマイクロサービスシステムの全APIエンドポイント仕様書です。

## 🌐 Base URLs

| Service | Base URL | Port |
|---------|----------|------|
| Document Service | `http://localhost:8001` | 8001 |
| Text Processing Service | `http://localhost:8002` | 8002 |
| Embedding Service | `http://localhost:8003` | 8003 |
| Vector Store Service | `http://localhost:8004` | 8004 |
| LLM Service | `http://localhost:8005` | 8005 |

## 📄 Document Service API

### Upload Document
PDFファイルをアップロードし、システムに登録します。

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data
```

**Parameters:**
- `files` (file, required): アップロードするPDFファイル
- `document_name` (string, optional): ドキュメント名

**Response:**
```json
{
  "success": true,
  "document_id": "uuid",
  "filename": "document.pdf",
  "file_size": 1024,
  "upload_time": 1.23
}
```

### Get Document
ドキュメント情報を取得します。

```http
GET /api/v1/documents/{document_id}
```

**Response:**
```json
{
  "document_id": "uuid",
  "filename": "document.pdf",
  "file_size": 1024,
  "upload_date": "2024-01-01T00:00:00Z",
  "metadata": {}
}
```

## ✂️ Text Processing Service API

### Process Text
テキストを分割してチャンクを作成します。

```http
POST /api/v1/text/process
Content-Type: application/json
```

**Request Body:**
```json
{
  "document_id": "uuid",
  "text": "処理するテキスト",
  "config": {
    "chunk_size": 200,
    "chunk_overlap": 50
  }
}
```

**Response:**
```json
{
  "success": true,
  "document_id": "uuid",
  "chunks": [
    {
      "chunk_id": "uuid",
      "content": "チャンクのテキスト",
      "chunk_index": 0,
      "start_position": 0,
      "end_position": 200,
      "metadata": {}
    }
  ],
  "total_chunks": 5,
  "processing_time": 0.123
}
```

### Get Chunks
ドキュメントのチャンク一覧を取得します。

```http
GET /api/v1/text/chunks/{document_id}?limit=100&offset=0
```

**Response:**
```json
{
  "success": true,
  "document_id": "uuid",
  "chunks": [...],
  "total_chunks": 5,
  "limit": 100,
  "offset": 0
}
```

## 🧮 Embedding Service API

### Generate Embeddings
テキストの埋め込みベクトルを生成します。

```http
POST /api/v1/embeddings/generate
Content-Type: application/json
```

**Request Body:**
```json
{
  "texts": ["テキスト1", "テキスト2"],
  "document_id": "uuid",
  "config": {
    "model_name": "all-MiniLM-L6-v2",
    "normalize_embeddings": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "embeddings": [
    {
      "embedding_id": "uuid",
      "chunk_id": "uuid",
      "vector": [0.1, 0.2, ...],
      "dimension": 384,
      "model_name": "all-MiniLM-L6-v2"
    }
  ],
  "total_count": 2,
  "processing_time": 2.45
}
```

### Get Embeddings
保存された埋め込みを取得します。

```http
GET /api/v1/embeddings/{document_id}
```

**Response:**
```json
{
  "success": true,
  "embeddings": [...],
  "total_count": 10
}
```

## 🔍 Vector Store Service API

### Create Index
ベクトルインデックスを作成します。

```http
POST /api/v1/vector/index
Content-Type: application/json
```

**Request Body:**
```json
{
  "document_id": "uuid",
  "embedding_vectors": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
  "embedding_ids": ["uuid1", "uuid2"],
  "chunk_ids": ["uuid1", "uuid2"]
}
```

**Response:**
```json
{
  "document_id": "uuid",
  "indexed_count": 2,
  "index_size_mb": 0.1,
  "creation_time": 0.05,
  "index_info": {
    "type": "IVFFlat",
    "metric": "IP",
    "dimension": 384
  }
}
```

### Search Vectors
ベクトル検索を実行します。

```http
POST /api/v1/vector/search
Content-Type: application/json
```

**Request Body:**
```json
{
  "document_id": "uuid",
  "query_vector": [0.1, 0.2, ...],
  "top_k": 5,
  "similarity_threshold": 0.7
}
```

**Response:**
```json
{
  "results": [
    {
      "embedding_id": "uuid",
      "chunk_id": "uuid",
      "similarity_score": 0.95,
      "metadata": {}
    }
  ],
  "total_found": 3,
  "search_time": 0.01
}
```

### List Indexes
インデックス一覧を取得します。

```http
GET /api/v1/vector/indexes
```

**Response:**
```json
{
  "indexes": [
    {
      "document_id": "uuid",
      "total_vectors": 100,
      "dimension": 384,
      "index_type": "IVFFlat",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total_count": 5
}
```

## 🤖 LLM Service API

### Question Answering
質問応答を実行します（RAGパイプライン統合）。

```http
POST /api/v1/qa
Content-Type: application/json
```

**Request Body:**
```json
{
  "question": "マイクロサービスについて教えて",
  "document_id": "uuid",
  "context_length": 3,
  "similarity_threshold": 0.3,
  "model": "nvidia/llama-3.1-nemotron-70b-instruct",
  "max_tokens": 1000,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "success": true,
  "question": "マイクロサービスについて教えて",
  "answer": "マイクロサービスアーキテクチャは...",
  "confidence": 0.85,
  "contexts_used": [
    {
      "chunk_id": "uuid",
      "content": "関連するテキスト",
      "similarity_score": 0.92
    }
  ],
  "total_contexts_found": 3,
  "model_used": "nvidia/llama-3.1-nemotron-70b-instruct",
  "processing_time": 3.45,
  "token_usage": {
    "prompt_tokens": 150,
    "completion_tokens": 200,
    "total_tokens": 350
  }
}
```

### Generate Response
NVIDIA Cloud LLMで直接応答生成します。

```http
POST /api/v1/generate
Content-Type: application/json
```

**Request Body:**
```json
{
  "prompt": "質問またはプロンプト",
  "context": "関連するコンテキスト",
  "model": "nvidia/llama-3.1-nemotron-70b-instruct",
  "max_tokens": 1000,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "success": true,
  "answer": "生成された応答",
  "model_used": "nvidia/llama-3.1-nemotron-70b-instruct",
  "token_usage": {
    "prompt_tokens": 50,
    "completion_tokens": 100,
    "total_tokens": 150
  },
  "processing_time": 2.1
}
```

### Test Connection
NVIDIA Cloud APIの接続をテストします。

```http
GET /api/v1/test
```

**Response:**
```json
{
  "success": true,
  "status": "connected",
  "api_key_status": "valid",
  "available_models": [
    "nvidia/llama-3.1-nemotron-70b-instruct"
  ]
}
```

## 🏥 Health Check Endpoints

全サービス共通のヘルスチェックエンドポイント：

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "document-service",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 📝 Error Responses

エラーレスポンスの共通フォーマット：

```json
{
  "detail": "エラーメッセージ",
  "error_code": "error_type",
  "timestamp": "2024-01-01T00:00:00Z",
  "service": "service-name"
}
```

### 一般的なHTTPステータスコード

| Code | Description |
|------|-------------|
| 200 | 成功 |
| 400 | 不正なリクエスト |
| 404 | リソースが見つからない |
| 422 | バリデーションエラー |
| 500 | サーバー内部エラー |

## 🔐 Authentication

現在のバージョンでは基本認証は実装されていません。本番環境では以下の実装を推奨：

- JWT トークンベース認証
- API キー管理
- Rate limiting
- CORS 設定

## 📊 Rate Limiting

現在は実装されていませんが、本番環境では推奨：

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## 🧪 Testing APIs

全APIは以下のツールでテスト可能：

- **Swagger UI**: `http://localhost:{port}/docs`
- **ReDoc**: `http://localhost:{port}/redoc`
- **curl**: コマンドライン
- **Postman**: GUI クライアント