import os
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # El autoreloader de Django ejecuta esto dos veces. 
        # Este 'if' asegura que el reloj se inicie solo una vez.
        if os.environ.get('RUN_MAIN', None) == 'true':
            from . import scheduler
            scheduler.start()