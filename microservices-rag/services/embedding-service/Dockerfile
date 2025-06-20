# Embedding Service Dockerfile

FROM python:3.12-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uv インストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# プロジェクト設定ファイルをコピー
COPY pyproject.toml uv.lock ./

# 依存関係インストール（埋め込み関連）
RUN uv sync --frozen --no-dev --extra embedding

# 共通ライブラリをコピー
COPY shared/ shared/

# アプリケーションコードをコピー
COPY services/embedding-service/ services/embedding-service/

# 環境変数設定（Pythonパス）
ENV PYTHONPATH=/app

# 作業ディレクトリ設定
WORKDIR /app/services/embedding-service

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# サービス起動
CMD ["uv", "run", "python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]