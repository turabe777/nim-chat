import os
import json
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import requests
from PyPDF2 import PdfReader
import pdfplumber
from sentence_transformers import SentenceTransformer
import faiss
from dataclasses import dataclass


@dataclass
class Document:
    """ドキュメントを表すデータクラス"""
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None


class PDFLoader:
    """PDFファイルを読み込むクラス"""
    
    def load_pdf(self, file_path: str) -> str:
        """
        PDFファイルからテキストを抽出する
        
        Args:
            file_path: PDFファイルのパス
            
        Returns:
            抽出されたテキスト
        """
        # まずpdfplumberを試す（日本語対応が良い）
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                if text.strip():
                    return text
        except Exception as e:
            print(f"pdfplumberでの読み込みエラー: {e}")
        
        # フォールバックとしてPyPDF2を使用
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"PyPDF2での読み込みエラー: {e}")
            return ""
    
    def load_pdfs_from_folder(self, folder_path: str) -> List[Document]:
        """
        フォルダ内のすべてのPDFファイルを読み込む
        
        Args:
            folder_path: PDFファイルが格納されているフォルダのパス
            
        Returns:
            ドキュメントのリスト
        """
        documents = []
        pdf_folder = Path(folder_path)
        
        for pdf_file in pdf_folder.glob("*.pdf"):
            text = self.load_pdf(str(pdf_file))
            if text:
                doc = Document(
                    content=text,
                    metadata={"source": str(pdf_file), "file_name": pdf_file.name}
                )
                documents.append(doc)
        
        return documents


class TextSplitter:
    """テキストを分割するクラス"""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """
        テキストをチャンクに分割する（文脈を考慮した改良版）
        
        Args:
            text: 分割するテキスト
            
        Returns:
            分割されたテキストのリスト
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # テキストの終端を超えないように調整
            if end >= len(text):
                chunk = text[start:]
                chunks.append(chunk.strip())
                break
            
            # 文や段落の境界で分割するよう調整
            chunk = text[start:end]
            
            # 改行で分割できる位置を探す
            newline_pos = chunk.rfind('\n\n')  # 段落境界
            if newline_pos > self.chunk_size * 0.5:  # 半分以上の位置にある場合
                chunk = text[start:start + newline_pos]
                start = start + newline_pos + 2
            else:
                # 文の境界で分割
                sentence_pos = chunk.rfind('。')
                if sentence_pos > self.chunk_size * 0.3:  # 30%以上の位置にある場合
                    chunk = text[start:start + sentence_pos + 1]
                    start = start + sentence_pos + 1
                else:
                    # 単語境界で分割
                    space_pos = chunk.rfind(' ')
                    if space_pos > 0:
                        chunk = text[start:start + space_pos]
                        start = start + space_pos + 1
                    else:
                        # 最後の手段として文字で分割
                        start = end - self.chunk_overlap
            
            if chunk.strip():
                chunks.append(chunk.strip())
        
        return chunks
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        ドキュメントリストを分割する
        
        Args:
            documents: ドキュメントのリスト
            
        Returns:
            分割されたドキュメントのリスト
        """
        split_docs = []
        
        for doc in documents:
            chunks = self.split_text(doc.content)
            for i, chunk in enumerate(chunks):
                split_doc = Document(
                    content=chunk,
                    metadata={
                        **doc.metadata,
                        "chunk_id": i,
                        "total_chunks": len(chunks)
                    }
                )
                split_docs.append(split_doc)
        
        return split_docs


class EmbeddingGenerator:
    """埋め込みベクトルを生成するクラス"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        テキストのリストから埋め込みベクトルを生成する
        
        Args:
            texts: テキストのリスト
            
        Returns:
            埋め込みベクトルの配列
        """
        return self.model.encode(texts)
    
    def embed_documents(self, documents: List[Document]) -> List[Document]:
        """
        ドキュメントに埋め込みベクトルを追加する
        
        Args:
            documents: ドキュメントのリスト
            
        Returns:
            埋め込みベクトルが追加されたドキュメントのリスト
        """
        texts = [doc.content for doc in documents]
        embeddings = self.generate_embeddings(texts)
        
        for doc, embedding in zip(documents, embeddings):
            doc.embedding = embedding
        
        return documents


