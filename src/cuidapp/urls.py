# En src/cuidapp/urls.py
from django.contrib import admin
from django.urls import path, include
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('registro/', views.registro, name='registro'),
    path('', views.dashboard, name='dashboard'),
    
    # Medicamentos
    path('nuevo-remedio/', views.nuevo_medicamento, name='nuevo_medicamento'),
    path('reponer/<int:pk>/', views.reponer_caja, name='reponer_caja'),
    path('eliminar-medicamento/<int:pk>/', views.eliminar_medicamento, name='eliminar_medicamento'),
    
    # Calendario
    path('calendario/', views.calendario_eventos, name='calendario'),
    path('calendario/nuevo/', views.nuevo_evento, name='nuevo_evento'),
    path('calendario/eliminar/<int:pk>/', views.eliminar_evento, name='eliminar_evento'),
    
    # Vinculación
    path('vincular/', views.vincular_anciano, name='vincular_anciano'),
    
    # Perfiles
    path('perfil/tutor/', views.perfil_tutor, name='perfil_tutor'),
    path('perfil/paciente/', views.perfil_paciente, name='perfil_paciente'),
    path('paciente/seleccionar/<int:paciente_id>/', views.seleccionar_paciente, name='seleccionar_paciente'),
    
    # Mediciones
    path('mediciones/', views.mediciones, name='mediciones'),
    path('fotos-mediciones/', views.fotos_mediciones, name='fotos_mediciones'),
    path('fotos-mediciones/<int:foto_id>/cargar/', views.cargar_dato_medicion, name='cargar_dato'),
]