import json
from django.db import models
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta
from django.core.paginator import Paginator
from .models import Medicamento, EventoCalendario, PerfilPaciente, FotoDocumento, DatoMedicion, RegistroToma, Notificacion, PerfilTutor, HorarioToma
from .forms import RegistroForm, MedicamentoForm, PerfilPacienteForm, SubirFotoForm, PerfilTutorForm
from .serializers import EventoCalendarioSerializer


# ========== HELPERS REFACTORIZADOS (CORREGIDO) ==========

def es_tutor(user):
    """
    Un usuario es tutor si está autenticado y tiene un PerfilTutor explícito.
    🛡️ SOLUCIÓN AL LIMBO: Si no tiene PerfilTutor ni PerfilPaciente, asumimos que es un
    tutor recién registrado y le creamos el perfil al vuelo para evitar bloqueos.
    """
    if not user.is_authenticated:
        return False
        
    if PerfilTutor.objects.filter(user=user).exists():
        return True
        
    if not PerfilPaciente.objects.filter(user=user).exists():
        PerfilTutor.objects.get_or_create(user=user)
        return True
        
    return False

def es_paciente(user):
    """Un usuario es paciente si está autenticado y tiene un PerfilPaciente explícito en la base de datos."""
    if not user.is_authenticated:
        return False
    return PerfilPaciente.objects.filter(user=user).exists()

def validar_acceso_tutor(request):
    if not es_tutor(request.user):
        messages.error(request, "❌ Solo los tutores pueden realizar esta acción.")
        return False
    return True

def obtener_paciente_activo(request):
    """
    Devuelve (perfil, paciente_user) según el rol.
    """
    # ✏️ ¡CORREGIDO AQUÍ! Agregado user=request.user para que Django pueda buscar bien
    if es_paciente(request.user):
        perfil_propio = PerfilPaciente.objects.filter(user=request.user).first()
        if perfil_propio:
            return perfil_propio, request.user

    paciente_id_sesion = request.session.get("paciente_seleccionado")
    if paciente_id_sesion:
        perfil = PerfilPaciente.objects.filter(
            user_id=paciente_id_sesion
        ).filter(
            models.Q(tutores=request.user) | models.Q(tutor=request.user)
        ).first()
        if perfil:
            if perfil.tutor == request.user and not perfil.tutores.filter(pk=request.user.pk).exists():
                perfil.tutores.add(request.user)
            return perfil, perfil.user

    # Fallback: buscar por tutores M2M o FK legacy
    perfil = PerfilPaciente.objects.filter(
        models.Q(tutores=request.user) | models.Q(tutor=request.user)
    ).first()
    if perfil:
        if perfil.tutor == request.user and not perfil.tutores.filter(pk=request.user.pk).exists():
            perfil.tutores.add(request.user)
        request.session["paciente_seleccionado"] = perfil.user.id
        return perfil, perfil.user

    return None, None


# ========== 1. AUTENTICACIÓN Y REGISTRO ==========

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            rol = form.cleaned_data.get('rol')
            if rol == 'paciente':
                PerfilPaciente.objects.create(user=user)
            # Nota: Si es tutor, el helper es_tutor se encargará de crearle el perfil en su primer acceso
            messages.success(request, '🎉 Registro exitoso. Ya podés iniciar sesión.')
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'registration/registro.html', {'form': form})


# ========== 2. DASHBOARD PANEL VITAL ==========

