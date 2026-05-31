from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ai.chunking import split_text_into_chunks
from ai.document_readers import DocumentReadError, is_supported_document, read_document_text
from ai.embeddings import embed_texts_with_backend

from .models import Attachment, KnowledgeChunk, KnowledgeDocument


def index_attachment(attachment):
    document = ensure_attachment_knowledge_document(attachment)
    _sync_document_scope(document, attachment=attachment)
    _mark_document(document, status=KnowledgeDocument.STATUS_PROCESSING, error_message="")

    try:
        text = read_document_text(
            attachment.file.path,
            attachment.original_name,
            max_chars=settings.RAG_INDEX_MAX_CHARS,
        )
        if not text.strip():
            raise DocumentReadError("文档中没有提取到可索引文本。")

        chunks = split_text_into_chunks(
            text,
            chunk_size=settings.RAG_CHUNK_SIZE,
            overlap=settings.RAG_CHUNK_OVERLAP,
        )
        if not chunks:
            raise DocumentReadError("文档切分后没有得到可索引片段。")

        embeddings, backend_name = embed_texts_with_backend([chunk.text for chunk in chunks])
        with transaction.atomic():
            KnowledgeChunk.objects.filter(document=document).delete()
            KnowledgeChunk.objects.bulk_create(
                [
                    KnowledgeChunk(
                        document=document,
                        owner=attachment.owner,
                        conversation=attachment.conversation,
                        attachment=attachment,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        token_count=chunk.token_count,
                        metadata_json={
                            "start_offset": chunk.start_offset,
                            "end_offset": chunk.end_offset,
                        },
                        embedding_json=embedding,
                    )
                    for chunk, embedding in zip(chunks, embeddings)
                ]
            )
            _mark_document(
                document,
                status=KnowledgeDocument.STATUS_COMPLETED,
                embedding_backend=backend_name,
                indexed_at=timezone.now(),
                error_message="",
            )
        return document
    except Exception as exc:
        _mark_document(
            document,
            status=KnowledgeDocument.STATUS_FAILED,
            error_message=str(exc),
        )
        return document


def ensure_attachment_knowledge_document(attachment):
    document, _created = KnowledgeDocument.objects.get_or_create(
        attachment=attachment,
        defaults={
            "owner": attachment.owner,
            "conversation": attachment.conversation,
            "title": attachment.original_name,
            "source_type": KnowledgeDocument.SOURCE_ATTACHMENT,
        },
    )
    _sync_document_scope(document, attachment=attachment)
    return document


def ensure_conversation_knowledge_indexed(*, conversation, owner):
    attachments = (
        Attachment.objects.filter(owner=owner, conversation=conversation)
        .select_related("knowledge_document")
        .order_by("created_at", "id")
    )
    for attachment in attachments:
        if not is_supported_document(attachment.original_name):
            continue

        try:
            document = attachment.knowledge_document
        except KnowledgeDocument.DoesNotExist:
            document = None
        if document is None:
            index_attachment(attachment)
            continue
        if document.index_status == KnowledgeDocument.STATUS_PENDING:
            index_attachment(attachment)


def bind_attachments_to_message(*, attachments, conversation, message):
    attachment_ids = [attachment.id for attachment in attachments]
    if not attachment_ids:
        return

    Attachment.objects.filter(id__in=attachment_ids).update(
        conversation=conversation,
        message=message,
    )
    KnowledgeDocument.objects.filter(attachment_id__in=attachment_ids).update(
        conversation=conversation,
    )
    KnowledgeChunk.objects.filter(attachment_id__in=attachment_ids).update(
        conversation=conversation,
    )


def _sync_document_scope(document, *, attachment):
    changed_fields = []
    if document.owner_id != attachment.owner_id:
        document.owner = attachment.owner
        changed_fields.append("owner")
    if document.conversation_id != attachment.conversation_id:
        document.conversation = attachment.conversation
        changed_fields.append("conversation")
    if document.title != attachment.original_name:
        document.title = attachment.original_name
        changed_fields.append("title")
    if changed_fields:
        changed_fields.append("updated_at")
        document.save(update_fields=changed_fields)


def _mark_document(
    document,
    *,
    status,
    error_message=None,
    embedding_backend=None,
    indexed_at=None,
):
    document.index_status = status
    if error_message is not None:
        document.error_message = error_message[:2000]
    if embedding_backend is not None:
        document.embedding_backend = embedding_backend
    if indexed_at is not None or status != KnowledgeDocument.STATUS_COMPLETED:
        document.indexed_at = indexed_at
    document.save(
        update_fields=[
            "index_status",
            "error_message",
            "embedding_backend",
            "indexed_at",
            "updated_at",
        ]
    )
