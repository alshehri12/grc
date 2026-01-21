from django.apps import AppConfig


class GovernanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "governance"
    
    def ready(self):
        # Import signals to register them
        try:
            import governance.signals  # noqa
        except ImportError:
            pass