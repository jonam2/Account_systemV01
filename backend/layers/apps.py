"""Layers app configuration"""
from django.apps import AppConfig


class LayersConfig(AppConfig):
    """Configuration for layers app"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'layers'
    verbose_name = 'Layers'
    
    def ready(self):
        """Import models when app is ready"""
        # Import all models here to register them
        from layers.models import user_models  # noqa
        from layers.models import product_models
        from layers.models import contact_models
        from layers.models import warehouse_models
        from layers.models import invoice_models

        