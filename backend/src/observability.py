"""
AgentCore Observability - 監視・トレース（バックエンド用）

AgentCore Observabilityは、エージェントの実行状況を監視する機能です。
CloudWatch Logsやメトリクスと連携して、トレース情報を収集します。

主な機能:
- 実行トレースの記録
- カスタム属性の付与
- CloudWatchへの連携
"""

from typing import Dict, Any


def create_trace_attributes(
    session_id: str,
    actor_id: str,
    gateway_url: str,
    memory_id: str,
    region: str
) -> Dict[str, Any]:
    """
    CloudWatchトレースに追加するカスタム属性を作成

    これらの属性はCloudWatch Logsに記録され、
    ログ検索やデバッグに活用できます。

    Args:
        session_id: セッションID（会話スレッドの識別子）
        actor_id: アクターID（ユーザー識別子）
        gateway_url: Gateway MCP URL
        memory_id: AgentCore Memory ID
        region: AWSリージョン

    Returns:
        Dict[str, Any]: トレース属性の辞書

    CloudWatchでの活用例:
        - session.idでフィルタして特定会話のログを追跡
        - actor.idでフィルタして特定ユーザーの履歴を確認
    """
    return {
        "session.id": session_id,
        "actor.id": actor_id,
        "gateway.url": gateway_url,
        "memory.id": memory_id,
        "region": region
    }