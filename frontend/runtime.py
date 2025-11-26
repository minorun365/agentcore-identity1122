"""
AgentCore Runtime - エージェント実行（フロントエンド用）

AgentCore Runtimeは、エージェントをホストして実行するための機能です。
フロントエンドでは、デプロイされたエージェントを呼び出してレスポンスを取得します。

主な機能:
- エージェントの実行（ストリーミングレスポンス）
- ツール利用状況の検出
"""

import json
import urllib.parse
from typing import Generator
import requests


def invoke_agent_stream(
    agent_arn: str,
    prompt: str,
    access_token: str,
    session_id: str,
    actor_id: str,
    gateway_url: str,
    region: str = "us-east-1",
    **kwargs
) -> Generator[dict, None, None]:
    """
    AgentCore Runtimeでエージェントを実行（ストリーミング）

    Args:
        agent_arn: AgentCore RuntimeのARN
        prompt: ユーザーのプロンプト
        access_token: JWTアクセストークン（Cognito Identity経由）
        session_id: セッションID（AgentCore Memory用）
        actor_id: アクターID（AgentCore Memory用ユーザー識別子）
        gateway_url: Gateway MCP URL（AgentCore Gateway経由でツール接続）
        region: AWSリージョン
        **kwargs: その他のペイロード

    Yields:
        dict: ストリーミングイベント
            - {"type": "text", "text": str} - テキスト出力
            - {"type": "tool_use", "tool_name": str} - ツール利用開始
            - {"type": "error", "message": str} - エラー発生
    """
    # エンドポイントURL構築
    escaped_agent_arn = urllib.parse.quote(agent_arn, safe='')
    url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{escaped_agent_arn}/invocations?qualifier=DEFAULT"

    # リクエスト送信（ストリーミングモード）
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
            "session_id": session_id,
            "actor_id": actor_id,
            **kwargs
        },
        stream=True
    )

    # HTTPエラーチェック
    if response.status_code != 200:
        yield {"type": "error", "message": f"HTTP {response.status_code}: {response.text[:500]}"}
        return

    # ストリーミングレスポンスを1行ずつ処理
    for line in response.iter_lines():
        if not line:
            continue

        decoded_line = line.decode("utf-8")
        if not decoded_line.startswith("data: "):
            continue

        data = decoded_line[6:]

        # 文字列コンテンツの場合は無視
        if data.startswith('"') or data.startswith("'"):
            continue

        try:
            event = json.loads(data)

            # ツール利用を検出
            if "event" in event and "contentBlockStart" in event["event"]:
                if "toolUse" in event["event"]["contentBlockStart"].get("start", {}):
                    tool_name = event["event"]["contentBlockStart"]["start"]["toolUse"].get("name", "unknown")
                    yield {"type": "tool_use", "tool_name": tool_name}

            # テキストコンテンツを検出
            if "data" in event and isinstance(event["data"], str):
                yield {"type": "text", "text": event["data"]}
            elif "event" in event and "contentBlockDelta" in event["event"]:
                text = event["event"]["contentBlockDelta"]["delta"].get("text", "")
                if text:
                    yield {"type": "text", "text": text}

        except json.JSONDecodeError:
            continue
