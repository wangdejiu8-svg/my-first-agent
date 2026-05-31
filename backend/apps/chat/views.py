import json
import time

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.document_readers import DocumentReadError, validate_uploaded_document

from .indexing import bind_attachments_to_message, ensure_attachment_knowledge_document
from .models import AgentRun, Attachment, Conversation, Message
from .serializers import (
    AttachmentSerializer,
    ConversationSerializer,
    MessageSerializer,
    SendMessageSerializer,
)
from .services import AssistantReply, generate_assistant_reply, generate_assistant_reply_stream


def get_owned_conversation(user, conversation_id):
    try:
        return Conversation.objects.active().owned_by(user).get(id=conversation_id)
    except Conversation.DoesNotExist as exc:
        raise NotFound("Conversation was not found.") from exc


def prepare_send_context(*, user, content, conversation_id, attachment_ids):
    if len(set(attachment_ids)) > settings.CHAT_MAX_ATTACHMENTS_PER_MESSAGE:
        raise ValueError(
            "Too many attachments for one message. "
            f"Max: {settings.CHAT_MAX_ATTACHMENTS_PER_MESSAGE}."
        )

    is_new_conversation = not conversation_id
    if conversation_id:
        conversation = get_owned_conversation(user, conversation_id)
    else:
        conversation = None

    attachments = []
    if attachment_ids:
        attachment_queryset = Attachment.objects.filter(
            id__in=attachment_ids,
            owner=user,
            message__isnull=True,
        )
        if is_new_conversation:
            attachment_queryset = attachment_queryset.filter(conversation__isnull=True)
        else:
            attachment_queryset = attachment_queryset.filter(
                Q(conversation__isnull=True) | Q(conversation=conversation)
            )
        attachments = list(attachment_queryset)
        if len(attachments) != len(set(attachment_ids)):
            raise ValueError("Attachment is invalid, already used, or outside this conversation.")

    return conversation, attachments


class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = (
            Conversation.objects.active()
            .owned_by(request.user)
            .order_by("-updated_at", "-created_at")
        )[:20]
        return Response(ConversationSerializer(conversations, many=True).data)

    def post(self, request):
        title = request.data.get("title") or "New conversation"
        conversation = Conversation.objects.create(owner=request.user, title=title[:120])
        return Response(
            ConversationSerializer(conversation).data,
            status=status.HTTP_201_CREATED,
        )


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, conversation_id):
        conversation = get_owned_conversation(request.user, conversation_id)
        serializer = ConversationSerializer(conversation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, conversation_id):
        conversation = get_owned_conversation(request.user, conversation_id)
        conversation.hard_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConversationMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = get_owned_conversation(request.user, conversation_id)
        messages = conversation.messages.all()
        return Response(MessageSerializer(messages, many=True).data)


class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data["content"].strip()
        conversation_id = serializer.validated_data.get("conversation_id")
        attachment_ids = serializer.validated_data.get("attachment_ids") or []

        try:
            conversation, attachments = prepare_send_context(
                user=request.user,
                content=content,
                conversation_id=conversation_id,
                attachment_ids=attachment_ids,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if conversation is None:
            conversation = Conversation.objects.create(
                owner=request.user,
                title=content[:60] or "New conversation",
            )

        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_USER,
            content=content,
        )
        if attachments:
            bind_attachments_to_message(
                attachments=attachments,
                conversation=conversation,
                message=user_message,
            )

        if conversation.messages.count() == 1:
            conversation.title = content[:60]
            conversation.save(update_fields=["title", "updated_at"])

        assistant_reply = generate_assistant_reply(conversation, request.user, content)
        assistant_content, assistant_metadata = _unwrap_assistant_reply(assistant_reply)
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_ASSISTANT,
            content=assistant_content,
            metadata_json=assistant_metadata,
        )
        conversation.save(update_fields=["updated_at"])

        return Response(
            {
                "conversation": ConversationSerializer(conversation).data,
                "user_message": MessageSerializer(user_message).data,
                "assistant_message": MessageSerializer(assistant_message).data,
            },
            status=status.HTTP_201_CREATED,
        )


class SendMessageStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data["content"].strip()
        conversation_id = serializer.validated_data.get("conversation_id")
        attachment_ids = serializer.validated_data.get("attachment_ids") or []

        try:
            conversation, attachments = prepare_send_context(
                user=request.user,
                content=content,
                conversation_id=conversation_id,
                attachment_ids=attachment_ids,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if conversation is None:
                conversation = Conversation.objects.create(
                    owner=request.user,
                    title=content[:60] or "New conversation",
                )

            user_message = Message.objects.create(
                conversation=conversation,
                role=Message.ROLE_USER,
                content=content,
            )
            if attachments:
                bind_attachments_to_message(
                    attachments=attachments,
                    conversation=conversation,
                    message=user_message,
                )

            if conversation.messages.count() == 1:
                conversation.title = content[:60]
                conversation.save(update_fields=["title", "updated_at"])

            assistant_message = Message.objects.create(
                conversation=conversation,
                role=Message.ROLE_ASSISTANT,
                content="",
                metadata_json={
                    "sources": [],
                    "used_chunks": [],
                    "is_rag_answer": False,
                    "rag_score": None,
                    "retrieval_decision": "skip",
                    "retrieval_reason": "stream_placeholder",
                    "retrieval_router_label": "",
                    "retrieval_relatedness": "unrelated",
                    "retrieval_probe_score": None,
                    "retrieval_judge_used": False,
                    "retrieval_decision_version": "placeholder",
                },
            )
            agent_run = AgentRun.objects.create(
                owner=request.user,
                conversation=conversation,
                request=content,
                response="",
                model=settings.OPENAI_MODEL,
                status="streaming",
                error="",
                latency_ms=0,
            )
            conversation.save(update_fields=["updated_at"])

        response = StreamingHttpResponse(
            streaming_content=self._stream_reply(
                conversation=conversation,
                user=request.user,
                user_content=content,
                user_message=user_message,
                assistant_message=assistant_message,
                agent_run=agent_run,
            ),
            content_type="application/x-ndjson; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    def _stream_reply(self, *, conversation, user, user_content, user_message, assistant_message, agent_run):
        started_at = time.perf_counter()
        assistant_reply = AssistantReply(
            content="",
            metadata={
                "sources": [],
                "used_chunks": [],
                "is_rag_answer": False,
                "rag_score": None,
                "retrieval_decision": "skip",
                "retrieval_reason": "stream_placeholder",
                "retrieval_router_label": "",
                "retrieval_relatedness": "unrelated",
                "retrieval_probe_score": None,
                "retrieval_judge_used": False,
                "retrieval_decision_version": "placeholder",
            },
        )
        reply_chunks = []

        yield _stream_payload(
            {
                "type": "start",
                "conversation": ConversationSerializer(conversation).data,
                "user_message": MessageSerializer(user_message).data,
                "assistant_message": MessageSerializer(assistant_message).data,
            }
        )

        try:
            stream = generate_assistant_reply_stream(conversation, user, user_content)
            while True:
                try:
                    chunk = next(stream)
                except StopIteration as stop:
                    assistant_reply = stop.value or assistant_reply
                    break
                if not chunk:
                    continue
                reply_chunks.append(chunk)
                yield _stream_payload({"type": "delta", "delta": chunk})
        except Exception as exc:
            fallback_content = "Message saved, but AI generation failed. Please try again later."
            assistant_reply = AssistantReply(
                content=fallback_content,
                metadata={
                    "sources": [],
                    "used_chunks": [],
                    "is_rag_answer": False,
                    "rag_score": None,
                    "retrieval_decision": "skip",
                    "retrieval_reason": "fallback",
                    "retrieval_router_label": "",
                    "retrieval_relatedness": "unrelated",
                    "retrieval_probe_score": None,
                    "retrieval_judge_used": False,
                    "retrieval_decision_version": "fallback",
                },
                status="fallback",
                error=str(exc),
            )
            reply_chunks = [fallback_content]
            yield _stream_payload({"type": "delta", "delta": fallback_content})

        assistant_content, assistant_metadata = _unwrap_assistant_reply(assistant_reply)
        if not assistant_content and reply_chunks:
            assistant_content = "".join(reply_chunks)

        assistant_message.content = assistant_content
        assistant_message.metadata_json = assistant_metadata
        assistant_message.save(update_fields=["content", "metadata_json"])

        agent_run.response = assistant_content
        agent_run.status = assistant_reply.status or "completed"
        agent_run.error = assistant_reply.error or ""
        agent_run.latency_ms = int((time.perf_counter() - started_at) * 1000)
        agent_run.save(update_fields=["response", "status", "error", "latency_ms"])

        conversation.save(update_fields=["updated_at"])

        yield _stream_payload(
            {
                "type": "done",
                "conversation": ConversationSerializer(conversation).data,
                "assistant_message": MessageSerializer(assistant_message).data,
            }
        )


class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded_files = list(request.FILES.getlist("file"))
        if not uploaded_files:
            single_file = request.FILES.get("file")
            if single_file is not None:
                uploaded_files = [single_file]

        if not uploaded_files:
            return Response({"detail": "Missing file."}, status=status.HTTP_400_BAD_REQUEST)

        if len(uploaded_files) > settings.CHAT_MAX_ATTACHMENTS_PER_MESSAGE:
            return Response(
                {
                    "detail": (
                        "Too many files in one upload. "
                        f"Max: {settings.CHAT_MAX_ATTACHMENTS_PER_MESSAGE}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation = None
        conversation_id = request.data.get("conversation_id")
        if conversation_id:
            conversation = get_owned_conversation(request.user, conversation_id)

        attachments = []
        validated_files = []
        for uploaded_file in uploaded_files:
            original_name, validation_error = self._validate_uploaded_file(uploaded_file)
            if validation_error:
                return Response({"detail": validation_error}, status=status.HTTP_400_BAD_REQUEST)
            validated_files.append((uploaded_file, original_name))

        for uploaded_file, original_name in validated_files:
            attachment = Attachment.objects.create(
                owner=request.user,
                conversation=conversation,
                file=uploaded_file,
                original_name=original_name,
                content_type=getattr(uploaded_file, "content_type", "") or "",
                size=uploaded_file.size,
            )
            attachments.append(attachment)
            ensure_attachment_knowledge_document(attachment)

        if len(attachments) == 1:
            return Response(AttachmentSerializer(attachments[0]).data, status=status.HTTP_201_CREATED)
        return Response(AttachmentSerializer(attachments, many=True).data, status=status.HTTP_201_CREATED)

    def _validate_uploaded_file(self, uploaded_file):
        content_type = (getattr(uploaded_file, "content_type", "") or "").lower()
        if content_type and content_type not in settings.CHAT_ALLOWED_ATTACHMENT_CONTENT_TYPES:
            return None, "File type is not allowed."

        try:
            original_name = validate_uploaded_document(
                uploaded_file,
                max_size_bytes=settings.CHAT_MAX_ATTACHMENT_SIZE_BYTES,
            )
        except DocumentReadError as exc:
            return None, str(exc)
        return original_name, None


def _unwrap_assistant_reply(reply):
    if isinstance(reply, AssistantReply):
        return reply.content, reply.metadata
    if isinstance(reply, str):
        return reply, {}
    return str(reply or ""), {}


def _stream_payload(payload):
    return json.dumps(payload, ensure_ascii=False) + "\n"
