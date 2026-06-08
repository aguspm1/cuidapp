from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views
 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('registro/', views.registro, name='registro'),
    path('', views.dashboard, name='dashboard'),
    path('editar-perfil/<int:paciente_id>/', views.editar_perfil, name='editar_perfil'),
 
    # Medicamentos
    path('nuevo-medicamento/', views.nuevo_medicamento, name='nuevo_medicamento'),
    path('registrar-toma/<int:medicamento_id>/', views.registrar_toma, name='registrar_toma'),
    path('reponer-medicamento/<int:medicamento_id>/', views.reponer_medicamento, name='reponer_medicamento'),
    path('editar-medicamento/<int:pk>/', views.editar_medicamento, name='editar_medicamento'),
    path('eliminar-medicamento/<int:pk>/', views.eliminar_medicamento, name='eliminar_medicamento'),
    path('historial-tomas/', views.historial_tomas, name='historial_tomas'),
    path('notif/leidas/', views.marcar_notif_leidas, name='marcar_notif_leidas'),

 
    # Calendario
    path('calendario/', views.calendario_eventos, name='calendario'),
    path('calendario/nuevo/', views.nuevo_evento, name='nuevo_evento'),
    path('calendario/editar/<int:pk>/', views.editar_evento, name='editar_evento'),
    path('calendario/eliminar/<int:pk>/', views.eliminar_evento, name='eliminar_evento'),
 
    # Vinculación
    path('vincular/', views.vincular_paciente, name='vincular_paciente'),
 
    # Perfiles
    path('perfil/tutor/', views.perfil_tutor, name='perfil_tutor'),
    path('perfil/paciente/', views.perfil_paciente, name='perfil_paciente'),
    path('paciente/seleccionar/<int:paciente_id>/', views.seleccionar_paciente, name='seleccionar_paciente'),
 
    # Mediciones y Fotos
    path('mediciones/', views.mediciones, name='mediciones'),
    path('fotos-mediciones/', views.fotos_mediciones, name='fotos_mediciones'),
    path('fotos-mediciones/subir/', views.subir_foto, name='subir_foto'),
    path('fotos-mediciones/<int:foto_id>/cargar/', views.cargar_dato_medicion, name='cargar_dato'),
    path('fotos-mediciones/<int:foto_id>/procesar/', views.procesar_documento, name='procesar_documento'),
    path('fotos-mediciones/<int:foto_id>/rechazar/', views.rechazar_documento, name='rechazar_documento'),
 
# Sirve archivos de media (imágenes/PDFs subidos) en modo desarrollo
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)