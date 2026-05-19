from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListCreateView,
    ConversationMessagesView,
    FileUploadView,
    SendMessageView,
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
    path("files/upload/", FileUploadView.as_view(), name="file-upload"),
]
