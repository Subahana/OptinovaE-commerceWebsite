from django.apps import AppConfig


class UserWalletConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_wallet'

    def ready(self):
        import user_wallet.signals