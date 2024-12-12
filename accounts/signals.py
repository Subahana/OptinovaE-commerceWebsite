from django.db.models.signals import post_save
from django.conf import settings
from django.dispatch import receiver
from django.core.mail import send_mail
from django.utils import timezone
from allauth.socialaccount.signals import social_account_added
from django.contrib.auth import get_user_model
from user_wallet.models import Wallet
from .models import OtpToken

User = get_user_model()

@receiver(social_account_added)
def handle_google_user(sender, request, sociallogin, **kwargs):
    user = sociallogin.user

    if sociallogin.account.provider == 'google':
        user.is_google_user = True
        user.is_active = True  # Activate Google Sign-In users immediately
        user.save()

        # Ensure a wallet is created for the user
        Wallet.objects.get_or_create(user=user)
        print(f"Google user setup complete for {user.email}")


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_token(sender, instance, created, **kwargs):
    if created:
        # Skip OTP creation for Google users and superusers
        if instance.is_google_user or instance.is_superuser:
            return

        # Create OTP token
        otp = OtpToken.objects.create(
            user=instance,
            otp_expires_at=timezone.now() + timezone.timedelta(minutes=1)
        )

        # Deactivate user until email verification
        instance.is_active = False
        instance.save(update_fields=['is_active'])

        # Ensure the OTP token was created successfully
        if otp and otp.otp_code:
            subject = "Email Verification"
            message = (
                f"Hi {instance.username}, here is your OTP: {otp.otp_code}. "
                f"It expires in 1 minute. Use the link below to verify your email:\n"
                f"http://127.0.0.1:8000/email_verify/{instance.username}"
            )
            sender_email = settings.DEFAULT_FROM_EMAIL
            receiver_email = [instance.email]

            try:
                # Send email
                send_mail(
                    subject,
                    message,
                    sender_email,
                    receiver_email,
                    fail_silently=False,
                )
                print(f"OTP email sent to {instance.email}")
            except Exception as e:
                print(f"Failed to send OTP email to {instance.email}: {e}")
        else:
            print(f"Failed to create OTP for user {instance.username}")
    else:
        print(f"User {instance.username} was updated, not created.")
