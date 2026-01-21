from django.apps import AppConfig


class BcmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bcm"
    
    def ready(self):
        # Import signals to register them
        try:
            import bcm.signals  # noqa
        except ImportError:
            pass