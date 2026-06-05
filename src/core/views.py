from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from .models import Medicamento, EventoCalendario, PerfilPaciente, FotoDocumento, DatoMedicion, RegistroToma
from .forms import RegistroForm, MedicamentoForm, PerfilPacienteForm


# ========== HELPERS DE PERMISOS ==========

def es_tutor(user):
    """Devuelve True si el usuario es tutor de al menos un paciente"""
    return PerfilPaciente.objects.filter(tutor=user).exists()

def es_paciente(user):
    """Devuelve True si el usuario tiene perfil de paciente"""
    return PerfilPaciente.objects.filter(user=user).exists()

def solo_tutor(request):
    """Shortcut: redirige con error si el usuario NO es tutor"""
    if not es_tutor(request.user):
        messages.error(request, "❌ Solo los tutores pueden realizar esta acción.")
        return True
    return False


# ========== 1. DASHBOARD ==========
@login_required
def dashboard(request):
    remedios = []
    eventos_proximos = []
    nombre_paciente = "Sin vincular"
    pacientes_a_cargo_list = []
    paciente_a_cargo = None

    pacientes_a_cargo_list = PerfilPaciente.objects.filter(tutor=request.user)

    paciente_id = request.session.get('paciente_seleccionado')
    if paciente_id:
        try:
            paciente_a_cargo = PerfilPaciente.objects.get(id=paciente_id, tutor=request.user)
        except PerfilPaciente.DoesNotExist:
            paciente_a_cargo = pacientes_a_cargo_list.first()
    else:
        paciente_a_cargo = pacientes_a_cargo_list.first()

    perfil_propio = PerfilPaciente.objects.filter(user=request.user).first()

    if paciente_a_cargo:
        target_user = paciente_a_cargo.user
        nombre_paciente = target_user.first_name or target_user.username
    elif perfil_propio:
        target_user = request.user
        nombre_paciente = "Mi Perfil"
    else:
        target_user = None

    if target_user:
        remedios = Medicamento.objects.filter(paciente=target_user)
        for r in remedios:
            r.porcentaje_stock = int((r.stock_actual / r.stock_total) * 100) if r.stock_total else 0
        eventos_proximos = EventoCalendario.objects.filter(
            paciente=target_user,
            fecha_hora__gte=timezone.now()
        ).order_by('fecha_hora')

    return render(request, 'core/dashboard.html', {
        'remedios': remedios,
        'eventos_proximos': eventos_proximos,
        'nombre_anciano': nombre_paciente,
        'pacientes_list': pacientes_a_cargo_list,
        'paciente_actual': paciente_a_cargo,
        'es_tutor': es_tutor(request.user),   # útil en templates para mostrar/ocultar botones
    })


# ========== 2. REGISTRO ==========
def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            PerfilPaciente.objects.create(user=user)
            messages.success(request, "¡Cuenta creada correctamente!")
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


# ========== 4. CALENDARIO ==========
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
    if solo_tutor(request):
        return redirect('dashboard')

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
def editar_evento(request, pk):
    if solo_tutor(request):
        return redirect('dashboard')

    evento = get_object_or_404(EventoCalendario, pk=pk)
    perfil = PerfilPaciente.objects.filter(user=evento.paciente).first()
    if not perfil or perfil.tutor != request.user:
        messages.error(request, "❌ No tenés permisos para editar este evento.")
        return redirect('calendario')

    nombre = evento.paciente.get_full_name() or evento.paciente.username

    if request.method == 'POST':
        evento.titulo      = request.POST.get('titulo')
        evento.fecha_hora  = request.POST.get('fecha_hora')
        evento.descripcion = request.POST.get('descripcion', '')
        evento.tipo        = request.POST.get('tipo', 'otro')
        evento.lugar       = request.POST.get('lugar', '')
        evento.save()
        messages.success(request, "✅ Evento actualizado correctamente.")
        return redirect('calendario')

    return render(request, 'core/nuevo_evento.html', {
        'nombre_anciano': nombre,
        'evento': evento,
    })

@login_required
def eliminar_evento(request, pk):
    if solo_tutor(request):
        return redirect('dashboard')

    if request.method == 'POST':
        evento = get_object_or_404(EventoCalendario, pk=pk)
        perfil = PerfilPaciente.objects.filter(user=evento.paciente).first()
        if not perfil or perfil.tutor != request.user:
            messages.error(request, "❌ No tenés permisos.")
            return redirect('calendario')
        evento.delete()
        messages.success(request, "✅ Evento eliminado.")
    return redirect('calendario')


