# AgentCore Identity 統合アプリケーション

このプロジェクトは、Amazon Bedrock AgentCore Runtime、AgentCore Memory、AgentCore Gateway、Cognito認証を統合した AI エージェントアプリケーションです。

## 📋 目次

- [概要](#概要)
- [機能](#機能)
- [アーキテクチャ](#アーキテクチャ)
- [必要な環境](#必要な環境)
- [セットアップ](#セットアップ)
- [デプロイ手順](#デプロイ手順)
- [使い方](#使い方)
- [Observability](#observability)
- [トラブルシューティング](#トラブルシューティング)

---

## 概要

このアプリケーションは、以下のAWSサービスを統合した高度なAIエージェントシステムです：

- **AgentCore Runtime**: サーバーレスでスケーラブルなエージェント実行環境
- **AgentCore Memory**: 短期記憶による会話履歴管理
- **AgentCore Gateway**: MCPプロトコルによるツール統合（Tavily検索など）
- **Amazon Cognito**: ユーザー認証・認可
- **Strands Agents SDK**: マルチモーダルエージェントフレームワーク
- **Streamlit**: ユーザーインターフェース

---

## 機能

### ✨ 主要機能

- 🔐 **Cognito認証**: JWTトークンベースの認証
- 🧠 **会話履歴管理**: AgentCore Memoryによるセッション管理
- 🛠️ **MCPツール統合**: Gateway経由でTavily検索などのツールを利用
- 📊 **Observability**: CloudWatchでトレース、メトリクス、ログを可視化
- 🎯 **カスタム属性**: セッションID、ユーザーID等をトレースに記録

### 🔧 技術スタック

**フロントエンド:**
- Streamlit
- streamlit-cognito-auth

**バックエンド:**
- Strands Agents SDK
- AWS Bedrock AgentCore Runtime
- MCP (Model Context Protocol)

**インフラ:**
- Amazon Bedrock AgentCore
- Amazon Cognito
- Amazon CloudWatch
- Amazon ECR

---

## アーキテクチャ

```
┌─────────────────┐
│  Streamlit UI   │
│(frontend/app.py)│
└────────┬────────┘
         │ HTTP + JWT
         ↓
┌─────────────────┐
│ AgentCore       │
│ Runtime         │
│(backend/src/    │
│  main.py)       │
└────┬─────┬──────┘
     │     │
     │     └──────────────────┐
     ↓                        ↓
┌─────────────┐      ┌──────────────┐
│ AgentCore   │      │  Gateway MCP │
│ Memory      │      │  (Tools)     │
│ (STM)       │      │  - Tavily    │
└─────────────┘      └──────────────┘
     │                        │
     └────────┬───────────────┘
              ↓
         ┌─────────┐
         │ Claude  │
         │ Sonnet  │
         │  4.5    │
         └─────────┘
```

### データフロー

1. **認証**: ユーザーがCognito経由でログイン → JWTトークン取得
2. **リクエスト**: StreamlitからAgentCore Runtimeに送信（JWT付き）
3. **エージェント実行**:
   - Memory から会話履歴を取得
   - Gateway経由でツール（Tavily検索など）を取得
   - Claude Sonnetモデルで推論
   - 結果をMemoryに保存
4. **レスポンス**: 結果をStreamlit UIに表示
5. **Observability**: 全ての実行フローをCloudWatchに送信

---

## 必要な環境

### ローカル開発環境

- Python 3.11 以上
- Docker（コンテナビルド用）
- AWS CLI v2
- AWS アカウント（sandbox プロファイル設定済み）

### AWSリソース

以下のリソースが事前に作成されている必要があります：

- ✅ Amazon Cognito ユーザープール
- ✅ AgentCore Runtime（既存）
- ✅ AgentCore Memory リソース
- ✅ AgentCore Gateway（MCP統合）
- ✅ ECR リポジトリ: `identity1122-agent`
- ⚠️ CloudWatch Transaction Search（初回のみ有効化）

---

## セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd agentcore-identity1122
```

### 2. 依存パッケージのインストール

#### Streamlit アプリ用

```bash
pip install -r requirements.txt
```

#### AgentCore Runtime用（agent ディレクトリ）

```bash
cd agent
pip install -r requirements.txt
cd ..
```

### 3. 環境変数の設定

`.streamlit/secrets.toml` を作成：

```toml
# Cognito設定
COGNITO_USER_POOL_ID = "us-east-1_XXXXXXXXX"
COGNITO_APP_CLIENT_ID = "XXXXXXXXXXXXXXXXXXXXXXXXXX"
COGNITO_APP_CLIENT_SECRET = "XXXXXXXXXXXXXXXXXXXXXXXXXX"

# AgentCore設定
AGENT_RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:XXXXXXXXXXXX:runtime/XXXXX"
GATEWAY_URL = "https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/prod/mcp"

# AWS設定
AWS_DEFAULT_REGION = "us-east-1"
```

### 4. CloudWatch Transaction Search を有効化（初回のみ）

詳細は [OBSERVABILITY.md](./OBSERVABILITY.md) を参照してください。

**簡易手順:**

1. [CloudWatch コンソール](https://console.aws.amazon.com/cloudwatch/) を開く
2. Application Signals > Transaction Search を選択
3. 「Enable Transaction Search」をクリック
4. 設定して保存（サンプリング率: 1%推奨）

⚠️ 有効化後、約10分で利用可能になります。

---

## デプロイ手順

### ステップ1: AWS SSO ログイン

```bash
aws sso login --profile sandbox
```

### ステップ2: ECR にログイン

```bash
aws ecr get-login-password --region us-east-1 --profile sandbox | \
  docker login --username AWS --password-stdin \
  715841358122.dkr.ecr.us-east-1.amazonaws.com
```

### ステップ3: Docker イメージをビルド＆プッシュ

```bash
# プロジェクトルートで実行
docker buildx build --platform linux/arm64 \
  -t 715841358122.dkr.ecr.us-east-1.amazonaws.com/identity1122-agent:latest \
  -f backend/Dockerfile .

docker push 715841358122.dkr.ecr.us-east-1.amazonaws.com/identity1122-agent:latest
```

**⚠️ 重要:**
- ARM64アーキテクチャが必須（AgentCore Runtimeの要件）
- プロジェクトルートからビルドすること
- Dockerfileは `backend/Dockerfile` を使用

### ステップ4: AgentCore Runtime を更新

みのるんがAWSマネコンで手動更新します。

---

## 使い方

### ローカルでStreamlitアプリを起動

```bash
streamlit run frontend/app.py
```

ブラウザで `http://localhost:8501` を開きます。

### 基本的な操作フロー

1. **ログイン**: Cognitoの認証情報でログイン
2. **質問入力**: チャット欄に質問を入力
3. **エージェント実行**: Gateway経由でツールを使い、Claudeが回答を生成
4. **結果表示**: 回答が表示される
5. **会話継続**: 会話履歴が保持され、文脈を理解した回答が可能

### 使用例

```
ユーザー: 「東京の天気を教えて」
↓
Gateway経由でTavily検索を実行
↓
Claude Sonnetが結果を整形して回答
↓
「東京の天気は晴れ、気温は15℃です...」
```

---

## Observability

### 🔧 Observability の設定

このプロジェクトは、AgentCore Runtime側での**自動計装**を使用しています。

#### 重要な設定ポイント

**1. 依存パッケージ（`backend/requirements.txt`）:**
```txt
strands-agents[otel]           # Strandsがトレースを生成
aws-opentelemetry-distro       # トレースをCloudWatchに送信
```

**2. Dockerfileの起動コマンド（`backend/Dockerfile`）:**
```dockerfile
# ⚠️ 重要: opentelemetry-instrument で起動すること！
CMD ["opentelemetry-instrument", "python", "-m", "src.main"]
```

**3. カスタム属性（`backend/src/main.py`）:**
```python
agent = Agent(
    model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    tools=tools,
    session_manager=session_manager,
    trace_attributes={
        "session.id": session_id,
        "actor.id": actor_id,
        "gateway.url": gateway_url,
        "memory.id": MEMORY_ID,
        "region": REGION_NAME
    }
)
```

**⚠️ よくある間違い:**
- `CMD ["python", "app.py"]` だけだとトレースが送信されません
- **必ず** `opentelemetry-instrument` を使って起動してください

### CloudWatch での確認方法

#### 1. GenAI Observability ダッシュボード

[GenAI Observability on CloudWatch](https://console.aws.amazon.com/cloudwatch/home#gen-ai-observability) で以下を確認：

- **Agents View**: エージェント一覧とメトリクス
- **Sessions View**: セッション別の実行履歴
- **Traces View**: 詳細な実行トレース

#### 2. 確認できる情報

**トレース:**
- エージェント実行フロー
- LLM呼び出し（プロンプト、レスポンス、トークン数）
- ツール実行（パラメータ、結果、実行時間）
- Gateway MCP通信

**メトリクス:**
- レイテンシ（TTFB, TTLB）
- トークン使用量（入力・出力・キャッシュ）
- エラー率
- ツール呼び出し回数

**カスタム属性:**
- `session.id`: セッション識別子
- `actor.id`: ユーザー識別子
- `gateway.url`: Gateway URL
- `memory.id`: Memory リソース ID
- `region`: AWSリージョン

### サンプリング率の調整

```bash
# 10%のサンプリングに変更
aws xray update-indexing-rule \
  --name "Default" \
  --rule '{"Probabilistic": {"DesiredSamplingPercentage": 10}}' \
  --region us-east-1 \
  --profile sandbox
```

詳細は [OBSERVABILITY.md](./OBSERVABILITY.md) を参照してください。

---

## トラブルシューティング

### デプロイ関連

#### 1. Docker ビルドが失敗する

**症状:** `no such file or directory: backend/requirements.txt`

**解決策:** プロジェクトルートからビルドしてください
```bash
# ❌ 間違い
cd backend && docker build -f Dockerfile .

# ✅ 正しい
docker buildx build -f backend/Dockerfile .
```

#### 2. ECR push が失敗する

**症状:** `denied: Your authorization token has expired`

**解決策:** ECRに再ログインしてください
```bash
aws ecr get-login-password --region us-east-1 --profile sandbox | \
  docker login --username AWS --password-stdin \
  715841358122.dkr.ecr.us-east-1.amazonaws.com
```

#### 3. ARM64 ビルドができない

**症状:** `exec user process caused: exec format error`

**解決策:** `--platform linux/arm64` を指定してください
```bash
docker buildx build --platform linux/arm64 ...
```

### Runtime 関連

#### 1. エージェントが応答しない

**確認事項:**
- Runtime のステータスが `ACTIVE` か確認
- CloudWatch Logs でエラーを確認: `/aws/bedrock-agentcore/runtimes/...`
- JWTトークンが有効か確認

#### 2. ツールが使えない

**確認事項:**
- Gateway URL が正しいか確認
- JWTトークンに必要な権限があるか確認
- Gateway側でツールが有効になっているか確認

### Observability 関連

#### 1. トレースが表示されない

**確認事項:**
- CloudWatch Transaction Search が有効か確認
- 有効化後、約10分待つ
- `strands-agents[otel]` と `aws-opentelemetry-distro` がインストールされているか確認
- 最新のDockerイメージがデプロイされているか確認

#### 2. カスタム属性が表示されない

**確認事項:**
- `backend/src/main.py` で `trace_attributes` が設定されているか確認
- Runtime に最新イメージがデプロイされているか確認

---

## プロジェクト構成

```
agentcore-identity1122/
├── README.md                      # このファイル
├── OBSERVABILITY.md               # Observability詳細ガイド
├── frontend/
│   ├── app.py                    # Streamlit フロントエンド
│   ├── requirements.txt          # Streamlit用依存パッケージ
│   └── runtime.py                # Runtime呼び出しヘルパー
├── backend/
│   ├── src/                      # アプリケーションコード
│   │   ├── main.py               # エージェントメイン
│   │   ├── memory.py             # Memory統合
│   │   ├── gateway.py            # Gateway統合
│   │   └── observability.py      # Observability設定
│   ├── Dockerfile                # コンテナイメージ定義
│   └── requirements.txt          # 依存パッケージ
└── .streamlit/
    └── secrets.toml              # Streamlit設定（gitignore）
```

---

## 参考リンク

### 公式ドキュメント

- [AWS AgentCore ドキュメント](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html)
- [Strands Agents SDK](https://strandsagents.com/latest/)
- [AgentCore Observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html)
- [CloudWatch Transaction Search](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Enable-TransactionSearch.html)

### 関連技術

- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/)
- [OpenTelemetry](https://opentelemetry.io/)
- [Streamlit](https://streamlit.io/)

---

## ライセンス

このプロジェクトは学習・開発目的で作成されています。

---

## お問い合わせ

質問や問題がある場合は、プロジェクトの Issue を作成してください。
