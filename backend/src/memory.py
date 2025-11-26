"""
AgentCore Memory - 会話履歴の永続化（バックエンド用）

AgentCore Memoryは、エージェントとユーザーの会話履歴を永続的に保存する機能です。
バックエンドでは、Strands AgentsのSessionManagerを通じて自動的に履歴を保存します。

主な機能:
- 会話履歴の自動保存
- セッション単位での履歴管理
- ユーザー（actor_id）ごとの履歴分離
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
        memory_id: AgentCore MemoryのID（AWSコンソールで作成）
        session_id: セッションID（会話スレッドの識別子、UUID推奨）
        actor_id: アクターID（ユーザー識別子、Cognito sub推奨）
        region: AWSリージョン

    Returns:
        AgentCoreMemorySessionManager: 会話履歴を管理するSessionManager

    使用例:
        session_manager = create_session_manager(
            memory_id="my-memory-id",
            session_id="uuid-session-id",
            actor_id="cognito-sub"
        )
        agent = Agent(model=MODEL_ID, session_manager=session_manager)
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