# ========== 5. MEDICAMENTOS ==========
@login_required
def nuevo_medicamento(request):
    if solo_tutor(request):
        return redirect('dashboard')

    if request.method == 'POST':
        print("POST horario_fijo:", request.POST.get("horario_fijo"))
        print("POST frecuencia_tipo:", request.POST.get("frecuencia_tipo"))
        form = MedicamentoForm(request.POST)
        if form.is_valid():
            med = form.save(commit=False)
            paciente_perfil = PerfilPaciente.objects.filter(tutor=request.user).first()
            if not paciente_perfil:
                messages.error(request, "❌ No tenés pacientes asignados.")
                return redirect('dashboard')
            med.paciente = paciente_perfil.user
            med.save()
            messages.success(request, f"✅ {med.nombre} guardado correctamente.")
            return redirect('dashboard')
        else:
            messages.error(request, "❌ Error en el formulario.")
    else:
        form = MedicamentoForm()

    return render(request, 'core/nuevo_medicamento.html', {'form': form})

@login_required
def registrar_toma(request, medicamento_id):
    """Solo el propio paciente puede registrar sus tomas"""
    if request.method == 'POST':
        # get_object_or_404 con paciente=request.user garantiza que solo el dueño puede registrar
        med = get_object_or_404(Medicamento, pk=medicamento_id, paciente=request.user)
        RegistroToma.objects.create(
            medicamento=med,
            paciente=request.user,
            cantidad_tomada=med.dosis_por_toma
        )
        med.stock_actual -= med.dosis_por_toma
        med.save()
        if med.tiene_stock_bajo():
            messages.warning(request, f"⚠️ Stock bajo: {med.nombre} - Quedan {med.tomas_restantes()} tomas.")
        else:
            messages.success(request, f"✅ Toma registrada: {med.nombre}.")
        return redirect('dashboard')
    return redirect('dashboard')

@login_required
def reponer_medicamento(request, medicamento_id):
    """Repone el stock completo del medicamento (una caja entera)"""
    if solo_tutor(request):
        return redirect('dashboard')

    med = get_object_or_404(Medicamento, pk=medicamento_id)
    get_object_or_404(PerfilPaciente, tutor=request.user, user=med.paciente)

    if request.method == 'POST':
        med.stock_actual = med.stock_total
        med.save()
        messages.success(request, f"✅ Stock repuesto: {med.nombre} ({med.stock_total} {med.unidad_medida}).")
    return redirect('dashboard')

@login_required
def eliminar_medicamento(request, pk):
    """Solo el tutor puede eliminar medicamentos de sus pacientes"""
    if solo_tutor(request):
        return redirect('dashboard')

    med = get_object_or_404(Medicamento, pk=pk)
    # Verifica que el medicamento sea de un paciente de ESTE tutor
    get_object_or_404(PerfilPaciente, tutor=request.user, user=med.paciente)

    if request.method == 'POST':
        med.delete()
        messages.success(request, "✅ Medicamento eliminado.")
    return redirect('dashboard')


# ========== 6. PERFILES ==========
@login_required
def perfil_tutor(request):
    pacientes = PerfilPaciente.objects.filter(tutor=request.user)
    return render(request, 'core/perfil_tutor.html', {
        'user': request.user,
        'pacientes': pacientes
    })

@login_required
def perfil_paciente(request):
    paciente_id = request.GET.get('id')

    if paciente_id:
        perfil = get_object_or_404(PerfilPaciente, id=paciente_id, tutor=request.user)
    else:
        paciente_id_sesion = request.session.get('paciente_seleccionado')
        if paciente_id_sesion:
            perfil = PerfilPaciente.objects.filter(id=paciente_id_sesion, tutor=request.user).first()
        else:
            perfil = PerfilPaciente.objects.filter(tutor=request.user).first()
        if not perfil:
            perfil = PerfilPaciente.objects.filter(user=request.user).first()

    if not perfil:
        messages.error(request, "❌ Perfil no encontrado.")
        return redirect('dashboard')

    return render(request, 'core/perfil_paciente.html', {
        'perfil':   perfil,
        'paciente': perfil.user,
        'es_tutor': perfil.tutor == request.user,
    })

@login_required
def seleccionar_paciente(request, paciente_id):
    paciente = get_object_or_404(PerfilPaciente, id=paciente_id, tutor=request.user)
    request.session['paciente_seleccionado'] = paciente.id
    messages.success(request, f"✅ Paciente seleccionado: {paciente.user.first_name}")
    return redirect('dashboard')

