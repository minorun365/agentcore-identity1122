# AgentCore Identity 統合アプリケーション

Amazon Bedrock AgentCoreの各機能を統合したAIエージェントのサンプルです。

## AgentCore機能

| 機能 | 説明 | ファイル |
|------|------|---------|
| **Identity** | Cognito認証、外部サービスOAuth2連携 | `backend/src/identity.py` |
| **Runtime** | エージェント実行環境 | `backend/src/main.py` |
| **Gateway** | MCPツール統合 | `backend/src/gateway.py` |
| **Memory** | 会話履歴管理 | `backend/src/memory.py` |
| **Observability** | CloudWatchトレース | `backend/src/observability.py` |

## クイックスタート

```bash
# 1. 依存パッケージをインストール
pip install -r frontend/requirements.txt

# 2. 設定ファイルを作成
cp frontend/.streamlit/secrets.toml.example frontend/.streamlit/secrets.toml
# secrets.toml を編集

# 3. Streamlitアプリを起動
streamlit run frontend/app.py
```

## デプロイ

詳細は [DEPLOY.md](./DEPLOY.md) を参照。

```bash
# ECRログイン → ビルド → プッシュ → Runtime更新
aws ecr get-login-password --region us-east-1 --profile sandbox | \
  docker login --username AWS --password-stdin 715841358122.dkr.ecr.us-east-1.amazonaws.com

docker buildx build --platform linux/arm64 \
  -t 715841358122.dkr.ecr.us-east-1.amazonaws.com/identity1122-agent:latest \
  -f backend/Dockerfile .

docker push 715841358122.dkr.ecr.us-east-1.amazonaws.com/identity1122-agent:latest
```

## 外部サービス連携（Confluence）

AgentCore Identityを使ったOAuth2認証のサンプルが`backend/src/identity.py`に含まれています。

### 設定手順

1. [Atlassian Developer Console](https://developer.atlassian.com/console/myapps/)でアプリ作成
2. OAuth 2.0 (3LO) でコールバックURLを設定:
   ```
   https://bedrock-agentcore.us-east-1.amazonaws.com/identities/oauth2/callback
   ```
3. AgentCore IdentityにOAuth2プロバイダーを作成:
   ```bash
   aws bedrock-agentcore-control create-oauth2-credential-provider \
     --region us-east-1 \
     --name "atlassian-confluence" \
     --credential-provider-vendor "AtlassianOAuth2" \
     --oauth2-provider-config-input '{
       "atlassianOauth2ProviderConfig": {
         "clientId": "<your-client-id>",
         "clientSecret": "<your-client-secret>"
       }
     }' \
     --profile sandbox
   ```

## 参考リンク

- [AWS AgentCore ドキュメント](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html)
- [Strands Agents SDK](https://strandsagents.com/latest/)
