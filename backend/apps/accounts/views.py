from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authentication import get_authorization_header
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserSettings
from .serializers import (
    AdminUserSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    UserSettingsSerializer,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        UserSettings.objects.get_or_create(user=user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _created = Token.objects.get_or_create(user=user)
        UserSettings.objects.get_or_create(user=user)
        response = Response({"user": UserSerializer(user).data})
        response.set_cookie(
            settings.AUTH_TOKEN_COOKIE_NAME,
            token.key,
            max_age=settings.AUTH_TOKEN_COOKIE_MAX_AGE,
            httponly=settings.AUTH_TOKEN_COOKIE_HTTPONLY,
            secure=settings.AUTH_TOKEN_COOKIE_SECURE,
            samesite=settings.AUTH_TOKEN_COOKIE_SAMESITE,
            path="/",
        )
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token_key = request.COOKIES.get(settings.AUTH_TOKEN_COOKIE_NAME) or _get_token_from_header(request)
        if token_key:
            Token.objects.filter(key=token_key).delete()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(
            settings.AUTH_TOKEN_COOKIE_NAME,
            path="/",
        )
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class SettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        settings_obj, _created = UserSettings.objects.get_or_create(user=request.user)
        return Response(UserSettingsSerializer(settings_obj).data)

    def patch(self, request):
        settings_obj, _created = UserSettings.objects.get_or_create(user=request.user)
        serializer = UserSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        Token.objects.filter(user=request.user).delete()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(
            settings.AUTH_TOKEN_COOKIE_NAME,
            path="/",
        )
        return response


class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if not user.is_staff and not user.is_superuser:
            return Response({"detail": "不是管理员账号。"}, status=status.HTTP_403_FORBIDDEN)
        token, _created = Token.objects.get_or_create(user=user)
        response = Response({"user": UserSerializer(user).data})
        response.set_cookie(
            settings.AUTH_TOKEN_COOKIE_NAME,
            token.key,
            max_age=settings.AUTH_TOKEN_COOKIE_MAX_AGE,
            httponly=settings.AUTH_TOKEN_COOKIE_HTTPONLY,
            secure=settings.AUTH_TOKEN_COOKIE_SECURE,
            samesite=settings.AUTH_TOKEN_COOKIE_SAMESITE,
            path="/",
        )
        return response


class AdminMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({"detail": "不是管理员账号。"}, status=status.HTTP_403_FORBIDDEN)
        return Response(UserSerializer(request.user).data)


class AdminUserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({"detail": "不是管理员账号。"}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.order_by("-date_joined", "-id")
        return Response(
            {
                "count": users.count(),
                "users": AdminUserSerializer(users, many=True).data,
            }
        )


class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id):
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({"detail": "不是管理员账号。"}, status=status.HTTP_403_FORBIDDEN)
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "用户不存在。"}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminUserSerializer(target, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminUserSerializer(target).data)

    def delete(self, request, user_id):
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({"detail": "不是管理员账号。"}, status=status.HTTP_403_FORBIDDEN)
        if request.user.id == user_id:
            return Response({"detail": "不能删除当前管理员自己。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "用户不存在。"}, status=status.HTTP_404_NOT_FOUND)
        target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _get_token_from_header(request):
    auth = get_authorization_header(request).split()
    if len(auth) == 2 and auth[0].lower() == b"token":
        return auth[1].decode("utf-8")
    return None

# Create your views here.
