from django.utils import timezone
from .models import PerfilPaciente, EventoCalendario, Medicamento, RegistroToma, Notificacion

def generar_alertas_automaticas(paciente, tutor):
    """
    Revisa si hay eventos inminentes o medicación y crea las notificaciones.
    (Es la misma función que tenías, pero ahora vive aquí)
    """
    ahora = timezone.now()
    en_una_hora = ahora + timezone.timedelta(hours=1)
    hora_actual_str = ahora.strftime('%H:00')

    # 1. ALERTAS DE EVENTOS
    eventos_proximos = EventoCalendario.objects.filter(
        paciente=paciente, fecha_hora__gte=ahora, fecha_hora__lte=en_una_hora
    )
    for ev in eventos_proximos:
        if not Notificacion.objects.filter(usuario=paciente, tipo='evento', referencia_id=ev.id).exists():
            Notificacion.objects.create(
                usuario=paciente, tipo='evento', referencia_id=ev.id,
                titulo=f"📅 Evento próximo: {ev.titulo}",
                mensaje=f"Tenés este evento a las {ev.fecha_hora.strftime('%H:%M')} hs."
            )

    # 2. ALERTAS DE MEDICACIÓN
    medicamentos = Medicamento.objects.filter(paciente=paciente, activo=True)
    for med in medicamentos:
        disparar_alerta = False
        
        if med.frecuencia_tipo == 'fijo' and med.horario_fijo:
            if hora_actual_str in med.horario_fijo:
                disparar_alerta = True

        elif med.frecuencia_tipo == 'evento' and med.evento_toma:
            mapa_eventos = {'desayuno': '09:00', 'almuerzo': '13:00', 'cena': '21:00', 'antes_dormir': '23:00'}
            if mapa_eventos.get(med.evento_toma) == hora_actual_str:
                disparar_alerta = True

        elif med.frecuencia_tipo == 'intervalo' and med.cada_cuantas_horas:
            ultima_toma = RegistroToma.objects.filter(medicamento=med, paciente=paciente).order_by('-fecha_hora').first()
            if ultima_toma:
                proxima_toma = ultima_toma.fecha_hora + timezone.timedelta(hours=med.cada_cuantas_horas)
                if proxima_toma <= ahora <= (proxima_toma + timezone.timedelta(hours=1)):
                    disparar_alerta = True
            else:
                disparar_alerta = True

        if disparar_alerta:
            ref_str = int(f"{med.id}{ahora.strftime('%d%m%H')}")
            if not Notificacion.objects.filter(usuario=paciente, tipo='medicacion', referencia_id=ref_str).exists():
                Notificacion.objects.create(
                    usuario=paciente, tipo='medicacion', referencia_id=ref_str,
                    titulo=f"💊 Hora de tomar: {med.nombre}",
                    mensaje=f"Dosis: {med.dosis_por_toma} {med.unidad_medida}"
                )
            if tutor and not Notificacion.objects.filter(usuario=tutor, tipo='medicacion', referencia_id=ref_str).exists():
                Notificacion.objects.create(
                    usuario=tutor, tipo='medicacion', referencia_id=ref_str,
                    titulo=f"⏰ Recordatorio para {paciente.first_name}",
                    mensaje=f"Debe tomar {med.nombre} ({med.dosis_por_toma} {med.unidad_medida})."
                )

def motor_global_notificaciones():
    """Esta es la tarea maestra que ejecutará el reloj en segundo plano"""
    print(f"[{timezone.now().strftime('%H:%M:%S')}] ⚙️ Ejecutando motor de notificaciones en segundo plano...")
    
    # Busca a todos los pacientes del sistema
    perfiles = PerfilPaciente.objects.select_related('user').all()
    for perfil in perfiles:
        paciente = perfil.user
        tutor = perfil.tutor if perfil.tutor else perfil.tutores.first()
        generar_alertas_automaticas(paciente, tutor)