@login_required
def dashboard(request):
    perfil, target_user = obtener_paciente_activo(request)

    # Obtenemos las notificaciones no leídas del usuario (sea tutor o paciente)
    notificaciones = Notificacion.objects.filter(usuario=request.user, leida=False)
    
    # Lista de pacientes para el selector del tutor
    pacientes_list = []
    if es_tutor(request.user):
        from django.db.models import Q
        pacientes_list = PerfilPaciente.objects.filter(
            Q(tutores=request.user) | Q(tutor=request.user)
        ).select_related('user').distinct()

    # Si el tutor no tiene pacientes asociados todavía
    if not target_user:
        context = {
            'paciente': None,
            'pacientes_list': pacientes_list,
            'tutor_sin_pacientes': True,
            'notificaciones_pendientes': notificaciones,
            'cantidad_notificaciones': notificaciones.count()
        }
        return render(request, 'core/dashboard.html', context)

    # Consultas optimizadas con select_related
    remedios = Medicamento.objects.filter(paciente=target_user, activo=True).select_related('paciente')

    # Calcular stock bajo en una sola iteración y evitar duplicar lógica
    remedios_stock_bajo = []
    for med in remedios:
        if med.stock_actual <= med.umbral_stock_minimo:
            remedios_stock_bajo.append(med)

    # Eventos de agenda médica de los próximos 7 días
    hoy = timezone.now()
    proximos_eventos = EventoCalendario.objects.filter(
        paciente=target_user, 
        fecha_hora__gte=hoy
    ).order_by('fecha_hora')[:3]

    # Gráfico de evolución semanal
    hace_una_semana = hoy - timezone.timedelta(days=7)
    mediciones_recientes = DatoMedicion.objects.filter(
        paciente=target_user,
        fecha_registro__gte=hace_una_semana
    ).order_by('fecha_registro')

    datos_grafico = {
        'presion': {'labels': [], 'valores_1': [], 'valores_2': []},
        'peso':    {'labels': [], 'valores_1': []},
        'glucosa': {'labels': [], 'valores_1': []}
    }
    
    for m in mediciones_recientes:
        fecha_str = m.fecha_registro.strftime('%d/%m %H:%M')
        if m.tipo in datos_grafico:
            datos_grafico[m.tipo]['labels'].append(fecha_str)
            datos_grafico[m.tipo]['valores_1'].append(m.valor_1)
            if m.tipo == 'presion':
                datos_grafico[m.tipo]['valores_2'].append(m.valor_2)

    # Controles médicos requeridos del paciente (como lista para los templates)
    controles_permitidos = []
    ultima_medicion = None
    docs_pendientes = 0
    eventos_esta_semana = []

    if perfil:
        if perfil.requiere_control_presion: controles_permitidos.append('presion')
        if perfil.requiere_control_glucosa: controles_permitidos.append('glucosa')
        if perfil.requiere_control_peso:    controles_permitidos.append('peso')
        ultima_medicion = DatoMedicion.objects.filter(
            paciente=target_user
        ).order_by('-fecha_registro').first()
        docs_pendientes = FotoDocumento.objects.filter(
            paciente=target_user, procesada=False
        ).count()
        fin_semana = hoy + timezone.timedelta(days=7)
        eventos_esta_semana = EventoCalendario.objects.filter(
            paciente=target_user,
            fecha_hora__gte=hoy,
            fecha_hora__lte=fin_semana
        ).order_by('fecha_hora')

    context = {
        'perfil':              perfil,
        'paciente':     target_user,
        'remedios':            remedios,
        'remedios_stock_bajo': remedios_stock_bajo,
        'proximos_eventos':    proximos_eventos,
        'eventos_proximos':    proximos_eventos,
        'eventos_esta_semana': eventos_esta_semana,
        'docs_pendientes':     docs_pendientes,
        'ultima_medicion':     ultima_medicion,
        'controles_permitidos': controles_permitidos,
        'controles_permitidos_json': json.dumps(controles_permitidos),
        'pacientes_list':      pacientes_list,
        'datos_grafico_json':  json.dumps(datos_grafico),
        'tutor_sin_pacientes': False,
        'notificaciones_pendientes': notificaciones,
        'cantidad_notificaciones': notificaciones.count()
    }
    return render(request, 'core/dashboard.html', context)


# ========== 3. GESTIÓN DE MEDICAMENTOS ==========
@login_required
def nuevo_medicamento(request):
    perfil, target_user = obtener_paciente_activo(request)
    
    if request.method == 'POST':
        form = MedicamentoForm(request.POST)
        
        if form.is_valid():
            medicamento = form.save(commit=False)
            medicamento.paciente = target_user
            medicamento.activo = True 
            
            if medicamento.dosis_por_toma > medicamento.stock_actual or medicamento.dosis_por_toma > medicamento.stock_total:
                messages.error(request, "❌ Error: La dosis no puede ser mayor que las unidades del stock.")
                return render(request, 'core/nuevo_medicamento.html', {'form': form})
                
            # 💡 SINCRONIZACIÓN 1: Capturamos los horarios del POST
            horarios_lista = []
            i = 0
            while True:
                h_str = request.POST.get(f'horario_{i}', '').strip()
                if h_str:
                    horarios_lista.append(h_str)
                    i += 1
                else:
                    break
            
            # Guardamos el string para que tasks.py y los templates viejos no rompan
            medicamento.horario_fijo = ", ".join(horarios_lista)
            medicamento.save()

            # Guardamos las relaciones en la nueva tabla para la API
            if medicamento.frecuencia_tipo == 'fijo':
                for h in horarios_lista:
                    HorarioToma.objects.create(medicamento=medicamento, hora=h)

            messages.success(request, f"💊 {medicamento.nombre} guardado con éxito en el plan.")
            return redirect('dashboard')
        else:
            messages.error(request, "❌ Revisá los datos. Hay errores en el formulario.")
    else:
        form = MedicamentoForm()

    return render(request, 'core/nuevo_medicamento.html', {'form': form})


