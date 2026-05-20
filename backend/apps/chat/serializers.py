from rest_framework import serializers

from .models import Attachment, Conversation, Message


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at"]


class MessageSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "conversation", "role", "content", "attachments", "created_at"]
        read_only_fields = ["conversation"]

    def get_attachments(self, obj):
        return AttachmentSerializer(obj.attachments.all(), many=True).data


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
    class Meta:
        model = Attachment
        fields = [
            "id",
            "conversation",
            "file",
            "original_name",
            "content_type",
            "size",
            "created_at",
        ]
        read_only_fields = ["original_name", "content_type", "size", "created_at"]
