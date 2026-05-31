from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from apps.chat.models import Message

from .context import build_agent_config
from .graph import build_chat_graph


def invoke_chat_agent(user, conversation, request_id=None, retrieval_reference_block=""):
    graph = build_chat_graph(user=user, conversation=conversation, streaming=False)
    messages = _conversation_to_langchain_messages(
        conversation,
        retrieval_reference_block=retrieval_reference_block,
    )
    result = graph.invoke(
        {"messages": messages},
        config=build_agent_config(user=user, conversation=conversation, request_id=request_id),
    )
    return _extract_last_ai_content(result)


def invoke_chat_agent_stream(user, conversation, request_id=None, retrieval_reference_block=""):
    graph = build_chat_graph(user=user, conversation=conversation, streaming=True)
    messages = _conversation_to_langchain_messages(
        conversation,
        retrieval_reference_block=retrieval_reference_block,
    )
    stream = graph.stream(
        {"messages": messages},
        config=build_agent_config(user=user, conversation=conversation, request_id=request_id),
        stream_mode="messages",
    )
    for chunk, _metadata in stream:
        text = _extract_stream_chunk_content(chunk)
        if text:
            yield text


def _conversation_to_langchain_messages(conversation, retrieval_reference_block=""):
    recent_messages = conversation.messages.order_by("-created_at", "-id")[:12]
    langchain_messages = []
    latest_user_message_id = next(
        (message.id for message in recent_messages if message.role == Message.ROLE_USER),
        None,
    )
    for message in reversed(list(recent_messages)):
        if message.role == Message.ROLE_USER:
            langchain_messages.append(
                HumanMessage(
                    content=_format_user_message(
                        message,
                        retrieval_reference_block=(
                            retrieval_reference_block
                            if message.id == latest_user_message_id
                            else ""
                        ),
                    )
                )
            )
        elif message.role == Message.ROLE_ASSISTANT:
            langchain_messages.append(AIMessage(content=message.content))
    return langchain_messages


def _format_user_message(message, retrieval_reference_block=""):
    attachments = list(message.attachments.all())
    sections = [message.content]
    attachment_lines = [
        (
            f"- ID: {attachment.id}, 文件名: {attachment.original_name}, "
            f"类型: {attachment.content_type or '未知'}, 大小: {attachment.size} bytes"
        )
        for attachment in attachments
    ]
    if attachment_lines:
        sections.append("[用户上传的附件]\n" + "\n".join(attachment_lines))
    if retrieval_reference_block:
        sections.append(retrieval_reference_block)
    return "\n\n".join(section for section in sections if section)


def _extract_last_ai_content(result):
    for message in reversed(result.get("messages", [])):
        if isinstance(message, AIMessage):
            return message.content or ""
    return ""


def _extract_stream_chunk_content(chunk):
    if isinstance(chunk, AIMessageChunk):
        text_attr = getattr(chunk, "text", None)
        if callable(text_attr):
            text = text_attr()
            if isinstance(text, str):
                return text
        elif isinstance(text_attr, str):
            return text_attr

        content = getattr(chunk, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            )
        return ""
    if isinstance(chunk, str):
        return chunk
    return ""
