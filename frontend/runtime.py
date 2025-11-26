import json
import urllib.parse
from typing import Generator, List, Dict, Any
import requests
import boto3


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


def list_memory_sessions(
    memory_id: str,
    actor_id: str,
    region: str = "us-east-1",
    max_results: int = 50,
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None
) -> List[Dict[str, Any]]:
    """
    AgentCore Memoryから指定アクターのセッション一覧を取得

    Args:
        memory_id: AgentCore MemoryのID
        actor_id: アクターID（ユーザー識別子）
        region: AWSリージョン
        max_results: 最大取得件数
        aws_access_key_id: AWSアクセスキーID（オプション）
        aws_secret_access_key: AWSシークレットアクセスキー（オプション）

    Returns:
        List[Dict]: セッション一覧（sessionId, actorId, createdAt含む）
    """
    try:
        # AWS認証情報が指定されている場合はそれを使用
        if aws_access_key_id and aws_secret_access_key:
            client = boto3.client(
                'bedrock-agentcore',
                region_name=region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
        else:
            client = boto3.client('bedrock-agentcore', region_name=region)

        sessions = []
        next_token = None

        while True:
            params = {
                'memoryId': memory_id,
                'actorId': actor_id,
                'maxResults': max_results
            }
            if next_token:
                params['nextToken'] = next_token

            response = client.list_sessions(**params)

            sessions.extend(response.get('sessionSummaries', []))

            next_token = response.get('nextToken')
            if not next_token:
                break

        return sessions

    except Exception as e:
        # エラーの場合は空のリストを返す（ローカル管理にフォールバック）
        print(f"Warning: Failed to list sessions from AgentCore Memory: {e}")
        return []
