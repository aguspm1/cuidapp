from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from .models import Medicamento, EventoCalendario, PerfilPaciente, FotoDocumento, DatoMedicion
from .forms import RegistroForm, MedicamentoForm

# 1. DASHBOARD PRINCIPAL
@login_required
def dashboard(request):
    remedios = []
    eventos_proximos = []
    nombre_paciente = "Sin vincular"
    pacientes_a_cargo_list = []
    paciente_a_cargo = None
    
    # Buscamos si el usuario actual es tutor de alguien
    pacientes_a_cargo_list = PerfilPaciente.objects.filter(tutor=request.user)
    
    # Obtener el paciente seleccionado desde session o tomar el primero
    paciente_id = request.session.get('paciente_seleccionado')
    
    if paciente_id:
        try:
            paciente_a_cargo = PerfilPaciente.objects.get(id=paciente_id, tutor=request.user)
        except PerfilPaciente.DoesNotExist:
            paciente_a_cargo = pacientes_a_cargo_list.first()
    else:
        paciente_a_cargo = pacientes_a_cargo_list.first()
    
    # Si el usuario es el paciente mismo (acceso directo)
    perfil_propio = PerfilPaciente.objects.filter(user=request.user).first()

    if paciente_a_cargo: # Caso Luis (Tutor)
        target_user = paciente_a_cargo.user
        nombre_paciente = target_user.first_name if target_user.first_name else target_user.username
    elif perfil_propio: # Caso Ana (Paciente)
        target_user = request.user
        nombre_paciente = "Mi Perfil"
    else:
        target_user = None

    if target_user:
        remedios = Medicamento.objects.filter(paciente=target_user)
        for r in remedios:
            # Cálculo de stock basado en el nuevo campo stock_total
            if r.stock_total and r.stock_total > 0:
                r.porcentaje_stock = int((r.stock_actual / r.stock_total) * 100)
            else:
                r.porcentaje_stock = 0
        
        eventos_proximos = EventoCalendario.objects.filter(
            paciente=target_user, 
            fecha_hora__gte=timezone.now()
        ).order_by('fecha_hora')

    return render(request, 'core/dashboard.html', {
        'remedios': remedios, 
        'eventos_proximos': eventos_proximos, 
        'nombre_anciano': nombre_paciente,
        'pacientes_list': pacientes_a_cargo_list,
        'paciente_actual': paciente_a_cargo
    })

# 2. REGISTRO DE USUARIOS 
def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Creamos el perfil de paciente automáticamente al registrarse
            PerfilPaciente.objects.create(user=user)
            messages.success(request, f"¡Cuenta creada como {form.cleaned_data.get('rol')}!")
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'registration/registro.html', {'form': form})

# 3. VINCULACIÓN
@login_required
def vincular_anciano(request):
    if request.method == 'POST':
        user_buscado = request.POST.get('username_anciano')
        try:
            anciano_user = User.objects.get(username=user_buscado)
            perfil = PerfilPaciente.objects.get(user=anciano_user)
            perfil.tutor = request.user
            perfil.save()
            messages.success(request, f"Vinculado con éxito a {user_buscado}")
            return redirect('dashboard')
        except User.DoesNotExist:
            messages.error(request, "No se encontró el usuario")
        except PerfilPaciente.DoesNotExist:
            messages.error(request, "El usuario no tiene un perfil de paciente creado")
    return render(request, 'core/vincular.html')

# 4. EVENTOS Y CALENDARIO
@login_required                                          # FIX: faltaba en la original
def calendario_eventos(request):
    paciente_perfil = PerfilPaciente.objects.filter(tutor=request.user).first()
    target = paciente_perfil.user if paciente_perfil else request.user
 
    nombre = target.get_full_name() or target.username   # FIX: muestra nombre real
 
    return render(request, 'core/calendario.html', {
        'todos_eventos': EventoCalendario.objects.filter(paciente=target).order_by('fecha_hora'),
        'nombre_anciano': nombre,
    })
 
 
@login_required
def nuevo_evento(request):
    paciente_perfil = PerfilPaciente.objects.filter(tutor=request.user).first()
    target = paciente_perfil.user if paciente_perfil else request.user
    nombre = target.get_full_name() or target.username
 
    if request.method == 'POST':
        EventoCalendario.objects.create(
            paciente    = target,
            titulo      = request.POST.get('titulo'),
            fecha_hora  = request.POST.get('fecha_hora'),
            descripcion = request.POST.get('descripcion', ''),
            tipo        = request.POST.get('tipo', 'otro'),   # FIX: se guardaba el tipo
            lugar       = request.POST.get('lugar', ''),      # FIX: se guardaba el lugar
        )
        messages.success(request, "Evento agendado correctamente.")
        return redirect('calendario')                          # FIX: redirige al calendario
 
    return render(request, 'core/nuevo_evento.html', {'nombre_anciano': nombre})
 
 
