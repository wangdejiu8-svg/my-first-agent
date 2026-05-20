from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase


User = get_user_model()


class CookieTokenCsrfSecurityTests(APITestCase):
    frontend_origin = "http://localhost:3000"

    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.client = APIClient(enforce_csrf_checks=True)

    def _login_with_cookie(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "alice", "password": "password123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("authToken", response.cookies)
        return response

    def _issue_csrf_cookie(self):
        response = self.client.get("/api/auth/me/", HTTP_ORIGIN=self.frontend_origin)
        self.assertEqual(response.status_code, 200)
        csrf_cookie = self.client.cookies.get("csrftoken")
        self.assertIsNotNone(csrf_cookie)
        return csrf_cookie.value

    def test_cookie_authenticated_unsafe_method_requires_csrf(self):
        self._login_with_cookie()

        response = self.client.patch(
            "/api/settings/",
            {"theme": "dark"},
            format="json",
            HTTP_ORIGIN=self.frontend_origin,
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF Failed", str(response.data["detail"]))

    def test_cookie_authenticated_unsafe_method_accepts_matching_csrf_token(self):
        self._login_with_cookie()
        csrf_token = self._issue_csrf_cookie()

        response = self.client.patch(
            "/api/settings/",
            {"theme": "dark"},
            format="json",
            HTTP_ORIGIN=self.frontend_origin,
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme"], "dark")

    def test_authorization_header_unsafe_method_does_not_require_csrf(self):
        token = Token.objects.create(user=self.user)
        header_client = APIClient(enforce_csrf_checks=True)

        response = header_client.patch(
            "/api/settings/",
            {"theme": "dark"},
            format="json",
            HTTP_AUTHORIZATION=f"Token {token.key}",
            HTTP_ORIGIN=self.frontend_origin,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme"], "dark")
