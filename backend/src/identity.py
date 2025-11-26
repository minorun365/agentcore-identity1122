"""
AgentCore Identity - 認証・認可管理（バックエンド用）

AgentCore Identityは、エージェントへのアクセス制御と外部サービス連携を提供します。

主な機能:
1. Cognito認証: JWTトークンによるユーザー識別
2. 外部サービス連携: OAuth2による外部API（Confluence等）へのアクセス
"""

from typing import Optional
from strands import tool
from bedrock_agentcore.identity.auth import requires_access_token
import httpx


# =============================================================================
# Cognito認証
# =============================================================================

def extract_actor_id(access_token: str) -> Optional[str]:
    """
    JWTアクセストークンからactor_id（ユーザー識別子）を抽出

    注意: 本番環境では、JWTの署名検証を行うべきです。
    AgentCore Runtimeは自動的にトークン検証を行うため、
    ここでは簡易的にペイロードからユーザー名を取得します。

    Args:
        access_token: Cognito JWTアクセストークン

    Returns:
        actor_id: ユーザー識別子（usernameまたはsub）
    """
    import base64
    import json

    try:
        # JWTのペイロード部分をデコード（署名検証は省略）
        payload_part = access_token.split(".")[1]
        # Base64URLデコード（パディング追加）
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_part))

        # usernameまたはsubを返す
        return payload.get("username") or payload.get("sub")

    except Exception:
        return None


def validate_identity_params(access_token: str, actor_id: str, session_id: str) -> Optional[str]:
    """
    Identity関連のパラメータを検証

    Args:
        access_token: JWTアクセストークン
        actor_id: アクターID
        session_id: セッションID

    Returns:
        エラーメッセージ（問題がなければNone）
    """
    if not access_token:
        return "access_tokenが指定されていません"

    if not actor_id:
        return "actor_idが指定されていません"

    if not session_id:
        return "session_idが指定されていません"

    # session_idは33文字以上が推奨（UUIDなど）
    if len(session_id) < 33:
        return "session_idは33文字以上にしてください（UUIDを推奨）"

    return None


# =============================================================================
# 外部サービス連携（Confluence）
# =============================================================================

# Atlassian OAuth2プロバイダー名（AgentCore Identityで作成）
ATLASSIAN_PROVIDER_NAME = "atlassian-oauth"
CONFLUENCE_SCOPES = ["read:confluence-content.all", "read:confluence-space.summary", "offline_access"]

# Atlassian Cloud ID（環境変数から取得）
import os
ATLASSIAN_CLOUD_ID = os.environ.get("ATLASSIAN_CLOUD_ID", "")



async def _search_confluence_impl(query: str, limit: int, access_token: str) -> str:
    """Confluence検索の実装（トークン取得後に呼ばれる）"""
    if not ATLASSIAN_CLOUD_ID:
        return "エラー: ATLASSIAN_CLOUD_ID が設定されていません"

    url = f"https://api.atlassian.com/ex/confluence/{ATLASSIAN_CLOUD_ID}/wiki/rest/api/content/search"
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    params = {"cql": query, "limit": limit, "expand": "space,version"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return f"エラー: HTTP {response.status_code} - {response.text}"

        results = response.json().get("results", [])
        if not results:
            return f"'{query}' に一致するページが見つかりません"

        output = f"検索結果: {len(results)}件\n"
        for page in results:
            output += f"- {page.get('title')} (ID: {page.get('id')})\n"
        return output


async def _get_confluence_page_impl(page_id: str, access_token: str) -> str:
    """Confluenceページ取得の実装（トークン取得後に呼ばれる）"""
    if not ATLASSIAN_CLOUD_ID:
        return "エラー: ATLASSIAN_CLOUD_ID が設定されていません"

    url = f"https://api.atlassian.com/ex/confluence/{ATLASSIAN_CLOUD_ID}/wiki/rest/api/content/{page_id}"
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    params = {"expand": "body.storage,space,version"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return f"エラー: HTTP {response.status_code} - {response.text}"

        page = response.json()
        body_html = page.get("body", {}).get("storage", {}).get("value", "")

        import re
        body_text = re.sub(r'<[^>]+>', '', body_html)[:2000]

        return f"""
タイトル: {page.get('title')}
スペース: {page.get('space', {}).get('name')}

内容:
{body_text}
"""


@tool
async def search_confluence(query: str, limit: int = 10) -> str:
    """
    Confluenceでページを検索します。

    Args:
        query: 検索クエリ（CQL形式、例: "text ~ 'キーワード'"）
        limit: 取得するページ数
    """
    @requires_access_token(
        provider_name=ATLASSIAN_PROVIDER_NAME,
        scopes=CONFLUENCE_SCOPES,
        auth_flow="CLIENT_CREDENTIALS",
    )
    async def execute(*, access_token: str) -> str:
        return await _search_confluence_impl(query, limit, access_token)

    return await execute(access_token="")


@tool
async def get_confluence_page(page_id: str) -> str:
    """
    Confluenceの特定ページの内容を取得します。

    Args:
        page_id: ConfluenceページID
    """
    @requires_access_token(
        provider_name=ATLASSIAN_PROVIDER_NAME,
        scopes=CONFLUENCE_SCOPES,
        auth_flow="CLIENT_CREDENTIALS",
    )
    async def execute(*, access_token: str) -> str:
        return await _get_confluence_page_impl(page_id, access_token)

    return await execute(access_token="")


def get_confluence_tools():
    """Confluenceツールのリストを返す"""
    return [search_confluence, get_confluence_page]