@login_required
def editar_medicamento(request, pk):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')

    perfil, target_user = obtener_paciente_activo(request)
    medicamento = get_object_or_404(Medicamento, pk=pk, paciente=target_user)

    if request.method == 'POST':
        form = MedicamentoForm(request.POST, instance=medicamento)
        if form.is_valid():
            medicamento = form.save(commit=False)
            
            # 💡 SINCRONIZACIÓN 2: Recolectamos los horarios modificados
            horarios_lista = []
            i = 0
            while True:
                h = request.POST.get(f'horario_{i}', '').strip()
                if h:
                    horarios_lista.append(h)
                    i += 1
                else:
                    break
            
            # Actualizamos el string plano
            medicamento.horario_fijo = ", ".join(horarios_lista)
            medicamento.save()
            
            # Limpiamos las relaciones viejas y recreamos las nuevas para mantener la DB limpia
            medicamento.horarios.all().delete()
            if medicamento.frecuencia_tipo == 'fijo':
                for h in horarios_lista:
                    HorarioToma.objects.create(medicamento=medicamento, hora=h)

            messages.success(request, '✏️ Medicamento actualizado.')
            return redirect('dashboard')
        else:
            messages.error(request, '❌ Revisá los datos del formulario.')
    else:
        form = MedicamentoForm(instance=medicamento)

    # El formulario lee el string separado por comas para dibujar los inputs en la web
    horarios_list = [h.strip() for h in medicamento.horario_fijo.split(',')] if medicamento.horario_fijo else []
    return render(request, 'core/editar_medicamento.html', {
        'form': form,
        'medicamento': medicamento,
        'horarios_list': horarios_list
    })

@login_required
def registrar_toma(request, medicamento_id):
    if request.method == 'POST':
        if es_tutor(request.user):
            messages.error(request, "❌ Acción denegada: Solo el paciente puede confirmar que tomó su medicación.")
            return redirect('dashboard')

        medicamento = get_object_or_404(Medicamento, id=medicamento_id, paciente=request.user, activo=True)
        ahora = timezone.now()
        
        ultima_toma = RegistroToma.objects.filter(
            medicamento=medicamento,
            paciente=request.user
        ).order_by('-fecha_hora').first()

        if ultima_toma:
            tiempo_transcurrido = ahora - ultima_toma.fecha_hora

            if tiempo_transcurrido < timedelta(minutes=10):
                messages.warning(request, f"¡Tranquilo! Ya se registró una toma de {medicamento.nombre} hace unos instantes.")
                return redirect('dashboard')

            if medicamento.frecuencia_tipo == 'evento':
                hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
                hoy_fin = bioreplace = ahora.replace(hour=23, minute=59, second=59, microsecond=999999)
                ya_tomo_hoy = RegistroToma.objects.filter(
                    medicamento=medicamento,
                    paciente=request.user,
                    fecha_hora__range=(hoy_inicio, hoy_fin)
                ).exists()
                if ya_tomo_hoy:
                    messages.warning(request, f"Ya registraste la toma diaria de {medicamento.nombre} correspondiente a hoy.")
                    return redirect('dashboard')

            elif medicamento.frecuencia_tipo == 'intervalo':
                horas_intervalo = medicamento.cada_cuantas_horas
                proxima_esperada = ultima_toma.fecha_hora + timedelta(hours=horas_intervalo)
                margen_tolerancia = timedelta(hours=1)
                
                if ahora < (proxima_esperada - margen_tolerancia):
                    tiempo_restante = proxima_esperada - ahora
                    horas_falta = tiempo_restante.seconds // 3600
                    minutos_falta = (tiempo_restante.seconds % 3600) // 60
                    messages.warning(
                        request, 
                        f"Es muy temprano para {medicamento.nombre}. Según tu plan de cada {horas_intervalo} horas, "
                        f"deberías tomarlo aprox. en {horas_falta}h y {minutos_falta} min."
                    )
                    return redirect('dashboard')

            elif medicamento.frecuencia_tipo == 'fijo':
                if tiempo_transcurrido < timedelta(hours=4):
                    messages.warning(request, f"Ya registraste la toma de {medicamento.nombre} correspondiente a este turno horario.")
                    return redirect('dashboard')

        if medicamento.stock_actual > 0:
            medicamento.stock_actual = max(0, float(medicamento.stock_actual) - float(medicamento.dosis_por_toma))
            medicamento.save()

            RegistroToma.objects.create(
                medicamento=medicamento,
                paciente=request.user,
                fecha_hora=ahora,
                cantidad_tomada=medicamento.dosis_por_toma 
            )

            if hasattr(request.user, 'perfil_medico'):
                tutores = request.user.perfil_medico.tutores.all()
                nombre_paciente = request.user.get_full_name() or request.user.username
                for tutor in tutores:
                    Notificacion.objects.create(
                        usuario=tutor,
                        tipo='medicacion',
                        titulo=f"💊 Toma registrada: {nombre_paciente}",
                        mensaje=f"El paciente confirmó la toma de {medicamento.nombre}.",
                        fecha_creacion=ahora
                    )

            messages.success(request, f"✅ Toma de {medicamento.nombre} registrada correctamente.")
        else:
            messages.error(request, f"❌ No hay stock suficiente de {medicamento.nombre}.")

    return redirect('dashboard')

