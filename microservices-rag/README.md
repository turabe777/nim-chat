# 🚀 RAG マイクロサービス システム

高性能なRetrieval-Augmented Generation (RAG) システムをマイクロサービスアーキテクチャで実装。NIM Local/NVIDIA Cloud切り替え対応の完全統合システムです。

## 📋 概要

PDFドキュメントからの質問応答を行うRAGシステムを6つの独立したマイクロサービス + Webフロントエンドで構成。NVIDIA NIM Local、NVIDIA Cloud API、Mockモードの動的切り替えに対応し、実用レベルのWebUIを提供します。

## 🏗️ アーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Document Service│────│Text Processing  │────│ Embedding       │
│ (8001)          │    │ Service (8002)  │    │ Service (8003)  │
│                 │    │                 │    │                 │
│ • PDF管理       │    │ • チャンク分割  │    │ • ベクトル生成  │
│ • ダウンロード  │    │ • テキスト処理  │    │ • SentenceT     │
│ • メタデータ    │    │ • 動的制限      │    │ • 384次元埋込   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Vector Store    │────│ LLM Service     │────│ Frontend        │
│ Service (8004)  │    │ (8005)          │    │ (3000)          │
│                 │    │                 │    │                 │
│ • FAISS検索     │    │ • 3モード切替   │    │ • React+TypeS   │
│ • グローバル検索│    │ • NIM/Cloud/Mock│    │ • モード切替UI  │
│ • 類似度計算    │    │ • 推奨モデル取得│    │ • 参考文書表示  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ サービス構成

| サービス | ポート | 機能 | 技術スタック | バージョン |
|----------|--------|------|-------------|------------|
| **Document Service** | 8001 | PDF管理・ダウンロード | FastAPI + PyPDF2 | 1.0.0 |
| **Text Processing Service** | 8002 | 動的制限テキスト処理 | FastAPI + Python | 1.0.0-lightweight |
| **Embedding Service** | 8003 | 384次元埋め込み生成 | FastAPI + SentenceTransformers | 1.0.0 |
| **Vector Store Service** | 8004 | FAISS検索・グローバル検索 | FastAPI + FAISS | 1.0.0 |
| **LLM Service** | 8005 | NIM/Cloud切り替え・QA | FastAPI + NVIDIA APIs | 1.2.0-mode-switching |
| **Frontend** | 3000 | WebUI・モード切り替え | React + TypeScript + Tailwind | 1.0.0 |

## 🎮 主要機能

### ✅ 完全実装済み機能

1. **エンドツーエンドRAGパイプライン**: PDF→処理→埋め込み→検索→回答
2. **複数文書横断検索**: 全文書から関連コンテキスト抽出
3. **NVIDIA LLM統合**: Cloud + Local NIM対応（実際の高品質回答）
4. **参考文書リンク**: チャット画面での文書ダウンロード
5. **完全ドキュメント管理**: アップロード・一覧・削除・ダウンロード
6. **LLMモード手動切り替え**: NIM Local ⇄ NVIDIA Cloud ⇄ Mock
7. **動的モデル名表示**: 現在使用中のモデルリアルタイム表示
8. **完全WebUI**: タブ式インターフェース・ドロップダウン選択

### 🎯 LLMモード

| モード | 説明 | 設定要件 | 推奨モデル |
|--------|------|----------|------------|
| **NIM Local** | ローカルNIMエンドポイント | `NIM_LOCAL_ENDPOINT` | 自動検出 |
| **NVIDIA Cloud** | NVIDIA Cloud API | `NVIDIA_API_KEY` | nvidia/llama-3.1-nemotron-70b-instruct |
| **Mock** | モック応答 | なし | mock-llm-model |
| **Auto** | 自動判定（Local→Cloud→Mock） | 利用可能なもの | 動的選択 |

## 🚀 クイックスタート

### 前提条件

- Docker & Docker Compose
- NVIDIA API Key（Cloud使用時）
- ローカルNIMエンドポイント（Local使用時、例: http://10.19.55.122:8000）

### 1. プロジェクトクローン

```bash
git clone https://github.com/turabe777/nim-chat.git
cd nim-chat/microservices-rag
git checkout feature/microservices-architecture
```

### 2. 環境変数設定

```bash
# NVIDIA Cloud API使用の場合
export NVIDIA_API_KEY="your_nvidia_api_key_here"

# ローカルNIM使用の場合（docker-compose-complete.ymlを編集）
# NIM_LOCAL_ENDPOINT=http://your-nim-ip:8000
```

### 3. システム起動

```bash
# 完全システム起動
docker-compose -f docker-compose-complete.yml up -d
```

### 4. WebUI アクセス

```
http://localhost:3000
```

### 5. 動作確認

```bash
# 全サービスの健全性確認
curl http://localhost:8001/health  # Document Service
curl http://localhost:8002/health  # Text Processing
curl http://localhost:8003/health  # Embedding Service
curl http://localhost:8004/health  # Vector Store
curl http://localhost:8005/health  # LLM Service
curl http://localhost:3000         # Frontend

# 現在のLLMモード確認
curl http://localhost:8005/api/v1/mode/current
```

## 📱 Web UI 使用方法

### 1. ドキュメント管理
- **アップロード**: PDF拖拽上传或点击选择
- **一覧表示**: アップロード済み文書の管理
- **削除**: 不要な文書の削除
- **ダウンロード**: 元PDFファイルの取得

### 2. 質問応答チャット
- **文書選択**: 質問対象文書を選択
- **質問入力**: 自然言語で質問
- **モード切り替え**: 右上のボタンでNIM Local/Cloud切り替え
- **参考文書**: 回答下の青いボックスから文書ダウンロード

