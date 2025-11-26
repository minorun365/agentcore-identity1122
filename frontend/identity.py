"""
AgentCore Identity - Cognito認証連携（フロントエンド用）

AgentCore Identityは、エージェントへのアクセスを制御する認証・認可機能です。
フロントエンドでは、Cognitoを使ったユーザー認証とJWTトークンの処理を行います。

主な機能:
- Cognito認証の初期化とログイン処理
- JWTアクセストークンからユーザー情報を抽出
- actor_id（AgentCore Memory用のユーザー識別子）の取得
"""

import base64
import json
import streamlit as st
from streamlit_cognito_auth import CognitoAuthenticator


def create_authenticator() -> CognitoAuthenticator:
    """
    Cognito認証を初期化

    Returns:
        CognitoAuthenticator: 認証オブジェクト
    """
    return CognitoAuthenticator(
        pool_id=st.secrets["COGNITO_USER_POOL_ID"],
        app_client_id=st.secrets["COGNITO_APP_CLIENT_ID"],
        app_client_secret=st.secrets["COGNITO_APP_CLIENT_SECRET"]
    )


def get_actor_id(access_token: str) -> str:
    """
    JWTアクセストークンからactor_id（Cognito sub）を取得

    AgentCore Memoryでは、ユーザーを識別するためにactor_idを使用します。
    Cognitoの場合、sub（Subject）クレームがユーザーの一意識別子となります。

    Args:
        access_token: Cognito JWTアクセストークン

    Returns:
        actor_id: ユーザー識別子（Cognito sub）
    """
    try:
        # JWTの構造: header.payload.signature
        payload_part = access_token.split(".")[1]

        # Base64URLデコード（パディング追加）
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += "=" * padding

        payload = json.loads(base64.urlsafe_b64decode(payload_part))
        return payload.get("sub", "")

    except Exception:
        return ""


def get_user_info(authenticator: CognitoAuthenticator) -> dict:
    """
    認証済みユーザーの情報を取得

    Args:
        authenticator: CognitoAuthenticatorインスタンス

    Returns:
        dict: {
            "display_name": 表示用ユーザー名,
            "access_token": JWTアクセストークン,
            "actor_id": AgentCore Memory用ユーザー識別子
        }
    """
    display_name = authenticator.get_username()
    access_token = authenticator.get_credentials().access_token
    actor_id = get_actor_id(access_token)

    return {
        "display_name": display_name,
        "access_token": access_token,
        "actor_id": actor_id
    }
