"""
AgentCore Runtime用のStrandsエージェント（Gateway統合）

学習内容:
- Strandsエージェントの基本構造
- Gateway MCPクライアントとの統合
- OAuth2 Bearer Token認証
"""

from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload):
    """
    Gateway統合したAIエージェント

    Args:
        payload: {
            "prompt": ユーザーのメッセージ,
            "access_token": Cognito JWTアクセストークン,
            "gateway_url": Gateway MCP URL
        }
    """
    user_message = payload.get("prompt", "Hello!")
    access_token = payload.get("access_token")
    gateway_url = payload.get("gateway_url")

    if not access_token or not gateway_url:
        return {
            "result": {
                "content": [{
                    "text": "エラー: access_tokenまたはgateway_urlが指定されていません"
                }]
            }
        }

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

        # Strandsエージェントを作成
        agent = Agent(
            model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            tools=tools
        )

        # エージェント実行
        result = agent(user_message)

        # result.messageからテキストを抽出
        # Strandsエージェントはresult.messageが辞書形式 {'role': 'assistant', 'content': [{'text': '...'}]}
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
