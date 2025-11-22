# 必要なライブラリをインポート
import boto3, json
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
            # AgentCoreランタイムを呼び出し
            agentcore = boto3.client('bedrock-agentcore')
            payload = json.dumps({
                "prompt": prompt,
                "tavily_api_key": st.secrets["TAVILY_API_KEY"]
            })
            response = agentcore.invoke_agent_runtime(
                agentRuntimeArn=st.secrets["AGENT_RUNTIME_ARN"],
                payload=payload.encode()
            )

            ### ここから下はストリーミングレスポンスの処理 ------------------------------------------
            container = st.container()
            text_holder = container.empty()
            buffer = ""

            # レスポンスを1行ずつチェック
            for line in response["response"].iter_lines():
                if line and line.decode("utf-8").startswith("data: "):
                    data = line.decode("utf-8")[6:]

                    # 文字列コンテンツの場合は無視
                    if data.startswith('"') or data.startswith("'"):
                        continue

                    # 読み込んだ行をJSONに変換
                    event = json.loads(data)

                    # ツール利用を検出
                    if "event" in event and "contentBlockStart" in event["event"]:
                        if "toolUse" in event["event"]["contentBlockStart"].get("start", {}):
                            # 現在のテキストを確定
                            if buffer:
                                text_holder.markdown(buffer)
                                buffer = ""
                            # ツールステータスを表示
                            container.info("🔍 Tavily検索ツールを利用しています")
                            text_holder = container.empty()

                    # テキストコンテンツを検出
                    if "data" in event and isinstance(event["data"], str):
                        buffer += event["data"]
                        text_holder.markdown(buffer)
                    elif "event" in event and "contentBlockDelta" in event["event"]:
                        buffer += event["event"]["contentBlockDelta"]["delta"].get("text", "")
                        text_holder.markdown(buffer)

            # 最後に残ったテキストを表示
            text_holder.markdown(buffer)
            ### ------------------------------------------------------------------------------

# メイン処理を実行
main_app()
