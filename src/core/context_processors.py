from django.utils import timezone
from datetime import timedelta
from django.db import models as db_models
from .models import PerfilPaciente, RegistroToma, Medicamento, Notificacion

def rol_usuario(request):
    if not request.user.is_authenticated:
        return {'usuario_es_tutor': False}
    tiene_perfil_paciente = PerfilPaciente.objects.filter(user=request.user).exists()
    return {'usuario_es_tutor': not tiene_perfil_paciente}


def notificaciones_tutor(request):
    """Inyecta de forma automática las alertas y la bitácora en el navbar de todas las páginas."""
    if not request.user.is_authenticated:
        return {}

    tiene_perfil_paciente = PerfilPaciente.objects.filter(user=request.user).exists()

    # 💡 OPTIMIZACIÓN: Definimos qué ID de pacientes monitorear según el rol del usuario logueado
    if tiene_perfil_paciente:
        pacientes_ids = [request.user.id]
    else:
        # Es tutor: obtenemos su red de apoyo completa
        pacientes_ids = PerfilPaciente.objects.filter(
            db_models.Q(tutores=request.user) | db_models.Q(tutor=request.user)
        ).values_list('user__id', flat=True).distinct()

    if not pacientes_ids and not tiene_perfil_paciente:
        return {}

    # Notificaciones directas pendientes para el usuario actual (sea paciente o tutor)
    notificaciones_pendientes = list(
        Notificacion.objects.filter(
            usuario=request.user,
            leida=False
        ).order_by('-fecha_creacion')[:20]
    )

    # Tomas de las últimas 24 hs para la bitácora
    desde = timezone.now() - timedelta(hours=24)
    tomas_notif = list(
        RegistroToma.objects
        .filter(paciente__id__in=pacientes_ids, fecha_hora__gte=desde)
        .select_related('medicamento', 'paciente')
        .order_by('-fecha_hora')[:20]
    )

    # Control de lecturas nuevas
    ultima_lectura_str = request.session.get('notif_ultima_lectura')
    if ultima_lectura_str:
        from datetime import datetime
        from django.utils.timezone import make_aware
        try:
            ultima_lectura = datetime.fromisoformat(ultima_lectura_str)
            if ultima_lectura.tzinfo is None:
                ultima_lectura = make_aware(ultima_lectura)
            tomas_nuevas = [t for t in tomas_notif if t.fecha_hora > ultima_lectura]
        except ValueError:
            tomas_nuevas = tomas_notif
    else:
        tomas_nuevas = tomas_notif

    # Alertas de stock bajo
    stock_notif = [
        m for m in Medicamento.objects.filter(
            paciente__id__in=pacientes_ids, activo=True
        ).select_related('paciente')
        if m.stock_actual <= m.umbral_stock_minimo
    ]

    cantidad_notificaciones = len(notificaciones_pendientes) + len(stock_notif)

    return {
        'notificaciones_pendientes': notificaciones_pendientes,
        'cantidad_notificaciones':   cantidad_notificaciones,
        'tomas_notif':               tomas_notif,
        'tomas_nuevas_count':        len(tomas_nuevas),
        'stock_notif':               stock_notif,
        'notif_count':               cantidad_notificaciones,
    }