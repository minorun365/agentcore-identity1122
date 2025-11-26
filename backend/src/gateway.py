"""
AgentCore Gateway - MCPツールの統合管理（バックエンド用）

AgentCore Gatewayは、複数のMCPサーバーを統合管理する機能です。
エージェントは、Gatewayを経由して様々なツール（Web検索、ファイル操作など）を利用できます。

主な機能:
- MCPサーバーへの接続管理
- ツール呼び出しの中継
- 認証トークンの伝播
"""

from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client


def create_gateway_client(gateway_url: str, access_token: str) -> MCPClient:
    """
    Gateway MCPクライアントを作成

    Gatewayに接続し、登録されているMCPツールを利用可能にします。
    認証にはCognitoのJWTトークンを使用します。

    Args:
        gateway_url: Gateway MCPのURL
        access_token: JWTアクセストークン（Cognito Identity経由）

    Returns:
        MCPClient: Gatewayに接続するMCPクライアント

    使用例:
        mcp_client = create_gateway_client(gateway_url, access_token)
        with mcp_client:
            tools = mcp_client.list_tools_sync()
            # ツールを使ってエージェントを実行
    """
    mcp_client = MCPClient(
        lambda: streamablehttp_client(
            gateway_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
    )
    return mcp_client