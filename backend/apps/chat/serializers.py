from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from .models import Attachment, Conversation, Message


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at"]


class MessageSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()
    sources = serializers.SerializerMethodField()
    used_chunks = serializers.SerializerMethodField()
    is_rag_answer = serializers.SerializerMethodField()
    rag_score = serializers.SerializerMethodField()
    retrieval_decision = serializers.SerializerMethodField()
    retrieval_reason = serializers.SerializerMethodField()
    retrieval_router_label = serializers.SerializerMethodField()
    retrieval_relatedness = serializers.SerializerMethodField()
    retrieval_probe_score = serializers.SerializerMethodField()
    retrieval_judge_used = serializers.SerializerMethodField()
    retrieval_decision_version = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "role",
            "content",
            "attachments",
            "sources",
            "used_chunks",
            "is_rag_answer",
            "rag_score",
            "retrieval_decision",
            "retrieval_reason",
            "retrieval_router_label",
            "retrieval_relatedness",
            "retrieval_probe_score",
            "retrieval_judge_used",
            "retrieval_decision_version",
            "created_at",
        ]
        read_only_fields = ["conversation"]

    def get_attachments(self, obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data

    def get_sources(self, obj):
        return (obj.metadata_json or {}).get("sources", [])

    def get_used_chunks(self, obj):
        return (obj.metadata_json or {}).get("used_chunks", [])

    def get_is_rag_answer(self, obj):
        return bool((obj.metadata_json or {}).get("is_rag_answer", False))

    def get_rag_score(self, obj):
        return (obj.metadata_json or {}).get("rag_score")

    def get_retrieval_decision(self, obj):
        return (obj.metadata_json or {}).get("retrieval_decision")

    def get_retrieval_reason(self, obj):
        return (obj.metadata_json or {}).get("retrieval_reason")

    def get_retrieval_router_label(self, obj):
        return (obj.metadata_json or {}).get("retrieval_router_label", "")

    def get_retrieval_relatedness(self, obj):
        return (obj.metadata_json or {}).get("retrieval_relatedness")

    def get_retrieval_probe_score(self, obj):
        return (obj.metadata_json or {}).get("retrieval_probe_score")

    def get_retrieval_judge_used(self, obj):
        return bool((obj.metadata_json or {}).get("retrieval_judge_used", False))

    def get_retrieval_decision_version(self, obj):
        return (obj.metadata_json or {}).get("retrieval_decision_version")


class SendMessageSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    attachment_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        error_messages={
            "not_a_list": "附件参数格式不正确。",
        },
    )
    content = serializers.CharField(
        allow_blank=False,
        error_messages={
            "blank": "请输入消息内容。",
            "required": "请输入消息内容。",
        },
    )


class AttachmentSerializer(serializers.ModelSerializer):
    knowledge_index_status = serializers.SerializerMethodField()
    knowledge_index_error = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "conversation",
            "file",
            "original_name",
            "content_type",
            "size",
            "knowledge_index_status",
            "knowledge_index_error",
            "created_at",
        ]
        read_only_fields = ["original_name", "content_type", "size", "created_at"]

    def get_knowledge_index_status(self, obj):
        try:
            document = obj.knowledge_document
        except ObjectDoesNotExist:
            document = None
        return getattr(document, "index_status", None)

    def get_knowledge_index_error(self, obj):
        try:
            document = obj.knowledge_document
        except ObjectDoesNotExist:
            document = None
        return getattr(document, "error_message", "")
