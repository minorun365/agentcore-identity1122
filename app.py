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

            # リクエストヘッダー（ストリーミングを要求）
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",  # ストリーミングレスポンスを要求
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

            # レスポンスのContent-Typeを確認
            content_type = response.headers.get('content-type', '')

            # Content-Typeに応じて処理を分岐
            if 'text/event-stream' in content_type:
                # ストリーミングレスポンス（SSE形式）
                container = st.container()
                text_holder = container.empty()
                buffer = ""

                # レスポンスを1行ずつチェック
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")

                        if line_str.startswith("data: "):
                            data = line_str[6:]

                            # 読み込んだ行をJSONに変換
                            try:
                                event = json.loads(data)
                            except json.JSONDecodeError:
                                continue

                            # テキストコンテンツを検出（イベントの構造を確認）
                            if isinstance(event, dict):
                                # パターン1: {"event": "text content"}
                                if "event" in event:
                                    if isinstance(event["event"], str):
                                        buffer += event["event"]
                                        text_holder.markdown(buffer)
                                    # パターン2: {"event": {"contentBlockDelta": {"delta": {"text": "..."}}}}
                                    elif isinstance(event["event"], dict) and "contentBlockDelta" in event["event"]:
                                        delta_text = event["event"]["contentBlockDelta"].get("delta", {}).get("text", "")
                                        buffer += delta_text
                                        text_holder.markdown(buffer)
                                # パターン3: {"data": "text content"}
                                elif "data" in event and isinstance(event["data"], str):
                                    buffer += event["data"]
                                    text_holder.markdown(buffer)
                                # パターン4: {"text": "text content"}
                                elif "text" in event and isinstance(event["text"], str):
                                    buffer += event["text"]
                                    text_holder.markdown(buffer)

                # 最後に残ったテキストを表示
                if buffer:
                    text_holder.markdown(buffer)

            elif 'application/json' in content_type:
                # 通常のJSONレスポンス（フォールバック）
                try:
                    result = response.json()

                    # result.content[].text からテキストを抽出
                    if "result" in result and "content" in result["result"]:
                        full_text = ""
                        for content_item in result["result"]["content"]:
                            if "text" in content_item:
                                full_text += content_item["text"]

                        if full_text:
                            st.markdown(full_text)
                        else:
                            st.warning("テキストコンテンツが見つかりませんでした。")
                    else:
                        st.warning("想定外のレスポンス形式です。")
                        st.json(result)

                except Exception as e:
                    st.error(f"JSONパースエラー: {e}")

            else:
                st.error(f"サポートされていないContent-Type: {content_type}")
                st.text(response.text[:500])
            ### ------------------------------------------------------------------------------

# メイン処理を実行
main_app()
