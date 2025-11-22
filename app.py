# 必要なライブラリをインポート
import json
import urllib.parse
import uuid
import requests
import streamlit as st
from streamlit_cognito_auth import CognitoAuthenticator

# Cognito認証の設定
authenticator = CognitoAuthenticator(
    pool_id=st.secrets["COGNITO_USER_POOL_ID"],
    app_client_id=st.secrets["COGNITO_APP_CLIENT_ID"],
    app_client_secret=st.secrets["COGNITO_APP_CLIENT_SECRET"]
)

# ログイン処理
is_logged_in = authenticator.login()

if not is_logged_in:
    # ログインしていない場合は、ログインフォームが表示される
    st.stop()

# ログイン成功後のメインアプリケーション
def main_app():
    """メインアプリケーション"""
    # セッションIDを初期化（UUIDを使用して33文字以上を保証）
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    # ヘッダー部分（ユーザー名とログアウトボタン）
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("なんでも検索エージェント")
        username = authenticator.get_username()
        st.write(f"ようこそ、**{username}**さん！")
    with col2:
        if st.button("ログアウト"):
            authenticator.logout()

    st.write("Strands AgentsがMCPサーバーを使って情報収集します！")

    # チャットボックスを描画
    if prompt := st.chat_input("メッセージを入力してね"):
        # ユーザーのプロンプトを表示
        with st.chat_message("user"):
            st.markdown(prompt)

        # エージェントの回答を表示
        with st.chat_message("assistant"):
            # JWTトークンを取得
            access_token = authenticator.get_credentials().access_token

            # AgentCore RuntimeのエンドポイントURL構築
            region = st.secrets["AWS_DEFAULT_REGION"]
            agent_arn = st.secrets["AGENT_RUNTIME_ARN"]
            escaped_agent_arn = urllib.parse.quote(agent_arn, safe='')
            url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{escaped_agent_arn}/invocations?qualifier=DEFAULT"

            # HTTPS POSTリクエスト
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": st.session_state.session_id
                },
                json={
                    "prompt": prompt,
                    "tavily_api_key": st.secrets["TAVILY_API_KEY"]
                }
            )

            # レスポンスを表示
            result = response.json()
            full_text = "".join([item["text"] for item in result["result"]["content"] if "text" in item])
            st.markdown(full_text)

# メイン処理を実行
main_app()
