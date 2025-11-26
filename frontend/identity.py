"""
AgentCore Identity - Cognito認証連携（フロントエンド用）

AgentCore Identityは、エージェントへのアクセスを制御する認証・認可機能です。
フロントエンドでは、Cognitoを使ったユーザー認証とJWTトークンの処理を行います。

主な機能:
- Cognito認証の初期化とログイン処理
- JWTアクセストークンからユーザー情報を抽出
- actor_id（AgentCore Memory用のユーザー識別子）の取得
- OAuth2 3LOコールバック処理（外部サービス連携用）
"""

import base64
import json
import boto3
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


# =============================================================================
# OAuth2 3LO コールバック処理（外部サービス連携）
# =============================================================================

def handle_oauth2_callback(actor_id: str) -> bool:
    """
    OAuth2 3LOコールバックを処理する

    AgentCore IdentityのUSER_FEDERATIONフローで、外部サービス（Atlassian等）の
    認証完了後にリダイレクトされてきた場合、CompleteResourceTokenAuthを呼び出して
    トークン取得を完了させる。

    Args:
        actor_id: ユーザー識別子（Cognito sub）

    Returns:
        bool: コールバック処理を実行した場合True
    """
    # クエリパラメータからsession_idを取得
    query_params = st.query_params
    session_id = query_params.get("session_id")

    if not session_id:
        return False

    # コールバック処理中であることを表示
    with st.spinner("外部サービスの認証を完了しています..."):
        try:
            # AWS認証情報
            region = st.secrets.get("AWS_DEFAULT_REGION", "us-east-1")

            # AgentCore クライアント（Identity機能を含む）
            client = boto3.client(
                "bedrock-agentcore",
                region_name=region,
                aws_access_key_id=st.secrets.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=st.secrets.get("AWS_SECRET_ACCESS_KEY"),
                aws_session_token=st.secrets.get("AWS_SESSION_TOKEN")
            )

            # CompleteResourceTokenAuth を呼び出し
            client.complete_resource_token_auth(
                sessionUri=session_id,
                userIdentifier={
                    "userId": actor_id
                }
            )

            # クエリパラメータをクリア
            st.query_params.clear()

            st.success("外部サービスの認証が完了しました！もう一度検索してください。")
            return True

        except Exception as e:
            st.error(f"認証完了処理でエラーが発生しました: {e}")
            # エラーでもクエリパラメータはクリア
            st.query_params.clear()
            return True

    return False