@login_required
def reponer_medicamento(request, medicamento_id):
    med = get_object_or_404(Medicamento, id=medicamento_id, paciente__perfil_medico__tutores=request.user)
    
    if request.method == 'POST':
        med.stock_actual += med.stock_total
        med.save()
        messages.success(request, f"¡Se sumó una caja de {med.stock_total} {med.unidad_medida} a {med.nombre}!")
        
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def eliminar_medicamento(request, pk):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')

    perfil, target_user = obtener_paciente_activo(request)
    med = get_object_or_404(Medicamento, pk=pk, paciente=target_user)
    med.activo = False
    med.save()
    messages.success(request, '🗑️ Medicamento archivado del sistema.')
    return redirect('dashboard')

@login_required
def historial_tomas(request):
    perfil, target_user = obtener_paciente_activo(request)
    med_id = request.GET.get('med')
    med_nombre = None

    if es_tutor(request.user):
        tomas_query = RegistroToma.objects.filter(paciente__perfil_medico__tutores=request.user).select_related('medicamento', 'paciente')
    else:
        tomas_query = RegistroToma.objects.filter(paciente=request.user).select_related('medicamento', 'paciente')

    if med_id:
        tomas_query = tomas_query.filter(medicamento_id=med_id)
        m = Medicamento.objects.filter(pk=med_id).first()
        if m: med_nombre = m.nombre

    paginator = Paginator(tomas_query.order_by('-fecha_hora'), 15)
    page_number = request.GET.get('page')
    tomas_paginadas = paginator.get_page(page_number)

    return render(request, 'core/historial_tomas.html', {'tomas': tomas_paginadas, 'medicamento_nombre': med_nombre})


# ========== 4. AGENDA / CALENDARIO ==========

@login_required
def calendario_eventos(request):
    perfil, target_user = obtener_paciente_activo(request)
    if not target_user:
        return render(request, 'core/calendario.html', {'eventos_json': '[]', 'paciente': "Sin Paciente"})

    eventos = EventoCalendario.objects.filter(paciente=target_user)
    
    eventos_data = []
    for ev in eventos:
        # 💡 CONVERSIÓN EN GET: Llevamos la fecha a hora local antes de enviarla a FullCalendar
        fecha_local = timezone.localtime(ev.fecha_hora) if ev.fecha_hora else None
        
        eventos_data.append({
            'id': ev.id,
            'title': ev.titulo,
            'start': fecha_local.isoformat() if fecha_local else "",
            'lugar': ev.lugar,
            'tipo': ev.tipo,
            'className': f'evento-tipo-{ev.tipo}'
        })

    return render(request, 'core/calendario.html', {
        'eventos_json': json.dumps(eventos_data),
        'paciente': target_user,
        'usuario_es_tutor': es_tutor(request.user)  # ✏️ CORRECCIÓN: Habilita el botón "+" en el HTML
    })

