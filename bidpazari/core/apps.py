from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "bidpazari.core"
    verbose_name = "Bidpazari Core"

    def ready(self):
        import bidpazari.core.signals
