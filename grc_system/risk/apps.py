from django.apps import AppConfig


class RiskConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "risk"
    
    def ready(self):
        # Import signals to register them
        try:
            import risk.signals  # noqa
        except ImportError:
            pass