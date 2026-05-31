import re

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers

from .models import UserSettings


User = get_user_model()
PRIVILEGED_ADMIN_FIELDS = {"is_staff", "is_superuser"}

PASSWORD_STRENGTH_HINT = "密码强度太弱，请至少包含大写字母、小写字母、数字和特殊字符中的 3 类。"


def translate_password_error(message):
    known_messages = {
        "This password is too short. It must contain at least 8 characters.": "密码至少需要 8 位。",
        "This password is too common.": "密码过于常见，请换一个更复杂的密码。",
        "This password is entirely numeric.": "密码不能全是数字。",
    }
    return known_messages.get(message, message)


def normalize_email(value):
    return (value or "").strip().lower()


def username_taken(value, exclude_user=None):
    return User.objects.exclude(pk=getattr(exclude_user, "pk", None)).filter(username=value).exists()


def is_privileged_user(user):
    return bool(user and (user.is_staff or user.is_superuser))


def validate_password_strength(password, user=None):
    checks = [
        bool(re.search(r"[a-z]", password or "")),
        bool(re.search(r"[A-Z]", password or "")),
        bool(re.search(r"\d", password or "")),
        bool(re.search(r"[^A-Za-z0-9]", password or "")),
    ]
    if sum(checks) < 3:
        raise serializers.ValidationError(PASSWORD_STRENGTH_HINT)
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(translate_password_error(exc.messages[0])) from exc


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
        ]


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "password",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        target = self.instance

        if getattr(actor, "is_superuser", False):
            return attrs

        if is_privileged_user(target):
            raise PermissionDenied("普通管理员只能管理非特权账号。")

        requested_privileged_fields = PRIVILEGED_ADMIN_FIELDS.intersection(self.initial_data.keys())
        for field_name in requested_privileged_fields:
            requested_value = attrs.get(field_name, getattr(target, field_name))
            if requested_value != getattr(target, field_name):
                raise PermissionDenied("只有超级管理员可以修改管理员角色。")

        return attrs

    def validate_email(self, value):
        value = normalize_email(value)
        user = self.instance
        if User.objects.exclude(pk=getattr(user, "pk", None)).filter(email__iexact=value).exists():
            raise serializers.ValidationError("邮箱已被占用。")
        return value

    def validate_username(self, value):
        user = self.instance
        if username_taken(value, exclude_user=user):
            raise serializers.ValidationError("用户名已被占用。")
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop("password", "")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        error_messages={"blank": "请输入用户名。", "required": "请输入用户名。"},
    )
    email = serializers.EmailField(
        error_messages={
            "blank": "请输入邮箱。",
            "required": "请输入邮箱。",
            "invalid": "请输入有效的邮箱地址。",
        }
    )
    password = serializers.CharField(
        write_only=True,
        error_messages={
            "blank": "请输入密码。",
            "required": "请输入密码。",
        },
    )
    confirm_password = serializers.CharField(
        write_only=True,
        error_messages={"blank": "请再次输入密码。", "required": "请再次输入密码。"},
    )

    def validate_username(self, value):
        if username_taken(value):
            raise serializers.ValidationError("用户名已被占用。")
        return value

    def validate_email(self, value):
        value = normalize_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("邮箱已被占用。")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "两次密码不一致。"})
        user = User(username=attrs.get("username", ""), email=attrs.get("email", ""))
        try:
            validate_password_strength(attrs["password"], user=user)
        except serializers.ValidationError:
            pass
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        error_messages={"blank": "请输入用户名或邮箱。", "required": "请输入用户名或邮箱。"}
    )
    password = serializers.CharField(
        write_only=True,
        error_messages={"blank": "请输入密码。", "required": "请输入密码。"},
    )

    def validate(self, attrs):
        username = attrs["username"]
        password = attrs["password"]
        user = authenticate(username=username, password=password)
        if user is None:
            try:
                user_obj = User.objects.get(email=username)
            except User.DoesNotExist:
                user_obj = None
            if user_obj is not None:
                user = authenticate(username=user_obj.username, password=password)
        if user is None:
            raise serializers.ValidationError("用户名、邮箱或密码错误。")
        attrs["user"] = user
        return attrs


class UserSettingsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        required=False,
        error_messages={"blank": "用户名不能为空。"},
    )
    email = serializers.EmailField(
        source="user.email",
        required=False,
        error_messages={"invalid": "请输入有效的邮箱地址。", "blank": "邮箱不能为空。"},
    )

    class Meta:
        model = UserSettings
        fields = ["username", "email", "theme", "language", "font_size"]

    def validate_username(self, value):
        user = getattr(self.instance, "user", None)
        if username_taken(value, exclude_user=user):
            raise serializers.ValidationError("用户名已被占用。")
        return value

    def validate_email(self, value):
        value = normalize_email(value)
        user = getattr(self.instance, "user", None)
        if User.objects.exclude(pk=getattr(user, "pk", None)).filter(email__iexact=value).exists():
            raise serializers.ValidationError("邮箱已被占用。")
        return value

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        if user_data:
            user.save(update_fields=list(user_data.keys()))
        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        error_messages={"blank": "请输入旧密码。", "required": "请输入旧密码。"},
    )
    new_password = serializers.CharField(
        write_only=True,
        error_messages={
            "blank": "请输入新密码。",
            "required": "请输入新密码。",
        },
    )
    confirm_password = serializers.CharField(
        write_only=True,
        error_messages={"blank": "请再次输入新密码。", "required": "请再次输入新密码。"},
    )

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "旧密码不正确。"})
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "两次密码不一致。"})
        try:
            validate_password_strength(attrs["new_password"], user=user)
        except serializers.ValidationError:
            pass
        return attrs
