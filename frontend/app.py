"""
なんでも検索エージェント - メインアプリケーション

AgentCoreの各機能を使用したチャットボットUIです。

使用するAgentCore機能:
- Identity: Cognito認証によるユーザー識別
- Runtime: エージェントの実行
- Memory: 会話履歴の永続化
- Gateway: MCPツールの統合（バックエンド側で使用）
"""

import uuid
import streamlit as st

# AgentCore機能モジュール
from identity import create_authenticator, get_user_info
from runtime import invoke_agent_stream
from memory import list_sessions, list_messages


# ========================================
# 認証処理（AgentCore Identity）
# ========================================

authenticator = create_authenticator()
is_logged_in = authenticator.login()

if not is_logged_in:
    st.stop()


# ========================================
# メインアプリケーション
# ========================================

def main_app():
    """メインアプリケーション"""

    # ユーザー情報を取得（Identity）
    user_info = get_user_info(authenticator)
    display_name = user_info["display_name"]
    access_token = user_info["access_token"]
    actor_id = user_info["actor_id"]

    # AWS認証情報（Memory API用）
    aws_credentials = {
        "region": st.secrets.get("AWS_DEFAULT_REGION", "us-east-1"),
        "aws_access_key_id": st.secrets.get("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": st.secrets.get("AWS_SECRET_ACCESS_KEY"),
        "aws_session_token": st.secrets.get("AWS_SESSION_TOKEN")
    }

    # ========================================
    # セッション状態の初期化
    # ========================================

    if "threads" not in st.session_state:
        st.session_state.threads = {}

    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = None

    if "memory_sessions_loaded" not in st.session_state:
        st.session_state.memory_sessions_loaded = False

    # ========================================
    # 会話履歴の読み込み（AgentCore Memory）
    # ========================================

    memory_id = st.secrets.get("MEMORY_ID")

    # 初回のみセッション一覧を取得
    if not st.session_state.memory_sessions_loaded and memory_id:
        sessions = list_sessions(
            memory_id=memory_id,
            actor_id=actor_id,
            **aws_credentials
        )
        # スレッド一覧に追加
        for session in sessions:
            session_id = session.get("sessionId")
            if session_id and session_id not in st.session_state.threads:
                created_at = session.get("createdAt")
                if created_at and hasattr(created_at, "strftime"):
                    title = created_at.strftime("%Y-%m-%d")
                elif created_at:
                    title = str(created_at)[:10]
                else:
                    title = "過去の会話"
                st.session_state.threads[session_id] = {"title": title, "messages": []}
        st.session_state.memory_sessions_loaded = True

    # ========================================
    # サイドバー（ユーザー情報・スレッド一覧）
    # ========================================

    with st.sidebar:
        st.subheader("ユーザーID")
        st.write(display_name)
        if st.button("ログアウト", use_container_width=True):
            authenticator.logout()

        st.subheader("会話履歴")

        # 新規スレッド作成
        if st.button("新しい会話", use_container_width=True, type="primary"):
            new_id = str(uuid.uuid4())
            st.session_state.threads[new_id] = {"title": "新しい会話", "messages": []}
            st.session_state.current_thread_id = new_id
            st.rerun()

        # スレッド一覧（新しい順）
        sorted_threads = sorted(
            st.session_state.threads.items(),
            key=lambda x: x[0],
            reverse=True
        )
        for thread_id, thread_data in sorted_threads:
            is_current = thread_id == st.session_state.current_thread_id
            label = "▶ 現在の会話" if is_current else thread_data["title"]
            if st.button(label, key=thread_id, use_container_width=True):
                st.session_state.current_thread_id = thread_id
                st.rerun()

    # ========================================
    # 現在のスレッド選択
    # ========================================

    if st.session_state.current_thread_id is None:
        if st.session_state.threads:
            latest_thread_id = sorted(st.session_state.threads.keys(), reverse=True)[0]
            st.session_state.current_thread_id = latest_thread_id
        else:
            new_id = str(uuid.uuid4())
            st.session_state.threads[new_id] = {"title": "新しい会話", "messages": []}
            st.session_state.current_thread_id = new_id

    current_thread = st.session_state.threads[st.session_state.current_thread_id]
    messages = current_thread["messages"]

    # メッセージが空の場合、Memoryから会話履歴を取得
    if not messages and memory_id:
        loaded_messages = list_messages(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=st.session_state.current_thread_id,
            **aws_credentials
        )
        if loaded_messages:
            current_thread["messages"] = loaded_messages
            messages = current_thread["messages"]
            # タイトルを最初のユーザーメッセージで更新
            first_user_msg = next((m["content"] for m in messages if m["role"] == "user"), None)
            if first_user_msg:
                current_thread["title"] = first_user_msg[:20] + ("..." if len(first_user_msg) > 20 else "")

    # ========================================
    # チャットUI
    # ========================================

    st.title("なんでも検索エージェント")
    st.write("Strands AgentsがMCPサーバーを使って情報収集します！")

    # 過去のチャット履歴を表示
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # チャット入力
    if prompt := st.chat_input("メッセージを入力してね"):
        messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # ========================================
        # エージェント実行（AgentCore Runtime）
        # ========================================

        with st.chat_message("assistant"):
            container = st.container()
            text_holder = container.empty()
            buffer = ""

            for event in invoke_agent_stream(
                agent_arn=st.secrets["AGENT_RUNTIME_ARN"],
                prompt=prompt,
                access_token=access_token,
                session_id=st.session_state.current_thread_id,
                actor_id=actor_id,
                gateway_url=st.secrets["GATEWAY_URL"],
                region=st.secrets["AWS_DEFAULT_REGION"]
            ):
                if event["type"] == "error":
                    st.error(f"エラー: {event.get('message', 'Unknown error')}")
                    break

                elif event["type"] == "tool_use":
                    if buffer:
                        text_holder.markdown(buffer)
                        buffer = ""
                    tool_name = event.get("tool_name", "unknown")
                    container.info(f"🔍 {tool_name} ツールを利用しています")
                    text_holder = container.empty()

                elif event["type"] == "text":
                    buffer += event["text"]
                    text_holder.markdown(buffer)

            text_holder.markdown(buffer)

            if buffer:
                messages.append({"role": "assistant", "content": buffer})

                # スレッドタイトルを更新
                if current_thread["title"] == "新しい会話":
                    first_user_msg = next((m["content"] for m in messages if m["role"] == "user"), None)
                    if first_user_msg:
                        current_thread["title"] = first_user_msg[:20] + ("..." if len(first_user_msg) > 20 else "")


# メイン処理
main_app()
