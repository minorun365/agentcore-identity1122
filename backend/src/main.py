from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from .memory import create_session_manager
from .gateway import create_gateway_client
from .observability import create_trace_attributes

app = BedrockAgentCoreApp()

# AgentCore Memory設定
MEMORY_ID = "identity1122-chChJ7CEmJ"
REGION_NAME = "us-east-1"

@app.entrypoint
async def invoke(payload):
    """
    Gateway統合 + Memory対応のAIエージェント（ストリーミング対応）

    Args:
        payload: {
            "prompt": ユーザーのメッセージ,
            "access_token": Cognito JWTアクセストークン,
            "gateway_url": Gateway MCP URL,
            "session_id": セッションID（会話の継続性を保つ）,
            "actor_id": アクターID（ユーザー識別子）
        }
    """
    user_message = payload.get("prompt", "Hello!")
    access_token = payload.get("access_token")
    gateway_url = payload.get("gateway_url")
    session_id = payload.get("session_id")
    actor_id = payload.get("actor_id")

    if not access_token or not gateway_url:
        yield "エラー: access_tokenまたはgateway_urlが指定されていません"
        return

    if not session_id or not actor_id:
        yield "エラー: session_idまたはactor_idが指定されていません"
        return

    # AgentCore MemoryのSessionManagerを作成
    session_manager = create_session_manager(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        region=REGION_NAME
    )

    # MCPクライアントでGatewayに接続
    mcp_client = create_gateway_client(gateway_url, access_token)

    # Gatewayからツールを取得してエージェントを実行
    with mcp_client:
        # Gateway経由で利用可能なツール（Tavily検索など）を取得
        tools = mcp_client.list_tools_sync()

        # Strandsエージェント作成（SessionManagerで会話履歴を管理）
        agent = Agent(
            model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            tools=tools,
            session_manager=session_manager,  # 会話履歴を保持
            # CloudWatchトレースにカスタム属性を追加
            trace_attributes=create_trace_attributes(
                session_id=session_id,
                actor_id=actor_id,
                gateway_url=gateway_url,
                memory_id=MEMORY_ID,
                region=REGION_NAME
            )
        )

        # ストリーミングでエージェント実行
        stream = agent.stream_async(user_message)
        async for event in stream:
            yield event

if __name__ == "__main__":
    app.run()
