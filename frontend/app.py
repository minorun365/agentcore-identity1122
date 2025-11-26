# 必要なライブラリをインポート
import uuid
import streamlit as st
from streamlit_cognito_auth import CognitoAuthenticator

# AgentCoreランタイム呼び出しモジュールをインポート
from runtime import invoke_agent_stream, list_memory_sessions, list_session_events

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
    # ユーザー名を取得
    username = authenticator.get_username()

    # スレッド一覧を初期化
    if "threads" not in st.session_state:
        st.session_state.threads = {}  # {session_id: {"title": str, "messages": list}}

    # 現在のスレッドIDを初期化
    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = None

    # AgentCore Memoryからセッション一覧を取得済みフラグ
    if "memory_sessions_loaded" not in st.session_state:
        st.session_state.memory_sessions_loaded = False

    # 初回のみAgentCore Memoryからセッション一覧を取得
    if not st.session_state.memory_sessions_loaded:
        memory_id = st.secrets.get("MEMORY_ID")
        if memory_id:
            memory_sessions = list_memory_sessions(
                memory_id=memory_id,
                actor_id=username,
                region=st.secrets.get("AWS_DEFAULT_REGION", "us-east-1"),
                aws_access_key_id=st.secrets.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=st.secrets.get("AWS_SECRET_ACCESS_KEY"),
                aws_session_token=st.secrets.get("AWS_SESSION_TOKEN")
            )
            # 取得したセッションをスレッド一覧に追加
            for session in memory_sessions:
                session_id = session.get("sessionId")
                if session_id and session_id not in st.session_state.threads:
                    created_at = session.get("createdAt", "")
                    # タイトルは作成日時を使用（後で最初のメッセージで更新される）
                    title = created_at[:10] if created_at else "過去の会話"
                    st.session_state.threads[session_id] = {"title": title, "messages": []}
        st.session_state.memory_sessions_loaded = True

    # サイドバー：ユーザー情報とスレッド一覧
    with st.sidebar:
        st.subheader("ユーザーID")
        st.write(username)
        if st.button("ログアウト", use_container_width=True):
            authenticator.logout()

        st.subheader("会話履歴")

        # 新規スレッド作成ボタン
        if st.button("新しい会話", use_container_width=True, type="primary"):
            new_id = str(uuid.uuid4())
            st.session_state.threads[new_id] = {"title": "新しい会話", "messages": []}
            st.session_state.current_thread_id = new_id
            st.rerun()

        # スレッド一覧を表示（新しい順）
        sorted_threads = sorted(
            st.session_state.threads.items(),
            key=lambda x: x[0],
            reverse=True
        )
        for thread_id, thread_data in sorted_threads:
            is_current = thread_id == st.session_state.current_thread_id
            if is_current:
                label = "▶ 現在の会話"
            else:
                label = thread_data["title"]
            if st.button(label, key=thread_id, use_container_width=True):
                st.session_state.current_thread_id = thread_id
                st.rerun()

    # 現在のスレッドがない場合は作成
    if st.session_state.current_thread_id is None:
        new_id = str(uuid.uuid4())
        st.session_state.threads[new_id] = {"title": "新しい会話", "messages": []}
        st.session_state.current_thread_id = new_id

    # 現在のスレッドのメッセージを取得
    current_thread = st.session_state.threads[st.session_state.current_thread_id]
    messages = current_thread["messages"]

    # メッセージが空の場合、AgentCore Memoryから会話履歴を取得
    memory_id = st.secrets.get("MEMORY_ID")
    if not messages and memory_id:
        loaded_messages = list_session_events(
            memory_id=memory_id,
            actor_id=username,
            session_id=st.session_state.current_thread_id,
            region=st.secrets.get("AWS_DEFAULT_REGION", "us-east-1"),
            aws_access_key_id=st.secrets.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=st.secrets.get("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=st.secrets.get("AWS_SESSION_TOKEN")
        )
        if loaded_messages:
            current_thread["messages"] = loaded_messages
            messages = current_thread["messages"]
            # タイトルを最初のユーザーメッセージで更新
            first_user_msg = next((m["content"] for m in messages if m["role"] == "user"), None)
            if first_user_msg:
                current_thread["title"] = first_user_msg[:20] + ("..." if len(first_user_msg) > 20 else "")

    # ヘッダー部分
    st.title("なんでも検索エージェント")

    st.write("Strands AgentsがMCPサーバーを使って情報収集します！")

    # 過去のチャット履歴を表示
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # チャットボックスを描画
    if prompt := st.chat_input("メッセージを入力してね"):
        # ユーザーのプロンプトを履歴に追加
        messages.append({"role": "user", "content": prompt})

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
                session_id=st.session_state.current_thread_id,
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

            # アシスタントの回答を履歴に追加
            if buffer:
                messages.append({"role": "assistant", "content": buffer})

                # スレッドタイトルを最初のユーザーメッセージで更新
                if current_thread["title"] == "新しい会話" and len(messages) >= 1:
                    first_user_msg = next((m["content"] for m in messages if m["role"] == "user"), None)
                    if first_user_msg:
                        current_thread["title"] = first_user_msg[:20] + ("..." if len(first_user_msg) > 20 else "")

# メイン処理を実行
main_app()
