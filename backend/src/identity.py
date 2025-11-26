"""
AgentCore Identity - 認証・認可管理（バックエンド用）

AgentCore Identityは、エージェントへのアクセス制御を提供します。

主な機能:
1. Cognito認証: JWTトークンによるユーザー識別
"""

from typing import Optional


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