@login_required
def eliminar_evento(request, pk):
    if request.method == 'POST':
        get_object_or_404(
            EventoCalendario,
            pk=pk,
            paciente__perfilpaciente__tutor=request.user
        ).delete()
        messages.success(request, "Evento eliminado.")
    return redirect('calendario')     

# 5. MEDICAMENTOS
@login_required
def nuevo_medicamento(request):
    if request.method == 'POST':
        form = MedicamentoForm(request.POST)
        if form.is_valid():
            med = form.save(commit=False)
            
            # --- PROCESAMIENTO DE DATOS DEL FORM ORIGINAL ---
            dosis = form.cleaned_data.get('dosis') or ""
            horario = form.cleaned_data.get('horario') or ""
            cada = form.cleaned_data.get('cada_cuantas_horas') or ""
            
            # Guardamos la combinación en el campo 'frecuencia'
            med.frecuencia = f"{dosis} - {horario} (Cada {cada}hs)".strip(" - (Cada hs)")
            
            # Mapeamos stock_inicial (del form) a stock_total (del modelo)
            if form.cleaned_data.get('stock_inicial'):
                med.stock_total = form.cleaned_data.get('stock_inicial')
            
            # Asignación automática del paciente
            paciente_perfil = PerfilPaciente.objects.filter(tutor=request.user).first()
            med.paciente = paciente_perfil.user if paciente_perfil else request.user
            
            med.save()
            messages.success(request, "Medicamento guardado correctamente.")
            return redirect('dashboard')
        else:
            messages.error(request, "Error en el formulario. Verifique los datos.")
    else:
        form = MedicamentoForm()
    
    return render(request, 'core/nuevo_medicamento.html', {'form': form})

@login_required
def reponer_caja(request, pk):
    if request.method == 'POST':
        m = get_object_or_404(Medicamento, pk=pk)
        # Reponemos al total definido en la caja
        m.stock_actual = m.stock_total if m.stock_total else 30
        m.save()
        messages.success(request, f"Stock de {m.nombre} repuesto.")
    return redirect('dashboard')

@login_required
def eliminar_medicamento(request, pk):
    if request.method == 'POST':
        get_object_or_404(Medicamento, pk=pk).delete()
        messages.success(request, "Medicamento eliminado.")
    return redirect('dashboard')

# ========== PERFILES ==========

@login_required
def perfil_tutor(request):
    """Página de perfil del tutor (Luis) con gestión de pacientes"""
    # Obtener todos los pacientes del tutor
    pacientes = PerfilPaciente.objects.filter(tutor=request.user)
    
    return render(request, 'core/perfil_tutor.html', {
        'user': request.user,
        'pacientes': pacientes
    })

@login_required
def perfil_paciente(request):
    """Página de perfil del paciente con datos médicos"""
    # Obtener paciente del parámetro o de la sesión/primer paciente
    paciente_id = request.GET.get('id')
    
    if paciente_id:
        perfil = get_object_or_404(PerfilPaciente, id=paciente_id, tutor=request.user)
    else:
        # Si es tutor, ve el paciente seleccionado o el primero
        paciente_id_sesion = request.session.get('paciente_seleccionado')
        if paciente_id_sesion:
            perfil = PerfilPaciente.objects.filter(id=paciente_id_sesion, tutor=request.user).first()
        else:
            perfil = PerfilPaciente.objects.filter(tutor=request.user).first()
        
        # Si es paciente, ve su propio perfil
        if not perfil:
            perfil = PerfilPaciente.objects.filter(user=request.user).first()
    
    if not perfil:
        messages.error(request, "Perfil no encontrado")
        return redirect('dashboard')
    
    return render(request, 'core/perfil_paciente.html', {
        'perfil': perfil,
        'paciente': perfil.user
    })

# ========== MEDICIONES ==========

