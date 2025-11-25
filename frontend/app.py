# 必要なライブラリをインポート
import uuid
import streamlit as st
from streamlit_cognito_auth import CognitoAuthenticator

# AgentCore機能をインポート
from runtime import invoke_agent_stream

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
            container = st.container()
            text_holder = container.empty()
            buffer = ""

            # AgentCore Runtimeでエージェントを実行（ストリーミング）
            for event in invoke_agent_stream(
                agent_arn=st.secrets["AGENT_RUNTIME_ARN"],
                prompt=prompt,
                access_token=authenticator.get_credentials().access_token,
                session_id=st.session_state.session_id,
                actor_id=username,
                gateway_url=st.secrets["GATEWAY_URL"],
                region=st.secrets["AWS_DEFAULT_REGION"]
            ):
                if event["type"] == "error":
                    st.error(f"エラー: {event.get('message', 'Unknown error')}")
                    break

                elif event["type"] == "tool_use":
                    # 現在のテキストを確定
                    if buffer:
                        text_holder.markdown(buffer)
                        buffer = ""
                    # ツールステータスを表示
                    tool_name = event.get("tool_name", "unknown")
                    container.info(f"🔍 {tool_name} ツールを利用しています")
                    text_holder = container.empty()

                elif event["type"] == "text":
                    buffer += event["text"]
                    text_holder.markdown(buffer)

            # 最後に残ったテキストを表示
            text_holder.markdown(buffer)

# メイン処理を実行
main_app()