@login_required
def nuevo_evento(request):
    if not validar_acceso_tutor(request):
        return redirect('calendario')

    perfil, target_user = obtener_paciente_activo(request)
    if not target_user:
        return redirect('calendario')

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        tipo = request.POST.get('tipo')
        lugar = request.POST.get('lugar')
        descripcion = request.POST.get('descripcion')
        
        fecha_hora_str = request.POST.get('fecha_hora')
        fecha_hora_aware = None
        if fecha_hora_str:
            dt = parse_datetime(fecha_hora_str)
            if dt and timezone.is_naive(dt):
                fecha_hora_aware = timezone.make_aware(dt)
            else:
                fecha_hora_aware = dt

        # ✏️ CORREGIDO: Ahora pasamos 'fecha_hora_aware' correctamente
        EventoCalendario.objects.create(
            paciente=target_user,
            titulo=titulo,
            tipo=tipo,
            fecha_hora=fecha_hora_aware, 
            lugar=lugar,
            descripcion=descripcion
        )
        messages.success(request, '📅 Evento agendado correctamente.')
        return redirect('calendario')

    return render(request, 'core/nuevo_evento.html', {'paciente': target_user})

@login_required
def editar_evento(request, pk):
    if not validar_acceso_tutor(request):
        return redirect('calendario')

    perfil, target_user = obtener_paciente_activo(request)
    evento = get_object_or_404(EventoCalendario, pk=pk, paciente=target_user)

    if request.method == 'POST':
        evento.titulo = request.POST.get('titulo')
        evento.tipo = request.POST.get('tipo')
        evento.lugar = request.POST.get('lugar')
        evento.descripcion = request.POST.get('descripcion')
        
        # 💡 PARSEO SEGURO (POST): Evita que se sumen 3 horas extras en cada edición
        fecha_hora_str = request.POST.get('fecha_hora')
        if fecha_hora_str:
            dt = parse_datetime(fecha_hora_str)
            if dt and timezone.is_naive(dt):
                evento.fecha_hora = timezone.make_aware(dt)
            else:
                evento.fecha_hora = dt
                
        evento.save()
        messages.success(request, '✏️ Evento modificado.')
        return redirect('calendario')

    # 💡 LECTURA LOCAL (GET): Traducimos el UTC de la base de datos a hora de Argentina para el input HTML
    fecha_local = timezone.localtime(evento.fecha_hora) if evento.fecha_hora else None
    fecha_iso = fecha_local.strftime('%Y-%m-%dT%H:%M') if fecha_local else ""
    
    return render(request, 'core/editar_evento.html', {
        'evento': evento, 
        'fecha_iso': fecha_iso,
        'usuario_es_tutor': es_tutor(request.user)
    })

@login_required
def eliminar_evento(request, pk):
    if not validar_acceso_tutor(request):
        return redirect('calendario')

    perfil, target_user = obtener_paciente_activo(request)
    evento = get_object_or_404(EventoCalendario, pk=pk, paciente=target_user)
    evento.delete()
    messages.success(request, '🗑️ Evento cancelado del calendario.')
    return redirect('calendario')


# ========== 5. ACCIONES DE VINCULACIÓN ==========

@login_required
def vincular_paciente(request):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username_paciente')
        user_paciente = User.objects.filter(username=username).first()

        if not user_paciente:
            messages.error(request, '❌ El nombre de usuario ingresado no existe.')
        else:
            perfil_medico = PerfilPaciente.objects.filter(user=user_paciente).first()
            if not perfil_medico:
                messages.error(request, '❌ El usuario seleccionado no está registrado con perfil de paciente.')
            elif perfil_medico.tutores.filter(pk=request.user.pk).exists():
                messages.warning(request, f'⚠️ Ya estás vinculado a {user_paciente.first_name or user_paciente.username}.')
            else:
                perfil_medico.tutores.add(request.user)
                if not perfil_medico.tutor:
                    perfil_medico.tutor = request.user
                    perfil_medico.save()
                request.session["paciente_seleccionado"] = user_paciente.id
                messages.success(request, f'✅ Vinculaste con éxito a {user_paciente.first_name or user_paciente.username}.')
                return redirect('dashboard')

    return render(request, 'core/vincular.html')

