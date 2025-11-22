# AgentCore Runtime用Dockerfile（ARM64アーキテクチャが必須）
FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係をコピーしてインストール
COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# agentcoreモジュール（機能別コード）をコピー
COPY agentcore ./agentcore

# アプリケーションコードをコピー（agent/app.pyを明示的に指定）
COPY agent/app.py .

# ポート8080を公開（AgentCore Runtimeの要件）
EXPOSE 8080

# アプリケーション起動
CMD ["python", "app.py"]
