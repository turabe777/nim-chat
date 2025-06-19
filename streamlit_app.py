import streamlit as st
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from rag_app import RAGApplication, Document
import tempfile
import time

# Streamlitページの設定
st.set_page_config(
    page_title="Python RAG質問応答システム",
    page_icon="🐍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSSスタイル
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #1976d2;
    }
    .assistant-message {
        background-color: #f3e5f5;
        border-left: 4px solid #7b1fa2;
    }
    .source-info {
        background-color: #fff3e0;
        border: 1px solid #ff9800;
        border-radius: 0.3rem;
        padding: 0.5rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .status-success {
        color: #4caf50;
        font-weight: bold;
    }
    .status-error {
        color: #f44336;
        font-weight: bold;
    }
    .status-warning {
        color: #ff9800;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state() -> None:
    """セッション状態を初期化"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "rag_app" not in st.session_state:
        st.session_state.rag_app = None
    if "is_initialized" not in st.session_state:
        st.session_state.is_initialized = False
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "endpoint_type" not in st.session_state:
        st.session_state.endpoint_type = "ngc"
    if "custom_endpoint" not in st.session_state:
        st.session_state.custom_endpoint = ""
    if "nim_endpoint_input" not in st.session_state:
        st.session_state.nim_endpoint_input = ""
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "nvidia/llama-3.1-nemotron-70b-instruct"

def get_rag_application(force_recreate: bool = False) -> Optional[RAGApplication]:
    """RAGアプリケーションを取得または初期化"""
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    if not nvidia_api_key:
        st.error("❌ NVIDIA_API_KEY環境変数が設定されていません。")
        st.info("環境変数を設定してからアプリケーションを再起動してください。")
        return None
    
    # エンドポイント設定の決定
    base_url = None
    if st.session_state.endpoint_type == "nim":
        # NIMエンドポイントの優先度: UI入力 > 環境変数
        if st.session_state.nim_endpoint_input.strip():
            base_url = st.session_state.nim_endpoint_input.strip()
        else:
            nim_endpoint = os.getenv("NVIDIA_NIM_ENDPOINT")
            if nim_endpoint:
                base_url = nim_endpoint
            else:
                st.warning("⚠️ NIMエンドポイントが設定されていません。UI入力または環境変数を設定してください。")
                return None
    elif st.session_state.endpoint_type == "custom":
        if st.session_state.custom_endpoint:
            base_url = st.session_state.custom_endpoint
        else:
            st.warning("⚠️ カスタムエンドポイントが設定されていません。")
            return None
    
    if st.session_state.rag_app is None or force_recreate:
        try:
            st.session_state.rag_app = RAGApplication(
                nvidia_api_key=nvidia_api_key,
                base_url=base_url,
                model_name=st.session_state.selected_model
            )
            
            # NIMモードの場合、利用可能なモデルでセッション状態を更新
            if st.session_state.endpoint_type == "nim":
                available_models = st.session_state.rag_app.llm.get_available_models()
                if available_models and available_models[0] != st.session_state.selected_model:
                    # 実際に利用可能なモデルがある場合、セッション状態を更新
                    # ただし、ユーザーが明示的に選択した場合は更新しない
                    pass  # 表示でのみ違いを示し、セッション状態は変更しない
                    
        except Exception as e:
            st.error(f"❌ RAGアプリケーションの初期化に失敗しました: {e}")
            return None
    
    return st.session_state.rag_app

def save_uploaded_file(uploaded_file) -> str:
    """アップロードされたファイルを保存"""
    pdfs_dir = Path("pdfs")
    pdfs_dir.mkdir(exist_ok=True)
    
    file_path = pdfs_dir / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(file_path)

def get_uploaded_files() -> List[str]:
    """アップロード済みのPDFファイル一覧を取得"""
    pdfs_dir = Path("pdfs")
    if not pdfs_dir.exists():
        return []
    
    pdf_files = list(pdfs_dir.glob("*.pdf"))
    return [str(f) for f in pdf_files]

def initialize_rag_system(chunk_size: int = 800, chunk_overlap: int = 100) -> bool:
    """RAGシステムを初期化"""
    rag_app = get_rag_application()
    if not rag_app:
        return False
    
    # チャンクサイズの設定を更新
    rag_app.text_splitter.chunk_size = chunk_size
    rag_app.text_splitter.chunk_overlap = chunk_overlap
    
    try:
        with st.spinner("RAGシステムを初期化中..."):
            rag_app.initialize_from_pdfs("pdfs")
            st.session_state.is_initialized = rag_app.is_initialized
            return rag_app.is_initialized
    except Exception as e:
        st.error(f"❌ 初期化エラー: {e}")
        return False

def display_chat_messages() -> None:
    """チャットメッセージを表示"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # ソース情報を表示
            if "sources" in message and message["sources"]:
                with st.expander("📄 参考ソース", expanded=False):
                    for i, source in enumerate(message["sources"], 1):
                        st.markdown(f"""
                        <div class="source-info">
                            <strong>ソース {i}:</strong> {source['metadata']['file_name']}<br>
                            <strong>類似度:</strong> {source['similarity_score']:.3f}<br>
                            <strong>内容:</strong> {source['content'][:200]}...
                        </div>
                        """, unsafe_allow_html=True)

def main() -> None:
    """メイン関数"""
    initialize_session_state()
    
    # ヘッダー
    st.markdown('<h1 class="main-header">🐍 Python RAG質問応答システム</h1>', 
                unsafe_allow_html=True)
    
    # サイドバー
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # API Key状態確認
        nvidia_api_key = os.getenv("NVIDIA_API_KEY")
        if nvidia_api_key:
            st.markdown('<p class="status-success">✅ NVIDIA API Key: 設定済み</p>', 
                       unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-error">❌ NVIDIA API Key: 未設定</p>', 
                       unsafe_allow_html=True)
            st.stop()
        
        st.divider()
        
        # エンドポイント設定
        st.subheader("🌐 エンドポイント設定")
        
        # エンドポイントタイプ選択
        endpoint_options = {
            "ngc": "NGC API (cloud)",
            "nim": "NVIDIA NIM (自動検出)",
            "custom": "カスタムエンドポイント"
        }
        
        new_endpoint_type = st.selectbox(
            "エンドポイントタイプ",
            options=list(endpoint_options.keys()),
            format_func=lambda x: endpoint_options[x],
            index=list(endpoint_options.keys()).index(st.session_state.endpoint_type)
        )
        
        # エンドポイントが変更された場合
        if new_endpoint_type != st.session_state.endpoint_type:
            st.session_state.endpoint_type = new_endpoint_type
            st.session_state.rag_app = None  # 再初期化が必要
            st.session_state.is_initialized = False
        
        # カスタムエンドポイント入力
        if st.session_state.endpoint_type == "custom":
            new_custom_endpoint = st.text_input(
                "カスタムエンドポイントURL",
                value=st.session_state.custom_endpoint,
                placeholder="http://localhost:8000/v1",
                help="NIMサーバーのエンドポイントURLを入力"
            )
            if new_custom_endpoint != st.session_state.custom_endpoint:
                st.session_state.custom_endpoint = new_custom_endpoint
                st.session_state.rag_app = None
                st.session_state.is_initialized = False
        
        # NIMエンドポイント設定
        elif st.session_state.endpoint_type == "nim":
            # NIMエンドポイント入力フィールド
            new_nim_endpoint = st.text_input(
                "NIMエンドポイントURL",
                value=st.session_state.nim_endpoint_input,
                placeholder="http://localhost:8000/v1",
                help="NIMサーバーのエンドポイントURLを入力（環境変数より優先）"
            )
            
            # 入力値変更時の処理
            if new_nim_endpoint != st.session_state.nim_endpoint_input:
                st.session_state.nim_endpoint_input = new_nim_endpoint
                st.session_state.rag_app = None
                st.session_state.is_initialized = False
            
            # 環境変数の状況表示
            nim_env_endpoint = os.getenv("NVIDIA_NIM_ENDPOINT")
            if nim_env_endpoint:
                if st.session_state.nim_endpoint_input.strip():
                    st.info(f"🔄 UI入力を使用中 | 環境変数: {nim_env_endpoint}")
                else:
                    st.info(f"📍 環境変数を使用中: {nim_env_endpoint}")
            else:
                if not st.session_state.nim_endpoint_input.strip():
                    st.warning("⚠️ NIMエンドポイントが未設定です。上記に入力するか、NVIDIA_NIM_ENDPOINT環境変数を設定してください。")
                else:
                    st.success(f"✅ UI入力を使用: {st.session_state.nim_endpoint_input}")
            
            # 優先度の説明
            st.caption("💡 優先度: UI入力 > 環境変数 (NVIDIA_NIM_ENDPOINT)")
            
            # NIMサーバー用のモデル名候補を表示
            if st.session_state.nim_endpoint_input.strip() or os.getenv("NVIDIA_NIM_ENDPOINT"):
                with st.expander("🤖 NIM用モデル名候補", expanded=False):
                    st.markdown("""
                    **一般的なNIMモデル名:**
                    - `nvidia/nemotron-4-340b-instruct`
                    - `meta/llama3-8b-instruct`
                    - `meta/llama3-70b-instruct`
                    - `microsoft/phi-3-mini-4k-instruct`
                    
                    **注意**: NIMサーバーで利用可能なモデル名は、サーバーの設定により異なります。
                    """)
        
        # 接続テストボタン
        if st.button("🔍 接続テスト", help="エンドポイントへの接続をテスト"):
            rag_app = get_rag_application()
            if rag_app:
                with st.spinner("接続をテスト中..."):
                    test_result = rag_app.llm.test_connection()
                    
                    if test_result["success"]:
                        st.success(f"✅ {test_result['message']}")
                        st.info(f"⚡ レスポンス時間: {test_result['response_time']:.2f}秒")
                        if test_result['models_count'] > 1:
                            st.info(f"📊 利用可能モデル数: {test_result['models_count']}")
                    else:
                        st.error(f"❌ {test_result['message']}")
                        
                        # 404エラーの場合の対処法を表示
                        if "404" in test_result['message']:
                            st.info("""
                            **404エラーの対処法:**
                            1. NIMサーバーが正常に起動しているか確認
                            2. エンドポイントURLが正しいか確認 (例: `http://localhost:8000/v1`)
                            3. `/v1` が含まれているか確認
                            4. NIMサーバーのドキュメントでAPI仕様を確認
                            """)
                        elif "接続エラー" in test_result['message']:
                            st.info("""
                            **接続エラーの対処法:**
                            1. NIMサーバーが起動しているか確認
                            2. ネットワーク接続を確認
                            3. ファイアウォール設定を確認
                            4. ポート番号が正しいか確認
                            """)
                        elif "401" in test_result['message'] or "403" in test_result['message']:
                            st.info("""
                            **認証エラーの対処法:**
                            1. NVIDIA_API_KEYが正しく設定されているか確認
                            2. API Keyの有効期限を確認
                            3. NIMサーバーの認証設定を確認
                            """)
        
        # エンドポイント情報表示
        rag_app = get_rag_application()
        if rag_app:
            endpoint_info = rag_app.llm.get_endpoint_info()
            endpoint_type = endpoint_info['endpoint_type']
            
            st.markdown(f"""
            **現在の設定:**
            - エンドポイント: `{endpoint_type.upper()}`
            - URL: `{endpoint_info['base_url']}`
            """)
            
            if endpoint_type == "nim":
                # NIMの場合：自動検出されたモデルを表示
                available_models = rag_app.llm.get_available_models()
                actual_model = available_models[0] if available_models else endpoint_info['model_name']
                st.success(f"✅ **自動検出モデル**: `{actual_model}`")
            else:
                # NGC/カスタムの場合：設定されたモデルを表示
                st.info(f"🤖 **使用モデル**: `{endpoint_info['model_name']}`")
        
        st.divider()
        
        # PDFファイル管理
        st.subheader("📄 PDFファイル管理")
        
        # ファイルアップロード
        uploaded_files = st.file_uploader(
            "PDFファイルをアップロード",
            type=["pdf"],
            accept_multiple_files=True,
            help="複数のPDFファイルを選択できます"
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                if uploaded_file.name not in [f.name for f in st.session_state.uploaded_files]:
                    file_path = save_uploaded_file(uploaded_file)
                    st.session_state.uploaded_files.append(uploaded_file)
                    st.success(f"✅ {uploaded_file.name} をアップロードしました")
                    st.session_state.is_initialized = False  # 再初期化が必要
        
        # アップロード済みファイル一覧
        pdf_files = get_uploaded_files()
        if pdf_files:
            st.subheader("📁 アップロード済みファイル")
            for pdf_file in pdf_files:
                file_name = Path(pdf_file).name
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(file_name)
                with col2:
                    if st.button("🗑️", key=f"delete_{file_name}"):
                        os.remove(pdf_file)
                        st.session_state.is_initialized = False
                        st.rerun()
        
        st.divider()
        
        # RAGシステム設定
        st.subheader("🔧 RAGシステム設定")
        
        # モデル選択
        rag_app = get_rag_application()
        if rag_app:
            endpoint_type = rag_app.llm.actual_endpoint_type
            available_models = rag_app.llm.get_available_models()
            
            if endpoint_type == "nim":
                # NIMの場合：自動検出されたモデルを表示のみ
                actual_model = available_models[0] if available_models else st.session_state.selected_model
                st.success(f"🤖 **NIM検出モデル**: `{actual_model}`")
                st.caption("💡 NIMサーバーからモデルを自動検出しました")
                
                # セッション状態を自動検出されたモデルに更新
                if actual_model != st.session_state.selected_model:
                    st.session_state.selected_model = actual_model
                    
            elif endpoint_type == "ngc":
                # NGC APIの場合：モデル選択UI表示
                if len(available_models) > 1:
                    new_model = st.selectbox(
                        "NGC APIモデル選択",
                        options=available_models,
                        index=available_models.index(st.session_state.selected_model) 
                        if st.session_state.selected_model in available_models else 0,
                        help="使用するNGC APIモデルを選択"
                    )
                    if new_model != st.session_state.selected_model:
                        st.session_state.selected_model = new_model
                        st.session_state.rag_app = None
                        st.session_state.is_initialized = False
                else:
                    st.info(f"🤖 使用モデル: {st.session_state.selected_model}")
                    
            else:
                # カスタムエンドポイントの場合：従来通り
                if len(available_models) > 1:
                    new_model = st.selectbox(
                        "モデル選択",
                        options=available_models,
                        index=available_models.index(st.session_state.selected_model) 
                        if st.session_state.selected_model in available_models else 0,
                        help="使用するLLMモデルを選択"
                    )
                    if new_model != st.session_state.selected_model:
                        st.session_state.selected_model = new_model
                        st.session_state.rag_app = None
                        st.session_state.is_initialized = False
                else:
                    st.info(f"🤖 使用モデル: {st.session_state.selected_model}")
        
        chunk_size = st.slider("チャンクサイズ", 400, 1200, 800, 50)
        chunk_overlap = st.slider("チャンク重複", 50, 200, 100, 25)
        search_results = st.slider("検索結果数", 1, 10, 3)
        
        # システム初期化
        if pdf_files and not st.session_state.is_initialized:
            if st.button("🚀 RAGシステムを初期化", type="primary"):
                if initialize_rag_system(chunk_size, chunk_overlap):
                    st.success("✅ RAGシステムが初期化されました！")
                    st.rerun()
        elif st.session_state.is_initialized:
            st.markdown('<p class="status-success">✅ RAGシステム: 初期化済み</p>', 
                       unsafe_allow_html=True)
            
            # 再初期化ボタン
            if st.button("🔄 再初期化"):
                st.session_state.is_initialized = False
                st.rerun()
        
        st.divider()
        
        # システム情報
        st.subheader("ℹ️ システム情報")
        if st.session_state.rag_app and st.session_state.is_initialized:
            st.info(f"📄 PDFファイル数: {len(pdf_files)}")
            # チャンク数などの情報も表示可能
    
    # メインエリア
    if not pdf_files:
        st.info("👈 まず、サイドバーからPDFファイルをアップロードしてください。")
        return
    
    if not st.session_state.is_initialized:
        st.warning("👈 サイドバーからRAGシステムを初期化してください。")
        return
    
    # チャット履歴表示
    display_chat_messages()
    
    # チャット入力
    if prompt := st.chat_input("Pythonについて質問してください..."):
        # ユーザーメッセージを追加
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # ユーザーメッセージを表示
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # アシスタント応答を生成
        with st.chat_message("assistant"):
            with st.spinner("回答を生成中..."):
                try:
                    # RAG応答生成
                    response = st.session_state.rag_app.query(prompt)
                    sources = st.session_state.rag_app.get_sources(prompt, search_results)
                    
                    # 応答を表示
                    st.markdown(response)
                    
                    # ソース情報を表示
                    if sources:
                        with st.expander("📄 参考ソース", expanded=False):
                            for i, source in enumerate(sources, 1):
                                st.markdown(f"""
                                <div class="source-info">
                                    <strong>ソース {i}:</strong> {source['metadata']['file_name']}<br>
                                    <strong>類似度:</strong> {source['similarity_score']:.3f}<br>
                                    <strong>内容:</strong> {source['content'][:200]}...
                                </div>
                                """, unsafe_allow_html=True)
                    
                    # アシスタントメッセージを保存
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "sources": sources
                    })
                    
                except Exception as e:
                    error_msg = f"❌ エラーが発生しました: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
    
    # フッター
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        🐍 Python RAG質問応答システム | Powered by NVIDIA Cloud & Streamlit
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()