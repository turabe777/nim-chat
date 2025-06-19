# RAG (Retrieval-Augmented Generation) アプリケーション

PDFファイルを基にしたRAGシステム。NVIDIA Cloud LLMを使用して質問応答を行います。

## 🚀 起動方法

### 1. 環境設定
```bash
# NVIDIA API Keyを設定（必須）
export NVIDIA_API_KEY=your_api_key_here

# NIM使用時（オプション）
export NVIDIA_NIM_ENDPOINT=http://localhost:8000/v1
```

### 2. 依存関係のインストール
```bash
uv sync
```

### 3. アプリケーション起動

#### 🌐 Web UI（推奨）
```bash
uv run streamlit run streamlit_app.py
```
ブラウザで http://localhost:8501 にアクセス

#### 💻 コマンドライン版
```bash
uv run python main.py
```

## 📱 Web UIの機能

### 主要機能
- **📄 PDFファイル管理**: ドラッグ&ドロップでアップロード
- **💬 チャット形式の質問応答**: リアルタイム会話
- **📊 ソース情報表示**: 回答根拠の可視化
- **🌐 エンドポイント切り替え**: NGC/NIM/カスタムエンドポイント対応
- **🔍 接続テスト**: エンドポイント接続状況の確認
- **🤖 モデル選択**: 利用可能モデルからの選択
- **⚙️ 設定調整**: チャンクサイズ、検索結果数の調整

### 使用手順
1. **エンドポイント設定**: NGC/NIM/カスタムから選択
2. **接続テスト**: エンドポイントの動作確認
3. **PDFアップロード**: サイドバーからファイルをアップロード
4. **システム初期化**: 「RAGシステムを初期化」ボタンをクリック  
5. **質問入力**: チャット欄にPythonに関する質問を入力
6. **回答確認**: AI回答とソース情報を確認

## 🛠️ システム構成

### ファイル構成
- `streamlit_app.py`: Webユーザーインターフェース
- `main.py`: コマンドライン版
- `rag_app.py`: RAGシステムの実装
- `pdfs/`: PDFファイル格納フォルダ

### アーキテクチャ
- **PDFLoader**: PDFファイル読み込み（pdfplumber使用）
- **TextSplitter**: 文脈を考慮したテキスト分割
- **EmbeddingGenerator**: 埋め込みベクトル生成（Sentence Transformers）
- **VectorStore**: ベクトル検索（FAISS）
- **NVIDIACloudLLM**: NVIDIA Cloud API連携

## 🌐 エンドポイント設定

### 対応エンドポイント
1. **NGC API (デフォルト)**
   ```bash
   export NVIDIA_API_KEY=your_ngc_key
   ```

2. **NVIDIA NIM**
   ```bash
   export NVIDIA_API_KEY=your_nim_key
   # オプション: 環境変数で設定
   export NVIDIA_NIM_ENDPOINT=http://localhost:8000/v1
   ```
   または WebUIから直接入力可能

3. **カスタムエンドポイント**
   - WebUIから直接URL入力可能
   - OpenAI Compatible API対応

### エンドポイント切り替え
- **WebUIから選択**: サイドバーでNGC/NIM/カスタムを選択
- **NIM柔軟設定**: UI入力 または 環境変数
- **優先度**: UI入力 > 環境変数 (NVIDIA_NIM_ENDPOINT)
- **リアルタイム**: 接続テスト・設定変更の即座反映

## 💡 NIM使用例

### パターン1: 環境変数設定
```bash
export NVIDIA_NIM_ENDPOINT=http://localhost:8000/v1
```
→ NIMモード選択時に自動適用

### パターン2: WebUI直接入力
1. サイドバーで「NIM (環境変数)」選択
2. 「NIMエンドポイントURL」フィールドに入力
3. 優先度: UI入力 > 環境変数

### パターン3: 動的切り替え
- 開発環境: `http://localhost:8000/v1`
- 本番環境: `https://nim.company.com/v1`
- WebUIで即座に切り替え可能

## 🔧 カスタマイズ

### 設定パラメータ
- **chunk_size**: テキスト分割サイズ（デフォルト: 800）
- **chunk_overlap**: チャンク重複量（デフォルト: 100）
- **search_results**: 検索結果数（デフォルト: 3）

### 対応ファイル形式
- PDF（日本語対応）

## 📝 サンプル質問

- "Pythonの特徴を教えてください"
- "リストの操作方法を説明してください"
- "関数の定義方法について教えてください"
- "例外処理のやり方を教えてください"
- "クラスの継承について説明してください"

## 🔍 トラブルシューティング

### よくある問題
- **NVIDIA API Key未設定**: 環境変数を確認
- **PDFが読み込めない**: ファイル形式・エンコーディングを確認
- **回答が生成されない**: ネットワーク接続・API制限を確認

## 📊 技術スタック

- **Python 3.12+**
- **Streamlit**: WebUI
- **pdfplumber**: PDF処理  
- **Sentence Transformers**: 埋め込み生成
- **FAISS**: ベクトル検索
- **NVIDIA Cloud LLM**: 回答生成

## 🎯 今後の改善予定

- [ ] 複数言語対応
- [ ] チャット履歴の永続化
- [ ] 複数ファイル形式サポート（Word、Excel等）
- [ ] 高度な検索フィルタリング
- [ ] レスポンス時間の最適化