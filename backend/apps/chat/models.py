from django.conf import settings
from django.db import models
from django.utils import timezone


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

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

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

# Create your models here.
