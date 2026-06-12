import sys
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.utils import timezone
from .tasks import motor_global_notificaciones

def start():
    # Evitamos que el reloj arranque si estás corriendo migraciones o tests
    if 'runserver' not in sys.argv:
        return

    scheduler = BackgroundScheduler(timezone=timezone.get_current_timezone())
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Configuramos la tarea para que se ejecute cada 1 minuto
    scheduler.add_job(
        motor_global_notificaciones,
        trigger='interval',
        minutes=1,  # Podés cambiar esto a 'hours=1' en producción si querés
        id='motor_notificaciones',
        max_instances=1,
        replace_existing=True,
    )

    register_events(scheduler)
    scheduler.start()
    print("⏳ [Scheduler] Iniciado correctamente. Revisando alertas cada 1 minuto.")