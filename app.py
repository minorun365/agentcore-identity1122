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
            credentials = authenticator.get_credentials()
            if not credentials:
                st.error("認証トークンが取得できませんでした。再ログインしてください。")
                st.stop()

            access_token = credentials.access_token

            # AgentCore RuntimeのエンドポイントURL構築
            region = st.secrets["AWS_DEFAULT_REGION"]
            agent_arn = st.secrets["AGENT_RUNTIME_ARN"]
            escaped_agent_arn = urllib.parse.quote(agent_arn, safe='')
            url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{escaped_agent_arn}/invocations?qualifier=DEFAULT"

            # リクエストヘッダー
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": st.session_state.session_id
            }

            # ペイロード
            payload = json.dumps({
                "prompt": prompt,
                "tavily_api_key": st.secrets["TAVILY_API_KEY"]
            })

            # HTTPS POSTリクエスト（ストリーミング）
            response = requests.post(url, headers=headers, data=payload, stream=True)

            ### ここから下はストリーミングレスポンスの処理 ------------------------------------------
            # HTTPステータスコードをチェック
            if response.status_code != 200:
                st.error(f"エラーが発生しました（ステータスコード: {response.status_code}）")
                try:
                    error_data = response.json()
                    st.error(f"エラー詳細: {json.dumps(error_data, indent=2)}")
                except:
                    st.error(f"レスポンス: {response.text}")
                st.stop()

            container = st.container()
            text_holder = container.empty()
            buffer = ""
            debug_lines = []  # デバッグ用

            # レスポンスのContent-Typeを確認
            content_type = response.headers.get('content-type', '')
            st.info(f"Content-Type: {content_type}")

            # レスポンスを1行ずつチェック
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    debug_lines.append(line_str[:100])  # デバッグ用：最初の100文字を保存

                    if line_str.startswith("data: "):
                        data = line_str[6:]

                        # 文字列コンテンツの場合は無視
                        if data.startswith('"') or data.startswith("'"):
                            continue

                        # 読み込んだ行をJSONに変換
                        try:
                            event = json.loads(data)
                            st.write(f"DEBUG - Event keys: {list(event.keys())}")  # デバッグ
                        except json.JSONDecodeError as e:
                            st.warning(f"JSON decode error: {e}, data: {data[:100]}")
                            continue

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

            # デバッグ情報を表示
            with st.expander("デバッグ情報（最初の10行）"):
                for i, line in enumerate(debug_lines[:10]):
                    st.text(f"{i}: {line}")

            # 最後に残ったテキストを表示
            if buffer:
                text_holder.markdown(buffer)
            else:
                st.warning("バッファが空です。レスポンスが正しく解析されていない可能性があります。")
            ### ------------------------------------------------------------------------------

# メイン処理を実行
main_app()
