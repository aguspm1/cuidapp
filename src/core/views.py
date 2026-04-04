from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Medicamento, Turno, Perfil
from django.utils import timezone
from .forms import RegistroForm, MedicamentoForm

@login_required
def dashboard(request):
    perfil = getattr(request.user, 'perfil', None)
    
    remedios = []
    turnos = []
    remedios_criticos = []
    nombre_anciano = "No vinculado"

    if perfil:
        if perfil.rol == 'tutor':
            # Buscamos al anciano vinculado
            anciano_vinculado = Perfil.objects.filter(tutor_asignado=request.user, rol='anciano').first()
            
            if anciano_vinculado:
                remedios = Medicamento.objects.filter(perfil=anciano_vinculado)
                turnos = Turno.objects.filter(perfil=anciano_vinculado)[:3]
                nombre_anciano = anciano_vinculado.user.get_full_name() or anciano_vinculado.user.username
        
        else: # Si el logueado es el Anciano (Ana)
            remedios = Medicamento.objects.filter(perfil=perfil)
            turnos = Turno.objects.filter(perfil=perfil)[:3]
            nombre_anciano = request.user.get_full_name() or request.user.username

        # LÓGICA INTELIGENTE: Comparamos stock_actual contra el stock_critico de cada remedio
        remedios_criticos = [r for r in remedios if r.stock_actual <= r.stock_critico]

    context = {
        'remedios': remedios,
        'turnos': turnos,
        'bajo_stock': len(remedios_criticos) > 0,
        'lista_bajo_stock': remedios_criticos,
        'perfil': perfil,
        'nombre_anciano': nombre_anciano
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def vincular_anciano(request):
    if request.method == 'POST':
        username_buscado = request.POST.get('username_anciano')
        try:
            user_anciano = User.objects.get(username=username_buscado)
            perfil_anciano = user_anciano.perfil
            
            if perfil_anciano.rol == 'anciano':
                perfil_anciano.tutor_asignado = request.user
                perfil_anciano.save()
                messages.success(request, f"¡Vinculación exitosa con {user_anciano.username}!")
                return redirect('dashboard')
            else:
                messages.error(request, "Ese usuario no es un perfil de Adulto Mayor.")
        except (User.DoesNotExist, Perfil.DoesNotExist):
            messages.error(request, "El nombre de usuario no existe.")
            
    return render(request, 'core/vincular.html')

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            Perfil.objects.create(user=user, rol=form.cleaned_data.get('rol'))
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'registration/registro.html', {'form': form})

@login_required
def nuevo_medicamento(request):
    if request.method == 'POST':
        form = MedicamentoForm(request.POST)
        if form.is_valid():
            medicamento = form.save(commit=False)
            # Buscamos a quién cuidar
            perfil_target = None
            if request.user.perfil.rol == 'tutor':
                perfil_target = Perfil.objects.filter(tutor_asignado=request.user, rol='anciano').first()
            else:
                perfil_target = request.user.perfil

            if perfil_target:
                medicamento.perfil = perfil_target
                medicamento.save()
                messages.success(request, "Medicamento guardado correctamente.")
                return redirect('dashboard')
            else:
                messages.error(request, "Debes vincular a un adulto mayor primero.")
    else:
        form = MedicamentoForm()
    
    return render(request, 'core/nuevo_medicamento.html', {'form': form})

@login_required
def reponer_caja(request, pk):
    """Suma stock_inicial al stock_actual con un solo clic"""
    if request.method == 'POST':
        medicamento = get_object_or_404(Medicamento, pk=pk)
        medicamento.reponer_stock()
        messages.success(request, f"Se repuso el stock de {medicamento.nombre}.")
    return redirect('dashboard')

def eliminar_medicamento(request, pk):
    """Elimina un medicamento del plan de Ana"""
    medicamento = get_object_or_404(Medicamento, pk=pk)
    
    # Verificamos que Luis solo pueda eliminar los de su anciano vinculado
    if request.method == 'POST':
        nombre_eliminado = medicamento.nombre
        medicamento.delete()
        messages.success(request, f"Se eliminó '{nombre_eliminado}' del plan correctamente.")
        
    return redirect('dashboard')