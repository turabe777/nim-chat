# 🚀 RAG マイクロサービス システム

高性能なRetrieval-Augmented Generation (RAG) システムをマイクロサービスアーキテクチャで実装したプロジェクトです。

## 📋 概要

このシステムは、PDFドキュメントからの質問応答を行うRAGシステムを5つの独立したマイクロサービスで構成しています。各サービスは特定の機能に特化し、Docker Composeで簡単にデプロイできます。

## 🏗️ アーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Document Service│────│Text Processing  │────│ Embedding       │
│ (8001)          │    │ Service (8002)  │    │ Service (8003)  │
│                 │    │                 │    │                 │
│ • PDF管理       │    │ • チャンク分割  │    │ • ベクトル生成  │
│ • メタデータ    │    │ • テキスト処理  │    │ • 埋め込み管理  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐
│ Vector Store    │────│ LLM Service     │
│ Service (8004)  │    │ (8005)          │
│                 │    │                 │
│ • ベクトル検索  │    │ • 質問応答      │
│ • FAISS管理     │    │ • NVIDIA Cloud  │
└─────────────────┘    └─────────────────┘
```

## 🛠️ サービス構成

| サービス | ポート | 機能 | 技術スタック |
|----------|--------|------|-------------|
| **Document Service** | 8001 | PDFアップロード・管理 | FastAPI + PyPDF2 |
| **Text Processing Service** | 8002 | テキスト分割・チャンク化 | FastAPI + Python |
| **Embedding Service** | 8003 | ベクトル埋め込み生成 | FastAPI + SentenceTransformers |
| **Vector Store Service** | 8004 | ベクトル検索・インデックス | FastAPI + FAISS |
| **LLM Service** | 8005 | 質問応答・RAG統合 | FastAPI + NVIDIA Cloud |

## 🚀 クイックスタート

### 前提条件

- Docker & Docker Compose
- NVIDIA API Key (環境変数 `NVIDIA_API_KEY` に設定)

### 1. プロジェクトクローン

```bash
git clone <repository-url>
cd microservices-rag
```

### 2. 環境変数設定

```bash
export NVIDIA_API_KEY="your_nvidia_api_key_here"
```

### 3. サービス起動

```bash
docker-compose up -d
```

### 4. 動作確認

```bash
# 全サービスの健全性確認
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
```

## 📚 API使用例

### 1. PDFドキュメントアップロード

```bash
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
  -F "files=@your_document.pdf" \
  -F "document_name=サンプル文書"
```

### 2. 質問応答

```bash
curl -X POST "http://localhost:8005/api/v1/qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "この文書について教えてください",
    "document_id": "document-uuid-here",
    "context_length": 3,
    "similarity_threshold": 0.3
  }'
```

## 🔧 開発環境

### ローカル開発

各サービスは独立して開発・テストできます：

```bash
# 個別サービスの起動例
cd services/document-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### テスト実行

```bash
# ユニットテスト
python -m pytest tests/unit/

# 統合テスト
python -m pytest tests/integration/

# E2Eテスト
python -m pytest tests/e2e/
```

## 📁 プロジェクト構造

```
microservices-rag/
├── services/                    # マイクロサービス
│   ├── document-service/        # Document Service
│   ├── text-processing-service/ # Text Processing Service
│   ├── embedding-service/       # Embedding Service
│   ├── vector-store-service/    # Vector Store Service
│   └── llm-service/            # LLM Service
├── shared/                     # 共通ライブラリ
│   ├── models/                 # Pydanticモデル
│   └── utils/                  # ユーティリティ
├── tests/                      # テストスイート
│   ├── unit/                   # ユニットテスト
│   ├── integration/            # 統合テスト
│   ├── e2e/                    # E2Eテスト
│   └── data/                   # テストデータ
├── docker-compose.yml          # Docker Compose設定
└── README.md                   # このファイル
```

## 🔐 セキュリティ

- NVIDIA API Keyは環境変数で管理
- サービス間通信はDocker内部ネットワーク使用
- 本番環境では適切な認証・認可の実装を推奨

## 📊 モニタリング

各サービスには以下のエンドポイントが用意されています：

- `/health` - ヘルスチェック
- `/docs` - API仕様（Swagger UI）
- `/redoc` - API仕様（ReDoc）

## 🤝 貢献

1. Forkしてブランチを作成
2. 変更を実装
3. テストを実行
4. Pull Requestを送信

## 📄 ライセンス

MIT License

## 🔗 関連リンク

- [NVIDIA Cloud API](https://docs.api.nvidia.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FAISS Documentation](https://faiss.ai/)