### 3. モード切り替え
- **Auto**: 自動判定（Local→Cloud→Mock優先順位）
- **NIM Local**: ローカルNIM強制使用
- **NVIDIA Cloud**: クラウドAPI強制使用
- **Mock**: モック応答（開発・テスト用）

## 📚 API 使用例

### LLMモード管理

```bash
# 現在のモード確認
curl http://localhost:8005/api/v1/mode/current

# NVIDIA Cloudに切り替え
curl -X POST http://localhost:8005/api/v1/mode/switch \
  -H "Content-Type: application/json" \
  -d '{"mode": "nvidia_cloud"}'

# 推奨モデル取得
curl http://localhost:8005/api/v1/models/recommended
```

### ドキュメント管理

```bash
# PDFアップロード
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
  -F "files=@your_document.pdf" \
  -F "document_name=サンプル文書"

# 文書一覧取得
curl http://localhost:8001/api/v1/documents

# 文書ダウンロード
curl http://localhost:8001/api/v1/documents/{id}/download
```

### 質問応答

```bash
# 単一文書QA
curl -X POST "http://localhost:8005/api/v1/qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "この文書について教えてください",
    "document_id": "document-uuid-here",
    "context_length": 3,
    "similarity_threshold": 0.3,
    "model": "tokyotech-llm/llama-3.1-swallow-8b-instruct-v0.1"
  }'

# 複数文書横断QA
curl -X POST "http://localhost:8005/api/v1/qa/multi" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "機械学習について",
    "document_ids": [],
    "context_length": 5
  }'
```

## 📁 プロジェクト構造

```
microservices-rag/
├── services/                          # マイクロサービス
│   ├── document-service/              # Document Service
│   │   ├── app/main.py               
│   │   ├── data/                     # アップロードファイル
│   │   └── Dockerfile
│   ├── text-processing-service/       # Text Processing Service
│   ├── embedding-service/             # Embedding Service  
│   ├── vector-store-service/          # Vector Store Service
│   └── llm-service/                   # LLM Service
├── frontend/                          # React Frontend
│   ├── src/components/
│   │   ├── Chat/ChatInterface.tsx    # チャット画面
│   │   ├── Document/DocumentManager.tsx # 文書管理
│   │   └── Mode/ModeSwitch.tsx       # モード切り替え
│   └── Dockerfile
├── shared/                            # 共通ファイル（ボリューム共有）
├── docker-compose-complete.yml       # 完全システム構成
├── WORK_LOG_FINAL.md                 # 詳細作業ログ
└── README.md                         # このファイル
```

## 🔧 開発・テスト

### ローカル開発

```bash
# 個別サービス開発
cd services/llm-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload

# フロントエンド開発
cd frontend
npm install
npm run dev
```

### テストコマンド

```bash
# システム状態確認
docker-compose -f docker-compose-complete.yml ps

# エンドツーエンドテスト
curl -X POST http://localhost:8005/api/v1/qa \
  -H "Content-Type: application/json" \
  -d '{
    "question": "JupyterLabの使用方法について教えてください",
    "document_id": "8ae15aca-3e1f-4c4c-beaf-359b4dc2fff7"
  }'
```

## ⚡ パフォーマンス指標

- **文書アップロード**: 1-3秒（PDF依存）
- **テキスト処理**: 0.5秒（軽量版）
- **埋め込み生成**: <1秒（初回除く）
- **ベクトル検索**: 0.1秒
- **LLM応答**: 5-45秒（NIM Local: ~44秒、NVIDIA Cloud: ~5-20秒）
- **類似度スコア**: 0.38-0.30（semantic search）
- **回答信頼度**: 85%（コンテキスト有）

## 🔐 セキュリティ

- NVIDIA API Keyは環境変数で管理
- サービス間通信はDocker内部ネットワーク使用
- NIMローカルエンドポイントは内部ネットワーク推奨
- 本番環境では適切な認証・認可の実装を推奨

## 📊 モニタリング

各サービスのエンドポイント：
- `/health` - ヘルスチェック・モード情報
- `/docs` - API仕様（Swagger UI）
- `/api/v1/mode/current` - LLMモード状態（8005のみ）

## 🔧 トラブルシューティング

### よくある問題

1. **NIM Local接続エラー**: エンドポイントのIP・ポート確認
2. **NVIDIA Cloud API エラー**: API Key設定確認
3. **モデル名不一致**: `/api/v1/models/recommended`で確認
4. **UI切り替えエラー**: ブラウザ更新・開発者ツール確認

### ログ確認

```bash
# サービスログ確認
docker logs rag-llm-service
docker logs rag-frontend

# コンテナ状態確認
docker-compose -f docker-compose-complete.yml ps
```

## 🤝 貢献

1. Forkしてブランチを作成
2. 変更を実装・テスト
3. WORK_LOG_FINAL.mdを更新
4. Pull Requestを送信

## 📄 ライセンス

MIT License

## 🔗 関連リンク

- [NVIDIA Cloud API](https://docs.api.nvidia.com/)
- [NVIDIA NIM](https://developer.nvidia.com/nim)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [FAISS Documentation](https://faiss.ai/)
- [SentenceTransformers](https://www.sbert.net/)

---

**🎯 現在のステータス**: 完全機能統合システム完成  
**⚡ 最新機能**: NIM Local/NVIDIA Cloud手動切り替え・動的モデル表示  
**🚀 次回目標**: ストリーミング応答・キャッシュ機能実装