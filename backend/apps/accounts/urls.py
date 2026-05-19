from django.urls import path

from .views import (
    AdminLoginView,
    AdminMeView,
    AdminUserDetailView,
    AdminUserListView,
    ChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("admin/login/", AdminLoginView.as_view(), name="admin-login"),
    path("admin/me/", AdminMeView.as_view(), name="admin-me"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-users"),
    path("admin/users/<int:user_id>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
]
