import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Medicamento, EventoCalendario, PerfilPaciente, FotoDocumento, DatoMedicion, RegistroToma
from .forms import RegistroForm, MedicamentoForm, PerfilPacienteForm, SubirFotoForm


# ========== HELPERS REFACTORIZADOS ==========

def es_tutor(user):
    """Un usuario es tutor si está autenticado y NO tiene un PerfilPaciente propio."""
    if not user.is_authenticated:
        return False
    return not PerfilPaciente.objects.filter(user=user).exists()

def es_paciente(user):
    return PerfilPaciente.objects.filter(user=user).exists()

def validar_acceso_tutor(request):
    """
    Verifica si el usuario es un tutor válido. 
    Devuelve True si el acceso es válido, False si debe ser denegado.
    """
    if not es_tutor(request.user):
        messages.error(request, "❌ Solo los tutores pueden realizar esta acción.")
        return False
    return True

def obtener_paciente_activo(request):
    """
    Devuelve (perfil, paciente_user) según el rol.
    - Paciente: su propio perfil.
    - Tutor: paciente seleccionado en sesión (valida que le pertenezca).
    """
    perfil_propio = PerfilPaciente.objects.filter(user=request.user).first()
    if perfil_propio:
        return perfil_propio, request.user

    paciente_id_sesion = request.session.get("paciente_seleccionado")
    if paciente_id_sesion:
        # Validación de seguridad: el paciente en sesión debe ser asignado a este tutor
        perfil = PerfilPaciente.objects.filter(user_id=paciente_id_sesion, tutor=request.user).first()
        if perfil:
            return perfil, perfil.user

    # Fallback: tomar el primero disponible si no hay sesión configurada
    perfil = PerfilPaciente.objects.filter(tutor=request.user).first()
    if perfil:
        request.session["paciente_seleccionado"] = perfil.user.id
        return perfil, perfil.user

    return None, None


# ========== 1. AUTENTICACIÓN Y REGISTRO ==========

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_validate():
            user = form.save()
            rol = form.cleaned_data.get('rol')
            if rol == 'paciente':
                PerfilPaciente.objects.create(user=user)
            messages.success(request, '🎉 Registro exitoso. Ya podés iniciar sesión.')
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'registration/registro.html', {'form': form})


# ========== 2. DASHBOARD PANEL VITAL ==========

@login_required
def dashboard(request):
    perfil, target_user = obtener_paciente_activo(request)
    
    # Lista de pacientes para el selector del tutor
    pacientes_list = []
    if es_tutor(request.user):
        pacientes_list = PerfilPaciente.objects.filter(tutor=request.user).select_related('user')

    # Si el tutor no tiene pacientes asociados todavía
    if not target_user:
        context = {
            'nombre_paciente': "Sin Pacientes",
            'pacientes_list': pacientes_list,
            'tutor_sin_pacientes': True
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

    datos_grafico = []
    for m in mediciones_recientes:
        datos_grafico.append({
            'tipo': m.tipo,
            'fecha': m.fecha_registro.strftime('%d/%m %H:%M'),
            'valor_1': m.valor_1,
            'valor_2': m.valor_2
        })

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
        'nombre_paciente':     target_user.first_name or target_user.username,
        'remedios':            remedios,
        'remedios_stock_bajo': remedios_stock_bajo,
        'proximos_eventos':    proximos_eventos,
        'eventos_proximos':    proximos_eventos,
        'eventos_esta_semana': eventos_esta_semana,
        'docs_pendientes':     docs_pendientes,
        'ultima_medicion':     ultima_medicion,
        'controles_permitidos': controles_permitidos,
        'pacientes_list':      pacientes_list,
        'datos_grafico_json':  json.dumps(datos_grafico),
        'tutor_sin_pacientes': False
    }
    return render(request, 'core/dashboard.html', context)


# ========== 3. GESTIÓN DE MEDICAMENTOS ==========

