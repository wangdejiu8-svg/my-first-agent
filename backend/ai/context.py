from dataclasses import dataclass


@dataclass(frozen=True)
class AgentContext:
    user_id: str
    conversation_id: str
    thread_id: str
    request_id: str | None = None


def build_agent_config(user, conversation, request_id=None):
    return {
        "configurable": {
            "user_id": str(user.id),
            "conversation_id": str(conversation.id),
            "thread_id": f"conversation-{conversation.id}",
            "request_id": request_id,
        },
        "metadata": {
            "source": "api",
            "conversation_id": str(conversation.id),
        },
    }


def get_agent_context(config):
    configurable = (config or {}).get("configurable") or {}
    user_id = configurable.get("user_id")
    conversation_id = configurable.get("conversation_id")
    thread_id = configurable.get("thread_id")

    if not user_id:
        raise ValueError("缺少用户上下文。")
    if not conversation_id:
        raise ValueError("缺少会话上下文。")
    if not thread_id:
        raise ValueError("缺少线程上下文。")

    return AgentContext(
        user_id=str(user_id),
        conversation_id=str(conversation_id),
        thread_id=str(thread_id),
        request_id=configurable.get("request_id"),
    )
