# En src/cuidapp/urls.py
from django.contrib import admin
from django.urls import path, include
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('registro/', views.registro, name='registro'), # Nueva ruta
    path('', views.dashboard, name='dashboard'),
    path('nuevo-remedio/', views.nuevo_medicamento, name='nuevo_medicamento'),
    path('vincular/', views.vincular_anciano, name='vincular_anciano'),
    path('reponer/<int:pk>/', views.reponer_caja, name='reponer_caja'),
    path('eliminar-medicamento/<int:pk>/', views.eliminar_medicamento, name='eliminar_medicamento'),
]