@login_required
def nuevo_medicamento(request):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')

    perfil, target_user = obtener_paciente_activo(request)
    if not target_user:
        messages.error(request, "❌ Debés vincular un paciente antes de agregar medicamentos.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = MedicamentoForm(request.POST)
        if form.is_valid():
            medicamento = form.save(commit=False)
            medicamento.paciente = target_user
            
            # Procesar el campo oculto de horarios dinámicos en formato JSON
            horarios_raw = request.POST.get('horarios_reales', '[]')
            try:
                lista_horarios = json.loads(horarios_raw)
                medicamento.horarios = ", ".join(lista_horarios)
            except json.JSONDecodeError:
                medicamento.horarios = ""

            medicamento.save()
            messages.success(request, f'✅ Medicamento "{medicamento.nombre}" cargado correctamente.')
            return redirect('dashboard')
    else:
        form = MedicamentoForm()
    
    return render(request, 'core/nuevo_medicamento.html', {'form': form, 'nombre_paciente': target_user.first_name})

@login_required
def editar_medicamento(request, pk):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')

    perfil, target_user = obtener_paciente_activo(request)
    # Seguridad: Validar que el medicamento pertenezca al paciente activo del tutor
    medicamento = get_object_or_404(Medicamento, pk=pk, paciente=target_user)

    if request.method == 'POST':
        form = MedicamentoForm(request.POST, instance=medicamento)
        if form.is_valid():
            med = form.save(commit=False)
            horarios_raw = request.POST.get('horarios_reales', '[]')
            try:
                lista_horarios = json.loads(horarios_raw)
                med.horarios = ", ".join(lista_horarios)
            except json.JSONDecodeError:
                pass
            med.save()
            messages.success(request, '✏️ Medicamento actualizado.')
            return redirect('dashboard')
    else:
        form = MedicamentoForm(instance=medicamento)

    # Parsear horarios existentes para mandarlos al front-end
    horarios_list = [h.strip() for h in medicamento.horarios.split(',')] if medicamento.horarios else []
    return render(request, 'core/editar_medicamento.html', {'form': form, 'medicamento': medicamento, 'horarios_list': horarios_list})

@login_required
def registrar_toma(request, medicamento_id):
    perfil, target_user = obtener_paciente_activo(request)
    # Seguridad: El medicamento debe pertenecer al paciente actual
    med = get_object_or_404(Medicamento, pk=medicamento_id, paciente=target_user, activo=True)

    if med.stock_actual >= med.dosis_por_toma:
        med.stock_actual = max(0.0, float(med.stock_actual) - float(med.dosis_por_toma))
        med.save()

        RegistroToma.objects.create(
            medicamento=med,
            paciente=target_user,
            cantidad_tomada=med.dosis_por_toma
        )
        messages.success(request, f'💊 Toma registrada para {med.nombre}. Stock reducido.')
    else:
        messages.error(request, f'⚠️ Stock insuficiente para {med.nombre}. ¡Por favor reponer!')

    return redirect('dashboard')

@login_required
def reponer_medicamento(request, medicamento_id):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')

    perfil, target_user = obtener_paciente_activo(request)
    med = get_object_or_404(Medicamento, pk=medicamento_id, paciente=target_user)
    
    # Corrección del bug: Resetea el stock al valor del empaque/caja nueva (stock_total)
    med.stock_actual = med.stock_total
    med.save()
    
    messages.success(request, f'📦 Caja nueva registrada para {med.nombre}. Stock reestablecido a {med.stock_total}.')
    return redirect('dashboard')

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
    
    # Filtro específico por ID de remedio opcional
    med_id = request.GET.get('medicamento')
    med_nombre = None

    if es_tutor(request.user):
        # Query optimizada directa mediante Filtro relacional
        tomas_query = RegistroToma.objects.filter(paciente__perfil_medico__tutor=request.user).select_related('medicamento', 'paciente')
    else:
        tomas_query = RegistroToma.objects.filter(paciente=request.user).select_related('medicamento', 'paciente')

    if med_id:
        tomas_query = tomas_query.filter(medicamento_id=med_id)
        m = Medicamento.objects.filter(pk=med_id).first()
        if m: med_nombre = m.nombre

    # Implementación de Paginación para prevenir tablas gigantes
    paginator = Paginator(tomas_query.order_by('-fecha_hora'), 15) # 15 tomas por página
    page_number = request.GET.get('page')
    tomas_paginadas = paginator.get_page(page_number)

    return render(request, 'core/historial_tomas.html', {'tomas': tomas_paginadas, 'medicamento_nombre': med_nombre})


# ========== 4. AGENDA / CALENDARIO ==========

@login_required
def calendario_eventos(request):
    perfil, target_user = obtener_paciente_activo(request)
    if not target_user:
        return render(request, 'core/calendario.html', {'eventos_json': '[]', 'nombre_paciente': "Sin Paciente"})

    eventos = EventoCalendario.objects.filter(paciente=target_user)
    
    eventos_data = []
    for ev in eventos:
        eventos_data.append({
            'id': ev.id,
            'title': ev.titulo,
            'start': ev.fecha_hora.isoformat(),
            'lugar': ev.lugar,
            'tipo': ev.tipo,
            'className': f'evento-tipo-{ev.tipo}'
        })

    return render(request, 'core/calendario.html', {
        'eventos_json': json.dumps(eventos_data),
        'nombre_paciente': target_user.first_name or target_user.username
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
        fecha_hora = request.POST.get('fecha_hora')
        lugar = request.POST.get('lugar')
        descripcion = request.POST.get('descripcion')

        EventoCalendario.objects.create(
            paciente=target_user,
            titulo=titulo,
            tipo=tipo,
            fecha_hora=fecha_hora,
            lugar=lugar,
            descripcion=descripcion
        )
        messages.success(request, '📅 Evento agendado correctamente.')
        return redirect('calendario')

    return render(request, 'core/nuevo_evento.html', {'nombre_paciente': target_user.first_name})

@login_required
def editar_evento(request, pk):
    if not validar_acceso_tutor(request):
        return redirect('calendario')

    perfil, target_user = obtener_paciente_activo(request)
    # Seguridad: El evento debe pertenecer al paciente del tutor actual
    evento = get_object_or_404(EventoCalendario, pk=pk, paciente=target_user)

    if request.method == 'POST':
        evento.titulo = request.POST.get('titulo')
        evento.tipo = request.POST.get('tipo')
        evento.fecha_hora = request.POST.get('fecha_hora')
        evento.lugar = request.POST.get('lugar')
        evento.descripcion = request.POST.get('descripcion')
        evento.save()
        messages.success(request, '✏️ Evento modificado.')
        return redirect('calendario')

    # Formatear la fecha para el input datetime-local nativo de HTML
    fecha_iso = evento.fecha_hora.strftime('%Y-%m-%dT%H:%M') if evento.fecha_hora else ""
    return render(request, 'core/editar_evento.html', {'evento': evento, 'fecha_iso': fecha_iso})

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
            elif perfil_medico.tutor is not None:
                messages.error(request, '⚠️ Este paciente ya posee un tutor asignado.')
            else:
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

    # Validar propiedad antes de cambiar de ambiente
    es_valido = PerfilPaciente.objects.filter(user_id=paciente_id, tutor=request.user).exists()
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
    pacientes = PerfilPaciente.objects.filter(tutor=request.user).select_related('user')
    return render(request, 'core/perfil_tutor.html', {'pacientes': pacientes})

@login_required
def perfil_paciente(request):
    perfil, target_user = obtener_paciente_activo(request)
    return render(request, 'core/perfil_paciente.html', {'perfil': perfil, 'paciente': target_user})

@login_required
def editar_perfil(request, paciente_id):
    # Seguridad básica de edición cruzada
    if es_tutor(request.user):
        perfil = get_object_or_404(PerfilPaciente, user_id=paciente_id, tutor=request.user)
    else:
        if request.user.id != paciente_id:
            messages.error(request, "❌ No podés editar perfiles ajenos.")
            return redirect('dashboard')
        perfil = get_object_or_404(PerfilPaciente, user=request.user)

    if request.method == 'POST':
        form = PerfilPacienteForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, '💾 Cambios del perfil guardados con éxito.')
            return redirect('perfil_paciente')
    else:
        form = PerfilPacienteForm(instance=perfil)
    return render(request, 'core/editar_perfil.html', {'form': form, 'perfil': perfil, 'paciente': perfil.user})


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
    })

