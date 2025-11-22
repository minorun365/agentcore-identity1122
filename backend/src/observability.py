from typing import Dict, Any


def create_trace_attributes(
    session_id: str,
    actor_id: str,
    gateway_url: str,
    memory_id: str,
    region: str
) -> Dict[str, Any]:
    """
    CloudWatch トレースに追加するカスタム属性を作成

    Args:
        session_id: セッション ID（会話の継続性を保つ）
        actor_id: アクター ID（ユーザー識別子）
        gateway_url: Gateway MCP URL
        memory_id: AgentCore Memory ID
        region: AWS リージョン

    Returns:
        Dict[str, Any]: トレース属性の辞書
    """
    return {
        "session.id": session_id,
        "actor.id": actor_id,
        "gateway.url": gateway_url,
        "memory.id": memory_id,
        "region": region
    }