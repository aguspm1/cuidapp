from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from .models import Medicamento, EventoCalendario, PerfilPaciente, FotoDocumento, DatoMedicion, RegistroToma
from .forms import RegistroForm, MedicamentoForm, PerfilPacienteForm

# ========== 1. DASHBOARD PRINCIPAL ==========
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

# ========== 2. REGISTRO DE USUARIOS ==========
def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Creamos el perfil de paciente automáticamente al registrarse
            PerfilPaciente.objects.create(user=user)
            messages.success(request, f"¡Cuenta creada!")
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'registration/registro.html', {'form': form})

# ========== 3. VINCULACIÓN ==========
@login_required
def vincular_anciano(request):
    if request.method == 'POST':
        user_buscado = request.POST.get('username_anciano')
        try:
            anciano_user = User.objects.get(username=user_buscado)
            perfil = PerfilPaciente.objects.get(user=anciano_user)
            perfil.tutor = request.user
            perfil.save()
            messages.success(request, f"✅ Vinculado con éxito a {user_buscado}")
            return redirect('dashboard')
        except User.DoesNotExist:
            messages.error(request, "❌ No se encontró el usuario")
        except PerfilPaciente.DoesNotExist:
            messages.error(request, "❌ El usuario no tiene perfil creado")
    return render(request, 'core/vincular.html')

# ========== 4. EVENTOS Y CALENDARIO ==========
@login_required
def calendario_eventos(request):
    paciente_perfil = PerfilPaciente.objects.filter(tutor=request.user).first()
    target = paciente_perfil.user if paciente_perfil else request.user
    nombre = target.get_full_name() or target.username
 
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
            tipo        = request.POST.get('tipo', 'otro'),
            lugar       = request.POST.get('lugar', ''),
        )
        messages.success(request, "✅ Evento agendado correctamente.")
        return redirect('calendario')
 
    return render(request, 'core/nuevo_evento.html', {'nombre_anciano': nombre})

@login_required
def eliminar_evento(request, pk):
    if request.method == 'POST':
        evento = get_object_or_404(EventoCalendario, pk=pk)
        perfil = PerfilPaciente.objects.get(user=evento.paciente)
        if perfil.tutor != request.user:
            messages.error(request, "❌ No tienes permisos")
            return redirect('calendario')
        
        evento.delete()
        messages.success(request, "✅ Evento eliminado.")
    return redirect('calendario')

# ========== 5. MEDICAMENTOS ==========
@login_required
def nuevo_medicamento(request):
    if request.method == 'POST':
        form = MedicamentoForm(request.POST)
        if form.is_valid():
            med = form.save(commit=False)
            
            # Asignar paciente
            paciente_perfil = PerfilPaciente.objects.filter(tutor=request.user).first()
            if not paciente_perfil:
                messages.error(request, "❌ No tienes pacientes asignados")
                return redirect('dashboard')
            
            med.paciente = paciente_perfil.user
            med.save()
            
            messages.success(request, f"✅ {med.nombre} guardado correctamente")
            return redirect('dashboard')
        else:
            messages.error(request, "❌ Error en el formulario")
    else:
        form = MedicamentoForm()
    
    return render(request, 'core/nuevo_medicamento.html', {'form': form})

@login_required
def registrar_toma(request, medicamento_id):
    """Paciente registra que tomó el medicamento"""
    if request.method == 'POST':
        med = get_object_or_404(Medicamento, pk=medicamento_id, paciente=request.user)
        
        # Crear registro inmutable
        RegistroToma.objects.create(
            medicamento=med,
            paciente=request.user,
            cantidad_tomada=med.dosis_por_toma
        )
        
        # Descontar stock
        med.stock_actual -= med.dosis_por_toma
        med.save()
        
        # Verificar alerta de stock bajo
        if med.tiene_stock_bajo():
            messages.warning(
                request, 
                f"⚠️ Stock bajo: {med.nombre} - Quedan {med.tomas_restantes()} tomas"
            )
        else:
            messages.success(request, f"✅ Toma registrada: {med.nombre}")
        
        return redirect('dashboard')
    
    return redirect('dashboard')

@login_required
def reponer_medicamento(request, medicamento_id):
    """Tutor repone stock del medicamento"""
    med = get_object_or_404(Medicamento, pk=medicamento_id)
    perfil = get_object_or_404(PerfilPaciente, tutor=request.user, user=med.paciente)
    
    if request.method == 'POST':
        cantidad = request.POST.get('cantidad')
        if cantidad:
            try:
                cantidad = int(cantidad)
                med.stock_actual += cantidad
                med.save()
                messages.success(request, f"✅ Reposición: +{cantidad} {med.unidad_medida}")
            except ValueError:
                messages.error(request, "❌ Cantidad inválida")
        return redirect('dashboard')
    
    return render(request, 'core/reponer_medicamento.html', {'medicamento': med})

