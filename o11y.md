# AgentCore Observability セットアップガイド

このドキュメントでは、AgentCore Runtime に Observability（可観測性）を組み込む方法を説明します。

## 📊 Observability とは？

AgentCore Observability により、以下の情報を CloudWatch で確認できるようになります：

- 🔄 **トレース**: エージェントの実行フロー全体（LLM呼び出し、ツール実行など）
- 📊 **メトリクス**: レイテンシ、トークン使用量、エラー率
- 📝 **ログ**: 詳細な実行ログ
- 👤 **カスタム属性**: セッションID、ユーザーIDなどのビジネス情報

---

## 🚀 セットアップ手順

### ステップ1: CloudWatch Transaction Search を有効化（初回のみ）

この手順は **AWS アカウントごとに1回だけ** 実行します。

#### オプション1: CloudWatch コンソールから有効化（推奨）

1. [CloudWatch コンソール](https://console.aws.amazon.com/cloudwatch/) を開く
2. 左のナビゲーションで **Application Signals** > **Transaction Search** を選択
3. **「Enable Transaction Search」** をクリック
4. 「Ingest spans as structured logs」にチェック
5. インデックス化する割合を入力（デフォルト: 1%、無料枠内）
6. **Save** をクリック

**⚠️ 注意**: 有効化後、スパンが検索可能になるまで約 **10分** かかります。

#### オプション2: AWS CLI から有効化

```bash
# 1. CloudWatch Logs へのアクセスポリシー作成
aws logs put-resource-policy \
  --policy-name TransactionSearchXRayAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "TransactionSearchXRayAccess",
      "Effect": "Allow",
      "Principal": {"Service": "xray.amazonaws.com"},
      "Action": "logs:PutLogEvents",
      "Resource": [
        "arn:aws:logs:us-east-1:YOUR-ACCOUNT-ID:log-group:aws/spans:*",
        "arn:aws:logs:us-east-1:YOUR-ACCOUNT-ID:log-group:/aws/application-signals/data:*"
      ],
      "Condition": {
        "ArnLike": {"aws:SourceArn": "arn:aws:xray:us-east-1:YOUR-ACCOUNT-ID:*"},
        "StringEquals": {"aws:SourceAccount": "YOUR-ACCOUNT-ID"}
      }
    }]
  }'

# 2. トレースセグメントの送信先を CloudWatch に設定
aws xray update-trace-segment-destination --destination CloudWatchLogs

# 3. （オプション）サンプリング率を設定（デフォルト: 1%）
aws xray update-indexing-rule \
  --name "Default" \
  --rule '{"Probabilistic": {"DesiredSamplingPercentage": 1}}'
```

**YOUR-ACCOUNT-ID** を実際の AWS アカウント ID に置き換えてください。

---

### ステップ2: 依存パッケージの確認

`agent/requirements.txt` に以下のパッケージが含まれていることを確認してください：

```txt
bedrock-agentcore[strands-agents]
strands-agents[otel]           # ← Strands がトレースを生成
aws-opentelemetry-distro       # ← トレースを CloudWatch に送信
mcp
```

**✅ このプロジェクトでは既に設定済みです！**

---

### ステップ3: コードの確認

`agent/app.py` で以下のカスタム属性が設定されていることを確認してください：

```python
agent = Agent(
    model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    tools=tools,
    session_manager=session_manager,
    # CloudWatch トレースにカスタム属性を追加
    trace_attributes={
        "session.id": session_id,      # セッション識別
        "actor.id": actor_id,           # ユーザー識別
        "gateway.url": gateway_url,     # Gateway URL
        "memory.id": MEMORY_ID,         # Memory リソース ID
        "region": REGION_NAME           # AWS リージョン
    }
)
```

**✅ このプロジェクトでは既に設定済みです！**

---

### ステップ4: AgentCore Runtime へデプロイ

AgentCore Runtime にデプロイすると、**自動的に Observability が有効化**されます。

#### デプロイ方法

```bash
# Starter Toolkit を使う場合
agentcore configure --entrypoint agent/app.py
agentcore launch

# または boto3 を使って手動デプロイ
python deploy_script.py
```

#### デプロイ後の自動設定

AgentCore Runtime は以下を**自動的に実行**します：

- OpenTelemetry の環境変数設定
- `opentelemetry-instrument` コマンドの実行
- CloudWatch へのトレース送信

**コード変更や環境変数設定は不要です！**

---

## 📈 CloudWatch で Observability データを確認

### GenAI Observability ダッシュボード

1. [GenAI Observability on CloudWatch](https://console.aws.amazon.com/cloudwatch/home#gen-ai-observability) を開く
2. **Bedrock AgentCore** タブを選択
3. 以下のビューが利用可能：
   - **Agents View**: エージェント一覧とメトリクス
   - **Sessions View**: セッション一覧（`session.id` でフィルタ可能）
   - **Traces View**: トレース詳細（タイムラインと実行フロー）

### 確認できる情報

#### トレース情報
- エージェント全体の実行フロー
- LLM 呼び出し（プロンプト、レスポンス、トークン数）
- ツール実行（パラメータ、結果、実行時間）
- Gateway MCP との通信

#### メトリクス
- レイテンシ（Time to First Byte, Time to Last Byte）
- トークン使用量（入力・出力・キャッシュ）
- エラー率
- ツール呼び出し回数

#### カスタム属性
- `session.id`: セッション識別子
- `actor.id`: アクター（ユーザー）識別子
- `gateway.url`: Gateway MCP の URL
- `memory.id`: AgentCore Memory リソース ID
- `region`: AWS リージョン

---

## 🔍 トレースの例

CloudWatch でトレースを確認すると、以下のような階層構造が表示されます：

```
└─ Strands Agent
   ├─ Cycle 1
   │  ├─ Model Invoke (Claude)
   │  └─ Tool: Tavily Search
   │     └─ Gateway MCP Request
   ├─ Cycle 2
   │  └─ Model Invoke (Claude)
   └─ Result
```

各スパンをクリックすると、詳細情報が確認できます：
- 実行時間
- 入力パラメータ
- 出力結果
- エラー情報（ある場合）

---

## ⚙️ 高度な設定（オプション）

### サンプリング率の調整

すべてのトレースを記録するとコストが増加するため、サンプリング率を調整できます：

```bash
# X-Ray のサンプリング率を 10% に設定
aws xray update-indexing-rule \
  --name "Default" \
  --rule '{"Probabilistic": {"DesiredSamplingPercentage": 10}}'
```

### CloudWatch アラームの設定

重要なメトリクスにアラームを設定できます：

1. CloudWatch コンソールで **Alarms** > **Create alarm** を選択
2. メトリクスを選択（例: エラー率、レイテンシ）
3. しきい値を設定（例: エラー率 > 5%）
4. 通知先を設定（SNS トピック）

---

## 💰 コストについて

### 無料枠
- CloudWatch Transaction Search: 1% サンプリングまで無料
- CloudWatch Logs: 月5GB まで無料
- X-Ray トレース: 月100,000 トレースまで無料

### 料金が発生するケース
- サンプリング率を上げる（1% 以上）
- ログ保存量が 5GB を超える
- トレース数が 100,000 を超える

**推奨**: 本番環境では 1-5% のサンプリング率が一般的です。

---

## 🔒 セキュリティとプライバシー

### PII（個人識別情報）の保護

トレースには個人情報が含まれないよう注意してください：

- ❌ ユーザーのメールアドレス、電話番号
- ❌ クレジットカード番号
- ❌ パスワードやAPIキー

**✅ 代わりに使用するもの**:
- ユーザーID（UUID など）
- セッションID（ランダムな識別子）

### データ保持期間

CloudWatch Logs のデフォルト保持期間は **無期限** です。不要なデータを削除するには：

1. CloudWatch コンソールで Log Groups を開く
2. `/aws/bedrock-agentcore/...` を選択
3. **Actions** > **Edit retention setting**
4. 保持期間を設定（例: 30日、90日）

---

## 🐛 トラブルシューティング

### トレースが表示されない

1. **CloudWatch Transaction Search が有効か確認**
   - CloudWatch コンソール > Application Signals > Transaction Search
   - 有効化後、約10分待つ

2. **requirements.txt を確認**
   - `strands-agents[otel]` が含まれているか
   - `aws-opentelemetry-distro` が含まれているか

3. **デプロイを確認**
   - AgentCore Runtime に正しくデプロイされているか
   - エージェントが実行されているか

### エラーが発生する

CloudWatch Logs でエラー詳細を確認：
1. CloudWatch コンソール > Logs > Log groups
2. `/aws/bedrock-agentcore/runtimes/...` を開く
3. エラーメッセージを確認

---

## 📚 参考リンク

- [AWS AgentCore Observability 公式ドキュメント](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html)
- [Strands Agents Observability ドキュメント](https://strandsagents.com/latest/documentation/docs/user-guide/observability-evaluation/observability/)
- [CloudWatch Transaction Search](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Enable-TransactionSearch.html)
- [OpenTelemetry 公式サイト](https://opentelemetry.io/)

---

## ✅ チェックリスト

実装が完了したら、以下を確認してください：

- [ ] CloudWatch Transaction Search を有効化した
- [ ] `agent/requirements.txt` に `strands-agents[otel]` と `aws-opentelemetry-distro` が含まれている
- [ ] `agent/app.py` に `trace_attributes` が設定されている
- [ ] AgentCore Runtime にデプロイした
- [ ] CloudWatch でトレースが確認できる
- [ ] GenAI Observability ダッシュボードでエージェントが表示される

---

以上で AgentCore Observability のセットアップは完了です！🎉
