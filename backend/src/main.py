"""
AgentCore Runtime - メインエントリーポイント

このファイルは、AgentCoreの各機能を統合してエージェントを実行します。

使用するAgentCore機能:
- Runtime: エージェントのホスティングとスケーリング
- Identity: Cognito認証によるアクセス制御
- Gateway: MCPツールの統合管理
- Memory: 会話履歴の永続化
- Observability: CloudWatchによる監視
"""

from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

# 各AgentCore機能モジュール
from .identity import validate_identity_params
from .gateway import create_gateway_client
from .memory import create_session_manager
from .observability import create_trace_attributes

# AgentCoreアプリケーション
app = BedrockAgentCoreApp()

# 設定
MEMORY_ID = "identity1122-chChJ7CEmJ"
REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


@app.entrypoint
async def invoke(payload):
    """
    エージェント実行エントリーポイント

    Args:
        payload: {
            "prompt": ユーザーのメッセージ,
            "access_token": Cognito JWTアクセストークン,
            "gateway_url": Gateway MCP URL,
            "session_id": セッションID,
            "actor_id": アクターID（ユーザー識別子）
        }
    """
    # ペイロードから値を取得
    prompt = payload.get("prompt", "Hello!")
    access_token = payload.get("access_token")
    gateway_url = payload.get("gateway_url")
    session_id = payload.get("session_id")
    actor_id = payload.get("actor_id")

    # Identity: パラメータ検証
    error = validate_identity_params(access_token, actor_id, session_id)
    if error:
        yield f"エラー: {error}"
        return

    if not gateway_url:
        yield "エラー: gateway_urlが指定されていません"
        return

    # Memory: セッション管理
    session_manager = create_session_manager(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        region=REGION
    )

    # Gateway: MCPクライアント作成
    mcp_client = create_gateway_client(gateway_url, access_token)

    # エージェント実行
    with mcp_client:
        # Gateway MCPツール
        tools = mcp_client.list_tools_sync()

        agent = Agent(
            model=MODEL_ID,
            tools=tools,
            session_manager=session_manager,
            # Observability: トレース属性
            trace_attributes=create_trace_attributes(
                session_id=session_id,
                actor_id=actor_id,
                gateway_url=gateway_url,
                memory_id=MEMORY_ID,
                region=REGION
            )
        )

        # ストリーミング実行
        async for event in agent.stream_async(prompt):
            yield event


if __name__ == "__main__":
    app.run()
