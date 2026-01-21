from django.apps import AppConfig


class ComplianceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "compliance"
    
    def ready(self):
        # Import signals to register them
        try:
            import compliance.signals  # noqa
        except ImportError:
            pass