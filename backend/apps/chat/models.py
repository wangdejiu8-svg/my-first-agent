from django.conf import settings
from django.db import models


class ConversationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(deleted_at__isnull=True)

    def owned_by(self, user):
        return self.filter(owner=user)


class Conversation(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    title = models.CharField(max_length=120, default="New conversation")
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ConversationQuerySet.as_manager()

    def hard_delete(self):
        attachment_files = [
            attachment.file
            for attachment in self.attachments.all()
            if getattr(attachment, "file", None)
        ]
        self.delete()
        for stored_file in attachment_files:
            file_name = getattr(stored_file, "name", "")
            storage = getattr(stored_file, "storage", None)
            if file_name and storage and storage.exists(file_name):
                storage.delete(file_name)

    def __str__(self):
        return f"{self.owner_id}:{self.title}"


class Message(models.Model):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_SYSTEM = "system"
    ROLE_CHOICES = (
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
        (ROLE_SYSTEM, "System"),
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}:{self.conversation_id}:{self.id}"


class Attachment(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="attachments",
        blank=True,
        null=True,
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
        blank=True,
        null=True,
    )
    file = models.FileField(upload_to="attachments/%Y/%m/%d/")
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class AgentRun(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="agent_runs",
    )
    request = models.TextField()
    response = models.TextField(blank=True)
    model = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, default="completed")
    error = models.TextField(blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class KnowledgeDocument(models.Model):
    SOURCE_ATTACHMENT = "attachment"
    SOURCE_CHOICES = ((SOURCE_ATTACHMENT, "Attachment"),)

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="knowledge_documents",
        blank=True,
        null=True,
    )
    attachment = models.OneToOneField(
        Attachment,
        on_delete=models.CASCADE,
        related_name="knowledge_document",
    )
    title = models.CharField(max_length=255)
    source_type = models.CharField(
        max_length=40,
        choices=SOURCE_CHOICES,
        default=SOURCE_ATTACHMENT,
    )
    index_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    embedding_backend = models.CharField(max_length=80, blank=True)
    indexed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["owner", "conversation", "index_status"]),
        ]


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="knowledge_chunks",
        blank=True,
        null=True,
    )
    attachment = models.ForeignKey(
        Attachment,
        on_delete=models.CASCADE,
        related_name="knowledge_chunks",
    )
    chunk_index = models.PositiveIntegerField()
    text = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    page_number = models.PositiveIntegerField(blank=True, null=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    embedding_json = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["chunk_index", "id"]
        indexes = [
            models.Index(fields=["owner", "conversation"]),
            models.Index(fields=["attachment", "chunk_index"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="chat_unique_document_chunk_index",
            ),
        ]


class RetrievalLog(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="retrieval_logs",
    )
    query = models.TextField()
    top_k = models.PositiveIntegerField(default=5)
    matched_chunk_ids = models.JSONField(default=list, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

# Create your models here.