class VectorStore:
    """ベクトルストレージクラス"""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.documents: List[Document] = []
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        ドキュメントをベクトルストアに追加する
        
        Args:
            documents: 追加するドキュメントのリスト
        """
        embeddings = np.array([doc.embedding for doc in documents])
        self.index.add(embeddings.astype('float32'))
        self.documents.extend(documents)
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[Document, float]]:
        """
        類似ドキュメントを検索する
        
        Args:
            query_embedding: クエリの埋め込みベクトル
            k: 返すドキュメント数
            
        Returns:
            (ドキュメント, スコア)のタプルのリスト
        """
        scores, indices = self.index.search(
            query_embedding.astype('float32').reshape(1, -1), k
        )
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents):
                results.append((self.documents[idx], float(score)))
        
        return results


class NVIDIALLM:
    """NVIDIA LLM（NGC/NIM）との連携クラス"""
    
    def __init__(
        self, 
        api_key: str, 
        model_name: str = "nvidia/llama-3.1-nemotron-70b-instruct",
        base_url: Optional[str] = None,
        endpoint_type: str = "auto"
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.endpoint_type = endpoint_type
        
        # エンドポイントURLの決定
        self.base_url = self._determine_endpoint(base_url)
        
        # 実際に使用されているエンドポイントタイプを設定
        self.actual_endpoint_type = self._detect_endpoint_type()
    
    def _determine_endpoint(self, base_url: Optional[str]) -> str:
        """
        使用するエンドポイントを決定する
        
        Args:
            base_url: 指定されたベースURL
            
        Returns:
            決定されたベースURL
        """
        # 1. 明示的にURLが指定されている場合
        if base_url:
            return base_url.rstrip('/')
        
        # 2. 環境変数からNIMエンドポイントを取得
        nim_endpoint = os.getenv("NVIDIA_NIM_ENDPOINT")
        if nim_endpoint:
            return nim_endpoint.rstrip('/')
        
        # 3. デフォルトはNGC API
        return "https://integrate.api.nvidia.com/v1"
    
    def _detect_endpoint_type(self) -> str:
        """
        実際のエンドポイントタイプを検出する
        
        Returns:
            エンドポイントタイプ（"ngc", "nim", "custom"）
        """
        if "integrate.api.nvidia.com" in self.base_url:
            return "ngc"
        elif ("localhost" in self.base_url or 
              "127.0.0.1" in self.base_url or
              ":8000" in self.base_url or  # 一般的なNIMポート
              os.getenv("NVIDIA_NIM_ENDPOINT") == self.base_url):  # 環境変数からの場合
            return "nim"
        else:
            return "custom"
    
    def get_endpoint_info(self) -> Dict[str, str]:
        """
        エンドポイント情報を取得する
        
        Returns:
            エンドポイント情報の辞書
        """
        return {
            "base_url": self.base_url,
            "endpoint_type": self.actual_endpoint_type,
            "model_name": self.model_name
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        エンドポイントへの接続をテストする
        
        Returns:
            接続テスト結果
        """
        try:
            start_time = time.time()
            
            # NIMの場合は直接chat/completionsエンドポイントをテスト
            if self.actual_endpoint_type == "nim":
                test_result = self._test_chat_endpoint()
                end_time = time.time()
                response_time = end_time - start_time
                
                return {
                    "success": test_result["success"],
                    "response_time": response_time,
                    "models_count": 1,
                    "endpoint_type": self.actual_endpoint_type,
                    "message": test_result["message"]
                }
            else:
                # NGC/カスタムの場合は従来通りモデル一覧取得
                models = self.get_available_models()
                end_time = time.time()
                response_time = end_time - start_time
                
                return {
                    "success": True,
                    "response_time": response_time,
                    "models_count": len(models),
                    "endpoint_type": self.actual_endpoint_type,
                    "message": f"接続成功 ({self.actual_endpoint_type.upper()})"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "endpoint_type": self.actual_endpoint_type,
                "message": f"接続失敗: {e}"
            }
    
    def _test_chat_endpoint(self) -> Dict[str, Any]:
        """
        chat/completionsエンドポイントの接続テスト
        
        Returns:
            テスト結果
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # NIMサーバー向けのモデル名調整
        # 利用可能なモデル一覧を取得
        available_models = self.get_available_models()
        if available_models and len(available_models) > 0:
            # 利用可能なモデルの最初のものを使用
            model_to_use = available_models[0]
            print(f"Debug: Using available model for connection test: {model_to_use}")
        else:
            model_to_use = self.model_name
            if "nvidia/llama-3.1-nemotron-70b-instruct" in self.model_name:
                model_to_use = "nvidia/nemotron-4-340b-instruct"
        
        # 簡単なテストメッセージ
        test_data = {
            "model": model_to_use,
            "messages": [{"role": "user", "content": "Test"}],
            "max_tokens": 1,
            "temperature": 0.1
        }
        
        # エンドポイントURL構築
        if self.base_url.endswith('/v1'):
            test_endpoint_url = f"{self.base_url}/chat/completions"
        else:
            test_endpoint_url = f"{self.base_url}/v1/chat/completions"
        
        print(f"Debug: Connection test endpoint: {test_endpoint_url}")
        print(f"Debug: Connection test data: {test_data}")
        
        try:
            response = requests.post(
                test_endpoint_url,
                headers=headers,
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "message": f"接続成功 (NIM)"}
            elif response.status_code == 404:
                return {"success": False, "message": "404エラー: エンドポイントが見つかりません"}
            elif response.status_code == 401:
                return {"success": False, "message": "401エラー: 認証に失敗しました"}
            elif response.status_code == 403:
                return {"success": False, "message": "403エラー: アクセスが拒否されました"}
            else:
                return {"success": False, "message": f"HTTPエラー: {response.status_code}"}
                
        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "接続エラー: サーバーに接続できません"}
        except requests.exceptions.Timeout:
            return {"success": False, "message": "タイムアウトエラー: サーバーの応答が遅すぎます"}
        except Exception as e:
            return {"success": False, "message": f"予期しないエラー: {e}"}
    
    def get_available_models(self) -> List[str]:
        """
        利用可能なモデル一覧を取得する
        
        Returns:
            モデル名のリスト
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # NGC APIの場合：よく使われるモデル一覧を返す
        if self.actual_endpoint_type == "ngc":
            ngc_models = [
                "nvidia/llama-3.1-nemotron-70b-instruct",
                "meta/llama-3.1-70b-instruct",
                "meta/llama-3.1-8b-instruct", 
                "microsoft/phi-3-medium-4k-instruct",
                "nvidia/nemotron-4-340b-instruct",
                "meta/llama3-70b-instruct",
                "meta/llama3-8b-instruct",
                "mistralai/mixtral-8x7b-instruct-v0.1",
                "google/gemma-7b-it"
            ]
            return ngc_models
        
        # NIM/カスタムの場合：APIから取得を試行
        try:
            # まず /v1/models を試す
            response = requests.get(
                f"{self.base_url}/v1/models",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                models_data = response.json()
                if "data" in models_data:
                    models = [model["id"] for model in models_data["data"]]
                    if models:
                        return models
            
            # フォールバック: /models を試す
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                models_data = response.json()
                if "data" in models_data:
                    models = [model["id"] for model in models_data["data"]]
                    if models:
                        return models
            
            # どちらも失敗した場合はデフォルトモデルを返す
            return [self.model_name]
                
        except Exception as e:
            # エラーの場合もデフォルトモデルを返す
            print(f"Warning: Failed to get models: {e}")
            return [self.model_name]
    
    def generate_response(self, prompt: str, max_tokens: int = 1024) -> str:
        """
        NVIDIA LLM（NGC/NIM）から回答を生成する
        
        Args:
            prompt: プロンプト
            max_tokens: 最大トークン数
            
        Returns:
            生成された回答
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # NIMサーバー向けのモデル名調整
        model_to_use = self.model_name
        fallback_models = []
        
        if self.actual_endpoint_type == "nim":
            # 利用可能なモデル一覧を取得
            available_models = self.get_available_models()
            if available_models and len(available_models) > 0:
                # 利用可能なモデルの最初のものを使用
                model_to_use = available_models[0]
                fallback_models = available_models[1:] + [self.model_name]
                print(f"Debug: Using available NIM model: {model_to_use}")
            else:
                # 従来のフォールバック
                if "nvidia/llama-3.1-nemotron-70b-instruct" in self.model_name:
                    fallback_models = [
                        "tokyotech-llm/llama-3.1-swallow-8b-instruct-v0.1",  # 実際に確認されたモデル
                        "nvidia/nemotron-4-340b-instruct",
                        "meta/llama3-70b-instruct",
                        "meta/llama-3.1-70b-instruct",
                        "llama3-70b-instruct",
                        "nemotron-4-340b-instruct",
                        self.model_name  # 元のモデル名も試行
                    ]
                    model_to_use = fallback_models[0]
        
        data = {
            "model": model_to_use,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        # 完全なエンドポイントURLを構築
        # base_urlに既に/v1が含まれている場合を考慮
        if self.base_url.endswith('/v1'):
            endpoint_url = f"{self.base_url}/chat/completions"
        else:
            endpoint_url = f"{self.base_url}/v1/chat/completions"
        
        # NIMサーバーの場合、複数のモデル名を試行
        models_to_try = [model_to_use] + fallback_models if fallback_models else [model_to_use]
        
        for attempt, model_name_attempt in enumerate(models_to_try, 1):
            if attempt > 1:
                print(f"Debug: Trying fallback model {attempt-1}: {model_name_attempt}")
                data["model"] = model_name_attempt
            
            try:
                if attempt == 1:  # 最初の試行でのみデバッグ情報を表示
                    print(f"Debug: Sending request to {endpoint_url}")
                    print(f"Debug: Base URL: {self.base_url}")
                    print(f"Debug: Original model: {self.model_name}")
                    print(f"Debug: Using model: {model_name_attempt}")
                    print(f"Debug: Endpoint type: {self.actual_endpoint_type}")
                    print(f"Debug: Available models: {self.get_available_models()}")
                    print(f"Debug: Headers: {headers}")
                
                response = requests.post(
                    endpoint_url,
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                if attempt == 1:
                    print(f"Debug: Response status: {response.status_code}")
                    print(f"Debug: Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    if attempt > 1:
                        print(f"Success: Model '{model_name_attempt}' worked!")
                    
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        return response_data["choices"][0]["message"]["content"]
                    else:
                        return f"予期しないレスポンス形式: {response_data}"
                
                elif response.status_code == 422 and attempt < len(models_to_try):
                    # 422エラー（無効なモデル名）の場合、次のモデルを試行
                    print(f"Debug: Model '{model_name_attempt}' not available (422), trying next...")
                    continue
                elif response.status_code == 404:
                    # 404エラーの場合、代替エンドポイントを試行
                    alternative_endpoints = [
                        f"{self.base_url}/completions",
                        f"{self.base_url}/generate", 
                        f"{self.base_url}/v1/completions",
                        f"{self.base_url.replace('/v1', '')}/chat/completions"
                    ]
                    
                    print(f"Debug: 404 error, trying alternative endpoints...")
                    for alt_endpoint in alternative_endpoints:
                        try:
                            # /completions エンドポイント用の形式に変換
                            if "completions" in alt_endpoint and "chat" not in alt_endpoint:
                                # text completions 形式
                                alt_data = {
                                    "model": data["model"],
                                    "prompt": data["messages"][0]["content"],
                                    "max_tokens": data["max_tokens"],
                                    "temperature": data["temperature"]
                                }
                            else:
                                # chat completions 形式
                                alt_data = data
                            
                            alt_response = requests.post(
                                alt_endpoint,
                                headers=headers,
                                json=alt_data,
                                timeout=10
                            )
                            print(f"Debug: Trying {alt_endpoint} with status {alt_response.status_code}")
                            
                            if alt_response.status_code == 200:
                                print(f"Success: Alternative endpoint worked: {alt_endpoint}")
                                response_json = alt_response.json()
                                
                                # レスポンス形式に応じて結果を取得
                                if "choices" in response_json and len(response_json["choices"]) > 0:
                                    choice = response_json["choices"][0]
                                    if "message" in choice:
                                        return choice["message"]["content"]
                                    elif "text" in choice:
                                        return choice["text"]
                                
                                return str(response_json)
                            elif alt_response.status_code != 404:
                                try:
                                    error_detail = alt_response.json()
                                    print(f"Debug: {alt_endpoint} error: {error_detail}")
                                except:
                                    print(f"Debug: {alt_endpoint} error: {alt_response.text}")
                        except Exception as e:
                            print(f"Debug: Exception for {alt_endpoint}: {e}")
                            continue
                    
                    return f"404エラー: エンドポイント '{endpoint_url}' が見つかりません。試行した代替パス: {alternative_endpoints}"
                elif response.status_code == 401:
                    return f"401エラー: 認証に失敗しました。API Keyを確認してください。"
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.HTTPError as e:
                if attempt == len(models_to_try):  # 最後の試行
                    return f"HTTPエラー: {e.response.status_code} - {e.response.text}"
                continue
            except Exception as e:
                if attempt == len(models_to_try):  # 最後の試行
                    break
                continue
        
        # すべてのモデル名を試行しても失敗
        return f"すべてのモデル名を試行しましたが失敗しました。試行したモデル: {models_to_try}"


class RAGApplication:
    """RAGアプリケーションのメインクラス"""
    
    def __init__(
        self, 
        nvidia_api_key: str, 
        base_url: Optional[str] = None,
        model_name: str = "nvidia/llama-3.1-nemotron-70b-instruct"
    ):
        self.pdf_loader = PDFLoader()
        self.text_splitter = TextSplitter()
        self.embedding_generator = EmbeddingGenerator()
        self.vector_store = VectorStore()
        self.llm = NVIDIALLM(
            api_key=nvidia_api_key,
            base_url=base_url,
            model_name=model_name
        )
        self.is_initialized = False
    
    def initialize_from_pdfs(self, pdf_folder_path: str) -> None:
        """
        PDFフォルダからRAGシステムを初期化する
        
        Args:
            pdf_folder_path: PDFファイルが格納されているフォルダのパス
        """
        print("PDFファイルを読み込み中...")
        documents = self.pdf_loader.load_pdfs_from_folder(pdf_folder_path)
        
        if not documents:
            print("PDFファイルが見つかりませんでした。")
            return
        
        print(f"{len(documents)}個のPDFファイルを読み込みました。")
        
        print("テキストを分割中...")
        split_documents = self.text_splitter.split_documents(documents)
        print(f"{len(split_documents)}個のチャンクに分割しました。")
        
        print("埋め込みベクトルを生成中...")
        embedded_documents = self.embedding_generator.embed_documents(split_documents)
        
        print("ベクトルストアに追加中...")
        self.vector_store.add_documents(embedded_documents)
        
        self.is_initialized = True
        print("RAGシステムの初期化が完了しました。")
    
    def query(self, question: str, k: int = 3) -> str:
        """
        質問に対する回答を生成する
        
        Args:
            question: 質問
            k: 検索するドキュメント数
            
        Returns:
            生成された回答
        """
        if not self.is_initialized:
            return "RAGシステムが初期化されていません。initialize_from_pdfs()を実行してください。"
        
        # 質問の埋め込みベクトルを生成
        query_embedding = self.embedding_generator.generate_embeddings([question])[0]
        
        # 関連ドキュメントを検索
        search_results = self.vector_store.search(query_embedding, k)
        
        if not search_results:
            return "関連するドキュメントが見つかりませんでした。"
        
        # コンテキストを構築
        context = "\n\n".join([doc.content for doc, _ in search_results])
        
        # プロンプトを作成
        prompt = f"""以下のコンテキストを基に、質問に回答してください。コンテキストに含まれていない情報については「情報が不足している」と回答してください。

コンテキスト:
{context}

質問: {question}

回答:"""
        
        # LLMから回答を生成
        response = self.llm.generate_response(prompt)
        return response
    
    def get_sources(self, question: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        質問に関連するソース情報を取得する
        
        Args:
            question: 質問
            k: 検索するドキュメント数
            
        Returns:
            ソース情報のリスト
        """
        if not self.is_initialized:
            return []
        
        query_embedding = self.embedding_generator.generate_embeddings([question])[0]
        search_results = self.vector_store.search(query_embedding, k)
        
        sources = []
        for doc, score in search_results:
            sources.append({
                "content": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                "metadata": doc.metadata,
                "similarity_score": score
            })
        
        return sources