@login_required
def subir_foto(request):
    perfil, target_user = obtener_paciente_activo(request)
    if request.method == 'POST':
        form = SubirFotoForm(request.POST, request.FILES)
        if form.is_valid():
            foto = form.save(commit=False)
            foto.paciente = request.user
            foto.save()
            messages.success(request, '📤 Documento subido. Tu tutor ya puede revisarlo.')
            return redirect('fotos_mediciones')
    else:
        form = SubirFotoForm()
    return render(request, 'core/subir_foto.html', {'form': form, 'perfil': perfil})

@login_required
def cargar_dato_medicion(request, foto_id):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')

    foto = get_object_or_404(FotoDocumento, pk=foto_id)
    perfil = PerfilPaciente.objects.filter(user=foto.paciente).first()
    
    if not perfil or perfil.tutor != request.user:
        messages.error(request, '❌ No tenés permisos sobre este archivo.')
        return redirect('fotos_mediciones')

    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        observaciones = request.POST.get('observaciones', '')

        v1, v2 = 0.0, None
        if tipo == 'presion':
            v1 = float(request.POST.get('presion_sistolica', 0))
            v2 = float(request.POST.get('presion_diastolica', 0))
        elif tipo == 'peso':
            v1 = float(request.POST.get('peso', 0))
        elif tipo == 'glucosa':
            v1 = float(request.POST.get('glucosa', 0))

        DatoMedicion.objects.create(
            paciente=foto.paciente,
            tipo=tipo,
            valor_1=v1,
            valor_2=v2,
            observaciones=observaciones
        )

        foto.procesada = True
        foto.nota_tutor = f"Medición procesada numéricamente el {timezone.now().strftime('%d/%m')}"
        foto.save()

        messages.success(request, '✅ Medición extraída y guardada en la ficha médica.')
        return redirect('fotos_mediciones')

    return render(request, 'core/cargar_dato.html', {'foto': foto, 'perfil': perfil})

@login_required
def procesar_documento(request, foto_id):
    if not validar_acceso_tutor(request):
        return redirect('dashboard')
    foto = get_object_or_404(FotoDocumento, pk=foto_id)
    perfil = PerfilPaciente.objects.filter(user=foto.paciente).first()
    if not perfil or perfil.tutor != request.user:
        messages.error(request, '❌ No tenés permisos.')
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
    if not perfil or perfil.tutor != request.user:
        messages.error(request, '❌ No tenés permisos.')
        return redirect('fotos_mediciones')
    foto.delete()
    messages.success(request, '✅ Documento eliminado.')
    return redirect('fotos_mediciones')

@login_required
def marcar_notif_leidas(request):
    if request.method == 'POST':
        request.session['notif_ultima_lectura'] = timezone.now().isoformat()
        return render(request, 'core/base.html') # Respuesta dummy exitosa para AJAX