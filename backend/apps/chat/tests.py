from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from docx import Document
from rest_framework.test import APITestCase

from ai.document_readers import read_document_text
from .models import Attachment, Conversation, Message


User = get_user_model()


class ChatApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password123",
        )
        self.client.post(
            "/api/auth/login/",
            {"username": "alice", "password": "password123"},
            format="json",
        )

    def test_conversation_list_only_returns_current_users_conversations(self):
        own = Conversation.objects.create(owner=self.user, title="Mine")
        Conversation.objects.create(owner=self.other_user, title="Other")

        response = self.client.get("/api/conversations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], own.id)

    def test_conversation_list_is_limited_to_twenty_items(self):
        for index in range(25):
            Conversation.objects.create(owner=self.user, title=f"Conv {index}")

        response = self.client.get("/api/conversations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 20)

    def test_get_messages_denies_other_users_conversation(self):
        other = Conversation.objects.create(owner=self.other_user, title="Other")

        response = self.client.get(f"/api/conversations/{other.id}/messages/")

        self.assertEqual(response.status_code, 404)

    @patch("apps.chat.views.generate_assistant_reply", return_value="你好，我已收到。")
    def test_send_message_creates_conversation_and_messages(self, _mock_reply):
        response = self.client.post(
            "/api/chat/send/",
            {"content": "Hello"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        conversation_id = response.data["conversation"]["id"]
        conversation = Conversation.objects.get(id=conversation_id)
        self.assertEqual(conversation.owner, self.user)
        self.assertEqual(conversation.messages.count(), 2)
        self.assertTrue(
            conversation.messages.filter(role=Message.ROLE_USER, content="Hello").exists()
        )
        self.assertTrue(
            conversation.messages.filter(role=Message.ROLE_ASSISTANT).exists()
        )

    @patch("apps.chat.views.generate_assistant_reply", return_value="文件已收到。")
    def test_send_message_binds_uploaded_file_to_user_message(self, _mock_reply):
        upload_response = self.client.post(
            "/api/files/upload/",
            {
                "file": SimpleUploadedFile(
                    "note.pdf",
                    b"%PDF-1.4 mock",
                    content_type="application/pdf",
                )
            },
            format="multipart",
        )
        self.assertEqual(upload_response.status_code, 201)

        response = self.client.post(
            "/api/chat/send/",
            {
                "content": "请看这个文件",
                "attachment_ids": [upload_response.data["id"]],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        user_message_id = response.data["user_message"]["id"]
        attachment = Attachment.objects.get(id=upload_response.data["id"])
        self.assertEqual(attachment.message_id, user_message_id)
        self.assertEqual(attachment.conversation_id, response.data["conversation"]["id"])
        self.assertEqual(response.data["user_message"]["attachments"][0]["original_name"], "note.pdf")

    def test_upload_rejects_unsupported_file_type(self):
        response = self.client.post(
            "/api/files/upload/",
            {"file": SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)

    def test_upload_rejects_oversized_file(self):
        oversized = SimpleUploadedFile(
            "large.pdf",
            b"a" * (settings.CHAT_MAX_ATTACHMENT_SIZE_BYTES + 1),
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/files/upload/",
            {"file": oversized},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)

    def test_send_message_rejects_too_many_attachments(self):
        attachments = [
            Attachment.objects.create(
                owner=self.user,
                file=SimpleUploadedFile(
                    f"note-{index}.pdf",
                    b"%PDF-1.4 mock",
                    content_type="application/pdf",
                ),
                original_name=f"note-{index}.pdf",
                content_type="application/pdf",
                size=12,
            )
            for index in range(settings.CHAT_MAX_ATTACHMENTS_PER_MESSAGE + 1)
        ]

        response = self.client.post(
            "/api/chat/send/",
            {
                "content": "请查看这些文件",
                "attachment_ids": [attachment.id for attachment in attachments],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_send_message_requires_authentication(self):
        self.client.cookies.clear()

        response = self.client.post(
            "/api/chat/send/",
            {"content": "Hello"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_docx_reader_extracts_text(self):
        document = Document()
        document.add_paragraph("项目简介")
        document.add_paragraph("这是一个 AI Agent 简历项目。")
        buffer = BytesIO()
        document.save(buffer)

        temp_path = None
        try:
            with NamedTemporaryFile(suffix=".docx", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(buffer.getvalue())
                temp_file.flush()
            text = read_document_text(temp_path, "resume.docx")
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

        self.assertIn("项目简介", text)
        self.assertIn("AI Agent 简历项目", text)
