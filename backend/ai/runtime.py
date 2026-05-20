from langchain_core.messages import AIMessage, HumanMessage

from apps.chat.models import Message

from .context import build_agent_config
from .graph import build_chat_graph


def invoke_chat_agent(user, conversation, request_id=None):
    graph = build_chat_graph(user=user, conversation=conversation)
    messages = _conversation_to_langchain_messages(conversation)
    result = graph.invoke(
        {"messages": messages},
        config=build_agent_config(user=user, conversation=conversation, request_id=request_id),
    )
    return _extract_last_ai_content(result)


def _conversation_to_langchain_messages(conversation):
    recent_messages = conversation.messages.order_by("-created_at", "-id")[:12]
    langchain_messages = []
    for message in reversed(list(recent_messages)):
        if message.role == Message.ROLE_USER:
            langchain_messages.append(HumanMessage(content=_format_user_message(message)))
        elif message.role == Message.ROLE_ASSISTANT:
            langchain_messages.append(AIMessage(content=message.content))
    return langchain_messages


def _format_user_message(message):
    attachments = list(message.attachments.all())
    if not attachments:
        return message.content
    attachment_lines = [
        f"- ID: {attachment.id}, 文件名: {attachment.original_name}, 类型: {attachment.content_type or '未知'}, 大小: {attachment.size} bytes"
        for attachment in attachments
    ]
    return f"{message.content}\n\n[用户上传的附件]\n" + "\n".join(attachment_lines)


def _extract_last_ai_content(result):
    for message in reversed(result.get("messages", [])):
        if isinstance(message, AIMessage):
            return message.content or ""
    return ""
