from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListCreateView,
    ConversationMessagesView,
    FileUploadView,
    SendMessageView,
    SendMessageStreamView,
)

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view(), name="conversations"),
    path(
        "conversations/<int:conversation_id>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path(
        "conversations/<int:conversation_id>/messages/",
        ConversationMessagesView.as_view(),
        name="conversation-messages",
    ),
    path("chat/send/", SendMessageView.as_view(), name="send-message"),
    path("chat/send-stream/", SendMessageStreamView.as_view(), name="send-message-stream"),
    path("files/upload/", FileUploadView.as_view(), name="file-upload"),
]
