"""
AgentCore Memory - 会話履歴の永続化（フロントエンド用）

AgentCore Memoryは、エージェントとユーザーの会話履歴を永続的に保存する機能です。
フロントエンドでは、保存された会話履歴の取得と表示を行います。

主な機能:
- セッション一覧の取得（ユーザーの過去の会話スレッド）
- セッション内の会話履歴の取得
"""

import json
from typing import List, Dict, Any
import boto3


def list_sessions(
    memory_id: str,
    actor_id: str,
    region: str = "us-east-1",
    max_results: int = 50,
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None,
    aws_session_token: str = None
) -> List[Dict[str, Any]]:
    """
    指定ユーザーのセッション一覧を取得

    Args:
        memory_id: AgentCore MemoryのID
        actor_id: アクターID（ユーザー識別子）
        region: AWSリージョン
        max_results: 最大取得件数
        aws_access_key_id: AWSアクセスキーID（オプション）
        aws_secret_access_key: AWSシークレットアクセスキー（オプション）
        aws_session_token: AWSセッショントークン（オプション）

    Returns:
        List[Dict]: セッション一覧（sessionId, actorId, createdAt含む）
    """
    try:
        # AWS認証情報でクライアント作成
        client_params = {'region_name': region}
        if aws_access_key_id and aws_secret_access_key:
            client_params['aws_access_key_id'] = aws_access_key_id
            client_params['aws_secret_access_key'] = aws_secret_access_key
            if aws_session_token:
                client_params['aws_session_token'] = aws_session_token

        client = boto3.client('bedrock-agentcore', **client_params)

        # ページネーションでセッション一覧を取得
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
        print(f"Warning: Failed to list sessions from AgentCore Memory: {e}")
        return []


def list_messages(
    memory_id: str,
    actor_id: str,
    session_id: str,
    region: str = "us-east-1",
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None,
    aws_session_token: str = None
) -> List[Dict[str, Any]]:
    """
    指定セッションの会話履歴を取得

    Args:
        memory_id: AgentCore MemoryのID
        actor_id: アクターID（ユーザー識別子）
        session_id: セッションID
        region: AWSリージョン
        aws_access_key_id: AWSアクセスキーID（オプション）
        aws_secret_access_key: AWSシークレットアクセスキー（オプション）
        aws_session_token: AWSセッショントークン（オプション）

    Returns:
        List[Dict]: メッセージ一覧（role, content形式）
    """
    try:
        # AWS認証情報でクライアント作成
        client_params = {'region_name': region}
        if aws_access_key_id and aws_secret_access_key:
            client_params['aws_access_key_id'] = aws_access_key_id
            client_params['aws_secret_access_key'] = aws_secret_access_key
            if aws_session_token:
                client_params['aws_session_token'] = aws_session_token

        client = boto3.client('bedrock-agentcore', **client_params)

        # ページネーションでイベント一覧を取得
        events = []
        next_token = None

        while True:
            params = {
                'memoryId': memory_id,
                'actorId': actor_id,
                'sessionId': session_id,
                'includePayloads': True
            }
            if next_token:
                params['nextToken'] = next_token

            response = client.list_events(**params)
            events.extend(response.get('events', []))

            next_token = response.get('nextToken')
            if not next_token:
                break

        # イベントを古い順にソート（会話の時系列順）
        events_sorted = sorted(events, key=lambda e: e.get('eventTimestamp', ''))

        # イベントをメッセージ形式に変換
        messages = []
        for event in events_sorted:
            message = _parse_event_to_message(event)
            if message:
                messages.append(message)

        return messages

    except Exception as e:
        print(f"Warning: Failed to list messages from AgentCore Memory: {e}")
        return []


def _parse_event_to_message(event: Dict) -> Dict[str, str] | None:
    """
    AgentCore Memoryのイベントをメッセージ形式に変換

    textキーを持つメッセージのみを抽出（toolUse/toolResultは除外）

    Args:
        event: AgentCore Memoryのイベント

    Returns:
        Dict: {"role": "user"|"assistant", "content": str} または None
    """
    payload = event.get('payload', [])

    for item in payload:
        if 'conversational' not in item:
            continue

        conv = item['conversational']
        role_raw = conv.get('role', 'USER')
        role = 'user' if role_raw == 'USER' else 'assistant'
        text_raw = conv.get('content', {}).get('text', '')

        if not text_raw:
            continue

        # textがJSON文字列の場合、パースして実際のコンテンツを取得
        content = _extract_text_content(text_raw)

        if content:
            return {'role': role, 'content': content}

    return None


def _extract_text_content(text_raw: str) -> str:
    """
    JSON形式のテキストから実際のコンテンツを抽出

    AgentCore Memoryに保存されるメッセージは以下の形式:
    {"message": {"content": [{"text": "実際のテキスト"}]}}

    toolUse/toolResultは除外し、textのみを抽出する

    Args:
        text_raw: 生のテキスト（JSON文字列またはプレーンテキスト）

    Returns:
        str: 抽出されたテキスト（textがない場合は空文字）
    """
    try:
        parsed = json.loads(text_raw)

        # message.content[0] の形式を解析
        if 'message' in parsed and 'content' in parsed['message']:
            content_list = parsed['message']['content']
            if isinstance(content_list, list) and len(content_list) > 0:
                first_content = content_list[0]
                # textキーがある場合のみ（toolUse/toolResultは除外）
                if 'text' in first_content:
                    return first_content['text']

        return ''

    except json.JSONDecodeError:
        # JSONでなければプレーンテキストとして返す
        return text_raw
