# Vector Store Service Dockerfile

FROM python:3.12-slim

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ設定
WORKDIR /app

# 共通ライブラリコピー
COPY shared/ /app/shared/

# 依存関係ファイルコピー
COPY services/vector-store-service/requirements.txt .

# uvインストール
RUN pip install uv

# Python依存関係インストール（uvを使用）
RUN uv pip install --system -r requirements.txt

# アプリケーションコピー
COPY services/vector-store-service/app/ /app/app/

# データディレクトリ作成
RUN mkdir -p /app/data/vectors

# 非rootユーザー作成・切り替え
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# ポート公開
EXPOSE 8004

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# アプリケーション起動
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]