@login_required
def seleccionar_paciente(request, paciente_id):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')

    es_valido = PerfilPaciente.objects.filter(user_id=paciente_id, tutores=request.user).exists()
    if es_valido:
        request.session["paciente_seleccionado"] = paciente_id
        messages.success(request, "🔄 Cambiaste el entorno de visualización del paciente.")
    else:
        messages.error(request, "❌ No tenés permisos sobre este perfil.")
        
    return redirect('dashboard')


# ========== 6. PERFILES DE USUARIOS ==========

@login_required
def perfil_tutor(request):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')
    pacientes = PerfilPaciente.objects.filter(tutores=request.user).select_related('user')
    perfil_tutor, created = PerfilTutor.objects.get_or_create(user=request.user)
    return render(request, 'core/perfil_tutor.html', {'pacientes': pacientes, 'perfil_tutor': perfil_tutor})

@login_required
def perfil_paciente(request):
    perfil, target_user = obtener_paciente_activo(request)
    return render(request, 'core/perfil_paciente.html', {'perfil': perfil, 'paciente': target_user})

@login_required
def editar_perfil(request, paciente_id):
    if es_tutor(request.user):
        perfil = get_object_or_404(PerfilPaciente, user_id=paciente_id, tutores=request.user)
    else:
        if request.user.id != paciente_id:
            messages.error(request, "❌ No podés editar perfiles ajenos.")
            return redirect('dashboard')
        perfil = get_object_or_404(PerfilPaciente, user=request.user)

    tutores = perfil.tutores.all()

    if request.method == 'POST':
        form = PerfilPacienteForm(request.POST, instance=perfil)
        if form.is_valid():
            perfil_actualizado = form.save(commit=False)
            
            contacto_seleccionado = request.POST.get('contacto_emergencia')
            if contacto_seleccionado == 'otro':
                perfil_actualizado.contacto_emergencia = request.POST.get('contacto_emergencia_manual', '')
            elif contacto_seleccionado:
                perfil_actualizado.contacto_emergencia = contacto_seleccionado

            # 🆘 Contacto de emergencia "real" (FK), el que usa la app para el botón de llamada.
            # Se setea con un <select name="tutor_emergencia_id"> que liste los tutores vinculados.
            tutor_emergencia_id = request.POST.get('tutor_emergencia_id')
            if tutor_emergencia_id:
                if tutores.filter(id=tutor_emergencia_id).exists():
                    perfil_actualizado.tutor_emergencia_id = tutor_emergencia_id
            else:
                perfil_actualizado.tutor_emergencia = None

            perfil_actualizado.save()
            messages.success(request, '💾 Cambios del perfil guardados con éxito.')
            return redirect('perfil_paciente')
    else:
        form = PerfilPacienteForm(instance=perfil)
        
    return render(request, 'core/editar_perfil.html', {
        'form': form, 
        'perfil': perfil, 
        'paciente': perfil.user,
        'tutores': tutores 
    })


# ========== 7. MEDICIONES, FOTOS Y DOCUMENTOS ==========

@login_required
def mediciones(request):
    perfil, target_user = obtener_paciente_activo(request)
    if not target_user:
        return redirect('dashboard')

    meds = DatoMedicion.objects.filter(paciente=target_user)
    context = {
        'perfil': perfil,
        'mediciones_presion': meds.filter(tipo='presion')[:10],
        'mediciones_peso': meds.filter(tipo='peso')[:10],
        'mediciones_glucosa': meds.filter(tipo='glucosa')[:10],
    }
    return render(request, 'core/mediciones.html', context)

@login_required
def fotos_mediciones(request):
    perfil, target_user = obtener_paciente_activo(request)
    if not target_user:
        return redirect('dashboard')

    tipo_filtro = request.GET.get('tipo', '')
    documentos = FotoDocumento.objects.filter(paciente=target_user).order_by('-fecha_subida')

    if tipo_filtro:
        documentos = documentos.filter(tipo=tipo_filtro)

    controles_permitidos = []
    if perfil:
        if perfil.requiere_control_presion: controles_permitidos.append('presion')
        if perfil.requiere_control_glucosa: controles_permitidos.append('glucosa')
        if perfil.requiere_control_peso:    controles_permitidos.append('peso')

    fotos_pendientes  = documentos.filter(procesada=False)
    fotos_procesadas  = documentos.filter(procesada=True)[:20]

    return render(request, 'core/fotos_mediciones.html', {
        'fotos_pendientes':     fotos_pendientes,
        'fotos_procesadas':     fotos_procesadas,
        'tipo_filtro':          tipo_filtro,
        'controles_permitidos': controles_permitidos,
        'perfil':               perfil,
        'usuario_es_tutor':     es_tutor(request.user),
        'paciente': target_user,
    })

