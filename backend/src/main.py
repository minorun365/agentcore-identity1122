"""
AgentCore Runtime用のStrandsエージェント（Gateway統合 + Memory）

学習内容:
- Strandsエージェントの基本構造
- Gateway MCPクライアントとの統合
- OAuth2 Bearer Token認証
- AgentCore Memory（短期記憶）による会話履歴管理
"""

from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from agentcore.memory import create_session_manager

app = BedrockAgentCoreApp()

# AgentCore Memory設定
MEMORY_ID = "identity1122-chChJ7CEmJ"
REGION_NAME = "us-east-1"

@app.entrypoint
def invoke(payload):
    """
    Gateway統合 + Memory対応のAIエージェント

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
        return {
            "result": {
                "content": [{
                    "text": "エラー: access_tokenまたはgateway_urlが指定されていません"
                }]
            }
        }

    if not session_id or not actor_id:
        return {
            "result": {
                "content": [{
                    "text": "エラー: session_idまたはactor_idが指定されていません"
                }]
            }
        }

    # AgentCore MemoryのSessionManagerを作成
    session_manager = create_session_manager(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        region=REGION_NAME
    )

    # MCPクライアントでGatewayに接続
    mcp_client = MCPClient(
        lambda: streamablehttp_client(
            gateway_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
    )

    # Gatewayからツールを取得してエージェントを実行
    with mcp_client:
        # Gateway経由で利用可能なツール（Tavily検索など）を取得
        tools = mcp_client.list_tools_sync()

        # Strandsエージェント作成（SessionManagerで会話履歴を管理）
        agent = Agent(
            model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            tools=tools,
            session_manager=session_manager,  # 会話履歴を保持
            # CloudWatchトレースにカスタム属性を追加
            trace_attributes={
                "session.id": session_id,
                "actor.id": actor_id,
                "gateway.url": gateway_url,
                "memory.id": MEMORY_ID,
                "region": REGION_NAME
            }
        )

        # エージェント実行
        result = agent(user_message)

        # result.messageからテキストを抽出
        if isinstance(result.message, dict) and 'content' in result.message:
            # content配列からtextを抽出
            text_content = "".join([
                item.get('text', '')
                for item in result.message['content']
                if isinstance(item, dict) and 'text' in item
            ])
        else:
            # フォールバック: 文字列として扱う
            text_content = str(result.message)

        return {
            "result": {
                "content": [{
                    "text": text_content
                }]
            }
        }

if __name__ == "__main__":
    app.run()