@login_required
def mediciones(request):
    """Ver historial de mediciones del paciente"""
    paciente_a_cargo = PerfilPaciente.objects.filter(tutor=request.user).first()
    perfil_propio = PerfilPaciente.objects.filter(user=request.user).first()
    
    perfil = paciente_a_cargo or perfil_propio
    
    if not perfil:
        messages.error(request, "Perfil no encontrado")
        return redirect('dashboard')
    
    # Mediciones por tipo
    mediciones_presion = DatoMedicion.objects.filter(
        paciente=perfil.user, 
        tipo='presion'
    ).order_by('-fecha_registro')[:30]
    
    mediciones_peso = DatoMedicion.objects.filter(
        paciente=perfil.user, 
        tipo='peso'
    ).order_by('-fecha_registro')[:30]
    
    mediciones_glucosa = DatoMedicion.objects.filter(
        paciente=perfil.user, 
        tipo='glucosa'
    ).order_by('-fecha_registro')[:30]
    
    return render(request, 'core/mediciones.html', {
        'perfil': perfil,
        'mediciones_presion': mediciones_presion,
        'mediciones_peso': mediciones_peso,
        'mediciones_glucosa': mediciones_glucosa,
    })

@login_required
def fotos_mediciones(request):
    """Ver documentos (fotos de mediciones, recetas, indicaciones, etc)"""
    # Obtener el paciente seleccionado en sesión o el primero
    paciente_id_sesion = request.session.get('paciente_seleccionado')
    if paciente_id_sesion:
        paciente_a_cargo = PerfilPaciente.objects.filter(id=paciente_id_sesion, tutor=request.user).first()
    else:
        paciente_a_cargo = PerfilPaciente.objects.filter(tutor=request.user).first()
    
    if not paciente_a_cargo:
        messages.error(request, "Solo tutores pueden ver documentos")
        return redirect('dashboard')
    
    # Filtrar por tipo de documento si se especifica
    tipo_filtro = request.GET.get('tipo', '')
    
    # Documentos pendientes de procesar
    fotos_pendientes = FotoDocumento.objects.filter(
        paciente=paciente_a_cargo.user,
        procesada=False
    )
    if tipo_filtro:
        fotos_pendientes = fotos_pendientes.filter(tipo=tipo_filtro)
    fotos_pendientes = fotos_pendientes.order_by('-fecha_subida')
    
    # Documentos ya procesados
    fotos_procesadas = FotoDocumento.objects.filter(
        paciente=paciente_a_cargo.user,
        procesada=True
    )
    if tipo_filtro:
        fotos_procesadas = fotos_procesadas.filter(tipo=tipo_filtro)
    fotos_procesadas = fotos_procesadas.order_by('-fecha_subida')[:20]
    
    return render(request, 'core/fotos_mediciones.html', {
        'perfil': paciente_a_cargo,
        'fotos_pendientes': fotos_pendientes,
        'fotos_procesadas': fotos_procesadas,
        'tipo_filtro': tipo_filtro,
    })

@login_required
def cargar_dato_medicion(request, foto_id):
    """Cargar datos numéricos desde una foto de medición"""
    foto = get_object_or_404(FotoDocumento, pk=foto_id, tipo='medicion')
    
    # Validar que el usuario sea el tutor de este paciente
    if foto.paciente.perfilpaciente_set.first().tutor != request.user:
        messages.error(request, "No tienes permisos para esto")
        return redirect('mediciones')
    
    if request.method == 'POST':
        tipo = request.POST.get('tipo')  # presion, peso, glucosa
        valor_1 = request.POST.get('valor_1')
        valor_2 = request.POST.get('valor_2')
        observaciones = request.POST.get('observaciones')
        
        if tipo and valor_1:
            DatoMedicion.objects.create(
                paciente=foto.paciente,
                tipo=tipo,
                valor_1=float(valor_1),
                valor_2=float(valor_2) if valor_2 else None,
                observaciones=observaciones
            )
            
            # Marcar foto como procesada
            foto.procesada = True
            foto.comentario_luis = f"Datos {tipo} cargados"
            foto.save()
            
            messages.success(request, "Datos cargados correctamente")
            return redirect('fotos_mediciones')
    
    return render(request, 'core/cargar_dato.html', {
        'foto': foto
    })

@login_required
def seleccionar_paciente(request, paciente_id):
    """Cambiar paciente activo en la sesión"""
    paciente = get_object_or_404(PerfilPaciente, id=paciente_id, tutor=request.user)
    request.session['paciente_seleccionado'] = paciente.id
    messages.success(request, f"Paciente: {paciente.user.first_name} seleccionado")
    return redirect('dashboard')