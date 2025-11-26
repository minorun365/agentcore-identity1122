# AgentCore Runtime用Dockerfile（ARM64アーキテクチャが必須）
FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係をコピーしてインストール
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY backend/src ./src

# Atlassian Cloud ID（Confluence連携用）
ENV ATLASSIAN_CLOUD_ID="60884799-9bb5-4252-90c3-0d4b3d617c11"

# ポート8080を公開（AgentCore Runtimeの要件）
EXPOSE 8080

# OpenTelemetryで自動計装してアプリケーション起動
CMD ["opentelemetry-instrument", "python", "-m", "src.main"]
