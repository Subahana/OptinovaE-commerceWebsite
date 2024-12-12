from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import secrets
from datetime import timedelta
from django.utils import timezone

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_google_user = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'  
    REQUIRED_FIELDS = ['username']  

    def __str__(self):
        return self.email

class OtpToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps")
    otp_code = models.CharField(max_length=6, default=secrets.token_hex(3))
    otp_created_at = models.DateTimeField(auto_now_add=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.otp_expires_at:
            self.otp_expires_at = self.otp_created_at + timedelta(minutes=5)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.otp_code}"
