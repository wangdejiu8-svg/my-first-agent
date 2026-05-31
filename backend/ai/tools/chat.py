from langchain_core.tools import tool

from ai.document_readers import is_supported_document, read_document_text
from ai.retrieval import (
    get_attachment_chunk_context as retrieve_attachment_chunk_context,
    search_current_conversation_knowledge,
)
from apps.accounts.models import UserSettings
from apps.chat.models import Attachment, Conversation


def build_tools(user, conversation):
    @tool
    def list_user_conversations(limit: int = 5):
        """列出当前登录用户最近的历史对话。"""
        limit = min(max(int(limit or 5), 1), 20)
        conversations = (
            Conversation.objects.active()
            .owned_by(user)
            .order_by("-updated_at", "-created_at")[:limit]
        )
        return [
            {
                "id": item.id,
                "title": item.title,
                "updated_at": item.updated_at.isoformat(),
            }
            for item in conversations
        ]

    @tool
    def get_current_conversation_messages(limit: int = 10):
        """读取当前会话最近的消息。"""
        limit = min(max(int(limit or 10), 1), 30)
        messages = conversation.messages.order_by("-created_at", "-id")[:limit]
        return [
            {
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
            for message in reversed(list(messages))
        ]

    @tool
    def get_user_settings():
        """读取当前登录用户的界面设置。"""
        settings_obj, _created = UserSettings.objects.get_or_create(user=user)
        return {
            "theme": settings_obj.theme,
            "language": settings_obj.language,
            "font_size": settings_obj.font_size,
        }

    @tool
    def search_current_conversation_knowledge_tool(query: str, top_k: int = 5):
        """检索当前会话中与问题最相关的文档片段。"""
        result = search_current_conversation_knowledge(
            user=user,
            conversation=conversation,
            query=query,
            top_k=top_k,
        )
        return {
            "sources": result.sources,
            "used_chunks": result.used_chunks,
            "is_rag_answer": result.is_rag_answer,
            "rag_score": result.rag_score,
        }

    @tool
    def get_attachment_chunk_context(attachment_id: int, query: str, top_k: int = 5):
        """检索当前会话内某个附件与问题最相关的片段。"""
        try:
            attachment = Attachment.objects.get(
                id=attachment_id,
                owner=user,
                conversation=conversation,
            )
        except Attachment.DoesNotExist:
            return {"error": "附件不存在或不属于当前会话。"}

        return {
            "used_chunks": retrieve_attachment_chunk_context(
                user=user,
                conversation=conversation,
                attachment=attachment,
                query=query,
                top_k=top_k,
            )
        }

    @tool
    def read_current_conversation_documents(limit: int = 3):
        """读取当前会话中最近上传的 Word 或 PDF 附件全文。"""
        limit = min(max(int(limit or 3), 1), 5)
        attachments = (
            Attachment.objects.filter(owner=user, conversation=conversation)
            .order_by("-created_at", "-id")
        )
        documents = []
        for attachment in attachments:
            if len(documents) >= limit:
                break
            if not is_supported_document(attachment.original_name):
                continue
            documents.append(_read_attachment(attachment))
        if not documents:
            return {
                "documents": [],
                "message": "当前会话没有可读取的 Word 或 PDF 附件。",
            }
        return {"documents": documents}

    @tool
    def read_uploaded_document(attachment_id: int):
        """按附件 ID 读取当前会话中的 Word 或 PDF 附件全文。"""
        try:
            attachment = Attachment.objects.get(
                id=attachment_id,
                owner=user,
                conversation=conversation,
            )
        except Attachment.DoesNotExist:
            return {"error": "附件不存在或不属于当前会话。"}
        if not is_supported_document(attachment.original_name):
            return {"error": "当前只支持读取 .docx 和 .pdf 文件。"}
        return {"document": _read_attachment(attachment)}

    return [
        list_user_conversations,
        get_current_conversation_messages,
        get_user_settings,
        search_current_conversation_knowledge_tool,
        get_attachment_chunk_context,
        read_current_conversation_documents,
        read_uploaded_document,
    ]


def _read_attachment(attachment):
    try:
        content = read_document_text(attachment.file.path, attachment.original_name)
    except Exception as exc:
        return {
            "id": attachment.id,
            "name": attachment.original_name,
            "error": f"文件读取失败：{exc}",
        }
    return {
        "id": attachment.id,
        "name": attachment.original_name,
        "content_type": attachment.content_type,
        "size": attachment.size,
        "text": content or "文件中没有提取到可读文本。",
    }
