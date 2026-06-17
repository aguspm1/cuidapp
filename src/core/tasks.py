from django.utils import timezone
from .models import PerfilPaciente, EventoCalendario, Medicamento, RegistroToma, Notificacion

VENTANA_MINUTOS = 5  # Margen para absorber delays del scheduler

def _minutos(t):
    """Convierte un time en minutos totales desde medianoche."""
    return t.hour * 60 + t.minute

def generar_alertas_automaticas(paciente, tutores):
    """
    Revisa si hay eventos inminentes o medicación y crea las notificaciones.
    """
    ahora = timezone.localtime(timezone.now())
    en_una_hora = ahora + timezone.timedelta(hours=1)
    ahora_minutos = _minutos(ahora.time())

    # 1. ALERTAS DE EVENTOS
    eventos_proximos = EventoCalendario.objects.filter(
        paciente=paciente, fecha_hora__gte=ahora, fecha_hora__lte=en_una_hora
    )
    for ev in eventos_proximos:
        if not Notificacion.objects.filter(usuario=paciente, tipo='evento', referencia_id=ev.id).exists():
            hora_local_ev = timezone.localtime(ev.fecha_hora)
            Notificacion.objects.create(
                usuario=paciente, tipo='evento', referencia_id=ev.id,
                titulo=f"📅 Evento próximo: {ev.titulo}",
                mensaje=f"Tenés este evento a las {hora_local_ev.strftime('%H:%M')} hs."
            )

    # 2. ALERTAS DE MEDICACIÓN
    medicamentos = Medicamento.objects.filter(paciente=paciente, activo=True)

    for med in medicamentos:

        # --- FRECUENCIA FIJA: usa HorarioToma con ventana de ±VENTANA_MINUTOS ---
        if med.frecuencia_tipo == 'fijo':
            for horario in med.horarios.all():
                delta = abs(ahora_minutos - _minutos(horario.hora))
                if delta > VENTANA_MINUTOS:
                    continue

                # referencia_id anclado al horario del modelo, no a 'ahora'
                # → el mismo horario genera el mismo ID aunque el scheduler corra 5 veces
                ref = int(f"{med.id}{ahora.strftime('%d%m')}{horario.hora.strftime('%H%M')}")

                if not Notificacion.objects.filter(usuario=paciente, tipo='medicacion', referencia_id=ref).exists():
                    Notificacion.objects.create(
                        usuario=paciente, tipo='medicacion', referencia_id=ref,
                        titulo=f"💊 Hora de tomar: {med.nombre}",
                        mensaje=f"Dosis: {med.dosis_por_toma} {med.unidad_medida}"
                    )

                if tutores:
                    for tutor in tutores:
                        if not Notificacion.objects.filter(usuario=tutor, tipo='medicacion', referencia_id=ref).exists():
                            Notificacion.objects.create(
                                usuario=tutor, tipo='medicacion', referencia_id=ref,
                                titulo=f"⏰ Recordatorio para {paciente.first_name}",
                                mensaje=f"Debe tomar {med.nombre} ({med.dosis_por_toma} {med.unidad_medida})."
                            )

        # --- FRECUENCIA POR EVENTO: mismo criterio de ventana ---
        elif med.frecuencia_tipo == 'evento' and med.evento_toma:
            mapa_eventos = {
                'desayuno':     (9, 0),
                'almuerzo':     (13, 0),
                'cena':         (21, 0),
                'antes_dormir': (23, 0),
            }
            hora_evento = mapa_eventos.get(med.evento_toma)
            if hora_evento:
                minutos_evento = hora_evento[0] * 60 + hora_evento[1]
                if abs(ahora_minutos - minutos_evento) <= VENTANA_MINUTOS:
                    ref = int(f"{med.id}{ahora.strftime('%d%m')}{hora_evento[0]:02d}{hora_evento[1]:02d}")

                    if not Notificacion.objects.filter(usuario=paciente, tipo='medicacion', referencia_id=ref).exists():
                        Notificacion.objects.create(
                            usuario=paciente, tipo='medicacion', referencia_id=ref,
                            titulo=f"💊 Hora de tomar: {med.nombre}",
                            mensaje=f"Dosis: {med.dosis_por_toma} {med.unidad_medida}"
                        )

                    if tutores:
                        for tutor in tutores:
                            if not Notificacion.objects.filter(usuario=tutor, tipo='medicacion', referencia_id=ref).exists():
                                Notificacion.objects.create(
                                    usuario=tutor, tipo='medicacion', referencia_id=ref,
                                    titulo=f"⏰ Recordatorio para {paciente.first_name}",
                                    mensaje=f"Debe tomar {med.nombre} ({med.dosis_por_toma} {med.unidad_medida})."
                                )

        # --- FRECUENCIA POR INTERVALO: lógica original, estaba bien ---
        elif med.frecuencia_tipo == 'intervalo' and med.cada_cuantas_horas:
            ultima_toma = RegistroToma.objects.filter(
                medicamento=med, paciente=paciente
            ).order_by('-fecha_hora').first()

            disparar = False
            if ultima_toma:
                proxima_toma = ultima_toma.fecha_hora + timezone.timedelta(hours=med.cada_cuantas_horas)
                if proxima_toma <= ahora <= (proxima_toma + timezone.timedelta(hours=1)):
                    disparar = True
            else:
                disparar = True  # nunca tomó → avisar ahora

            if disparar:
                ref = int(f"{med.id}{ahora.strftime('%d%m%H')}")

                if not Notificacion.objects.filter(usuario=paciente, tipo='medicacion', referencia_id=ref).exists():
                    Notificacion.objects.create(
                        usuario=paciente, tipo='medicacion', referencia_id=ref,
                        titulo=f"💊 Hora de tomar: {med.nombre}",
                        mensaje=f"Dosis: {med.dosis_por_toma} {med.unidad_medida}"
                    )

                if tutores:
                    for tutor in tutores:
                        if not Notificacion.objects.filter(usuario=tutor, tipo='medicacion', referencia_id=ref).exists():
                            Notificacion.objects.create(
                                usuario=tutor, tipo='medicacion', referencia_id=ref,
                                titulo=f"⏰ Recordatorio para {paciente.first_name}",
                                mensaje=f"Debe tomar {med.nombre} ({med.dosis_por_toma} {med.unidad_medida})."
                            )


def motor_global_notificaciones():
    """Tarea maestra que ejecuta el scheduler en segundo plano."""
    ahora_local = timezone.localtime(timezone.now())
    print(f"[{ahora_local.strftime('%H:%M:%S')}] ⚙️ Ejecutando motor de notificaciones en segundo plano...")

    perfiles = PerfilPaciente.objects.select_related('user').all()
    for perfil in perfiles:
        paciente = perfil.user
        tutores = perfil.tutores.all()
        generar_alertas_automaticas(paciente, tutores)