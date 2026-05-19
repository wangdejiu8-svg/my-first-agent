from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Attachment, Conversation, Message
from .serializers import (
    AttachmentSerializer,
    ConversationSerializer,
    MessageSerializer,
    SendMessageSerializer,
)
from .services import generate_assistant_reply


def get_owned_conversation(user, conversation_id):
    try:
        return Conversation.objects.active().owned_by(user).get(id=conversation_id)
    except Conversation.DoesNotExist as exc:
        raise NotFound("对话不存在或已被删除。") from exc


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
        title = request.data.get("title") or "新对话"
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
        conversation.soft_delete()
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
        if len(set(attachment_ids)) > settings.CHAT_MAX_ATTACHMENTS_PER_MESSAGE:
            return Response(
                {"detail": f"单条消息最多只能附带 {settings.CHAT_MAX_ATTACHMENTS_PER_MESSAGE} 个文件。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if conversation_id:
            conversation = get_owned_conversation(request.user, conversation_id)
        else:
            conversation = Conversation.objects.create(
                owner=request.user,
                title=content[:60] or "新对话",
            )

        attachments = Attachment.objects.none()
        if attachment_ids:
            attachments = Attachment.objects.filter(
                id__in=attachment_ids,
                owner=request.user,
                message__isnull=True,
            ).filter(Q(conversation__isnull=True) | Q(conversation=conversation))
            if attachments.count() != len(set(attachment_ids)):
                return Response(
                    {"detail": "附件不存在、已被使用或不属于当前对话。"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_USER,
            content=content,
        )
        if attachment_ids:
            attachments.update(conversation=conversation, message=user_message)

        if conversation.messages.count() == 1:
            conversation.title = content[:60]
            conversation.save(update_fields=["title", "updated_at"])

        assistant_content = generate_assistant_reply(conversation, request.user, content)
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_ASSISTANT,
            content=assistant_content,
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
            return Response({"detail": "请选择要上传的文件。"}, status=status.HTTP_400_BAD_REQUEST)

        if len(uploaded_files) > settings.CHAT_MAX_ATTACHMENTS_PER_MESSAGE:
            return Response(
                {"detail": f"一次最多上传 {settings.CHAT_MAX_ATTACHMENTS_PER_MESSAGE} 个文件。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation = None
        conversation_id = request.data.get("conversation_id")
        if conversation_id:
            conversation = get_owned_conversation(request.user, conversation_id)

        attachments = []
        for uploaded_file in uploaded_files:
            validation_error = self._validate_uploaded_file(uploaded_file)
            if validation_error:
                return Response({"detail": validation_error}, status=status.HTTP_400_BAD_REQUEST)

            attachment = Attachment.objects.create(
                owner=request.user,
                conversation=conversation,
                file=uploaded_file,
                original_name=uploaded_file.name,
                content_type=getattr(uploaded_file, "content_type", "") or "",
                size=uploaded_file.size,
            )
            attachments.append(attachment)

        if len(attachments) == 1:
            return Response(AttachmentSerializer(attachments[0]).data, status=status.HTTP_201_CREATED)
        return Response(AttachmentSerializer(attachments, many=True).data, status=status.HTTP_201_CREATED)

    def _validate_uploaded_file(self, uploaded_file):
        suffix = Path(uploaded_file.name or "").suffix.lower()
        content_type = (getattr(uploaded_file, "content_type", "") or "").lower()

        if suffix not in settings.CHAT_ALLOWED_ATTACHMENT_EXTENSIONS:
            return "仅支持上传 .docx 和 .pdf 文件。"
        if content_type and content_type not in settings.CHAT_ALLOWED_ATTACHMENT_CONTENT_TYPES:
            return "文件类型不被允许。"
        if uploaded_file.size > settings.CHAT_MAX_ATTACHMENT_SIZE_BYTES:
            max_size_mb = settings.CHAT_MAX_ATTACHMENT_SIZE_BYTES // (1024 * 1024)
            return f"单个文件不能超过 {max_size_mb}MB。"
        return None
