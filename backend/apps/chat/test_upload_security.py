from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from ai.document_readers import DocumentReadError, read_document_text
from apps.chat.models import Attachment


User = get_user_model()


class UploadSecurityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="security-user",
            email="security@example.com",
            password="password123",
        )
        self.client.post(
            "/api/auth/login/",
            {"username": "security-user", "password": "password123"},
            format="json",
        )

    def test_upload_rejects_pdf_with_invalid_signature(self):
        response = self.client.post(
            "/api/files/upload/",
            {
                "file": SimpleUploadedFile(
                    "spoofed.pdf",
                    b"not a real pdf",
                    content_type="application/pdf",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Attachment.objects.count(), 0)

    def test_upload_rejects_docx_missing_required_members(self):
        archive_buffer = BytesIO()
        with ZipFile(archive_buffer, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", "<Types></Types>")
            archive.writestr("_rels/.rels", "<Relationships></Relationships>")

        response = self.client.post(
            "/api/files/upload/",
            {
                "file": SimpleUploadedFile(
                    "broken.docx",
                    archive_buffer.getvalue(),
                    content_type=(
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    ),
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Attachment.objects.count(), 0)

    def test_upload_accepts_valid_pdf_with_octet_stream_content_type(self):
        response = self.client.post(
            "/api/files/upload/",
            {
                "file": SimpleUploadedFile(
                    "nested/report.pdf",
                    b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
                    content_type="application/octet-stream",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["original_name"], "report.pdf")

    def test_read_document_text_raises_stable_error_for_malformed_pdf(self):
        temp_path = None
        try:
            with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(
                    b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
                )
                temp_file.flush()

            with self.assertRaises(DocumentReadError) as error:
                read_document_text(temp_path, "broken.pdf")
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

        self.assertEqual(str(error.exception), "文档读取失败，请重新上传后重试。")
