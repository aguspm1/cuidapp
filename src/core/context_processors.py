from django.utils import timezone
from datetime import timedelta
from django.db import models as db_models
from .models import PerfilPaciente, RegistroToma, Medicamento, Notificacion


def rol_usuario(request):
    if not request.user.is_authenticated:
        return {'usuario_es_tutor': False}
    tiene_perfil_propio = PerfilPaciente.objects.filter(user=request.user).exists()
    return {'usuario_es_tutor': not tiene_perfil_propio}


def notificaciones_tutor(request):
    """Inyecta notificaciones en todos los templates."""
    if not request.user.is_authenticated:
        return {}

    # Solo para tutores
    tiene_perfil_propio = PerfilPaciente.objects.filter(user=request.user).exists()
    if tiene_perfil_propio:
        return {}

    # Pacientes a cargo — soporta FK legacy y M2M
    pacientes_ids = PerfilPaciente.objects.filter(
        db_models.Q(tutores=request.user) | db_models.Q(tutor=request.user)
    ).values_list('user__id', flat=True).distinct()

    if not pacientes_ids:
        return {}

    # Notificaciones del modelo Notificacion (para el panel)
    notificaciones_pendientes = list(
        Notificacion.objects.filter(
            usuario__id__in=pacientes_ids,
            leida=False
        ).order_by('-fecha_creacion')[:20]
    )

    # Tomas de las últimas 24 hs (para mostrar actividad)
    desde = timezone.now() - timedelta(hours=24)
    tomas_notif = list(
        RegistroToma.objects
        .filter(paciente__id__in=pacientes_ids, fecha_hora__gte=desde)
        .select_related('medicamento', 'paciente')
        .order_by('-fecha_hora')[:20]
    )

    # Timestamp de última lectura en sesión
    ultima_lectura_str = request.session.get('notif_ultima_lectura')
    if ultima_lectura_str:
        from datetime import datetime
        from django.utils.timezone import make_aware
        ultima_lectura = datetime.fromisoformat(ultima_lectura_str)
        if ultima_lectura.tzinfo is None:
            ultima_lectura = make_aware(ultima_lectura)
        tomas_nuevas = [t for t in tomas_notif if t.fecha_hora > ultima_lectura]
    else:
        tomas_nuevas = tomas_notif

    # Medicamentos con stock bajo
    stock_notif = [
        m for m in Medicamento.objects.filter(
            paciente__id__in=pacientes_ids, activo=True
        ).select_related('paciente')
        if m.stock_actual <= m.umbral_stock_minimo
    ]

    # Total para el badge
    cantidad_notificaciones = len(notificaciones_pendientes) + len(stock_notif)

    return {
        # Variables que usa base.html
        'notificaciones_pendientes': notificaciones_pendientes,
        'cantidad_notificaciones':   cantidad_notificaciones,
        # Variables extra para el panel completo
        'tomas_notif':               tomas_notif,
        'tomas_nuevas_count':        len(tomas_nuevas),
        'stock_notif':               stock_notif,
        'notif_count':               cantidad_notificaciones,  # alias por compatibilidad
    }