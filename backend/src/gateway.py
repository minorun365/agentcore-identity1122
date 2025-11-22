from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client


def create_gateway_client(gateway_url: str, access_token: str) -> MCPClient:
    """
    Gateway MCP クライアントを作成

    Args:
        gateway_url: Gateway MCP の URL
        access_token: JWT アクセストークン（Cognito）

    Returns:
        MCPClient: Gateway に接続する MCP クライアント
    """
    mcp_client = MCPClient(
        lambda: streamablehttp_client(
            gateway_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
    )
    return mcp_client