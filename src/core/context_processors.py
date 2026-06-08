from django.utils import timezone
from datetime import timedelta
from .models import PerfilPaciente, RegistroToma, Medicamento


def rol_usuario(request):
    if not request.user.is_authenticated:
        return {'usuario_es_tutor': False}

    tiene_perfil_propio = PerfilPaciente.objects.filter(user=request.user).exists()
    es_tutor = not tiene_perfil_propio
    return {'usuario_es_tutor': es_tutor}


def notificaciones_tutor(request):
    """Inyecta en todos los templates las notificaciones para el tutor en un entorno optimizado."""
    if not request.user.is_authenticated:
        return {}

    # OPTIMIZACIÓN CRÍTICA: Cortocircuitar inmediatamente si es un Paciente
    tiene_perfil_propio = PerfilPaciente.objects.filter(user=request.user).exists()
    if tiene_perfil_propio:
        return {}

    # Ahora sí, sabemos al 100% que es un Tutor, buscamos sus pacientes a cargo
    pacientes_ids = PerfilPaciente.objects.filter(
        tutor=request.user
    ).values_list('user__id', flat=True)

    if not pacientes_ids:
        return {}

    # Tomas de las últimas 24 hs
    desde = timezone.now() - timedelta(hours=24)
    tomas_notif = list(
        RegistroToma.objects
        .filter(paciente__id__in=pacientes_ids, fecha_hora__gte=desde)
        .select_related('medicamento', 'paciente')
        .order_by('-fecha_hora')[:20]
    )

    # Timestamp de última lectura guardado en sesión
    ultima_lectura_str = request.session.get('notif_ultima_lectura')
    if ultima_lectura_str:
        from datetime import datetime
        ultima_lectura = datetime.fromisoformat(ultima_lectura_str)
        if ultima_lectura.tzinfo is None:
            from django.utils.timezone import make_aware
            ultima_lectura = make_aware(ultima_lectura)
        tomas_nuevas = [t for t in tomas_notif if t.fecha_hora > ultima_lectura]
    else:
        tomas_nuevas = tomas_notif

    # Stock bajo directo sin cálculos redundantes
    remedios_bajos = Medicamento.objects.filter(
        paciente__id__in=pacientes_ids, 
        activo=True
    ).select_related('paciente')
    
    count_stock_bajo = 0
    for r in remedios_bajos:
        if r.stock_actual <= r.umbral_stock_minimo:
            count_stock_bajo += 1

    return {
        'notif_tomas': tomas_notif,
        'notif_nuevas_count': len(tomas_nuevas) + count_stock_bajo,
        'notif_tomas_nuevas': tomas_nuevas,
        'count_stock_bajo': count_stock_bajo
    }