@login_required
def editar_perfil(request, paciente_id):
    """Solo el tutor puede editar el perfil del paciente"""
    if solo_tutor(request):
        return redirect('dashboard')

    perfil = get_object_or_404(PerfilPaciente, id=paciente_id, tutor=request.user)

    if request.method == 'POST':
        form = PerfilPacienteForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Perfil actualizado correctamente.")
            return redirect(f'/perfil/paciente/?id={perfil.id}')
    else:
        form = PerfilPacienteForm(instance=perfil)

    return render(request, 'core/editar_perfil.html', {
        'form':     form,
        'perfil':   perfil,
        'paciente': perfil.user
    })


# ========== 7. MEDICIONES ==========
@login_required
def mediciones(request):
    paciente_a_cargo = PerfilPaciente.objects.filter(tutor=request.user).first()
    perfil_propio    = PerfilPaciente.objects.filter(user=request.user).first()
    perfil = paciente_a_cargo or perfil_propio

    if not perfil:
        messages.error(request, "❌ Perfil no encontrado.")
        return redirect('dashboard')

    mediciones_presion = DatoMedicion.objects.filter(
        paciente=perfil.user, tipo='presion').order_by('-fecha_registro')[:30]
    mediciones_peso    = DatoMedicion.objects.filter(
        paciente=perfil.user, tipo='peso').order_by('-fecha_registro')[:30]
    mediciones_glucosa = DatoMedicion.objects.filter(
        paciente=perfil.user, tipo='glucosa').order_by('-fecha_registro')[:30]

    return render(request, 'core/mediciones.html', {
        'perfil': perfil,
        'mediciones_presion': mediciones_presion,
        'mediciones_peso':    mediciones_peso,
        'mediciones_glucosa': mediciones_glucosa,
    })

@login_required
def fotos_mediciones(request):
    if solo_tutor(request):
        return redirect('dashboard')

    paciente_id_sesion = request.session.get('paciente_seleccionado')
    if paciente_id_sesion:
        paciente_a_cargo = PerfilPaciente.objects.filter(id=paciente_id_sesion, tutor=request.user).first()
    else:
        paciente_a_cargo = PerfilPaciente.objects.filter(tutor=request.user).first()

    if not paciente_a_cargo:
        messages.error(request, "❌ No tenés pacientes asignados.")
        return redirect('dashboard')

    tipo_filtro = request.GET.get('tipo', '')

    fotos_pendientes = FotoDocumento.objects.filter(paciente=paciente_a_cargo.user, procesada=False)
    if tipo_filtro:
        fotos_pendientes = fotos_pendientes.filter(tipo=tipo_filtro)
    fotos_pendientes = fotos_pendientes.order_by('-fecha_subida')

    fotos_procesadas = FotoDocumento.objects.filter(paciente=paciente_a_cargo.user, procesada=True)
    if tipo_filtro:
        fotos_procesadas = fotos_procesadas.filter(tipo=tipo_filtro)
    fotos_procesadas = fotos_procesadas.order_by('-fecha_subida')[:20]

    return render(request, 'core/fotos_mediciones.html', {
        'perfil':           paciente_a_cargo,
        'fotos_pendientes': fotos_pendientes,
        'fotos_procesadas': fotos_procesadas,
        'tipo_filtro':      tipo_filtro,
    })

@login_required
def cargar_dato_medicion(request, foto_id):
    if solo_tutor(request):
        return redirect('dashboard')

    foto = get_object_or_404(FotoDocumento, pk=foto_id, tipo='medicion')
    perfil = foto.paciente.perfilpaciente_set.first()
    if not perfil or perfil.tutor != request.user:
        messages.error(request, "❌ No tenés permisos.")
        return redirect('fotos_mediciones')

    if request.method == 'POST':
        tipo   = request.POST.get('tipo')
        valor1 = request.POST.get('valor_1')
        valor2 = request.POST.get('valor_2')
        obs    = request.POST.get('observaciones')

        if tipo and valor1:
            DatoMedicion.objects.create(
                paciente      = foto.paciente,
                tipo          = tipo,
                valor_1       = float(valor1),
                valor_2       = float(valor2) if valor2 else None,
                observaciones = obs
            )
            foto.procesada       = True
            foto.comentario_luis = f"Datos {tipo} cargados"
            foto.save()
            messages.success(request, "✅ Datos cargados correctamente.")
            return redirect('fotos_mediciones')

    return render(request, 'core/cargar_dato.html', {'foto': foto})