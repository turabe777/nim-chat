# RAG マイクロサービス フロントエンド

React + TypeScript + Tailwind CSS で構築されたRAGシステムのWeb UI。

## 🚀 機能

- **ドキュメント管理**: PDFファイルのアップロード・管理
- **質問応答チャット**: アップロードした文書に対する自然言語での質問応答
- **サービス監視**: マイクロサービスの稼働状況確認
- **設定管理**: LLMパラメータとRAG設定の調整

## 🛠️ 技術スタック

- **Framework**: React 18 + TypeScript
- **Styling**: Tailwind CSS
- **Build Tool**: Vite
- **HTTP Client**: Axios
- **UI Components**: Lucide React Icons
- **File Upload**: React Dropzone
- **Notifications**: React Hot Toast
- **Container**: Docker + nginx

## 📦 開発環境セットアップ

### 前提条件

- Node.js 18+
- npm または yarn

### インストール

```bash
# 依存関係のインストール
npm install

# 環境変数設定
cp .env.example .env

# 開発サーバー起動
npm run dev
```

アプリケーションは `http://localhost:3000` で起動します。

## 🏗️ ビルド

```bash
# プロダクションビルド
npm run build

# ビルド結果をプレビュー
npm run preview
```

## 🐳 Docker

```bash
# Dockerイメージのビルド
docker build -t rag-frontend .

# コンテナ実行
docker run -p 3000:3000 rag-frontend
```

## 📁 プロジェクト構造

```
frontend/
├── src/
│   ├── components/          # 再利用可能なコンポーネント
│   │   ├── Layout/         # レイアウトコンポーネント
│   │   ├── Upload/         # ファイルアップロード
│   │   ├── Chat/           # チャットインターフェース
│   │   └── Status/         # サービス状態表示
│   ├── pages/              # ページコンポーネント
│   ├── services/           # API通信
│   ├── hooks/              # カスタムフック
│   ├── types/              # TypeScript型定義
│   └── utils/              # ユーティリティ
├── public/                 # 静的ファイル
├── Dockerfile             # Docker設定
├── nginx.conf             # nginx設定
└── package.json           # 依存関係定義
```

## 🔧 主要コンポーネント

### DocumentUpload
PDFファイルのドラッグ&ドロップアップロード機能

### ChatInterface
質問応答チャット。コンテキスト表示、信頼度表示機能付き

### ServiceStatus
マイクロサービスの稼働状況をリアルタイム監視

## 🌐 API統合

フロントエンドは以下のマイクロサービスと通信:

- **Document Service** (8001): ファイルアップロード
- **LLM Service** (8005): 質問応答
- **全サービス**: ヘルスチェック

## 📱 レスポンシブデザイン

Tailwind CSSによりモバイルファーストで設計:

- デスクトップ: フル機能表示
- タブレット: 適応レイアウト
- モバイル: コンパクト表示

## 🔐 セキュリティ

- nginx セキュリティヘッダー設定
- XSS保護
- CSRF保護 (将来実装予定)
- API認証 (将来実装予定)

## 🧪 テスト

```bash
# 型チェック
npm run type-check

# リント
npm run lint

# 統合テスト (将来実装予定)
npm run test
```

## 🚀 デプロイ

1. Docker Composeでの起動:
```bash
docker-compose up -d
```

2. 単体での起動:
```bash
docker build -t rag-frontend .
docker run -p 3000:3000 rag-frontend
```

## 📋 環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `VITE_API_BASE_URL` | バックエンドAPIのベースURL | `http://localhost:8001` |

## 🔄 開発ワークフロー

1. バックエンドサービスを起動
2. フロントエンド開発サーバーを起動
3. ブラウザで `http://localhost:3000` にアクセス
4. Viteのホットリロードで開発

## 📞 トラブルシューティング

### API接続エラー
- バックエンドサービスが起動しているか確認
- `VITE_API_BASE_URL` が正しく設定されているか確認

### ビルドエラー
- Node.js バージョンが18+か確認
- `node_modules` を削除して再インストール

### Docker関連
- Dockerサービスが起動しているか確認
- ポート3000が他のプロセスで使用されていないか確認