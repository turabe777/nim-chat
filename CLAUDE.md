# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

PDFファイルを基にしたRAG（Retrieval-Augmented Generation）システム。NVIDIA Cloud LLMを使用して、PDFの内容から質問応答を行う。

## アーキテクチャ

- `rag_app.py`: RAGシステムのメインロジック
  - `PDFLoader`: PDFファイルの読み込み
  - `TextSplitter`: テキストの分割
  - `EmbeddingGenerator`: 埋め込みベクトル生成
  - `VectorStore`: ベクトル検索（FAISS使用）
  - `NVIDIACloudLLM`: NVIDIA Cloud API連携
- `main.py`: ユーザーインターフェース

## セットアップ・実行

```bash
# 依存関係のインストール
pip install -r requirements.txt

# NVIDIA API Key設定
export NVIDIA_API_KEY=your_api_key_here

# 実行
python main.py
```

## 使用方法

1. `pdfs/` フォルダにPDFファイルを配置
2. `python main.py` で起動
3. 質問を入力して回答を取得

## 重要な型アノテーション規則

全ての関数には型アノテーションを必須で記述する

## コーディングガイドライン

- Pythonの関数では必ず型アノテーションを入れていください。