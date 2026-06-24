from django.apps import AppConfig


class VehicleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.vehicles'

    def ready(self):
        # import apps.vehicles.signals  # noqa
        pass