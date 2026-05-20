from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


User = get_user_model()


class AdminRoleBoundaryTests(APITestCase):
    def admin_login(self, username, password):
        response = self.client.post(
            "/api/auth/admin/login/",
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_cannot_promote_other_users_to_staff_or_superuser(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staff-password",
            is_staff=True,
        )
        target = User.objects.create_user(
            username="target",
            email="target@example.com",
            password="target-password",
        )
        self.admin_login(staff_user.username, "staff-password")

        response = self.client.patch(
            f"/api/auth/admin/users/{target.id}/",
            {"is_staff": True, "is_superuser": True},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        target.refresh_from_db()
        self.assertFalse(target.is_staff)
        self.assertFalse(target.is_superuser)

    def test_staff_cannot_promote_themselves_to_superuser(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staff-password",
            is_staff=True,
        )
        self.admin_login(staff_user.username, "staff-password")

        response = self.client.patch(
            f"/api/auth/admin/users/{staff_user.id}/",
            {"is_superuser": True},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        staff_user.refresh_from_db()
        self.assertFalse(staff_user.is_superuser)

    def test_staff_can_still_update_non_privileged_admin_fields(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staff-password",
            is_staff=True,
        )
        target = User.objects.create_user(
            username="target",
            email="target@example.com",
            password="target-password",
        )
        self.admin_login(staff_user.username, "staff-password")

        response = self.client.patch(
            f"/api/auth/admin/users/{target.id}/",
            {"first_name": "Updated", "is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        target.refresh_from_db()
        self.assertEqual(target.first_name, "Updated")
        self.assertFalse(target.is_active)

    def test_staff_can_update_non_privileged_user_when_role_fields_are_unchanged(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staff-password",
            is_staff=True,
        )
        target = User.objects.create_user(
            username="target",
            email="target@example.com",
            password="target-password",
        )
        self.admin_login(staff_user.username, "staff-password")

        response = self.client.patch(
            f"/api/auth/admin/users/{target.id}/",
            {
                "first_name": "Updated",
                "is_staff": target.is_staff,
                "is_superuser": target.is_superuser,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        target.refresh_from_db()
        self.assertEqual(target.first_name, "Updated")
        self.assertFalse(target.is_staff)
        self.assertFalse(target.is_superuser)

    def test_staff_cannot_modify_other_staff_account(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staff-password",
            is_staff=True,
        )
        target = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="manager-password",
            is_staff=True,
        )
        self.admin_login(staff_user.username, "staff-password")

        response = self.client.patch(
            f"/api/auth/admin/users/{target.id}/",
            {"first_name": "Blocked", "is_staff": True},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        target.refresh_from_db()
        self.assertEqual(target.first_name, "")

    def test_staff_cannot_delete_staff_account(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staff-password",
            is_staff=True,
        )
        target = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="manager-password",
            is_staff=True,
        )
        self.admin_login(staff_user.username, "staff-password")

        response = self.client.delete(f"/api/auth/admin/users/{target.id}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(id=target.id).exists())

    def test_staff_can_delete_non_privileged_account(self):
        staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staff-password",
            is_staff=True,
        )
        target = User.objects.create_user(
            username="target",
            email="target@example.com",
            password="target-password",
        )
        self.admin_login(staff_user.username, "staff-password")

        response = self.client.delete(f"/api/auth/admin/users/{target.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(id=target.id).exists())

    def test_superuser_can_modify_privileged_admin_fields(self):
        superuser = User.objects.create_user(
            username="root",
            email="root@example.com",
            password="root-password",
            is_staff=True,
            is_superuser=True,
        )
        target = User.objects.create_user(
            username="target",
            email="target@example.com",
            password="target-password",
        )
        self.admin_login(superuser.username, "root-password")

        response = self.client.patch(
            f"/api/auth/admin/users/{target.id}/",
            {"is_staff": True, "is_superuser": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        target.refresh_from_db()
        self.assertTrue(target.is_staff)
        self.assertTrue(target.is_superuser)
