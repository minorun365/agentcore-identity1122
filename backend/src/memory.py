"""
AgentCore Memory機能
会話履歴の管理を担当

学習内容:
- AgentCore Memory（短期記憶）の設定
- Strands AgentsとMemoryの統合
- Session Manager（会話履歴の永続化）
"""

from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager


def create_session_manager(
    memory_id: str,
    session_id: str,
    actor_id: str,
    region: str = "us-east-1"
) -> AgentCoreMemorySessionManager:
    """
    AgentCore MemoryのSessionManagerを作成

    このSessionManagerをStrandsエージェントに渡すことで、
    会話履歴が自動的にAgentCore Memoryに保存されます。

    Args:
        memory_id: AgentCore MemoryのID
        session_id: セッションID（会話の継続性を保つ）
        actor_id: アクターID（ユーザー識別子）
        region: AWSリージョン

    Returns:
        AgentCoreMemorySessionManager: 会話履歴を管理するSessionManager
    """
    # Memory設定
    memory_config = AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id,
        actor_id=actor_id
    )

    # SessionManager作成
    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=memory_config,
        region_name=region
    )

    return session_manager
