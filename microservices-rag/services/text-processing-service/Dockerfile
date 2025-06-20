# Text Processing Service Dockerfile

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

# 依存関係インストール
RUN uv sync --frozen --no-dev

# 共通ライブラリをコピー
COPY shared/ shared/

# アプリケーションコードをコピー
COPY services/text-processing-service/ services/text-processing-service/

# 環境変数設定（Pythonパス）
ENV PYTHONPATH=/app

# 作業ディレクトリ設定
WORKDIR /app/services/text-processing-service

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# サービス起動
CMD ["uv", "run", "python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]