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
            
            # 💡 Convertimos a minúsculas y buscamos palabras clave (igual que en models.py)
            texto_evento = med.evento_toma.lower()
            hora_evento = None
            
            if 'desayuno' in texto_evento or 'levantar' in texto_evento or 'mañana' in texto_evento:
                hora_evento = (9, 0)
            elif 'almuerzo' in texto_evento or 'mediod' in texto_evento:
                hora_evento = (13, 0)
            elif 'cena' in texto_evento:
                hora_evento = (21, 0)
            elif 'dormir' in texto_evento or 'acostar' in texto_evento or 'noche' in texto_evento:
                hora_evento = (23, 0)

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

def auditar_tomas_atrasadas():
    """
    Se ejecuta periódicamente. Busca tomas que debieron hacerse hace más de 1 hora
    y que todavía no tienen un registro en la base de datos.
    """
    ahora = timezone.localtime(timezone.now())
    ahora_minutos = ahora.hour * 60 + ahora.minute
    
    # Buscamos todos los medicamentos activos
    medicamentos = Medicamento.objects.filter(activo=True)

    for med in medicamentos:
        paciente = med.paciente
        tutores = paciente.perfil_medico.tutores.all() if hasattr(paciente, 'perfil_medico') else []
        
        hora_objetivo = None
        
        # 1. Chequeamos horarios fijos
        if med.frecuencia_tipo == 'fijo':
            horarios = sorted([h.hora for h in med.horarios.all()])
            if not horarios and med.horario_fijo:
                from datetime import datetime
                for part in med.horario_fijo.split():
                    try:
                        horarios.append(datetime.strptime(part.replace('hs', '').strip()[:5], '%H:%M').time())
                    except ValueError:
                        continue
            
            # Buscamos si hay un horario que ya pasó
            pasados = [h for h in horarios if h <= ahora.time()]
            if pasados:
                hora_objetivo = pasados[-1] # El último horario que ya pasó hoy
                minutos_objetivo = hora_objetivo.hour * 60 + hora_objetivo.minute
                
        # 2. Chequeamos eventos
        elif med.frecuencia_tipo == 'evento' and med.evento_toma:
            texto = med.evento_toma.lower()
            if 'desayuno' in texto or 'mañana' in texto: minutos_objetivo = 9 * 60
            elif 'almuerzo' in texto or 'mediod' in texto: minutos_objetivo = 13 * 60
            elif 'cena' in texto: minutos_objetivo = 21 * 60
            elif 'dormir' in texto or 'noche' in texto: minutos_objetivo = 23 * 60
            else: minutos_objetivo = None
            
            if minutos_objetivo and ahora_minutos >= minutos_objetivo:
                hora_objetivo = True # Bandera para saber que ya pasó la hora

        # 3. Si encontramos una hora objetivo que ya pasó, calculamos el atraso
        if hora_objetivo:
            # Calculamos si pasaron entre 60 y 70 minutos desde la hora pautada
            atraso = ahora_minutos - minutos_objetivo
            
            if 60 <= atraso <= 70:
                # Armamos una referencia ÚNICA para el atraso (le sumamos 999 al final para no pisar la alerta normal)
                ref_atraso = int(f"{med.id}{ahora.strftime('%d%m')}999")
                
                # Verificamos si NO tomó la pastilla hoy en esta ventana
                inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
                ya_la_tomo = med.registros_toma.filter(fecha_hora__gte=inicio_dia).exists()
                
                # Verificamos si no le mandamos ya esta misma alerta de atraso
                ya_avisamos = Notificacion.objects.filter(referencia_id=ref_atraso).exists()

                if not ya_la_tomo and not ya_avisamos:
                    # 🚨 1. Alerta para el Paciente
                    Notificacion.objects.create(
                        usuario=paciente, tipo='sistema', referencia_id=ref_atraso,
                        titulo="⚠️ Toma Olvidada",
                        mensaje=f"Pasó más de una hora y no registraste la toma de {med.nombre}. ¡No te olvides!"
                    )
                    
                    # 🚨 2. Alerta para los Tutores
                    for tutor in tutores:
                        Notificacion.objects.create(
                            usuario=tutor, tipo='sistema', referencia_id=ref_atraso,
                            titulo=f"🚨 Alerta: {paciente.first_name} se atrasó",
                            mensaje=f"Pasó más de una hora del horario pautado para {med.nombre} y el paciente no ha confirmado la toma."
                        )