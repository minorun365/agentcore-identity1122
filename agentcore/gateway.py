"""
AgentCore Gateway機能
MCPサーバーとツールの統合を担当

学習内容:
- OAuth2 Client Credentials Grant（機械間認証）
- MCP (Model Context Protocol) Client
- Streamable HTTP Transport
- Tool Discovery & Invocation
"""

import requests
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client


def fetch_access_token(client_id: str, client_secret: str, token_url: str) -> str:
    """
    OAuth2 Client Credentials Grantでアクセストークンを取得

    Args:
        client_id: CognitoアプリクライアントID
        client_secret: Cognitoアプリクライアントシークレット
        token_url: トークンエンドポイントURL

    Returns:
        str: アクセストークン
    """
    response = requests.post(
        token_url,
        data=f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}",
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    return response.json()['access_token']


def list_gateway_tools(gateway_url: str, client_id: str, client_secret: str, token_url: str) -> list:
    """
    AgentCore Gatewayから利用可能なツールのリストを取得

    Args:
        gateway_url: Gateway MCP URL
        client_id: CognitoアプリクライアントID
        client_secret: Cognitoアプリクライアントシークレット
        token_url: トークンエンドポイントURL

    Returns:
        list: ツールのリスト
    """
    # アクセストークンを取得
    access_token = fetch_access_token(client_id, client_secret, token_url)

    # MCPクライアントを作成
    mcp_client = MCPClient(
        lambda: streamablehttp_client(gateway_url, headers={"Authorization": f"Bearer {access_token}"})
    )

    with mcp_client:
        # ページネーション対応でツールリストを取得
        tools = []
        pagination_token = None

        while True:
            tmp_tools = mcp_client.list_tools_sync(pagination_token=pagination_token)
            tools.extend(tmp_tools)

            if tmp_tools.pagination_token is None:
                break

            pagination_token = tmp_tools.pagination_token

        return tools


def invoke_gateway_tool(
    gateway_url: str,
    tool_name: str,
    tool_arguments: dict,
    client_id: str,
    client_secret: str,
    token_url: str
):
    """
    AgentCore Gateway経由でツールを実行

    Args:
        gateway_url: Gateway MCP URL
        tool_name: 実行するツール名
        tool_arguments: ツールの引数
        client_id: CognitoアプリクライアントID
        client_secret: Cognitoアプリクライアントシークレット
        token_url: トークンエンドポイントURL

    Returns:
        ツールの実行結果
    """
    # アクセストークンを取得
    access_token = fetch_access_token(client_id, client_secret, token_url)

    # MCPクライアントを作成
    mcp_client = MCPClient(
        lambda: streamablehttp_client(gateway_url, headers={"Authorization": f"Bearer {access_token}"})
    )

    with mcp_client:
        # ツールを実行
        result = mcp_client.call_tool_sync(
            tool_name=tool_name,
            arguments=tool_arguments
        )

        return result
