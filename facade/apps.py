from django.apps import AppConfig


class FacadeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'facade'

    def ready(self):
        # Implicitly connect signal handlers decorated with @receiver.
        from . import signals
