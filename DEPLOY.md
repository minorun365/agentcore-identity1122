# デプロイ手順

このドキュメントでは、AgentCore Runtimeへのデプロイ手順を説明します。

## 前提条件

- AWS CLI v2 がインストール済み
- Docker がインストール済み
- AWS SSO プロファイル `sandbox` が設定済み

---

## クイックデプロイ（全ステップ一括）

```bash
# 1. AWS認証
aws sso login --profile sandbox
export AWS_PROFILE=sandbox

# 2. ECRログイン
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  715841358122.dkr.ecr.us-east-1.amazonaws.com

# 3. ビルド＆プッシュ
docker buildx build --platform linux/arm64 \
  -t 715841358122.dkr.ecr.us-east-1.amazonaws.com/identity1122-agent:latest \
  -f backend/Dockerfile .

docker push 715841358122.dkr.ecr.us-east-1.amazonaws.com/identity1122-agent:latest

# 4. Runtime更新
aws bedrock-agentcore-control update-agent-runtime \
  --region "us-east-1" \
  --agent-runtime-id "hosted_agent_kogc7-b1Enyl6XB6" \
  --agent-runtime-artifact "containerConfiguration={containerUri=715841358122.dkr.ecr.us-east-1.amazonaws.com/identity1122-agent:latest}" \
  --role-arn "arn:aws:iam::715841358122:role/service-role/AmazonBedrockAgentCoreRuntimeDefaultServiceRole-9js7z" \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --authorizer-configuration '{
    "customJWTAuthorizer": {
      "discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_hALafr7YC/.well-known/openid-configuration",
      "allowedClients": ["55u30q7bfb0fbj48qavmer0a1m"]
    }
  }'

# 5. 完了確認
aws bedrock-agentcore-control get-agent-runtime \
  --region us-east-1 \
  --agent-runtime-id hosted_agent_kogc7-b1Enyl6XB6 \
  --query '[status, authorizerConfiguration]' \
  --output json
```

---

## 詳細手順

### ステップ1: AWS SSO ログイン

```bash
aws sso login --profile sandbox
export AWS_PROFILE=sandbox
```

### ステップ2: ECR にログイン

```bash
aws ecr get-login-password --region us-east-1 | \
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

**注意点:**
- ARM64アーキテクチャが必須（AgentCore Runtimeの要件）
- プロジェクトルートからビルドすること
- Dockerfileは `backend/Dockerfile` を使用

### ステップ4: AgentCore Runtime を更新

```bash
aws bedrock-agentcore-control update-agent-runtime \
  --region "us-east-1" \
  --agent-runtime-id "hosted_agent_kogc7-b1Enyl6XB6" \
  --agent-runtime-artifact "containerConfiguration={containerUri=715841358122.dkr.ecr.us-east-1.amazonaws.com/identity1122-agent:latest}" \
  --role-arn "arn:aws:iam::715841358122:role/service-role/AmazonBedrockAgentCoreRuntimeDefaultServiceRole-9js7z" \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --authorizer-configuration '{
    "customJWTAuthorizer": {
      "discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_hALafr7YC/.well-known/openid-configuration",
      "allowedClients": ["55u30q7bfb0fbj48qavmer0a1m"]
    }
  }'
```

**重要: `--authorizer-configuration` を必ず指定すること！**

このパラメータを省略すると、認証タイプがデフォルトの `IAM許可` に戻ってしまい、Cognito JWT認証が無効になります。

### ステップ5: デプロイ完了を確認

```bash
aws bedrock-agentcore-control get-agent-runtime \
  --region us-east-1 \
  --agent-runtime-id hosted_agent_kogc7-b1Enyl6XB6 \
  --query '[status, authorizerConfiguration]' \
  --output json
```

以下のように表示されればOKです：

```json
[
    "READY",
    {
        "customJWTAuthorizer": {
            "discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_hALafr7YC/.well-known/openid-configuration",
            "allowedClients": ["55u30q7bfb0fbj48qavmer0a1m"]
        }
    }
]
```

---

## パラメータ一覧

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| Runtime ID | `hosted_agent_kogc7-b1Enyl6XB6` | AgentCore RuntimeのID |
| ECR URI | `715841358122.dkr.ecr.us-east-1.amazonaws.com/identity1122-agent:latest` | コンテナイメージURI |
| IAM Role | `AmazonBedrockAgentCoreRuntimeDefaultServiceRole-9js7z` | Runtime実行ロール |
| User Pool ID | `us-east-1_hALafr7YC` | Cognito User Pool |
| Client ID | `55u30q7bfb0fbj48qavmer0a1m` | Cognito App Client |
| Region | `us-east-1` | AWSリージョン |

---

## トラブルシューティング

### Docker ビルドが失敗する

**症状:** `no such file or directory: backend/requirements.txt`

**解決策:** プロジェクトルートからビルドしてください
```bash
# ❌ 間違い
cd backend && docker build -f Dockerfile .

# ✅ 正しい
docker buildx build -f backend/Dockerfile .
```

### ECR push が失敗する

**症状:** `denied: Your authorization token has expired`

**解決策:** ECRに再ログインしてください
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  715841358122.dkr.ecr.us-east-1.amazonaws.com
```

### 認証エラー（403）が発生する

**症状:** `Authorization method mismatch`

**原因:** `--authorizer-configuration` を指定せずにデプロイしたため、認証タイプが `IAM許可` になっている

**解決策:** `--authorizer-configuration` を含めて再デプロイしてください

### Runtime が UPDATING のまま

**解決策:** 数分待ってからステータスを再確認してください
```bash
aws bedrock-agentcore-control get-agent-runtime \
  --region us-east-1 \
  --agent-runtime-id hosted_agent_kogc7-b1Enyl6XB6 \
  --query 'status' \
  --output text
```
