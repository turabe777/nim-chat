import os
from typing import Optional
from rag_app import RAGApplication


def main() -> None:
    """RAGアプリケーションのメイン実行関数"""
    # NVIDIA API Keyの設定
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    if not nvidia_api_key:
        print("NVIDIA_API_KEY環境変数を設定してください。")
        print("例: export NVIDIA_API_KEY=your_api_key_here")
        return
    
    # RAGアプリケーションの初期化
    rag_app = RAGApplication(nvidia_api_key)
    
    # PDFフォルダからの初期化
    pdf_folder = "pdfs"
    if not os.path.exists(pdf_folder):
        print(f"PDFフォルダ '{pdf_folder}' が存在しません。")
        print("pdfsフォルダを作成してPDFファイルを配置してください。")
        return
    
    print("RAGシステムを初期化しています...")
    rag_app.initialize_from_pdfs(pdf_folder)
    
    if not rag_app.is_initialized:
        print("RAGシステムの初期化に失敗しました。")
        return
    
    print("\n" + "="*50)
    print("RAG質問応答システムが起動しました")
    print("終了するには 'quit' または 'exit' を入力してください")
    print("="*50 + "\n")
    
    # 対話ループ
    while True:
        try:
            question = input("質問を入力してください: ").strip()
            
            if question.lower() in ['quit', 'exit', '終了']:
                print("システムを終了します。")
                break
            
            if not question:
                print("質問を入力してください。")
                continue
            
            if question.lower() == 'sources':
                print("最後の質問のソース情報を表示します。")
                continue
            
            print("\n回答を生成中...")
            response = rag_app.query(question)
            
            print(f"\n回答: {response}")
            
            # ソース情報の表示
            sources = rag_app.get_sources(question)
            if sources:
                print(f"\n参考ソース ({len(sources)}件):")
                for i, source in enumerate(sources, 1):
                    print(f"{i}. {source['metadata']['file_name']} (類似度: {source['similarity_score']:.3f})")
                    print(f"   内容: {source['content']}")
                    print()
            
        except KeyboardInterrupt:
            print("\n\nシステムを終了します。")
            break
        except Exception as e:
            print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    main()