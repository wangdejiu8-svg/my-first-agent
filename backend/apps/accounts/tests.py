from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


User = get_user_model()


class AuthApiTests(APITestCase):
    def test_register_login_and_me(self):
        register_response = self.client.post(
            "/api/auth/register/",
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            format="json",
        )
        self.assertEqual(register_response.status_code, 201)

        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "alice", "password": "Password123!"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertIn("authToken", login_response.cookies)
        self.assertNotIn("token", login_response.data)

        me_response = self.client.get("/api/auth/me/")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data["username"], "alice")

    def test_register_rejects_invalid_email(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "alice",
                "email": "alice-at-example",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_register_allows_numeric_local_part_email(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "alice",
                "email": "39@qq.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_register_allows_weak_password_but_still_registers(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": "password123",
                "confirm_password": "password123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_settings_updates_profile_for_current_user(self):
        user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.client.post(
            "/api/auth/login/",
            {"username": "alice", "password": "password123"},
            format="json",
        )

        response = self.client.patch(
            "/api/settings/",
            {"username": "alice2", "theme": "dark"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.username, "alice2")
        self.assertEqual(user.settings_profile.theme, "dark")

    def test_settings_rejects_duplicate_username(self):
        User.objects.create_user(
            username="taken",
            email="taken@example.com",
            password="password123",
        )
        User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.client.post(
            "/api/auth/login/",
            {"username": "alice", "password": "password123"},
            format="json",
        )

        response = self.client.patch(
            "/api/settings/",
            {"username": "taken"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_settings_allows_username_that_only_differs_by_case(self):
        User.objects.create_user(
            username="anan",
            email="anan@example.com",
            password="password123",
        )
        renamed_user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.client.post(
            "/api/auth/login/",
            {"username": "alice", "password": "password123"},
            format="json",
        )

        response = self.client.patch(
            "/api/settings/",
            {"username": "Anan"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        renamed_user.refresh_from_db()
        self.assertEqual(renamed_user.username, "Anan")

    def test_logout_revokes_cookie_token(self):
        user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "alice", "password": "password123"},
            format="json",
        )

        token_key = login_response.cookies["authToken"].value
        self.assertTrue(Token.objects.filter(user=user, key=token_key).exists())

        logout_response = self.client.post("/api/auth/logout/")

        self.assertEqual(logout_response.status_code, 204)
        self.assertFalse(Token.objects.filter(user=user, key=token_key).exists())

    def test_admin_endpoints_reject_non_staff_users(self):
        User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password123",
        )
        self.client.post(
            "/api/auth/login/",
            {"username": "alice", "password": "password123"},
            format="json",
        )

        response = self.client.get("/api/auth/admin/users/")

        self.assertEqual(response.status_code, 403)

    def test_admin_can_reset_user_password(self):
        admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="admin123",
            is_staff=True,
            is_superuser=True,
        )
        target = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="old-password",
        )
        self.client.post(
            "/api/auth/admin/login/",
            {"username": "admin", "password": "admin123"},
            format="json",
        )

        response = self.client.patch(
            f"/api/auth/admin/users/{target.id}/",
            {"password": "new-password-123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        target.refresh_from_db()
        self.assertTrue(target.check_password("new-password-123"))
        self.assertNotIn("password", response.data)
