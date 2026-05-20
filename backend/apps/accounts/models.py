from django.conf import settings
from django.db import models


class UserSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="settings_profile",
    )
    theme = models.CharField(max_length=20, default="light")
    language = models.CharField(max_length=20, default="zh-CN")
    font_size = models.CharField(max_length=20, default="medium")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"settings:{self.user_id}"

# Create your models here.