@login_required
def subir_foto(request):
    perfil, target_user = obtener_paciente_activo(request)
    
    if request.method == 'POST':
        form = SubirFotoForm(request.POST, request.FILES)
        if form.is_valid():
            tipo = form.cleaned_data.get('tipo')
            
            if tipo == 'medicion':
                if not (perfil.requiere_control_presion or 
                        perfil.requiere_control_glucosa or 
                        perfil.requiere_control_peso):
                    messages.error(request, "⚠️ No tienes controles de mediciones habilitados en tu perfil.")
                    return redirect('subir_foto')
            
            foto = form.save(commit=False)
            foto.paciente = target_user
            foto.save()
            messages.success(request, '📤 Documento subido. Tu tutor ya puede revisarlo.')
            return redirect('fotos_mediciones')
    else:
        form = SubirFotoForm()
        
    return render(request, 'core/subir_foto.html', {'form': form, 'perfil': perfil})

@login_required
def cargar_dato_medicion(request, foto_id):
    foto = get_object_or_404(FotoDocumento, id=foto_id)
    perfil = PerfilPaciente.objects.filter(user=foto.paciente).first()
    
    # 🛡️ BLINDAJE DE SEGURIDAD INTERMEDIO (IDOR): Reemplaza el bloqueo anterior
    if es_tutor(request.user):
        # Si es tutor, validamos que pertenezca a la red de tutores de este paciente específico
        if not perfil or not perfil.tutores.filter(pk=request.user.pk).exists():
            messages.error(request, "❌ No tienes permisos sobre el perfil de este paciente.")
            return redirect('fotos_mediciones')
    else:
        # Si es paciente, validamos que la foto que intenta procesar sea estrictamente suya
        if foto.paciente != request.user:
            messages.error(request, "❌ No tienes acceso a este documento.")
            return redirect('fotos_mediciones')

    # Conseguir los controles permitidos del perfil del paciente
    controles_permitidos = []
    if perfil:
        if perfil.requiere_control_presion: controles_permitidos.append('presion')
        if perfil.requiere_control_glucosa: controles_permitidos.append('glucosa')
        if perfil.requiere_control_peso:    controles_permitidos.append('peso')

    medicion_existente = DatoMedicion.objects.filter(foto=foto).first()

    if foto.procesada and not medicion_existente:
        messages.error(request, "⚠️ Este documento ya ha sido procesado.")
        return redirect('fotos_mediciones')

    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        
        if tipo not in controles_permitidos:
            messages.error(request, "⚠️ Esta medición no está habilitada para el perfil del paciente.")
            return redirect('fotos_mediciones')

        val1 = 0.0
        val2 = None

        try:
            if tipo == 'presion':
                val1 = float(request.POST.get('presion_sistolica', 0))
                val2 = float(request.POST.get('presion_diastolica', 0))
                if val1 <= 0 or val2 <= 0:
                    messages.error(request, "❌ Error: Los valores de presión arterial deben ser mayores a cero.")
                    return redirect('cargar_dato', foto_id=foto.id)
            elif tipo == 'peso':
                val1 = float(request.POST.get('peso', 0))
                if val1 <= 0:
                    messages.error(request, "❌ Error: El peso registrado debe ser mayor a cero.")
                    return redirect('cargar_dato', foto_id=foto.id)
            elif tipo == 'glucosa':
                val1 = float(request.POST.get('glucosa', 0))
                if val1 <= 0:
                    messages.error(request, "❌ Error: El nivel de glucosa debe ser mayor a cero.")
                    return redirect('cargar_dato', foto_id=foto.id)
        except ValueError:
            messages.error(request, "❌ Error: Formato numérico incorrecto en la medición.")
            return redirect('cargar_dato', foto_id=foto.id)

        if medicion_existente:
            medicion = medicion_existente
        else:
            medicion = DatoMedicion(paciente=foto.paciente, foto=foto)

        medicion.tipo = tipo
        medicion.valor_1 = val1
        medicion.valor_2 = val2 if tipo == 'presion' else None 
        medicion.observaciones = request.POST.get('observaciones', '')
        medicion.save()

        foto.procesada = True
        foto.save()

        messages.success(request, "📊 Datos médicos guardados correctamente.")
        return redirect('fotos_mediciones')

    context = {
        'foto': foto,
        'perfil': perfil,
        'controles_permitidos': controles_permitidos,
        'medicion': medicion_existente,
    }
    return render(request, 'core/cargar_dato.html', context)

