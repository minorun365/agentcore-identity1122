"""
AgentCore Runtime機能
エージェントの実行とレスポンス処理を担当
"""

import json
import urllib.parse
import requests


def invoke_agent(
    agent_arn: str,
    prompt: str,
    access_token: str,
    session_id: str,
    gateway_url: str,
    region: str = "us-east-1",
    **kwargs
) -> str:
    """
    AgentCore Runtimeでエージェントを実行する

    Args:
        agent_arn: AgentCore RuntimeのARN
        prompt: ユーザーのプロンプト
        access_token: JWTアクセストークン（Cognito）
        session_id: セッションID（会話の継続性を保つ）
        gateway_url: Gateway MCP URL（Runtime内でGateway接続に使用）
        region: AWSリージョン
        **kwargs: その他のペイロード

    Returns:
        str: エージェントからのレスポンステキスト
    """
    # エンドポイントURL構築
    escaped_agent_arn = urllib.parse.quote(agent_arn, safe='')
    url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{escaped_agent_arn}/invocations?qualifier=DEFAULT"

    # リクエスト送信
    # Runtime内でGatewayに接続するため、access_tokenとgateway_urlをpayloadに含める
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id
        },
        json={
            "prompt": prompt,
            "access_token": access_token,
            "gateway_url": gateway_url,
            **kwargs
        }
    )

    # レスポンス解析
    result = response.json()
    full_text = "".join([
        item["text"]
        for item in result["result"]["content"]
        if "text" in item
    ])

    return full_text
