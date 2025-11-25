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
    AgentCore Runtimeでエージェントを実行し、ストリーミングでレスポンスを返す

    Args:
        agent_arn: AgentCore RuntimeのARN
        prompt: ユーザーのプロンプト
        access_token: JWTアクセストークン（Cognito）
        session_id: セッションID（会話の継続性を保つ）
        actor_id: アクターID（ユーザー識別子、通常はCognitoのusername）
        gateway_url: Gateway MCP URL（Runtime内でGateway接続に使用）
        region: AWSリージョン
        **kwargs: その他のペイロード

    Yields:
        dict: ストリーミングイベント（"text", "tool_use", "error"のいずれか）
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

    # デバッグ: HTTPステータスとヘッダー
    yield {"type": "debug", "message": f"HTTP {response.status_code}, Content-Type: {response.headers.get('Content-Type', 'N/A')}"}

    # HTTPエラーチェック
    if response.status_code != 200:
        yield {"type": "error", "message": f"HTTP {response.status_code}: {response.text[:500]}"}
        return

    # レスポンスを1行ずつ処理
    line_count = 0
    for line in response.iter_lines():
        line_count += 1
        # 最初の5行をデバッグ出力
        if line_count <= 5:
            yield {"type": "debug", "message": f"Line {line_count}: {str(line)[:150]}"}

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


def invoke_agent(
    agent_arn: str,
    prompt: str,
    access_token: str,
    session_id: str,
    actor_id: str,
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
        actor_id: アクターID（ユーザー識別子、通常はCognitoのusername）
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
            "session_id": session_id,
            "actor_id": actor_id,
            **kwargs
        }
    )

    # レスポンス解析
    result = response.json()

    # エラーハンドリング：レスポンスにresultキーがない場合
    if "result" not in result:
        error_message = f"エラーレスポンス: {json.dumps(result, indent=2, ensure_ascii=False)}"
        raise Exception(error_message)

    full_text = "".join([
        item["text"]
        for item in result["result"]["content"]
        if "text" in item
    ])

    return full_text
