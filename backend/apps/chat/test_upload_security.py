from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from pypdf import PdfWriter
from rest_framework.test import APITestCase

from ai.document_readers import (
    DocumentReadError,
    _extract_pdf_page_text_with_ocr,
    _resolve_pdf_ocr_language,
    read_document_text,
)
from apps.chat.models import Attachment


User = get_user_model()


@override_settings(OPENAI_API_KEY="")
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

    def test_read_document_text_falls_back_to_pymupdf_when_pypdf_returns_empty(self):
        temp_path = None
        try:
            with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_path = temp_file.name
                writer = PdfWriter()
                writer.add_blank_page(width=72, height=72)
                writer.write(temp_file)
                temp_file.flush()

            with patch(
                "ai.document_readers._read_pdf_with_pymupdf",
                return_value=("[第 1 页]\nPyMuPDF fallback text", False),
            ) as mock_pymupdf:
                text = read_document_text(temp_path, "fallback.pdf")
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

        self.assertEqual(text, "[第 1 页]\nPyMuPDF fallback text")
        mock_pymupdf.assert_called_once_with(Path(temp_path), max_chars=12000)

    def test_read_document_text_uses_ocr_fallback_after_non_ocr_extractors_fail(self):
        temp_path = None
        try:
            with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_path = temp_file.name
                writer = PdfWriter()
                writer.add_blank_page(width=72, height=72)
                writer.write(temp_file)
                temp_file.flush()

            with patch(
                "ai.document_readers._read_pdf_with_pymupdf",
                side_effect=[("", False), ("[第 1 页]\nOCR fallback text", False)],
            ) as mock_pymupdf, patch(
                "ai.document_readers._ocr_fallback_is_configured",
                return_value=True,
            ), patch(
                "ai.document_readers._resolve_pdf_ocr_language",
                return_value="chi_sim+eng",
            ):
                text = read_document_text(temp_path, "ocr.pdf")
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

        self.assertEqual(text, "[第 1 页]\nOCR fallback text")
        self.assertEqual(mock_pymupdf.call_count, 2)
        mock_pymupdf.assert_any_call(
            Path(temp_path),
            max_chars=12000,
            use_ocr=True,
            ocr_language="chi_sim+eng",
            ocr_dpi=300,
        )

    def test_read_document_text_returns_empty_when_ocr_fallback_is_unavailable(self):
        temp_path = None
        try:
            with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_path = temp_file.name
                writer = PdfWriter()
                writer.add_blank_page(width=72, height=72)
                writer.write(temp_file)
                temp_file.flush()

            with patch(
                "ai.document_readers._read_pdf_with_pymupdf",
                return_value=("", False),
            ) as mock_pymupdf, patch(
                "ai.document_readers._ocr_fallback_is_configured",
                return_value=False,
            ):
                text = read_document_text(temp_path, "no-ocr.pdf")
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

        self.assertEqual(text, "")
        mock_pymupdf.assert_called_once_with(Path(temp_path), max_chars=12000)

    def test_resolve_pdf_ocr_language_prefers_chinese_and_english_when_auto(self):
        with patch(
            "ai.document_readers._get_available_tesseract_languages",
            return_value=frozenset({"chi_sim", "eng"}),
        ):
            self.assertEqual(_resolve_pdf_ocr_language("auto"), "chi_sim+eng")

    def test_resolve_pdf_ocr_language_keeps_explicit_setting(self):
        self.assertEqual(_resolve_pdf_ocr_language("eng"), "eng")

    def test_extract_pdf_page_text_with_ocr_uses_full_page_sorted_high_dpi(self):
        page = MagicMock()
        text_page = object()
        page.get_textpage_ocr.return_value = text_page
        page.get_text.return_value = "OCR text"

        text = _extract_pdf_page_text_with_ocr(
            page,
            ocr_language="chi_sim+eng",
            ocr_dpi=300,
        )

        self.assertEqual(text, "OCR text")
        page.get_textpage_ocr.assert_called_once_with(
            language="chi_sim+eng",
            dpi=300,
            full=True,
        )
        page.get_text.assert_called_once_with(
            "text",
            textpage=text_page,
            sort=True,
        )