@login_required
def procesar_documento(request, foto_id):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')
    foto = get_object_or_404(FotoDocumento, pk=foto_id)
    perfil = PerfilPaciente.objects.filter(user=foto.paciente).first()
    
    if not perfil or not perfil.tutores.filter(pk=request.user.pk).exists():
        messages.error(request, '❌ No tenés permisos sobre este documento.')
        return redirect('fotos_mediciones')
        
    foto.procesada = True
    foto.nota_tutor = 'Revisado por el tutor'
    foto.save()
    messages.success(request, '✅ Documento marcado como revisado.')
    return redirect('fotos_mediciones')

@login_required
def rechazar_documento(request, foto_id):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')
    foto = get_object_or_404(FotoDocumento, pk=foto_id)
    perfil = PerfilPaciente.objects.filter(user=foto.paciente).first()
    
    if not perfil or not perfil.tutores.filter(pk=request.user.pk).exists():
        messages.error(request, '❌ No tenés permisos sobre este documento.')
        return redirect('fotos_mediciones')
        
    foto.delete()
    messages.success(request, '✅ Documento eliminado.')
    return redirect('fotos_mediciones')

@login_required
def marcar_notif_leidas(request):
    if request.method == 'POST':
        Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
        return JsonResponse({'status': 'ok'})
    return redirect('dashboard')

@login_required
def editar_medicion(request, pk):
    medicion = get_object_or_404(DatoMedicion, pk=pk)
    if medicion.paciente != request.user and not es_tutor(request.user):
        messages.error(request, "❌ No tenés permiso.")
        return redirect('dashboard')

    if request.method == 'POST':
        medicion.valor_1 = float(request.POST.get('valor_1', medicion.valor_1))
        if medicion.tipo == 'presion':
            medicion.valor_2 = float(request.POST.get('valor_2', medicion.valor_2))
        medicion.observaciones = request.POST.get('observaciones', medicion.observaciones)
        medicion.save()
        messages.success(request, '✅ Medición actualizada correctamente.')
        return redirect('mediciones')
    
    return render(request, 'core/editar_medicion.html', {'medicion': medicion})

@login_required
def eliminar_foto(request, foto_id):
    foto = get_object_or_404(FotoDocumento, id=foto_id)
    
    if foto.paciente != request.user and not es_tutor(request.user):
        messages.error(request, "❌ No tenés permisos.")
        return redirect('fotos_mediciones')
    
    if hasattr(foto, 'datomedicion'):
        foto.datomedicion.delete()
    
    foto.delete()
    messages.success(request, '🗑️ Documento y medición eliminados.')
    return redirect('fotos_mediciones')

@login_required
def eliminar_medicion(request, pk):
    medicion = get_object_or_404(DatoMedicion, pk=pk)
    
    if medicion.paciente != request.user and not es_tutor(request.user):
        messages.error(request, "❌ No tenés permiso.")
        return redirect('dashboard')
    
    foto_a_borrar = medicion.foto
    medicion.delete()
    
    if foto_a_borrar:
        foto_a_borrar.delete() 
        
    messages.success(request, '🗑️ Medición y su foto asociada eliminadas correctamente.')
    return redirect('mediciones')


# ========== 8. NUEVA VISTA PERFIL TUTOR ==========

@login_required
def editar_perfil_tutor(request):
    if not es_tutor(request.user):
        return redirect('dashboard')

    perfil, created = PerfilTutor.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = PerfilTutorForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, '💾 Perfil actualizado correctamente.')
            return redirect('dashboard')
    else:
        form = PerfilTutorForm(instance=perfil)
        
    return render(request, 'core/editar_tutor.html', {'form': form})