@login_required
def eliminar_medicamento(request, pk):
    if request.method == 'POST':
        get_object_or_404(Medicamento, pk=pk).delete()
        messages.success(request, "✅ Medicamento eliminado.")
    return redirect('dashboard')

# ========== 6. PERFILES ==========
@login_required
def perfil_tutor(request):
    """Página de perfil del tutor (Luis) con gestión de pacientes"""
    pacientes = PerfilPaciente.objects.filter(tutor=request.user)
    return render(request, 'core/perfil_tutor.html', {
        'user': request.user,
        'pacientes': pacientes
    })

@login_required
def perfil_paciente(request):
    """Página de perfil del paciente con datos médicos"""
    paciente_id = request.GET.get('id')
    
    if paciente_id:
        perfil = get_object_or_404(PerfilPaciente, id=paciente_id, tutor=request.user)
    else:
        # Si es tutor
        paciente_id_sesion = request.session.get('paciente_seleccionado')
        if paciente_id_sesion:
            perfil = PerfilPaciente.objects.filter(id=paciente_id_sesion, tutor=request.user).first()
        else:
            perfil = PerfilPaciente.objects.filter(tutor=request.user).first()
        
        # Si es paciente
        if not perfil:
            perfil = PerfilPaciente.objects.filter(user=request.user).first()
    
    if not perfil:
        messages.error(request, "❌ Perfil no encontrado")
        return redirect('dashboard')
    
    return render(request, 'core/perfil_paciente.html', {
        'perfil': perfil,
        'paciente': perfil.user
    })

@login_required
def seleccionar_paciente(request, paciente_id):
    """Cambiar paciente activo en la sesión"""
    paciente = get_object_or_404(PerfilPaciente, id=paciente_id, tutor=request.user)
    request.session['paciente_seleccionado'] = paciente.id
    messages.success(request, f"✅ Paciente seleccionado: {paciente.user.first_name}")
    return redirect('dashboard')

@login_required
def editar_perfil(request, paciente_id):
    """Editar perfil del paciente - Solo el tutor puede hacerlo"""
    perfil = get_object_or_404(PerfilPaciente, id=paciente_id, tutor=request.user)
    
    if request.method == 'POST':
        form = PerfilPacienteForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Perfil actualizado correctamente")
            return redirect(f'/perfil/paciente/?id={perfil.id}')
    else:
        form = PerfilPacienteForm(instance=perfil)
    
    return render(request, 'core/editar_perfil.html', {
        'form': form,
        'perfil': perfil,
        'paciente': perfil.user
    })

# ========== 7. MEDICIONES ==========
@login_required
def mediciones(request):
    """Ver historial de mediciones del paciente"""
    paciente_a_cargo = PerfilPaciente.objects.filter(tutor=request.user).first()
    perfil_propio = PerfilPaciente.objects.filter(user=request.user).first()
    
    perfil = paciente_a_cargo or perfil_propio
    
    if not perfil:
        messages.error(request, "❌ Perfil no encontrado")
        return redirect('dashboard')
    
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
    paciente_id_sesion = request.session.get('paciente_seleccionado')
    if paciente_id_sesion:
        paciente_a_cargo = PerfilPaciente.objects.filter(id=paciente_id_sesion, tutor=request.user).first()
    else:
        paciente_a_cargo = PerfilPaciente.objects.filter(tutor=request.user).first()
    
    if not paciente_a_cargo:
        messages.error(request, "❌ Solo tutores pueden ver documentos")
        return redirect('dashboard')
    
    tipo_filtro = request.GET.get('tipo', '')
    
    # Documentos pendientes
    fotos_pendientes = FotoDocumento.objects.filter(
        paciente=paciente_a_cargo.user,
        procesada=False
    )
    if tipo_filtro:
        fotos_pendientes = fotos_pendientes.filter(tipo=tipo_filtro)
    fotos_pendientes = fotos_pendientes.order_by('-fecha_subida')
    
    # Documentos procesados
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
    
    if foto.paciente.perfilpaciente_set.first().tutor != request.user:
        messages.error(request, "❌ No tienes permisos")
        return redirect('mediciones')
    
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
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
            
            foto.procesada = True
            foto.comentario_luis = f"Datos {tipo} cargados"
            foto.save()
            
            messages.success(request, "✅ Datos cargados correctamente")
            return redirect('fotos_mediciones')
    
    return render(request, 'core/cargar_dato.html', {
        'foto': foto
    })